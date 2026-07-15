"""JWT authentication + user management."""
import os
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr

from deps import get_db, get_current_user, _jwt_secret, JWT_ALGORITHM


router = APIRouter(prefix="/auth", tags=["auth"])


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {"sub": user_id, "email": email, "role": role, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "type": "refresh",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def _set_cookies(response: Response, access: str, refresh: str):
    response.set_cookie("access_token", access, httponly=True, secure=True,
                        samesite="none", max_age=8 * 3600, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True,
                        samesite="none", max_age=7 * 86400, path="/")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "maker"
    organisation: str = "Shree Textiles Pvt Ltd"


@router.post("/register")
async def register(body: RegisterIn, response: Response, db=Depends(get_db)):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": body.name,
        "role": body.role,
        "organisation": body.organisation,
        "password_hash": hash_password(body.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    access = create_access_token(user["id"], email, user["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"user": user, "access_token": access}


@router.post("/login")
async def login(body: LoginIn, response: Response, request: Request, db=Depends(get_db)):
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'unknown'}:{email}"
    attempts = await db.login_attempts.find_one({"identifier": ident})
    if attempts and attempts.get("locked_until"):
        locked_until = datetime.fromisoformat(attempts["locked_until"])
        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(429, "Too many failed attempts. Try later.")

    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        # increment failed
        count = (attempts["count"] if attempts else 0) + 1
        update = {"identifier": ident, "count": count,
                  "updated_at": datetime.now(timezone.utc).isoformat()}
        if count >= 5:
            update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": ident}, {"$set": update}, upsert=True)
        raise HTTPException(401, "Invalid credentials")

    await db.login_attempts.delete_one({"identifier": ident})
    access = create_access_token(user["id"], email, user["role"])
    refresh = create_refresh_token(user["id"])
    _set_cookies(response, access, refresh)
    user.pop("password_hash", None)
    user.pop("_id", None)
    return {"user": user, "access_token": access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response, db=Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh token")
    user = await db.users.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    access = create_access_token(user["id"], user["email"], user["role"])
    response.set_cookie("access_token", access, httponly=True, secure=True,
                        samesite="none", max_age=8 * 3600, path="/")
    return {"ok": True}


@router.get("/users")
async def list_users(user=Depends(get_current_user), db=Depends(get_db)):
    if user["role"] not in ("admin", "owner", "auditor"):
        raise HTTPException(403, "Not permitted")
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(200)
    return rows


# ---------- seeding ----------

SEED_USERS = [
    ("admin@vyaparrakshak.in",     "Admin User",       "admin",       "System Administrator"),
    ("owner@vyaparrakshak.in",     "Rajiv Mehta",      "owner",       "Business Owner"),
    ("finance@vyaparrakshak.in",   "Anita Sharma",     "finance",     "Finance Manager"),
    ("maker@vyaparrakshak.in",     "Suresh Kumar",     "maker",       "Payment Maker"),
    ("checker@vyaparrakshak.in",   "Priya Iyer",       "checker",     "Payment Checker"),
    ("procurement@vyaparrakshak.in","Vikram Singh",    "procurement", "Procurement Officer"),
    ("auditor@vyaparrakshak.in",   "Meera Nair",       "auditor",     "Internal Auditor"),
    ("vendor@textilepro.in",       "Arjun Patel",      "vendor",      "Vendor Rep"),
]


async def ensure_indexes(db):
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)


async def seed_users(db):
    default_pw = os.environ.get("ADMIN_PASSWORD", "Owner@123")
    for email, name, role, title in SEED_USERS:
        existing = await db.users.find_one({"email": email})
        if existing is None:
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                "email": email,
                "name": name,
                "role": role,
                "title": title,
                "organisation": "Shree Textiles Pvt Ltd",
                "password_hash": hash_password(default_pw),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

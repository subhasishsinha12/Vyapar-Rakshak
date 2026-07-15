"""Vendor Trust Passport endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_db, get_current_user

router = APIRouter(prefix="/vendors", tags=["vendors"])


class VendorIn(BaseModel):
    name: str
    gstin: Optional[str] = None
    pan: Optional[str] = None
    category: Optional[str] = None
    address: Optional[str] = None
    contacts: list = []
    approved_bank_accounts: list = []


@router.get("")
async def list_vendors(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.vendors.find({}, {"_id": 0}).sort("trust_score", -1).to_list(500)
    return rows


@router.get("/{vendor_id}")
async def get_vendor(vendor_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    v = await db.vendors.find_one({"id": vendor_id}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Vendor not found")
    # attach payments
    payments = await db.payments.find({"vendor_id": vendor_id}, {"_id": 0}).sort("requested_at", -1).to_list(200)
    v["payment_history"] = payments
    return v


@router.post("")
async def create_vendor(body: VendorIn, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner", "procurement", "finance"):
        raise HTTPException(403, "Not permitted")
    v = body.model_dump()
    v["id"] = str(uuid.uuid4())
    v["trust_score"] = 60
    v["blocked"] = False
    v["created_at"] = datetime.now(timezone.utc).isoformat()
    v["average_invoice_amount"] = 0
    v["max_historical_amount"] = 0
    await db.vendors.insert_one(v)
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": v["created_at"], "device": "web", "ip": "10.0.0.1",
        "action": "vendor.create", "entity_type": "vendor", "entity_id": v["id"],
        "previous": None, "new": {"name": v["name"]}, "reason": "New vendor onboarded",
    })
    v.pop("_id", None)
    return v


@router.post("/{vendor_id}/block")
async def block_vendor(vendor_id: str, reason: dict, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner", "finance"):
        raise HTTPException(403, "Not permitted")
    v = await db.vendors.find_one({"id": vendor_id})
    if not v:
        raise HTTPException(404, "Not found")
    await db.vendors.update_one({"id": vendor_id},
                                 {"$set": {"blocked": True, "block_reason": reason.get("reason", "Blocked internally")}})
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": "web", "ip": "10.0.0.1",
        "action": "vendor.block", "entity_type": "vendor", "entity_id": vendor_id,
        "previous": {"blocked": False}, "new": {"blocked": True},
        "reason": reason.get("reason"),
    })
    return {"ok": True}

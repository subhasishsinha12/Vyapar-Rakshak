"""Vendor self-service portal.

Every vendor user is linked to exactly one vendor document via user.vendor_id.
"""
import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pydantic import BaseModel

from deps import get_db, get_current_user

router = APIRouter(prefix="/vendor", tags=["vendor-portal"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/backend/uploads/kyc"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_KYC_KINDS = ["gst_certificate", "pan_card", "cancelled_cheque",
                     "bank_proof", "incorporation", "address_proof", "other"]
MAX_KYC_SIZE = 5 * 1024 * 1024  # 5 MB


async def _get_vendor_for_user(db, user) -> dict:
    if user["role"] != "vendor":
        raise HTTPException(403, "Vendor portal is only for vendor role")
    vid = user.get("vendor_id")
    if not vid:
        raise HTTPException(404, "No vendor profile linked to this user")
    v = await db.vendors.find_one({"id": vid}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Linked vendor profile missing")
    return v


@router.get("/me")
async def me(db=Depends(get_db), user=Depends(get_current_user)):
    v = await _get_vendor_for_user(db, user)
    # bank change requests
    changes = await db.beneficiary_changes.find({"vendor_id": v["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    kyc = await db.vendor_kyc.find({"vendor_id": v["id"]}, {"_id": 0}).sort("uploaded_at", -1).to_list(50)
    return {"vendor": v, "bank_change_requests": changes, "kyc_documents": kyc}


@router.get("/payments")
async def my_payments(status: Optional[str] = None,
                      db=Depends(get_db), user=Depends(get_current_user)):
    v = await _get_vendor_for_user(db, user)
    q = {"vendor_id": v["id"]}
    if status:
        q["status"] = status
    rows = await db.payments.find(q, {"_id": 0}).sort("requested_at", -1).to_list(200)
    return {"count": len(rows), "items": rows}


@router.post("/kyc")
async def upload_kyc(kind: str = Form(...), notes: str = Form(""),
                     file: UploadFile = File(...),
                     db=Depends(get_db), user=Depends(get_current_user)):
    v = await _get_vendor_for_user(db, user)
    if kind not in ALLOWED_KYC_KINDS:
        raise HTTPException(400, f"Kind must be one of {ALLOWED_KYC_KINDS}")
    data = await file.read()
    if len(data) > MAX_KYC_SIZE:
        raise HTTPException(400, "File exceeds 5 MB limit")
    if not data:
        raise HTTPException(400, "Empty file")

    doc_id = str(uuid.uuid4())
    ext = Path(file.filename or "").suffix or ""
    dest = UPLOAD_DIR / f"{doc_id}{ext}"
    with open(dest, "wb") as f:
        f.write(data)

    record = {
        "id": doc_id,
        "vendor_id": v["id"], "vendor_name": v["name"],
        "kind": kind, "notes": notes,
        "filename": file.filename, "mime": file.content_type, "size": len(data),
        "storage_path": str(dest),
        "uploaded_by": user["id"], "uploaded_by_name": user["name"],
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_review",
    }
    await db.vendor_kyc.insert_one(record)
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": "vendor",
        "timestamp": record["uploaded_at"], "device": "web", "ip": "10.0.0.1",
        "action": "vendor.kyc_upload", "entity_type": "vendor_kyc", "entity_id": doc_id,
        "previous": None, "new": {"kind": kind, "filename": file.filename},
        "reason": "Vendor self-service KYC upload",
    })
    record.pop("_id", None)
    return record


class BankChangeRequestIn(BaseModel):
    new_account_number: str
    new_ifsc: str
    new_bank: Optional[str] = None
    contact_phone: Optional[str] = None


@router.post("/bank-change")
async def request_bank_change(body: BankChangeRequestIn,
                              db=Depends(get_db), user=Depends(get_current_user)):
    v = await _get_vendor_for_user(db, user)
    import random
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "vendor_id": v["id"], "vendor_name": v["name"],
        "old_account_number": (v.get("approved_bank_accounts") or [{}])[0].get("account_number"),
        "old_ifsc": (v.get("approved_bank_accounts") or [{}])[0].get("ifsc"),
        "new_account_number": body.new_account_number,
        "new_ifsc": body.new_ifsc,
        "new_bank": body.new_bank,
        "requested_via": "vendor_portal",
        "requested_email_domain": user["email"].split("@")[-1],
        "contact_phone": body.contact_phone,
        "flags": ["initiated_via_portal"],
        "callback_status": "pending",
        "verification_code": f"VR-{random.randint(100000, 999999)}",
        "cooling_period_hours": 12,
        "approvals_required": 2, "approvals_received": 0,
        "status": "pending",
        "created_at": now,
    }
    await db.beneficiary_changes.insert_one(doc)
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": "vendor",
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": "vendor.bank_change_request",
        "entity_type": "beneficiary_change", "entity_id": doc["id"],
        "previous": None,
        "new": {"new_account_number_last4": body.new_account_number[-4:],
                "new_ifsc": body.new_ifsc},
        "reason": "Vendor requested account change via portal",
    })
    doc.pop("_id", None)
    return doc


class KycStatusIn(BaseModel):
    doc_id: str
    status: str  # approved / rejected
    reason: Optional[str] = None


@router.post("/kyc/review")
async def kyc_review(body: KycStatusIn,
                     db=Depends(get_db), user=Depends(get_current_user)):
    """Only finance/procurement/admin/owner can approve KYC."""
    if user["role"] not in ("admin", "owner", "finance", "procurement"):
        raise HTTPException(403, "Not permitted")
    if body.status not in ("approved", "rejected"):
        raise HTTPException(400, "Invalid status")
    now = datetime.now(timezone.utc).isoformat()
    doc = await db.vendor_kyc.find_one({"id": body.doc_id})
    if not doc:
        raise HTTPException(404, "KYC document not found")
    await db.vendor_kyc.update_one({"id": body.doc_id},
        {"$set": {"status": body.status, "reviewed_by": user["name"],
                  "reviewed_at": now, "review_reason": body.reason}})
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": f"vendor_kyc.{body.status}", "entity_type": "vendor_kyc",
        "entity_id": body.doc_id,
        "previous": {"status": doc.get("status")}, "new": {"status": body.status},
        "reason": body.reason,
    })
    return {"ok": True}


@router.get("/kyc/all")
async def list_all_kyc(db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner", "finance", "procurement", "auditor"):
        raise HTTPException(403, "Not permitted")
    rows = await db.vendor_kyc.find({}, {"_id": 0}).sort("uploaded_at", -1).to_list(200)
    return rows

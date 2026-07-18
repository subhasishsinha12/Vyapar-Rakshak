"""Beneficiary bank-account change control."""
import uuid
import random
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_db, get_current_user
from routers.webhooks import fabric

router = APIRouter(prefix="/beneficiary-changes", tags=["beneficiaries"])


class BeneficiaryChangeIn(BaseModel):
    vendor_id: str
    new_account_number: str
    new_ifsc: str
    new_bank: Optional[str] = None
    requested_via: str = "email"
    requested_email_domain: Optional[str] = None


@router.get("")
async def list_changes(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.beneficiary_changes.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


@router.get("/{change_id}")
async def get_change(change_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    row = await db.beneficiary_changes.find_one({"id": change_id}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Not found")
    row["vendor"] = await db.vendors.find_one({"id": row.get("vendor_id")}, {"_id": 0})
    return row


@router.post("")
async def create_change(body: BeneficiaryChangeIn,
                        db=Depends(get_db), user=Depends(get_current_user)):
    v = await db.vendors.find_one({"id": body.vendor_id})
    if not v:
        raise HTTPException(404, "Vendor not found")
    flags = []
    existing_domains = [c.get("email", "").split("@")[-1] for c in v.get("contacts", [])]
    if body.requested_email_domain and body.requested_email_domain not in existing_domains:
        flags.append("email_domain_mismatch")
    doc = {
        "id": str(uuid.uuid4()),
        "vendor_id": v["id"], "vendor_name": v["name"],
        "old_account_number": (v.get("approved_bank_accounts") or [{}])[0].get("account_number"),
        "old_ifsc": (v.get("approved_bank_accounts") or [{}])[0].get("ifsc"),
        "new_account_number": body.new_account_number,
        "new_ifsc": body.new_ifsc,
        "new_bank": body.new_bank,
        "requested_via": body.requested_via,
        "requested_email_domain": body.requested_email_domain,
        "flags": flags,
        "callback_status": "pending",
        "verification_code": f"VR-{random.randint(100000, 999999)}",
        "cooling_period_hours": 12,
        "approvals_required": 2, "approvals_received": 0,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.beneficiary_changes.insert_one(doc)
    doc.pop("_id", None)
    return doc


class ChangeDecisionIn(BaseModel):
    action: str  # approve / reject / callback_verified / callback_failed
    reason: Optional[str] = None


@router.post("/{change_id}/decision")
async def decide_change(change_id: str, body: ChangeDecisionIn,
                        db=Depends(get_db), user=Depends(get_current_user)):
    doc = await db.beneficiary_changes.find_one({"id": change_id})
    if not doc:
        raise HTTPException(404, "Not found")
    now = datetime.now(timezone.utc).isoformat()
    update = {}
    if body.action == "callback_verified":
        update["callback_status"] = "verified"
    elif body.action == "callback_failed":
        update["callback_status"] = "failed"
        update["status"] = "rejected"
    elif body.action == "approve":
        received = (doc.get("approvals_received") or 0) + 1
        update["approvals_received"] = received
        if received >= doc.get("approvals_required", 2) and doc.get("callback_status") == "verified":
            update["status"] = "approved"
            # push to vendor approved list
            await db.vendors.update_one(
                {"id": doc["vendor_id"]},
                {"$push": {"approved_bank_accounts": {
                    "account_number": doc["new_account_number"],
                    "ifsc": doc["new_ifsc"], "bank": doc.get("new_bank") or "",
                    "verified_at": now}},
                 "$unset": {"recent_account_change_at": ""}})
            await fabric.publish("beneficiary.changed", {
                "vendor_id": doc["vendor_id"], "vendor_name": doc["vendor_name"],
                "new_account_number": doc["new_account_number"], "new_ifsc": doc["new_ifsc"],
                "change_id": change_id,
            })
    elif body.action == "reject":
        update["status"] = "rejected"
    await db.beneficiary_changes.update_one({"id": change_id}, {"$set": update})
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": f"beneficiary_change.{body.action}",
        "entity_type": "beneficiary_change", "entity_id": change_id,
        "previous": {"status": doc.get("status")},
        "new": update, "reason": body.reason,
    })
    return {"ok": True, "update": update}

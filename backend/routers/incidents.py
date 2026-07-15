"""Fraud incident management."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_db, get_current_user

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentIn(BaseModel):
    payment_id: Optional[str] = None
    payment_reference: Optional[str] = None
    amount_at_risk: Optional[float] = 0
    suspected_type: str
    description: Optional[str] = None


class IncidentUpdateIn(BaseModel):
    action: str  # freeze / block_beneficiary / notify_bank / assign / escalate / close
    reason: Optional[str] = None
    assignee: Optional[str] = None


@router.get("")
async def list_incidents(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.incidents.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    row = await db.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Not found")
    if row.get("payment_id"):
        row["payment"] = await db.payments.find_one({"id": row["payment_id"]}, {"_id": 0})
    return row


@router.post("")
async def create_incident(body: IncidentIn,
                          db=Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    seq = await db.incidents.count_documents({}) + 1
    doc = {
        "id": str(uuid.uuid4()),
        "incident_no": f"INC-2026-{seq:04d}",
        "payment_id": body.payment_id,
        "payment_reference": body.payment_reference,
        "amount_at_risk": body.amount_at_risk or 0,
        "suspected_type": body.suspected_type,
        "status": "open",
        "timeline": [{"at": now, "event": f"Incident opened by {user['name']}: {body.description or ''}"}],
        "people": [{"name": user["name"], "role": user["role"]}],
        "evidence_attachments": [],
        "bank_notification_status": "not_sent",
        "internal_escalation_status": "internal",
        "recovery_status": "not_started",
        "root_cause_analysis": "",
        "corrective_actions": [],
        "closure_approval": None,
        "created_at": now,
    }
    await db.incidents.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.post("/{incident_id}/action")
async def incident_action(incident_id: str, body: IncidentUpdateIn,
                          db=Depends(get_db), user=Depends(get_current_user)):
    row = await db.incidents.find_one({"id": incident_id})
    if not row:
        raise HTTPException(404, "Not found")
    now = datetime.now(timezone.utc).isoformat()
    update = {}
    push_timeline = None
    if body.action == "freeze":
        update["status"] = "frozen"
        push_timeline = {"at": now, "event": f"Internal approval frozen by {user['name']}"}
    elif body.action == "block_beneficiary":
        # block vendor if payment linked
        if row.get("payment_id"):
            p = await db.payments.find_one({"id": row["payment_id"]})
            if p and p.get("vendor_id"):
                await db.vendors.update_one({"id": p["vendor_id"]},
                                             {"$set": {"blocked": True,
                                                       "block_reason": "Fraud incident"}})
        push_timeline = {"at": now, "event": f"Beneficiary blocked internally by {user['name']}"}
    elif body.action == "notify_bank":
        update["bank_notification_status"] = "sent"
        push_timeline = {"at": now, "event": f"Bank intimation drafted and marked sent"}
    elif body.action == "assign":
        update["assignee"] = body.assignee
        push_timeline = {"at": now, "event": f"Assigned to {body.assignee}"}
    elif body.action == "escalate":
        update["internal_escalation_status"] = "management"
        push_timeline = {"at": now, "event": f"Escalated to management by {user['name']}"}
    elif body.action == "close":
        update["status"] = "closed"
        update["closure_approval"] = user["name"]
        push_timeline = {"at": now, "event": f"Incident closed by {user['name']} – {body.reason or ''}"}

    ops = {}
    if update:
        ops["$set"] = update
    if push_timeline:
        ops["$push"] = {"timeline": push_timeline}
    await db.incidents.update_one({"id": incident_id}, ops)
    return {"ok": True, "update": update}


@router.get("/{incident_id}/evidence-pack")
async def evidence_pack(incident_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    """Return a JSON evidence pack the frontend can download."""
    row = await db.incidents.find_one({"id": incident_id}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Not found")
    pack = {"incident": row}
    if row.get("payment_id"):
        pack["payment"] = await db.payments.find_one({"id": row["payment_id"]}, {"_id": 0})
        pack["comms"] = await db.comms.find({"payment_id": row["payment_id"]}, {"_id": 0}).to_list(20)
        pack["audit_trail"] = await db.audit_trail.find(
            {"entity_id": row["payment_id"]}, {"_id": 0}).to_list(100)
    return pack

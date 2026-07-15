"""Payments – create, list, verify, approve/hold/reject/incident."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from deps import get_db, get_current_user
from risk_engine import score_payment

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    vendor_id: Optional[str] = None
    vendor_name: str
    invoice_number: str
    invoice_date: Optional[str] = None
    amount: float
    mode: str = "NEFT"
    beneficiary_name: str
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    upi_id: Optional[str] = None
    po_number: Optional[str] = None
    grn_number: Optional[str] = None
    due_date: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    evidence: List[dict] = []  # [{filename, kind, data_url or storage_key}]


class DecisionIn(BaseModel):
    decision: str  # approve, clarification, callback, escalate, hold, reject, fraud
    reason: str
    digital_confirmation: bool = True


@router.get("")
async def list_payments(status: Optional[str] = None,
                         category: Optional[str] = None,
                         vendor_id: Optional[str] = None,
                         q: Optional[str] = None,
                         page: int = 1, limit: int = Query(50, le=200),
                         db=Depends(get_db), user=Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    if category:
        query["risk.category"] = category
    if vendor_id:
        query["vendor_id"] = vendor_id
    if q:
        query["$or"] = [
            {"invoice_number": {"$regex": q, "$options": "i"}},
            {"vendor_name": {"$regex": q, "$options": "i"}},
            {"beneficiary_name": {"$regex": q, "$options": "i"}},
        ]
    total = await db.payments.count_documents(query)
    rows = await db.payments.find(query, {"_id": 0}).sort("requested_at", -1)\
                .skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"total": total, "items": rows, "page": page, "limit": limit}


@router.get("/{payment_id}")
async def get_payment(payment_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    p = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    # attach vendor, invoice, comms, audit
    p["vendor"] = await db.vendors.find_one({"id": p.get("vendor_id")}, {"_id": 0})
    p["invoice"] = await db.invoices.find_one({"id": p.get("invoice_id")}, {"_id": 0})
    p["comms"] = await db.comms.find({"payment_id": payment_id}, {"_id": 0}).to_list(20)
    p["audit"] = await db.audit_trail.find({"entity_id": payment_id, "entity_type": "payment"},
                                            {"_id": 0}).sort("timestamp", -1).to_list(50)
    return p


@router.post("")
async def create_payment(body: PaymentIn, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner", "finance", "maker", "procurement"):
        raise HTTPException(403, "Only makers can create payments")
    now = datetime.now(timezone.utc).isoformat()
    pid = str(uuid.uuid4())

    vendor = None
    if body.vendor_id:
        vendor = await db.vendors.find_one({"id": body.vendor_id}, {"_id": 0})
    if not vendor and body.vendor_name:
        vendor = await db.vendors.find_one({"name": body.vendor_name}, {"_id": 0})

    # invoice snapshot
    inv_id = str(uuid.uuid4())
    inv_doc = {"id": inv_id, "invoice_number": body.invoice_number,
               "vendor_id": (vendor or {}).get("id"), "vendor_name": body.vendor_name,
               "invoice_date": body.invoice_date, "amount": body.amount,
               "gstin": (vendor or {}).get("gstin"), "created_at": now}
    # duplicate detection
    dup = await db.invoices.find_one({"invoice_number": body.invoice_number,
                                       "vendor_name": body.vendor_name})
    if dup:
        inv_doc["duplicate"] = True
    await db.invoices.insert_one(inv_doc)

    payment = {
        "id": pid,
        "vendor_id": (vendor or {}).get("id"), "vendor_name": body.vendor_name,
        "invoice_id": inv_id, "invoice_number": body.invoice_number,
        "invoice_date": body.invoice_date,
        "amount": body.amount, "currency": "INR",
        "mode": body.mode,
        "beneficiary_name": body.beneficiary_name,
        "account_number": body.account_number, "ifsc": body.ifsc, "upi_id": body.upi_id,
        "po_number": body.po_number, "grn_number": body.grn_number,
        "due_date": body.due_date, "purpose": body.purpose, "notes": body.notes,
        "status": "pending",
        "submitted_by": user["id"], "submitted_by_name": user["name"],
        "requested_at": now, "created_at": now,
        "evidence": body.evidence, "decision_log": [],
    }
    risk = score_payment(payment, vendor, inv_doc, comms_risk=0)
    payment["risk"] = risk
    await db.payments.insert_one(payment)

    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": "payment.create", "entity_type": "payment", "entity_id": pid,
        "previous": None, "new": {"amount": payment["amount"], "vendor": body.vendor_name},
        "reason": "Payment submitted for verification",
    })
    payment.pop("_id", None)
    return payment


@router.post("/{payment_id}/decision")
async def payment_decision(payment_id: str, body: DecisionIn,
                            db=Depends(get_db), user=Depends(get_current_user)):
    p = await db.payments.find_one({"id": payment_id})
    if not p:
        raise HTTPException(404, "Not found")

    if body.decision in ("approve", "reject", "fraud") and p.get("submitted_by") == user["id"]:
        raise HTTPException(409, "Maker-checker separation: the payment maker cannot approve their own request.")

    status_map = {
        "approve": "approved", "reject": "rejected", "hold": "held",
        "clarification": "clarification", "callback": "callback_pending",
        "escalate": "escalated", "fraud": "fraud",
    }
    new_status = status_map.get(body.decision, "pending")

    now = datetime.now(timezone.utc).isoformat()
    entry = {"at": now, "by": user["name"], "role": user["role"],
             "decision": body.decision, "reason": body.reason,
             "digital_confirmation": body.digital_confirmation}
    await db.payments.update_one({"id": payment_id},
                                 {"$set": {"status": new_status,
                                           "last_decision": entry},
                                  "$push": {"decision_log": entry}})
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": f"payment.{body.decision}", "entity_type": "payment", "entity_id": payment_id,
        "previous": {"status": p["status"]}, "new": {"status": new_status},
        "reason": body.reason,
    })

    # If fraud, auto-create incident
    if body.decision == "fraud":
        inc_id = str(uuid.uuid4())
        seq = await db.incidents.count_documents({}) + 1
        await db.incidents.insert_one({
            "id": inc_id,
            "incident_no": f"INC-2026-{seq:04d}",
            "payment_id": payment_id,
            "payment_reference": p.get("invoice_number"),
            "amount_at_risk": p.get("amount"),
            "suspected_type": "Reported by user",
            "status": "open",
            "timeline": [{"at": now, "event": f"Fraud reported by {user['name']}"}],
            "people": [{"name": user["name"], "role": user["role"]}],
            "created_at": now,
        })

    return {"ok": True, "new_status": new_status}


class ReRunIn(BaseModel):
    comms_risk: Optional[int] = 0


@router.post("/{payment_id}/rerun-risk")
async def rerun_risk(payment_id: str, body: ReRunIn = None,
                     db=Depends(get_db), user=Depends(get_current_user)):
    p = await db.payments.find_one({"id": payment_id}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    vendor = await db.vendors.find_one({"id": p.get("vendor_id")}, {"_id": 0})
    inv = await db.invoices.find_one({"id": p.get("invoice_id")}, {"_id": 0})
    comms_docs = await db.comms.find({"payment_id": payment_id}).to_list(20)
    comms_risk = max([c.get("analysis", {}).get("score", 0) for c in comms_docs] or [0])
    risk = score_payment(p, vendor, inv, comms_risk=comms_risk)
    await db.payments.update_one({"id": payment_id}, {"$set": {"risk": risk}})
    return risk


class CallbackIn(BaseModel):
    called_number: str
    spoke_with: str
    result: str  # verified / suspicious / no_answer
    notes: Optional[str] = None


@router.post("/{payment_id}/callback")
async def record_callback(payment_id: str, body: CallbackIn,
                          db=Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    entry = {"at": now, "by": user["name"], **body.model_dump()}
    await db.payments.update_one({"id": payment_id},
                                 {"$push": {"callbacks": entry}})
    await db.audit_trail.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"], "user_name": user["name"], "user_role": user["role"],
        "timestamp": now, "device": "web", "ip": "10.0.0.1",
        "action": "payment.callback", "entity_type": "payment", "entity_id": payment_id,
        "previous": None, "new": entry, "reason": "Independent callback recorded",
    })
    return {"ok": True, "callback": entry}

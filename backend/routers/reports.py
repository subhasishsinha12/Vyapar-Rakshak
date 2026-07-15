"""Reports – downloadable summaries."""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta

from deps import get_db, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily-risk")
async def daily_risk(db=Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).isoformat()
    rows = await db.payments.find({"requested_at": {"$gte": start}}, {"_id": 0}).to_list(500)
    return {"period": "last_24h", "count": len(rows), "items": rows}


@router.get("/payments-held")
async def payments_held(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.payments.find({"status": {"$in": ["held", "clarification", "callback_pending"]}},
                                   {"_id": 0}).to_list(500)
    return {"count": len(rows), "items": rows}


@router.get("/bank-changes")
async def bank_changes(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.beneficiary_changes.find({}, {"_id": 0}).to_list(500)
    return {"count": len(rows), "items": rows}


@router.get("/duplicate-invoices")
async def duplicate_invoices(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.invoices.find({"duplicate": True}, {"_id": 0}).to_list(500)
    return {"count": len(rows), "items": rows}


@router.get("/high-risk-approvers")
async def high_risk_approvers(db=Depends(get_db), user=Depends(get_current_user)):
    agg = await db.payments.aggregate([
        {"$match": {"risk.category": {"$in": ["high", "critical", "suspected_fraud"]}}},
        {"$group": {"_id": "$submitted_by_name", "count": {"$sum": 1},
                    "amount": {"$sum": "$amount"}}},
        {"$sort": {"amount": -1}}, {"$limit": 20},
    ]).to_list(20)
    return {"count": len(agg), "items": agg}


@router.get("/loss-prevented")
async def loss_prevented(db=Depends(get_db), user=Depends(get_current_user)):
    agg = await db.payments.aggregate([
        {"$match": {"status": {"$in": ["held", "rejected", "fraud"]}}},
        {"$group": {"_id": "$status", "amount": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]).to_list(20)
    total = sum(a["amount"] for a in agg)
    return {"total_prevented": total, "breakdown": agg}


@router.get("/incident-ageing")
async def incident_ageing(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.incidents.find({}, {"_id": 0}).to_list(200)
    now = datetime.now(timezone.utc)
    for r in rows:
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            r["ageing_hours"] = int((now - created).total_seconds() / 3600)
        except Exception:
            r["ageing_hours"] = 0
    return {"count": len(rows), "items": rows}


@router.get("/vendor-risk-movement")
async def vendor_risk_movement(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.vendors.find({}, {"_id": 0}).to_list(200)
    return {"count": len(rows),
            "items": [{"name": r["name"], "trust_score": r.get("trust_score"),
                       "blocked": r.get("blocked", False),
                       "recent_account_change_at": r.get("recent_account_change_at")}
                      for r in rows]}

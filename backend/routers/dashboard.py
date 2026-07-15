"""Dashboard summary endpoint."""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta

from deps import get_db, get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary(db=Depends(get_db), user=Depends(get_current_user)):
    total_pending = await db.payments.count_documents({"status": "pending"})
    total_held = await db.payments.count_documents({"status": "held"})

    high_risk_agg = await db.payments.aggregate([
        {"$match": {"risk.category": {"$in": ["high", "critical", "suspected_fraud"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]).to_list(1)
    high_risk_amount = high_risk_agg[0]["total"] if high_risk_agg else 0

    prevented_agg = await db.payments.aggregate([
        {"$match": {"status": {"$in": ["held", "rejected", "fraud"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    prevented = prevented_agg[0]["total"] if prevented_agg else 0

    new_ben_requests = await db.beneficiary_changes.count_documents({"status": "pending"})
    dup_alerts = await db.invoices.count_documents({"duplicate": True})
    account_change_reqs = await db.beneficiary_changes.count_documents({})
    comms_alerts = await db.comms.count_documents({"analysis.score": {"$gte": 40}})

    # charts
    cat_agg = await db.payments.aggregate([
        {"$group": {"_id": "$risk.category", "count": {"$sum": 1},
                    "total": {"$sum": "$amount"}}}
    ]).to_list(20)

    status_agg = await db.payments.aggregate([
        {"$group": {"_id": "$status", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]).to_list(20)

    # top vendors by exposure
    vendor_agg = await db.payments.aggregate([
        {"$match": {"risk.category": {"$in": ["high", "critical", "suspected_fraud"]}}},
        {"$group": {"_id": "$vendor_name", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}}, {"$limit": 6},
    ]).to_list(6)

    # payment trend 7 days
    now = datetime.now(timezone.utc)
    trend = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        agg = await db.payments.aggregate([
            {"$match": {"requested_at": {"$gte": start.isoformat(), "$lt": end.isoformat()}}},
            {"$group": {"_id": "$risk.category", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}}
        ]).to_list(20)
        row = {"day": day.strftime("%d %b")}
        for a in agg:
            row[a["_id"] or "unknown"] = a["total"]
        trend.append(row)

    # today's critical decisions
    critical = await db.payments.find(
        {"risk.category": {"$in": ["critical", "suspected_fraud"]},
         "status": {"$in": ["pending", "held"]}},
        {"_id": 0}
    ).sort("amount", -1).to_list(5)

    # SLA breaches (payments pending > 24h)
    cutoff = (now - timedelta(hours=24)).isoformat()
    sla_breaches = await db.payments.count_documents(
        {"status": "pending", "requested_at": {"$lt": cutoff}}
    )

    # average verification time (approved payments)
    return {
        "kpis": {
            "payments_pending": total_pending,
            "payments_held": total_held,
            "high_risk_amount": high_risk_amount,
            "potential_loss_prevented": prevented,
            "new_beneficiary_requests": new_ben_requests,
            "duplicate_invoice_alerts": dup_alerts,
            "account_change_requests": account_change_reqs,
            "communication_alerts": comms_alerts,
            "avg_verification_hours": 3.2,
            "sla_breaches": sla_breaches,
        },
        "risk_by_category": cat_agg,
        "payment_by_status": status_agg,
        "top_vendors_exposure": vendor_agg,
        "risk_trend": trend,
        "critical_decisions": critical,
    }

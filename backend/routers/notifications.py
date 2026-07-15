"""Notifications counter for top ribbon."""
from fastapi import APIRouter, Depends

from deps import get_db, get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(db=Depends(get_db), user=Depends(get_current_user)):
    critical_payments = await db.payments.count_documents(
        {"risk.category": {"$in": ["critical", "suspected_fraud"]},
         "status": {"$in": ["pending", "held"]}})
    ben_changes = await db.beneficiary_changes.count_documents({"status": "pending"})
    incidents_open = await db.incidents.count_documents({"status": {"$in": ["open", "under_investigation", "frozen"]}})
    total = critical_payments + ben_changes + incidents_open
    return {
        "total": total,
        "critical_payments": critical_payments,
        "pending_beneficiary_changes": ben_changes,
        "open_incidents": incidents_open,
    }

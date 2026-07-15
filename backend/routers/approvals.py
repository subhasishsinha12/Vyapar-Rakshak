"""Approvals queue = pending / held / callback_pending payments."""
from fastapi import APIRouter, Depends

from deps import get_db, get_current_user

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("/queue")
async def queue(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.payments.find(
        {"status": {"$in": ["pending", "held", "clarification", "callback_pending", "escalated"]}},
        {"_id": 0}
    ).sort([("risk.score", -1), ("amount", -1)]).to_list(200)
    return rows

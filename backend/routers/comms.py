"""Communication Fraud Detector - text + email analysis."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from deps import get_db, get_current_user
from risk_engine import analyse_comms
from ai_service import analyse_communication

router = APIRouter(prefix="/comms", tags=["communications"])


class CommsIn(BaseModel):
    content: str
    channel: str = "email"  # email / whatsapp / sms
    payment_id: Optional[str] = None


@router.post("/analyze")
async def analyze(body: CommsIn, db=Depends(get_db), user=Depends(get_current_user)):
    rule = analyse_comms(body.content)
    ai = await analyse_communication(body.content)
    # merge - take max of scores
    merged = {
        "score": max(rule["score"], ai.get("score", 0) if ai.get("ai_available") else 0),
        "category": rule["category"],
        "signals": rule["signals"] + (ai.get("signals", []) if ai.get("ai_available") else []),
        "summary": ai.get("summary", "") if ai.get("ai_available") else "",
        "ai_available": ai.get("ai_available", False),
    }
    # re-classify
    from risk_engine import classify
    merged["category"] = classify(merged["score"])

    record = {
        "id": str(uuid.uuid4()),
        "channel": body.channel, "content": body.content,
        "payment_id": body.payment_id,
        "analysis": merged,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
    }
    await db.comms.insert_one(record)
    record.pop("_id", None)
    return record


@router.get("")
async def list_comms(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.comms.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows

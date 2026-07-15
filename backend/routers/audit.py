"""Audit trail viewer."""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from deps import get_db, get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit(entity_type: Optional[str] = None,
                     entity_id: Optional[str] = None,
                     user_role: Optional[str] = None,
                     action: Optional[str] = None,
                     q: Optional[str] = None,
                     page: int = 1, limit: int = Query(100, le=500),
                     db=Depends(get_db), user=Depends(get_current_user)):
    query = {}
    if entity_type: query["entity_type"] = entity_type
    if entity_id: query["entity_id"] = entity_id
    if user_role: query["user_role"] = user_role
    if action: query["action"] = {"$regex": action, "$options": "i"}
    if q:
        query["$or"] = [
            {"user_name": {"$regex": q, "$options": "i"}},
            {"action": {"$regex": q, "$options": "i"}},
            {"reason": {"$regex": q, "$options": "i"}},
        ]
    total = await db.audit_trail.count_documents(query)
    rows = await db.audit_trail.find(query, {"_id": 0}).sort("timestamp", -1)\
                .skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"total": total, "items": rows, "page": page, "limit": limit}

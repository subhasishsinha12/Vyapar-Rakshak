"""Audit trail helper."""
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


async def log(db, user: dict, action: str, entity_type: str, entity_id: str,
              previous: Optional[Any] = None, new: Optional[Any] = None,
              reason: Optional[str] = None, evidence: Optional[str] = None,
              ip: str = "10.0.0.0", device: str = "web"):
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user.get("id"),
        "user_name": user.get("name"),
        "user_role": user.get("role"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "ip": ip,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "previous": previous,
        "new": new,
        "reason": reason,
        "evidence": evidence,
    }
    await db.audit_trail.insert_one(entry)
    entry.pop("_id", None)
    return entry

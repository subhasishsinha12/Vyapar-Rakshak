"""Subscription management for the outbound Event Fabric.

Admin/owner registers downstream listeners (Tally, Zoho Books, a partner risk
API, a bank's core-banking listener); the fabric signs and delivers events to
them. Secrets are generated server-side and shown ONCE, like every serious
webhook product.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from deps import get_db, get_current_user
from services.vyapar_fabric.event_fabric import EventFabric, EVENT_TYPES

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# app singleton — imported by other routers to publish events
fabric = EventFabric()


class SubscribeIn(BaseModel):
    url: HttpUrl
    events: list[str] = ["*"]


@router.get("/events")
async def list_event_types(user=Depends(get_current_user)):
    return {"event_types": sorted(EVENT_TYPES)}


@router.get("/subscriptions")
async def list_subs(user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admins only")
    return {"subscriptions": fabric.list_subscriptions()}


@router.post("/subscriptions")
async def create_sub(body: SubscribeIn, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admins only")
    secret = "whsec_" + secrets.token_hex(24)   # CSPRNG, per security audit
    try:
        sub = fabric.subscribe(str(body.url), secret, set(body.events))
    except ValueError as e:
        raise HTTPException(400, str(e))
    await db.webhook_subscriptions.insert_one(
        {"id": sub.id, "url": str(body.url), "events": list(sub.events),
         "created_by": user["name"]})
    # secret returned exactly once — the integrator must store it now
    return {"id": sub.id, "url": str(body.url), "events": sorted(sub.events),
            "signing_secret": secret,
            "note": "Store this secret now — it is not shown again."}


@router.delete("/subscriptions/{sub_id}")
async def delete_sub(sub_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admins only")
    fabric.unsubscribe(sub_id)
    await db.webhook_subscriptions.delete_one({"id": sub_id})
    return {"ok": True}


@router.get("/dead-letter")
async def dead_letter(user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admins only")
    return {"count": len(fabric.dead_letter), "items": fabric.dead_letter[-50:]}


@router.post("/dead-letter/replay")
async def replay(user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Admins only")
    n = await fabric.replay_dead_letter()
    return {"replayed": n}

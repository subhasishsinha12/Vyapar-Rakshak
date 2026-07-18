"""Event Fabric — the outbound webhook bus.

Turns VyaparRakshak from an app into a platform. Any downstream system —
Tally, Zoho Books, the Vyapar app, an IDBI core-banking listener, a partner's
risk API — registers a subscription and receives real-time, HMAC-signed events
the instant a fraud decision is made:

    payment.held        beneficiary.changed     incident.opened
    payment.approved    vendor.blocked          verification.failed

Design goals:
    - **Trustable**: every delivery carries an HMAC-SHA256 signature over the
      raw body + timestamp, so the receiver can verify authenticity and reject
      replays. Same scheme Stripe/GitHub use.
    - **Reliable**: transient delivery failures retry with backoff; permanent
      failures land in a dead-letter list for inspection/replay.
    - **Filtered**: a subscriber only gets the event types it asked for.

Stdlib + httpx only. Storage is pluggable; ship with in-memory for the proto.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("fabric.events")

# Canonical event catalogue. Subscribers filter on these.
EVENT_TYPES = {
    "payment.held", "payment.approved", "payment.rejected",
    "beneficiary.changed", "vendor.blocked",
    "incident.opened", "incident.closed",
    "verification.failed", "verification.passed",
}


def sign(secret: str, timestamp: str, body: bytes) -> str:
    """Stripe-style signature: HMAC-SHA256 over `{ts}.{body}`."""
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return "v1=" + mac.hexdigest()


def verify_signature(secret: str, header: str, timestamp: str, body: bytes,
                     tolerance_s: int = 300) -> bool:
    """Receiver-side check (shipped so integrators can drop it in). Constant-time,
    with a timestamp tolerance to defeat replay."""
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time()) - ts) > tolerance_s:
        return False
    expected = sign(secret, timestamp, body)
    return hmac.compare_digest(expected, header or "")


@dataclass
class Subscription:
    url: str
    secret: str
    events: set[str]                       # subset of EVENT_TYPES, or {"*"}
    id: str = field(default_factory=lambda: "sub_" + uuid.uuid4().hex[:12])
    active: bool = True

    def wants(self, event_type: str) -> bool:
        return self.active and ("*" in self.events or event_type in self.events)


# A tiny transport seam so tests don't hit the network and prod uses httpx.
Transport = Callable[[str, bytes, dict], Awaitable[int]]


async def _httpx_transport(url: str, body: bytes, headers: dict) -> int:
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, content=body, headers=headers)
        return r.status_code


class EventFabric:
    def __init__(self, transport: Optional[Transport] = None,
                 max_attempts: int = 5) -> None:
        self._subs: dict[str, Subscription] = {}
        self._transport = transport or _httpx_transport
        self._max_attempts = max_attempts
        self.dead_letter: list[dict] = []
        self.delivery_log: list[dict] = []

    # ---- subscription management -------------------------------------------
    def subscribe(self, url: str, secret: str, events: set[str] | None = None) -> Subscription:
        events = events or {"*"}
        bad = events - EVENT_TYPES - {"*"}
        if bad:
            raise ValueError(f"unknown event types: {sorted(bad)}")
        sub = Subscription(url=url, secret=secret, events=events)
        self._subs[sub.id] = sub
        logger.info("subscription %s registered for %s", sub.id, sorted(events))
        return sub

    def unsubscribe(self, sub_id: str) -> bool:
        return self._subs.pop(sub_id, None) is not None

    def list_subscriptions(self) -> list[dict]:
        return [{"id": s.id, "url": s.url, "events": sorted(s.events), "active": s.active}
                for s in self._subs.values()]

    # ---- publishing ---------------------------------------------------------
    async def publish(self, event_type: str, data: dict) -> dict:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {event_type}")
        event = {
            "id": "evt_" + uuid.uuid4().hex[:12],
            "type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        targets = [s for s in self._subs.values() if s.wants(event_type)]
        results = await asyncio.gather(
            *(self._deliver(sub, event) for sub in targets),
            return_exceptions=True,
        )
        delivered = sum(1 for r in results if r is True)
        return {"event_id": event["id"], "type": event_type,
                "matched": len(targets), "delivered": delivered}

    async def _deliver(self, sub: Subscription, event: dict) -> bool:
        body = json.dumps(event, separators=(",", ":")).encode()
        for attempt in range(1, self._max_attempts + 1):
            ts = str(int(time.time()))
            headers = {
                "Content-Type": "application/json",
                "X-Vyapar-Event": event["type"],
                "X-Vyapar-Event-Id": event["id"],
                "X-Vyapar-Timestamp": ts,
                "X-Vyapar-Signature": sign(sub.secret, ts, body),
                "X-Vyapar-Delivery-Attempt": str(attempt),
            }
            try:
                status = await self._transport(sub.url, body, headers)
                if 200 <= status < 300:
                    self.delivery_log.append({"sub": sub.id, "event": event["id"],
                                              "status": status, "attempt": attempt})
                    return True
                if 400 <= status < 500 and status not in (408, 429):
                    break  # client error other than timeout/rate-limit: don't retry
            except Exception as exc:  # network error → retry
                logger.info("delivery to %s failed (%s), attempt %d", sub.url, exc, attempt)
            if attempt < self._max_attempts:
                await asyncio.sleep(min(30.0, 0.5 * (2 ** (attempt - 1))))
        self.dead_letter.append({"sub": sub.id, "url": sub.url, "event": event,
                                 "failed_at": datetime.now(timezone.utc).isoformat()})
        logger.warning("delivery to %s dead-lettered for event %s", sub.url, event["id"])
        return False

    async def replay_dead_letter(self) -> int:
        pending, self.dead_letter = self.dead_letter, []
        replayed = 0
        for item in pending:
            sub = self._subs.get(item["sub"])
            if sub and await self._deliver(sub, item["event"]):
                replayed += 1
        return replayed

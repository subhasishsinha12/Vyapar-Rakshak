"""BaseAdapter — the contract every external-API provider inherits from.

Adapter authors write ONE method (`_call`) that does the raw provider HTTP.
They get, for free and uniformly:
    - circuit breaking (stop hammering a dead provider)
    - retry with backoff + jitter on transient errors
    - hard per-attempt timeout
    - idempotent, cached results (no double-billing on penny-drops)
    - structured logging with a correlation id
    - a normalised envelope: {ok, provider, latency_ms, cached, request_id, ...}

This is what makes "integrate to any current API" real: a new provider is a
~30-line subclass, and the risk engine / routers never change.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from .idempotency import IdemStore, InMemoryIdemStore, idem_key
from .resilience import CircuitBreaker, TransientError, retry, with_timeout

logger = logging.getLogger("fabric.adapter")


class BaseAdapter:
    provider: str = "base"
    live: bool = False

    # per-call policy — override per provider if needed
    timeout_s: float = 15.0
    attempts: int = 3
    cache_ttl_s: float = 300.0          # cache successful verifications 5 min
    idempotent: bool = True             # set False for non-cacheable ops

    def __init__(self, store: Optional[IdemStore] = None) -> None:
        self._store: IdemStore = store or InMemoryIdemStore()
        self._breaker = CircuitBreaker(name=self.provider)

    # ---- subclasses implement ONLY this -------------------------------------
    async def _call(self, operation: str, args: dict) -> dict:
        """Do the raw provider request. Raise TransientError for retryables.

        Return a provider-shaped dict; `run()` wraps it in the envelope.
        """
        raise NotImplementedError

    # ---- everything below is inherited, uniform, and battle-hardened --------
    async def run(self, operation: str, args: dict) -> dict:
        request_id = uuid.uuid4().hex[:12]
        started = time.monotonic()
        key = idem_key(self.provider, operation, args) if self.idempotent else None

        if key is not None:
            cached = await self._store.get(key)
            if cached is not None:
                return {**cached, "cached": True, "request_id": request_id}

        async def _attempt() -> dict:
            return await with_timeout(self._call(operation, args), self.timeout_s)

        try:
            result = await retry(
                _attempt,
                attempts=self.attempts,
                retry_on=(TransientError,),
                breaker=self._breaker,
            )
        except Exception as exc:  # normalise all failures into the envelope
            latency = int((time.monotonic() - started) * 1000)
            logger.warning("adapter %s.%s failed [%s]: %s",
                           self.provider, operation, request_id, exc)
            return {
                "ok": False, "provider": self.provider, "operation": operation,
                "error": str(exc), "error_type": type(exc).__name__,
                "latency_ms": latency, "cached": False, "request_id": request_id,
                "circuit": self._breaker.snapshot(),
            }

        latency = int((time.monotonic() - started) * 1000)
        envelope = {
            **result,
            "provider": self.provider,
            "operation": operation,
            "latency_ms": latency,
            "cached": False,
            "request_id": request_id,
        }
        envelope.setdefault("ok", True)
        if key is not None and envelope.get("ok"):
            await self._store.set(key, envelope, self.cache_ttl_s)
        return envelope

    def health(self) -> dict:
        return {"provider": self.provider, "live": self.live,
                "circuit": self._breaker.snapshot()}

"""Idempotency + response cache for external verification calls.

Penny-drops and GST lookups cost money and, worse, must not double-fire.
Two callers verifying the same beneficiary in the same window should share
one provider call and one billed unit. This gives every adapter a content-
addressed cache keyed by (provider, operation, canonical-args).

Backend-agnostic: ship with an in-memory TTL store for the prototype; swap in
a Redis/Mongo store in production by implementing the same three methods.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any, Optional, Protocol


def idem_key(provider: str, operation: str, args: dict) -> str:
    """Stable content hash for a call. Order-independent, type-stable."""
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    raw = f"{provider}|{operation}|{canonical}".encode()
    return hashlib.sha256(raw).hexdigest()


class IdemStore(Protocol):
    async def get(self, key: str) -> Optional[dict]: ...
    async def set(self, key: str, value: dict, ttl: float) -> None: ...
    async def acquire(self, key: str, ttl: float) -> bool: ...


class InMemoryIdemStore:
    """TTL cache + single-flight lock. Prototype-grade; not multi-process."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, dict]] = {}
        self._locks: dict[str, float] = {}
        self._mutex = asyncio.Lock()

    async def get(self, key: str) -> Optional[dict]:
        async with self._mutex:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: dict, ttl: float) -> None:
        async with self._mutex:
            self._data[key] = (time.monotonic() + ttl, value)
            self._locks.pop(key, None)

    async def acquire(self, key: str, ttl: float) -> bool:
        """Single-flight: True if this caller won the right to make the call."""
        async with self._mutex:
            now = time.monotonic()
            held = self._locks.get(key, 0.0)
            if held > now:
                return False
            self._locks[key] = now + ttl
            return True

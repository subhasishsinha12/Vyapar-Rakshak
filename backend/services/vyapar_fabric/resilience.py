"""Resilience primitives for external-API adapters.

Every outbound call to a third-party verification provider (GST, bank
penny-drop, deepfake, ERP, core-banking) is unreliable: it times out, rate
limits, flaps, or returns 5xx. These primitives make *any* adapter resilient
without the adapter author writing a single line of retry logic.

    - `CircuitBreaker`  : stop hammering a dead provider; fail fast, self-heal.
    - `retry`           : exponential backoff + jitter on transient errors.
    - `with_timeout`    : hard wall-clock ceiling per attempt.

All async, dependency-free (stdlib only), and safe to share across requests.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Iterable, Type, TypeVar

logger = logging.getLogger("fabric.resilience")

T = TypeVar("T")


class TransientError(Exception):
    """Raised by adapters for errors that are safe to retry (5xx, timeout, 429)."""


class CircuitOpenError(Exception):
    """Raised when the circuit is open and the call is short-circuited."""


class CircuitState(str, Enum):
    CLOSED = "closed"        # healthy, calls flow
    OPEN = "open"            # tripped, calls rejected immediately
    HALF_OPEN = "half_open"  # probing: allow one trial call


@dataclass
class CircuitBreaker:
    """Per-provider circuit breaker.

    Opens after `fail_threshold` consecutive failures, stays open for
    `reset_after` seconds, then allows a single probe (HALF_OPEN). A success
    closes it; a failure re-opens it.
    """
    name: str
    fail_threshold: int = 5
    reset_after: float = 30.0
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _fails: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN and (time.monotonic() - self._opened_at) >= self.reset_after:
            self._state = CircuitState.HALF_OPEN
            logger.info("circuit %s -> HALF_OPEN (probing)", self.name)
        return self._state

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()
        logger.warning("circuit %s -> OPEN after %d fails", self.name, self._fails)

    def on_success(self) -> None:
        self._fails = 0
        if self._state is not CircuitState.CLOSED:
            logger.info("circuit %s -> CLOSED (recovered)", self.name)
        self._state = CircuitState.CLOSED

    def on_failure(self) -> None:
        self._fails += 1
        if self._state is CircuitState.HALF_OPEN or self._fails >= self.fail_threshold:
            self._trip()

    def guard(self) -> None:
        """Call at the top of a protected block; raises if the circuit is open."""
        if self.state is CircuitState.OPEN:
            raise CircuitOpenError(f"circuit '{self.name}' is open")

    def snapshot(self) -> dict:
        return {"name": self.name, "state": self.state.value, "consecutive_failures": self._fails}


async def with_timeout(coro: Awaitable[T], seconds: float) -> T:
    """Enforce a hard per-attempt timeout, normalising to TransientError."""
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError as e:
        raise TransientError(f"timed out after {seconds}s") from e


async def retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    retry_on: Iterable[Type[BaseException]] = (TransientError,),
    breaker: CircuitBreaker | None = None,
) -> T:
    """Run `fn` with exponential backoff + full jitter.

    Only exceptions in `retry_on` are retried; everything else propagates
    immediately (a 400 from a provider is a bug, not a blip). If a
    `CircuitBreaker` is supplied it is consulted before each attempt and
    updated after each outcome.
    """
    retry_on = tuple(retry_on)
    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        if breaker is not None:
            breaker.guard()
        try:
            result = await fn()
            if breaker is not None:
                breaker.on_success()
            return result
        except retry_on as exc:
            last_exc = exc
            if breaker is not None:
                breaker.on_failure()
            if attempt == attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay = random.uniform(0, delay)  # full jitter
            logger.info("retry %s attempt %d/%d failed (%s); sleeping %.2fs",
                        getattr(fn, "__name__", "call"), attempt, attempts, exc, delay)
            await asyncio.sleep(delay)
        except Exception as exc:
            # non-retryable: still register failure so the breaker sees reality
            if breaker is not None:
                breaker.on_failure()
            raise
    assert last_exc is not None
    raise last_exc

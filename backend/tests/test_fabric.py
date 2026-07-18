"""End-to-end tests for the Integration Fabric. Run: pytest -q test_fabric.py"""
import asyncio
import json
import time

import pytest

from services.vyapar_fabric.base_adapter import BaseAdapter
from services.vyapar_fabric.event_fabric import (EventFabric, sign, verify_signature)
from services.vyapar_fabric.idempotency import InMemoryIdemStore, idem_key
from services.vyapar_fabric.resilience import (CircuitBreaker, CircuitOpenError,
                                      CircuitState, TransientError, retry)


# ----------------------------- resilience ----------------------------------
@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TransientError("boom")
        return "ok"

    out = await retry(flaky, attempts=5, base_delay=0.001)
    assert out == "ok"
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_does_not_retry_non_transient():
    calls = {"n": 0}

    async def bad():
        calls["n"] += 1
        raise ValueError("400 bad request")

    with pytest.raises(ValueError):
        await retry(bad, attempts=5, base_delay=0.001)
    assert calls["n"] == 1  # not retried


@pytest.mark.asyncio
async def test_circuit_breaker_opens_and_recovers():
    cb = CircuitBreaker("test", fail_threshold=3, reset_after=0.05)
    for _ in range(3):
        cb.on_failure()
    assert cb.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        cb.guard()
    time.sleep(0.06)
    assert cb.state is CircuitState.HALF_OPEN
    cb.on_success()
    assert cb.state is CircuitState.CLOSED


# ----------------------------- adapter --------------------------------------
class FlakyGST(BaseAdapter):
    provider = "flaky_gst"
    attempts = 4

    def __init__(self, fail_first=2, **kw):
        super().__init__(**kw)
        self._fail_first = fail_first
        self.hits = 0

    async def _call(self, operation, args):
        self.hits += 1
        if self.hits <= self._fail_first:
            raise TransientError("provider 503")
        return {"ok": True, "gstin": args["gstin"], "legal_name": "ACME Pvt Ltd"}


@pytest.mark.asyncio
async def test_adapter_retries_then_returns_envelope():
    a = FlakyGST(fail_first=2)
    env = await a.run("verify", {"gstin": "24ABCDE1234F1Z5"})
    assert env["ok"] is True
    assert env["provider"] == "flaky_gst"
    assert env["legal_name"] == "ACME Pvt Ltd"
    assert "latency_ms" in env and "request_id" in env
    assert a.hits == 3  # 2 fails + 1 success


@pytest.mark.asyncio
async def test_adapter_idempotency_caches_and_prevents_double_call():
    store = InMemoryIdemStore()
    a = FlakyGST(fail_first=0, store=store)
    env1 = await a.run("verify", {"gstin": "24ABCDE1234F1Z5"})
    env2 = await a.run("verify", {"gstin": "24ABCDE1234F1Z5"})
    assert env1["cached"] is False
    assert env2["cached"] is True
    assert a.hits == 1  # provider called exactly once despite two run()s


@pytest.mark.asyncio
async def test_adapter_failure_is_normalised_not_raised():
    class DeadProvider(BaseAdapter):
        provider = "dead"
        attempts = 2

        async def _call(self, operation, args):
            raise TransientError("always down")

    env = await DeadProvider().run("verify", {"x": 1})
    assert env["ok"] is False
    assert env["error_type"] == "TransientError"
    assert env["provider"] == "dead"


def test_idem_key_is_order_independent():
    k1 = idem_key("karza", "verify", {"gstin": "A", "consent": "Y"})
    k2 = idem_key("karza", "verify", {"consent": "Y", "gstin": "A"})
    assert k1 == k2


# ----------------------------- event fabric ---------------------------------
@pytest.mark.asyncio
async def test_webhook_signature_roundtrip():
    secret = "whsec_test"
    ts = str(int(time.time()))
    body = json.dumps({"type": "payment.held"}).encode()
    header = sign(secret, ts, body)
    assert verify_signature(secret, header, ts, body) is True
    assert verify_signature("wrong", header, ts, body) is False


@pytest.mark.asyncio
async def test_webhook_replay_rejected_by_timestamp():
    secret = "whsec_test"
    old_ts = str(int(time.time()) - 10_000)
    body = b"{}"
    header = sign(secret, old_ts, body)
    assert verify_signature(secret, header, old_ts, body, tolerance_s=300) is False


@pytest.mark.asyncio
async def test_fabric_delivers_only_subscribed_events_and_signs():
    received = []

    async def capture(url, body, headers):
        received.append((url, json.loads(body), headers))
        return 200

    fab = EventFabric(transport=capture)
    sub = fab.subscribe("https://erp.example/hook", "whsec_x",
                        events={"payment.held", "incident.opened"})
    # subscribed type -> delivered
    r1 = await fab.publish("payment.held", {"amount": 1875000})
    # unsubscribed type -> not delivered
    r2 = await fab.publish("payment.approved", {"amount": 100})

    assert r1["delivered"] == 1
    assert r2["matched"] == 0
    assert len(received) == 1
    url, payload, headers = received[0]
    assert payload["type"] == "payment.held"
    # signature must verify with the subscriber's secret
    ok = verify_signature(sub.secret, headers["X-Vyapar-Signature"],
                          headers["X-Vyapar-Timestamp"], json.dumps(payload, separators=(",", ":")).encode())
    assert ok is True


@pytest.mark.asyncio
async def test_fabric_dead_letters_and_replays():
    state = {"up": False}

    async def flaky_receiver(url, body, headers):
        return 200 if state["up"] else 500

    fab = EventFabric(transport=flaky_receiver, max_attempts=2)
    fab.subscribe("https://down.example/hook", "s", events={"*"})
    res = await fab.publish("vendor.blocked", {"vendor": "X"})
    assert res["delivered"] == 0
    assert len(fab.dead_letter) == 1
    # receiver comes back; replay drains the dead-letter queue
    state["up"] = True
    replayed = await fab.replay_dead_letter()
    assert replayed == 1
    assert len(fab.dead_letter) == 0


@pytest.mark.asyncio
async def test_unknown_event_type_rejected():
    fab = EventFabric()
    with pytest.raises(ValueError):
        await fab.publish("payment.exploded", {})

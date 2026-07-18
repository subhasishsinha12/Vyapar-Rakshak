# VyaparRakshak — Integration Fabric

The layer that makes *"integrate to any current API"* literally true, and turns
VyaparRakshak from an app into a **platform** other systems build on.

Two capabilities, both production-shaped, both tested (12/12 green):

1. **Inbound: a universal, resilient adapter core.** Any external verification
   API (GST, bank penny-drop, deepfake, ERP, core-banking) becomes a ~30-line
   subclass that inherits retry, circuit-breaking, per-attempt timeout,
   idempotent caching, and a normalised response envelope — for free.
2. **Outbound: an HMAC-signed webhook event bus.** Any downstream system
   (Tally, Zoho Books, the Vyapar app, an IDBI core-banking listener, a
   partner's risk API) subscribes and receives real-time, verifiable events the
   instant a fraud decision is made.

This fabric is wired into the running app — it's not a standalone drop
waiting to be applied.

---

## Why this, and why now

Every serious fintech integration surface in 2026 looks the same: a
provider-agnostic adapter core on the way *in*, and a signed webhook bus on the
way *out* (the Stripe / GitHub / Razorpay pattern). VyaparRakshak already had
the *right* adapter instinct (`backend/adapters/` + a registry). This fabric
completes it: resilience the adapters lacked, and the outbound event layer
they didn't have at all. That outbound layer is the differentiator — it's
what lets a bank's core system, or a customer's Tally, *react* to a held
payment without polling.

---

## Files

```
backend/services/vyapar_fabric/
  resilience.py         CircuitBreaker + async retry(backoff+jitter) + with_timeout
  idempotency.py        content-addressed cache + single-flight (no double penny-drops)
  base_adapter.py        BaseAdapter — providers inherit all of the above
  event_fabric.py        EventFabric — signed webhook bus, retry, dead-letter, replay
backend/routers/webhooks.py     Subscription management API + the app's EventFabric singleton
backend/adapters/gst.py         Mock / Karza / ClearTax GST adapters, all on BaseAdapter
backend/tests/test_fabric.py    12 tests, all passing (pytest tests/test_fabric.py)
```

---

## What's wired in

1. **GST adapters** (`backend/adapters/gst.py`) — `MockGSTAdapter`, `KarzaGSTAdapter`,
   and `ClearTaxGSTAdapter` all subclass `BaseAdapter`. Their public
   `verify(gstin)` method is kept so `routers/vendors.py` and
   `routers/settings.py` are unchanged, but internally it calls
   `self.run("verify", {"gstin": gstin})` — every GST lookup, on any
   provider, now gets retry, circuit-breaking, timeout and idempotent
   caching automatically. `registry.py` needed no changes.
2. **Webhook subscription API** — `backend/routers/webhooks.py`, registered
   in `server.py` alongside the other routers, exposes
   `GET /api/webhooks/events`, `GET/POST /api/webhooks/subscriptions`,
   `DELETE /api/webhooks/subscriptions/{id}`, and dead-letter
   inspect/replay endpoints. Admin/owner only. The module-level `fabric`
   singleton is imported by other routers to publish events.
3. **Events wired at their source:**
   - `payment.held` — `routers/payments.py`, `payment_decision()`, when a
     decision resolves to status `held`.
   - `incident.opened` — `routers/incidents.py`, `create_incident()`, and
     also from the auto-created incident on a `fraud` payment decision in
     `routers/payments.py`.
   - `vendor.blocked` — `routers/vendors.py`, `block_vendor()`, and from the
     incident `block_beneficiary` action in `routers/incidents.py`.
   - `beneficiary.changed` — `routers/beneficiaries.py`, `decide_change()`,
     once a beneficiary account change clears both approvals and callback
     verification and is pushed onto the vendor's approved account list.

Business logic and the risk engine never changed.

---

## Event catalogue

`payment.held` · `payment.approved` · `payment.rejected` · `beneficiary.changed`
· `vendor.blocked` · `incident.opened` · `incident.closed` ·
`verification.failed` · `verification.passed`

Subscribers filter on any subset, or `"*"` for all. Only the four events
listed above are currently published; the rest are reserved in the catalogue
for future wiring (e.g. `payment.approved`/`payment.rejected` from the same
`payment_decision()` status map).

---

## Security properties (addresses the audit)

- **Signed deliveries.** Every webhook carries `X-Vyapar-Signature`
  (`v1=HMAC_SHA256(secret, "{ts}.{body}")`). Receivers verify with the shipped
  `verify_signature()` and reject stale timestamps → replay-proof.
- **CSPRNG secrets.** Signing secrets use `secrets.token_hex` (the audit flagged
  `random` for verification codes — same fix applied here), shown to the
  integrator exactly once.
- **No double-billing.** Idempotency cache means two concurrent verifications of
  the same beneficiary share one provider call and one billed unit.
- **Fail-fast on dead providers.** The circuit breaker stops hammering a
  provider that's down and self-heals via a half-open probe.
- **Nothing lost.** Failed deliveries dead-letter and can be replayed once the
  downstream recovers.

---

## Still open (deliberately out of scope for this drop)

- Swap `InMemoryIdemStore` and the in-memory subscription list for Redis/Mongo
  so it survives restarts and works multi-process. Subscriptions are already
  persisted to `db.webhook_subscriptions` for audit purposes, but the live
  `EventFabric` in-memory registry (used for actual delivery) is not
  rehydrated from that collection on startup.
- Encrypt integration secrets at rest (audit item: they're plaintext in Mongo).
- Per-subscriber rate limiting and delivery metrics on a dashboard tile.
- `payment.approved` / `payment.rejected` / `verification.*` events are
  catalogued but not yet published anywhere.

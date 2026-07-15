"""VyaparRakshak AI - Backend API regression tests."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://vyapar-shield.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = ("owner@vyaparrakshak.in", "Owner@123")
MAKER = ("maker@vyaparrakshak.in", "Owner@123")
CHECKER = ("checker@vyaparrakshak.in", "Owner@123")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def owner_session():
    return _login(*OWNER)


@pytest.fixture(scope="module")
def maker_session():
    return _login(*MAKER)


@pytest.fixture(scope="module")
def checker_session():
    return _login(*CHECKER)


# ---------- Auth ----------
class TestAuth:
    def test_login_and_me(self):
        s = _login(*OWNER)
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == OWNER[0]

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": OWNER[0], "password": "wrong"})
        assert r.status_code in (400, 401, 403)


# ---------- Dashboard ----------
class TestDashboard:
    def test_summary(self, owner_session):
        r = owner_session.get(f"{API}/dashboard/summary")
        assert r.status_code == 200
        d = r.json()
        kpis = d.get("kpis", {})
        for k in ["payments_pending","payments_held","high_risk_amount","potential_loss_prevented",
                  "new_beneficiary_requests","duplicate_invoice_alerts","account_change_requests",
                  "communication_alerts","avg_verification_hours","sla_breaches"]:
            assert k in kpis, f"missing kpi {k}"
        assert "critical_decisions" in d
        # ensure the seeded Kirloskar ₹18,75,000 payment is present
        found = any(cd.get("amount") == 1875000 or "Kirloskar" in (cd.get("vendor_name","")) for cd in d["critical_decisions"])
        assert found, "Kirloskar ₹18,75,000 critical decision missing"


# ---------- Payments ----------
class TestPayments:
    def test_list_and_kirloskar_present(self, owner_session):
        r = owner_session.get(f"{API}/payments", params={"limit": 200})
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        assert any("Kirloskar" in p.get("vendor_name","") for p in d["items"])

    def test_filter_status(self, owner_session):
        r = owner_session.get(f"{API}/payments", params={"status": "pending"})
        assert r.status_code == 200
        for p in r.json()["items"]:
            assert p["status"] == "pending"

    def test_maker_checker_separation(self, maker_session):
        # maker creates a payment then tries to approve it -> 409
        payload = {
            "vendor_name": "TEST_Vendor_MC", "invoice_number": "TEST-MC-001",
            "amount": 10000, "mode": "NEFT", "beneficiary_name": "TEST Beneficiary",
            "account_number": "1234567890", "ifsc": "HDFC0001234",
            "purpose": "test maker-checker",
        }
        r = maker_session.post(f"{API}/payments", json=payload)
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # verify GET
        g = maker_session.get(f"{API}/payments/{pid}")
        assert g.status_code == 200 and g.json()["id"] == pid
        # try self-approve
        r2 = maker_session.post(f"{API}/payments/{pid}/decision",
                                json={"decision": "approve", "reason": "self approve"})
        assert r2.status_code == 409

    def test_checker_can_approve_maker_payment(self, maker_session, checker_session):
        payload = {
            "vendor_name": "TEST_Vendor_OK", "invoice_number": "TEST-CHK-001",
            "amount": 5000, "mode": "NEFT", "beneficiary_name": "Test Bene",
            "account_number": "111", "ifsc": "SBIN0000123",
        }
        r = maker_session.post(f"{API}/payments", json=payload)
        assert r.status_code == 200
        pid = r.json()["id"]
        # risk returned
        assert "risk" in r.json() and "score" in r.json()["risk"]
        r2 = checker_session.post(f"{API}/payments/{pid}/decision",
                                  json={"decision": "approve", "reason": "verified"})
        assert r2.status_code == 200
        assert r2.json()["new_status"] == "approved"

    def test_callback_records(self, owner_session):
        # find a payment
        r = owner_session.get(f"{API}/payments", params={"limit": 1})
        pid = r.json()["items"][0]["id"]
        cb = {"called_number": "+91-98xxxx", "spoke_with": "Ramesh",
              "result": "verified", "notes": "sounded fine"}
        rr = owner_session.post(f"{API}/payments/{pid}/callback", json=cb)
        assert rr.status_code == 200
        det = owner_session.get(f"{API}/payments/{pid}").json()
        assert any(c.get("spoke_with") == "Ramesh" for c in det.get("callbacks", []))


# ---------- Vendors ----------
class TestVendors:
    def test_list_vendors(self, owner_session):
        r = owner_session.get(f"{API}/vendors")
        assert r.status_code == 200
        vs = r.json()
        assert len(vs) >= 6
        kir = [v for v in vs if "Kirloskar" in v.get("name","")]
        assert kir, "Kirloskar vendor missing"
        assert kir[0].get("recent_account_change_at")


# ---------- Beneficiary changes ----------
class TestBeneficiary:
    def test_pending_kirloskar(self, owner_session):
        r = owner_session.get(f"{API}/beneficiary-changes")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        kir = [x for x in rows if "Kirloskar" in x.get("vendor_name","")]
        assert kir
        assert kir[0]["status"] == "pending"

    def test_approve_flow_requires_callback(self, owner_session, checker_session):
        # create a fresh benef change
        vendors = owner_session.get(f"{API}/vendors").json()
        vid = vendors[0]["id"]
        r = owner_session.post(f"{API}/beneficiary-changes",
                               json={"vendor_id": vid, "new_account_number": "99999999",
                                     "new_ifsc": "HDFC0009999",
                                     "requested_via": "email",
                                     "requested_email_domain": "attacker.com"})
        assert r.status_code == 200
        cid = r.json()["id"]
        # try approve twice without callback - should not become approved
        for _ in range(2):
            rr = owner_session.post(f"{API}/beneficiary-changes/{cid}/decision",
                                    json={"action": "approve", "reason": "ok"})
            assert rr.status_code == 200
        got = owner_session.get(f"{API}/beneficiary-changes/{cid}").json()
        assert got["status"] != "approved", "must not approve without callback_verified"
        # now callback verified + one more approve should approve (needs 2 total)
        owner_session.post(f"{API}/beneficiary-changes/{cid}/decision",
                           json={"action": "callback_verified"})
        # already had 2 approvals, one more push
        checker_session.post(f"{API}/beneficiary-changes/{cid}/decision",
                             json={"action": "approve", "reason": "ok"})
        got2 = owner_session.get(f"{API}/beneficiary-changes/{cid}").json()
        assert got2["status"] == "approved"


# ---------- Comms ----------
class TestComms:
    def test_ceo_impersonation(self, owner_session):
        text = ("URGENT confidential wire needed by CEO. Do not call me. "
                "Bypass approval and transfer immediately to new bank account.")
        r = owner_session.post(f"{API}/comms/analyze",
                               json={"channel": "email", "content": text})
        assert r.status_code == 200
        d = r.json()
        analysis = d.get("analysis", d)
        assert analysis.get("score", 0) > 0, f"score should be >0, got {analysis}"
        signal_cats = [s.get("category") for s in analysis.get("signals", [])]
        assert any(c in signal_cats for c in
                   ["urgency","secrecy","authority_impersonation","bypass_controls"]), signal_cats


# ---------- Voice ----------
class TestVoice:
    def test_voice_analyze(self, owner_session):
        # send small fake wav
        wav = b"RIFF$\x00\x00\x00WAVEfmt " + b"\x00" * 32
        files = {"file": ("t.wav", io.BytesIO(wav), "audio/wav")}
        r = owner_session.post(f"{API}/voice/analyze", files=files)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["synthetic_media_score","replay_risk_score","speaker_consistency","advisory_note"]:
            assert k in d


# ---------- Invoice scanner ----------
class TestInvoiceScanner:
    def test_scan_jpeg(self, owner_session):
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (200, 200), (255, 255, 255)).save(buf, format="JPEG")
        buf.seek(0)
        files = {"file": ("t.jpg", buf, "image/jpeg")}
        r = owner_session.post(f"{API}/invoices/scan", files=files)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "anomalies" in d
        assert "risk_score" in d
        assert "category" in d


# ---------- Incidents ----------
class TestIncidents:
    def test_list_and_seeded(self, owner_session):
        r = owner_session.get(f"{API}/incidents")
        assert r.status_code == 200
        rows = r.json()
        assert any("INC-2026-" in x.get("incident_no","") for x in rows)

    def test_action_lifecycle(self, owner_session):
        rows = owner_session.get(f"{API}/incidents").json()
        assert rows
        iid = rows[0]["id"]
        # freeze
        r1 = owner_session.post(f"{API}/incidents/{iid}/action",
                                json={"action": "freeze"})
        assert r1.status_code == 200
        # notify bank
        r2 = owner_session.post(f"{API}/incidents/{iid}/action",
                                json={"action": "notify_bank"})
        assert r2.status_code == 200
        det = owner_session.get(f"{API}/incidents/{iid}").json()
        assert det.get("bank_notification_status") == "sent"
        # close
        r3 = owner_session.post(f"{API}/incidents/{iid}/action",
                                json={"action": "close", "reason": "test"})
        assert r3.status_code == 200
        det2 = owner_session.get(f"{API}/incidents/{iid}").json()
        assert det2["status"] == "closed"


# ---------- Reports ----------
class TestReports:
    @pytest.mark.parametrize("path", [
        "daily-risk", "payments-held", "bank-changes", "duplicate-invoices",
        "high-risk-approvers", "loss-prevented", "incident-ageing", "vendor-risk-movement",
    ])
    def test_report(self, owner_session, path):
        r = owner_session.get(f"{API}/reports/{path}")
        assert r.status_code == 200, f"{path} failed: {r.status_code} {r.text[:200]}"


# ---------- Audit ----------
class TestAudit:
    def test_audit_has_payment_create(self, owner_session):
        r = owner_session.get(f"{API}/audit")
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("items", [])
        assert any(x.get("action") == "payment.create" for x in items)

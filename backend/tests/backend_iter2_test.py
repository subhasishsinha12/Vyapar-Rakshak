"""Iteration 2 tests: integrations adapters, vendor portal, PDF exports."""
import io
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

OWNER = ("owner@vyaparrakshak.in", "Owner@123")
VENDOR = ("vendor@textilepro.in", "Owner@123")
MAKER = ("maker@vyaparrakshak.in", "Owner@123")
FINANCE = ("finance@vyaparrakshak.in", "Owner@123")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def owner_s():
    return _login(*OWNER)


@pytest.fixture(scope="module")
def vendor_s():
    return _login(*VENDOR)


@pytest.fixture(scope="module")
def maker_s():
    return _login(*MAKER)


@pytest.fixture(scope="module")
def finance_s():
    return _login(*FINANCE)


# ---------- Integrations ----------
class TestIntegrations:
    def test_get_owner(self, owner_s):
        r = owner_s.get(f"{API}/settings/integrations")
        assert r.status_code == 200
        d = r.json()
        snap = d.get("snapshot", d)
        for k in ("gst", "bank", "deepfake"):
            assert k in snap, f"missing {k} in snapshot: {snap}"
            assert snap[k].get("provider") == "mock"
            assert isinstance(snap[k].get("available_providers"), list) and snap[k]["available_providers"]

    def test_get_forbidden_for_maker(self, maker_s):
        r = maker_s.get(f"{API}/settings/integrations")
        assert r.status_code == 403, f"expected 403, got {r.status_code}"

    def test_put_and_mask(self, owner_s):
        body = {
            "gst": {"provider": "mock"},
            "bank": {"provider": "mock"},
            "deepfake": {"provider": "mock"},
        }
        r = owner_s.put(f"{API}/settings/integrations", json=body)
        assert r.status_code == 200, r.text
        # subsequent GET still works
        g = owner_s.get(f"{API}/settings/integrations")
        assert g.status_code == 200

    def test_test_gst(self, owner_s):
        r = owner_s.post(f"{API}/settings/integrations/test/gst", json={})
        assert r.status_code == 200, r.text
        d = r.json()
        # Look through response body for provider=mock and simulated=true
        text = str(d).lower()
        assert "mock" in text
        assert "simulated" in text or d.get("simulated") is True or d.get("result", {}).get("simulated") is True

    def test_test_bank(self, owner_s):
        r = owner_s.post(f"{API}/settings/integrations/test/bank", json={})
        assert r.status_code == 200, r.text
        d = r.json()
        assert "verdict" in str(d).lower()

    def test_test_deepfake(self, owner_s):
        r = owner_s.post(f"{API}/settings/integrations/test/deepfake", json={})
        assert r.status_code == 200, r.text


# ---------- Vendor adapter routes on vendors ----------
class TestVendorAdapters:
    def test_verify_gst(self, owner_s):
        vs = owner_s.get(f"{API}/vendors").json()
        vid = vs[0]["id"]
        r = owner_s.post(f"{API}/vendors/{vid}/verify-gst")
        assert r.status_code == 200, r.text
        d = r.json()
        # provider mock + ok true + legal_name + status
        assert d.get("provider") == "mock"
        assert d.get("ok") is True
        assert "legal_name" in d or "gstin" in d
        # audit trail entry created
        aud = owner_s.get(f"{API}/audit").json()
        items = aud if isinstance(aud, list) else aud.get("items", [])
        assert any(x.get("action") == "vendor.gst_verify" for x in items), "audit vendor.gst_verify missing"

    def test_verify_bank(self, owner_s):
        vs = owner_s.get(f"{API}/vendors").json()
        vid = vs[0]["id"]
        body = {"account_number": "1234567890", "ifsc": "HDFC0001234", "expected_name": "Test Bene"}
        r = owner_s.post(f"{API}/vendors/{vid}/verify-bank", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("verdict") in ("match", "partial", "mismatch")
        assert "name_match_score" in d


# ---------- Vendor Portal ----------
class TestVendorPortal:
    def test_me(self, vendor_s):
        r = vendor_s.get(f"{API}/vendor/me")
        assert r.status_code == 200, r.text
        d = r.json()
        v = d.get("vendor", d)
        assert "TextilePro" in v.get("name", ""), v
        assert "approved_bank_accounts" in v
        # kyc_documents may be at top level or in vendor
        assert "kyc_documents" in d or "kyc_documents" in v

    def test_me_forbidden_for_owner(self, owner_s):
        r = owner_s.get(f"{API}/vendor/me")
        assert r.status_code == 403

    def test_payments(self, vendor_s):
        r = vendor_s.get(f"{API}/vendor/payments")
        assert r.status_code == 200
        d = r.json()
        items = d if isinstance(d, list) else d.get("items", [])
        # Optional: all belong to TextilePro
        assert isinstance(items, list)

    def test_kyc_upload(self, vendor_s):
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (50, 50), (255, 255, 255)).save(buf, format="PNG")
        buf.seek(0)
        files = {"file": ("pan.png", buf, "image/png")}
        data = {"kind": "pan_card", "notes": ""}
        r = vendor_s.post(f"{API}/vendor/kyc", files=files, data=data)
        assert r.status_code == 200, r.text
        d = r.json()
        assert (d.get("status") or d.get("record", {}).get("status")) == "pending_review"
        # store doc id for review test
        pytest.kyc_doc_id = d.get("id") or d.get("record", {}).get("id")

    def test_kyc_review_by_finance(self, finance_s):
        doc_id = getattr(pytest, "kyc_doc_id", None)
        if not doc_id:
            pytest.skip("no kyc doc id from upload")
        r = finance_s.post(f"{API}/vendor/kyc/review", json={"doc_id": doc_id, "status": "approved"})
        assert r.status_code == 200, r.text

    def test_bank_change(self, vendor_s, owner_s):
        body = {
            "new_account_number": "88887777",
            "new_ifsc": "HDFC0008888",
            "new_bank": "HDFC Bank",
            "contact_phone": "+91-9000000000",
        }
        r = vendor_s.post(f"{API}/vendor/bank-change", json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        row = d if "status" in d else d.get("record", {})
        assert row.get("status") == "pending"
        assert row.get("requested_via") == "vendor_portal"
        # appears in buyer's beneficiary-changes list
        bc = owner_s.get(f"{API}/beneficiary-changes").json()
        rows = bc if isinstance(bc, list) else bc.get("items", [])
        assert any(x.get("requested_via") == "vendor_portal" for x in rows), "vendor_portal bc not visible to buyer"


# ---------- PDF exports ----------
REPORTS = [
    "daily-risk", "payments-held", "bank-changes", "duplicate-invoices",
    "high-risk-approvers", "loss-prevented", "incident-ageing", "vendor-risk-movement",
]


class TestPdfExports:
    @pytest.mark.parametrize("path", REPORTS)
    def test_pdf(self, owner_s, path):
        r = owner_s.get(f"{API}/reports/{path}", params={"format": "pdf"})
        assert r.status_code == 200, f"{path} pdf failed: {r.status_code}"
        assert "application/pdf" in r.headers.get("content-type", "").lower(), r.headers
        cd = r.headers.get("content-disposition", "").lower()
        assert "attachment" in cd, cd
        assert len(r.content) > 100

    @pytest.mark.parametrize("path", REPORTS)
    def test_json_regression(self, owner_s, path):
        r = owner_s.get(f"{API}/reports/{path}")
        assert r.status_code == 200, r.text
        d = r.json()
        # loss-prevented uses aggregate shape (breakdown/total_prevented); accept either
        assert "items" in d or "breakdown" in d or "total_prevented" in d, f"{path} unexpected shape: {d}"

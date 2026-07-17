"""Bank account verification adapters – Mock, Razorpay, Cashfree.

Uses penny-drop / name-match APIs to confirm the account exists and the
account-holder name matches the beneficiary on record.
"""
import os
import re
import logging
import difflib
import hashlib
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger("adapters.bank")

IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


def _match_score(a: str, b: str) -> int:
    if not a or not b:
        return 0
    r = difflib.SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()
    return int(round(r * 100))


class MockBankAdapter:
    provider = "mock"
    live = False

    async def penny_drop(self, account_number: str, ifsc: str,
                         expected_name: Optional[str] = None) -> Dict[str, Any]:
        acc = (account_number or "").strip()
        ifsc = (ifsc or "").upper().strip()
        if not acc or len(acc) < 6:
            return {"ok": False, "provider": self.provider,
                    "error": "Account number invalid", "simulated": True}
        if not IFSC_RE.match(ifsc):
            return {"ok": False, "provider": self.provider,
                    "error": "IFSC invalid", "simulated": True}
        # Deterministic pseudo-name derived from digest — for demo variety.
        h = hashlib.sha256(acc.encode()).hexdigest()[:6]
        name_at_bank = expected_name or f"Account Holder {h.upper()}"
        # If the account looks suspicious (from the seed) return a mismatch:
        if acc.startswith("6099911") or acc.startswith("77712345") or acc.startswith("62888112"):
            name_at_bank = f"UNKNOWN HOLDER {h.upper()}"
        score = _match_score(name_at_bank, expected_name or name_at_bank)
        return {
            "ok": True, "provider": self.provider, "simulated": True,
            "account_number_last4": acc[-4:],
            "ifsc": ifsc,
            "bank_name": {"HDFC0000123": "HDFC Bank", "ICIC0000456": "ICICI Bank",
                          "SBIN0004321": "State Bank of India", "AXIS0000112": "Axis Bank",
                          "IOBA0000789": "Indian Overseas Bank",
                          "YESB0000199": "Yes Bank",
                          "KKBK0000876": "Kotak Mahindra Bank"}.get(ifsc, "Unknown Bank"),
            "branch": "—",
            "name_at_bank": name_at_bank,
            "name_match_score": score,
            "verdict": "match" if score >= 80 else ("partial" if score >= 55 else "mismatch"),
            "note": "This is a mocked response. Wire Razorpay / Cashfree keys to go live.",
        }


class RazorpayBankAdapter:
    provider = "razorpay"
    live = True

    def __init__(self, key_id: str, key_secret: str):
        self.key_id = key_id
        self.key_secret = key_secret
        self.base_url = "https://api.razorpay.com/v1"

    async def penny_drop(self, account_number: str, ifsc: str,
                         expected_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20,
                                          auth=(self.key_id, self.key_secret)) as client:
                # Fund-account validation (Razorpay X)
                r = await client.post(
                    f"{self.base_url}/fund_accounts/validations",
                    json={"account_type": "bank_account",
                          "bank_account": {"name": expected_name or "Beneficiary",
                                           "ifsc": ifsc,
                                           "account_number": account_number},
                          "amount": 100, "currency": "INR"},
                )
            r.raise_for_status()
            data = r.json()
            name_at_bank = ((data.get("bank_account") or {}).get("beneficiary_name")
                            or data.get("results", {}).get("account_status") or "")
            score = _match_score(name_at_bank, expected_name or "")
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "account_number_last4": account_number[-4:],
                "ifsc": ifsc,
                "bank_name": (data.get("bank_account") or {}).get("bank_name") or "—",
                "branch": (data.get("bank_account") or {}).get("branch_name") or "—",
                "name_at_bank": name_at_bank,
                "name_match_score": score,
                "verdict": "match" if score >= 80 else ("partial" if score >= 55 else "mismatch"),
                "raw": data,
            }
        except Exception as e:
            logger.error(f"Razorpay penny_drop failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}


class CashfreeBankAdapter:
    provider = "cashfree"
    live = True

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://payout-api.cashfree.com/payout/v1"
        self._token: Optional[str] = None

    async def _token_get(self, client: httpx.AsyncClient) -> str:
        r = await client.post(
            f"{self.base_url}/authorize",
            headers={"X-Client-Id": self.client_id, "X-Client-Secret": self.client_secret},
        )
        r.raise_for_status()
        self._token = r.json()["data"]["token"]
        return self._token

    async def penny_drop(self, account_number: str, ifsc: str,
                         expected_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                tok = await self._token_get(client)
                r = await client.get(
                    f"{self.base_url}/validation/bankDetails",
                    headers={"Authorization": f"Bearer {tok}"},
                    params={"bankAccount": account_number, "ifsc": ifsc,
                            "name": expected_name or ""},
                )
            r.raise_for_status()
            data = r.json().get("data", {})
            name_at_bank = data.get("nameAtBank") or ""
            score = _match_score(name_at_bank, expected_name or "")
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "account_number_last4": account_number[-4:],
                "ifsc": ifsc,
                "bank_name": data.get("bankName") or "—",
                "branch": data.get("branch") or "—",
                "name_at_bank": name_at_bank,
                "name_match_score": score,
                "verdict": "match" if score >= 80 else ("partial" if score >= 55 else "mismatch"),
                "raw": data,
            }
        except Exception as e:
            logger.error(f"Cashfree penny_drop failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}

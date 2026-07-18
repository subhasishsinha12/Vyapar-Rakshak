"""Mobile-number fraud-risk adapters – Mock, Cashfree, Signzy.

Checks a beneficiary/contact mobile number against India's Financial Fraud
Risk Indicator (FRI) lineage: DoT's Digital Intelligence Platform classifies
numbers Medium / High / Very High risk using signals from the National
Cybercrime Reporting Portal (NCRP), DoT's Chakshu platform, and bank-reported
intelligence — the same "check before money moves" signal RBI advised banks
to integrate from 30 June 2025.

VyaparRakshak is not itself a bank/NBFC/UPI PSP, so it has no direct DPIP/FRI
API access (those are gated to RBI-regulated entities). The live providers
here instead wrap FRI-derived signals via a licensed payment aggregator or
KYC/risk vendor that already sits inside that regulated perimeter — e.g.
Cashfree RiskShield's Fraud Risk Indicator product resells the government
signal to any subscribing merchant. Endpoints below are best-effort templates
pending each vendor's live integration docs and a real API key — exactly the
same caveat that already applies to this repo's other "live" adapters
(Karza, Razorpay, Reality Defender, ...).
"""
import re
import hashlib
import logging
from typing import Dict, Any

import httpx

from services.vyapar_fabric.base_adapter import BaseAdapter
from services.vyapar_fabric.resilience import TransientError

logger = logging.getLogger("adapters.mobile_risk")


def _mask(mobile: str) -> str:
    digits = re.sub(r"\D", "", mobile or "")
    return f"XXXXXX{digits[-4:]}" if len(digits) >= 4 else "XXXXXX"


def _normalise(mobile: str) -> str:
    digits = re.sub(r"\D", "", mobile or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits


def _recommendation(risk_level: str) -> str:
    return {"very_high": "block", "high": "warn", "medium": "warn",
            "low": "allow"}.get(risk_level, "allow")


class MockMobileRiskAdapter(BaseAdapter):
    provider = "mock"
    live = False

    # A handful of seeded numbers so the demo can show every risk tier.
    _SEEDED = {
        "9099911234": "very_high",
        "7771234567": "high",
        "6288811222": "medium",
    }

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        raw = args.get("mobile_number") or ""
        digits = _normalise(raw)
        if len(digits) != 10 or digits[0] not in "6789":
            return {"ok": False, "error": "Mobile number invalid", "simulated": True}

        risk_level = self._SEEDED.get(digits)
        if risk_level is None:
            # Deterministic pseudo-classification from hash — mostly "low".
            h = int(hashlib.sha256(digits.encode()).hexdigest()[:2], 16)
            risk_level = "low" if h < 220 else "medium"

        return {
            "ok": True, "simulated": True,
            "mobile_number_masked": _mask(raw),
            "risk_level": risk_level,
            "risk_score": {"low": 5, "medium": 45, "high": 75, "very_high": 95}[risk_level],
            "sources": ["mock"] if risk_level == "low" else ["mock", "NCRP (simulated)"],
            "recommendation": _recommendation(risk_level),
            "note": "This is a mocked response. Wire Cashfree / Signzy keys to go live.",
        }

    async def check(self, mobile_number: str) -> Dict[str, Any]:
        return await self.run("check", {"mobile_number": mobile_number})


class CashfreeMobileRiskAdapter(BaseAdapter):
    """Wraps Cashfree RiskShield's Fraud Risk Indicator product, which
    resells DoT's government FRI mobile-number risk signal to subscribing
    merchants (Cashfree is a licensed Payment Aggregator with DIP access)."""
    provider = "cashfree"
    live = True

    def __init__(self, api_key: str, **kw):
        super().__init__(**kw)
        self.api_key = api_key
        self.base_url = "https://api.cashfree.com/verification"

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        mobile_number = args.get("mobile_number") or ""
        digits = _normalise(mobile_number)
        if len(digits) != 10:
            return {"ok": False, "error": "Mobile number invalid"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(
                    f"{self.base_url}/fraud-risk-indicator",
                    headers={"x-client-id": self.api_key, "Content-Type": "application/json"},
                    json={"phone": digits},
                )
        except httpx.TransportError as e:
            raise TransientError(f"network: {e}") from e

        if r.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"provider {r.status_code}")
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Cashfree mobile risk check failed: {e}")
            return {"ok": False, "error": str(e)}

        data = r.json()
        risk_level = (data.get("risk_level") or data.get("fri_category") or "unknown").lower()
        return {
            "ok": True, "simulated": False,
            "mobile_number_masked": _mask(mobile_number),
            "risk_level": risk_level,
            "risk_score": data.get("risk_score"),
            "sources": data.get("sources") or ["DoT FRI (via Cashfree RiskShield)"],
            "recommendation": _recommendation(risk_level),
            "raw": data,
        }

    async def check(self, mobile_number: str) -> Dict[str, Any]:
        return await self.run("check", {"mobile_number": mobile_number})


class SignzyMobileRiskAdapter(BaseAdapter):
    """Wraps Signzy's mobile-intelligence / fraud-risk product."""
    provider = "signzy"
    live = True

    def __init__(self, api_key: str, **kw):
        super().__init__(**kw)
        self.api_key = api_key
        self.base_url = "https://api.signzy.app/api/v3/mobile-intelligence"

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        mobile_number = args.get("mobile_number") or ""
        digits = _normalise(mobile_number)
        if len(digits) != 10:
            return {"ok": False, "error": "Mobile number invalid"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(
                    f"{self.base_url}/risk-check",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"mobileNumber": digits},
                )
        except httpx.TransportError as e:
            raise TransientError(f"network: {e}") from e

        if r.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"provider {r.status_code}")
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Signzy mobile risk check failed: {e}")
            return {"ok": False, "error": str(e)}

        data = r.json().get("result") or {}
        risk_level = (data.get("riskCategory") or "unknown").lower()
        return {
            "ok": True, "simulated": False,
            "mobile_number_masked": _mask(mobile_number),
            "risk_level": risk_level,
            "risk_score": data.get("riskScore"),
            "sources": data.get("sources") or ["Signzy"],
            "recommendation": _recommendation(risk_level),
            "raw": data,
        }

    async def check(self, mobile_number: str) -> Dict[str, Any]:
        return await self.run("check", {"mobile_number": mobile_number})

"""GST verification adapters – Mock, Karza, ClearTax."""
import os
import re
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger("adapters.gst")

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z][A-Z\d]{1}$")


class MockGSTAdapter:
    provider = "mock"
    live = False

    async def verify(self, gstin: str) -> Dict[str, Any]:
        gstin = (gstin or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "provider": self.provider,
                    "error": "GSTIN format invalid",
                    "simulated": True}
        # Deterministic pseudo-response from gstin
        legal = f"{gstin[2:7]} Business Pvt Ltd (mock)"
        return {
            "ok": True, "provider": self.provider, "simulated": True,
            "gstin": gstin,
            "legal_name": legal,
            "trade_name": legal.replace(" Pvt Ltd (mock)", ""),
            "status": "Active",
            "registration_date": "2019-06-14",
            "filing_status": "Regular filer – last GSTR-3B filed",
            "address": "Registered address on record with GSTN (mock)",
            "note": "This is a mocked response. Wire Karza / ClearTax keys to go live.",
        }


class KarzaGSTAdapter:
    provider = "karza"
    live = True

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.karza.in/v3"

    async def verify(self, gstin: str) -> Dict[str, Any]:
        gstin = (gstin or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "provider": self.provider,
                    "error": "GSTIN format invalid"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{self.base_url}/gstin",
                    headers={"x-karza-key": self.api_key},
                    json={"gstin": gstin, "consent": "Y", "consent_text": "I hereby declare my consent for fetching GSTIN details."},
                )
            r.raise_for_status()
            data = r.json()
            result = data.get("result") or {}
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "gstin": gstin,
                "legal_name": result.get("legalName"),
                "trade_name": result.get("tradeName"),
                "status": result.get("status"),
                "registration_date": result.get("registrationDate"),
                "filing_status": result.get("filingStatus") or "—",
                "address": result.get("principalPlaceAddress"),
                "raw": result,
            }
        except Exception as e:
            logger.error(f"Karza verify failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}


class ClearTaxGSTAdapter:
    provider = "cleartax"
    live = True

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cleartax.in/gst/v1"

    async def verify(self, gstin: str) -> Dict[str, Any]:
        gstin = (gstin or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "provider": self.provider,
                    "error": "GSTIN format invalid"}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{self.base_url}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params={"gstin": gstin},
                )
            r.raise_for_status()
            data = r.json()
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "gstin": gstin,
                "legal_name": data.get("lgnm"),
                "trade_name": data.get("tradeNam"),
                "status": data.get("sts"),
                "registration_date": data.get("rgdt"),
                "filing_status": data.get("stjCd") or "—",
                "address": (data.get("pradr") or {}).get("adr"),
                "raw": data,
            }
        except Exception as e:
            logger.error(f"ClearTax verify failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}

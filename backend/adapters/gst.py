"""GST verification adapters – Mock, Karza, ClearTax.

Each provider is a thin subclass of the Integration Fabric's ``BaseAdapter``
(``services/vyapar_fabric``): implement ``_call``, inherit retry with
backoff, circuit breaking, per-attempt timeout and idempotent caching for
free. ``verify(gstin)`` is kept as the public entry point so existing callers
(routers/vendors.py, routers/settings.py) are unaffected.
"""
import re
import logging
from typing import Dict, Any

import httpx

from services.vyapar_fabric.base_adapter import BaseAdapter
from services.vyapar_fabric.resilience import TransientError

logger = logging.getLogger("adapters.gst")

GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z][A-Z\d]{1}$")


class MockGSTAdapter(BaseAdapter):
    provider = "mock"
    live = False

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        gstin = (args.get("gstin") or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "error": "GSTIN format invalid", "simulated": True}
        # Deterministic pseudo-response from gstin
        legal = f"{gstin[2:7]} Business Pvt Ltd (mock)"
        return {
            "ok": True, "simulated": True,
            "gstin": gstin,
            "legal_name": legal,
            "trade_name": legal.replace(" Pvt Ltd (mock)", ""),
            "status": "Active",
            "registration_date": "2019-06-14",
            "filing_status": "Regular filer – last GSTR-3B filed",
            "address": "Registered address on record with GSTN (mock)",
            "note": "This is a mocked response. Wire Karza / ClearTax keys to go live.",
        }

    async def verify(self, gstin: str) -> Dict[str, Any]:
        return await self.run("verify", {"gstin": gstin})


class KarzaGSTAdapter(BaseAdapter):
    provider = "karza"
    live = True

    def __init__(self, api_key: str, **kw):
        super().__init__(**kw)
        self.api_key = api_key
        self.base_url = "https://api.karza.in/v3"

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        gstin = (args.get("gstin") or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "error": "GSTIN format invalid"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(
                    f"{self.base_url}/gstin",
                    headers={"x-karza-key": self.api_key},
                    json={"gstin": gstin, "consent": "Y", "consent_text": "I hereby declare my consent for fetching GSTIN details."},
                )
        except httpx.TransportError as e:
            raise TransientError(f"network: {e}") from e

        if r.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"provider {r.status_code}")
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Karza verify failed: {e}")
            return {"ok": False, "error": str(e)}

        data = r.json()
        result = data.get("result") or {}
        return {
            "ok": True, "simulated": False,
            "gstin": gstin,
            "legal_name": result.get("legalName"),
            "trade_name": result.get("tradeName"),
            "status": result.get("status"),
            "registration_date": result.get("registrationDate"),
            "filing_status": result.get("filingStatus") or "—",
            "address": result.get("principalPlaceAddress"),
            "raw": result,
        }

    async def verify(self, gstin: str) -> Dict[str, Any]:
        return await self.run("verify", {"gstin": gstin})


class ClearTaxGSTAdapter(BaseAdapter):
    provider = "cleartax"
    live = True

    def __init__(self, api_key: str, **kw):
        super().__init__(**kw)
        self.api_key = api_key
        self.base_url = "https://api.cleartax.in/gst/v1"

    async def _call(self, operation: str, args: dict) -> Dict[str, Any]:
        gstin = (args.get("gstin") or "").upper().strip()
        if not GSTIN_RE.match(gstin):
            return {"ok": False, "error": "GSTIN format invalid"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.get(
                    f"{self.base_url}/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    params={"gstin": gstin},
                )
        except httpx.TransportError as e:
            raise TransientError(f"network: {e}") from e

        if r.status_code in (429, 500, 502, 503, 504):
            raise TransientError(f"provider {r.status_code}")
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"ClearTax verify failed: {e}")
            return {"ok": False, "error": str(e)}

        data = r.json()
        return {
            "ok": True, "simulated": False,
            "gstin": gstin,
            "legal_name": data.get("lgnm"),
            "trade_name": data.get("tradeNam"),
            "status": data.get("sts"),
            "registration_date": data.get("rgdt"),
            "filing_status": data.get("stjCd") or "—",
            "address": (data.get("pradr") or {}).get("adr"),
            "raw": data,
        }

    async def verify(self, gstin: str) -> Dict[str, Any]:
        return await self.run("verify", {"gstin": gstin})

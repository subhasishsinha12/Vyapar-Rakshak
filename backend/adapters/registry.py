"""Adapter registry – singleton, driven by system_settings.integrations."""
import os
import logging
from typing import Optional

from .gst import MockGSTAdapter, KarzaGSTAdapter, ClearTaxGSTAdapter
from .bank import MockBankAdapter, RazorpayBankAdapter, CashfreeBankAdapter
from .deepfake import MockDeepfakeAdapter, RealityDefenderAdapter, PindropAdapter

logger = logging.getLogger("adapters.registry")


class Registry:
    def __init__(self):
        self.gst = MockGSTAdapter()
        self.bank = MockBankAdapter()
        self.deepfake = MockDeepfakeAdapter()
        self._config: dict = {}

    def snapshot(self) -> dict:
        return {
            "gst": {"provider": self.gst.provider,
                    "live": getattr(self.gst, "live", False),
                    "available_providers": ["mock", "karza", "cleartax"]},
            "bank": {"provider": self.bank.provider,
                     "live": getattr(self.bank, "live", False),
                     "available_providers": ["mock", "razorpay", "cashfree"]},
            "deepfake": {"provider": self.deepfake.provider,
                         "live": getattr(self.deepfake, "live", False),
                         "available_providers": ["mock", "reality_defender", "pindrop"]},
        }

    def configure(self, cfg: dict):
        """cfg = {gst: {provider, ...keys}, bank: {...}, deepfake: {...}}"""
        self._config = cfg or {}
        # GST
        g = self._config.get("gst") or {}
        gp = g.get("provider", "mock")
        if gp == "karza" and g.get("api_key"):
            self.gst = KarzaGSTAdapter(g["api_key"])
        elif gp == "cleartax" and g.get("api_key"):
            self.gst = ClearTaxGSTAdapter(g["api_key"])
        else:
            self.gst = MockGSTAdapter()

        # Bank
        b = self._config.get("bank") or {}
        bp = b.get("provider", "mock")
        if bp == "razorpay" and b.get("key_id") and b.get("key_secret"):
            self.bank = RazorpayBankAdapter(b["key_id"], b["key_secret"])
        elif bp == "cashfree" and b.get("client_id") and b.get("client_secret"):
            self.bank = CashfreeBankAdapter(b["client_id"], b["client_secret"])
        else:
            self.bank = MockBankAdapter()

        # Deepfake
        d = self._config.get("deepfake") or {}
        dp = d.get("provider", "mock")
        if dp == "reality_defender" and d.get("api_key"):
            self.deepfake = RealityDefenderAdapter(d["api_key"])
        elif dp == "pindrop" and d.get("api_key"):
            self.deepfake = PindropAdapter(d["api_key"])
        else:
            self.deepfake = MockDeepfakeAdapter()

        logger.info(f"Adapters configured: {self.snapshot()}")


registry = Registry()

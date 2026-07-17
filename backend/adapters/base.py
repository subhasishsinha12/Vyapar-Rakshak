"""Replaceable-adapter interfaces for external verification services.

Every adapter implementation returns a normalised dict so callers do not
depend on the specific provider. Swap providers via /api/settings/integrations
without touching business code.
"""
from typing import Protocol, Dict, Any


class GSTAdapter(Protocol):
    provider: str

    async def verify(self, gstin: str) -> Dict[str, Any]:
        """Return {ok, provider, legal_name, trade_name, status, address,
                    registration_date, filing_status, error?}."""
        ...


class BankAdapter(Protocol):
    provider: str

    async def penny_drop(self, account_number: str, ifsc: str,
                        expected_name: str | None = None) -> Dict[str, Any]:
        """Return {ok, provider, name_at_bank, name_match_score,
                    bank_name, branch, error?, simulated}."""
        ...


class DeepfakeAdapter(Protocol):
    provider: str

    async def screen(self, data: bytes, mime: str) -> Dict[str, Any]:
        """Return {ok, provider, synthetic_media_score, replay_risk_score,
                    speaker_consistency, metadata_anomalies, verdict, error?,
                    simulated}."""
        ...

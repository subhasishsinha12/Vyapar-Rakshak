"""Deepfake / synthetic-media adapters – Mock, Reality Defender, Pindrop."""
import os
import logging
import hashlib
import httpx
from typing import Dict, Any

logger = logging.getLogger("adapters.deepfake")


def _verdict(synth: int, replay: int, consistency: float) -> str:
    if synth >= 75 or consistency < 0.5:
        return "likely_synthetic"
    if synth >= 55 or replay >= 60:
        return "suspicious"
    return "likely_authentic"


class MockDeepfakeAdapter:
    provider = "mock"
    live = False

    async def screen(self, data: bytes, mime: str) -> Dict[str, Any]:
        h = hashlib.sha256(data).hexdigest()
        # deterministic pseudo scores based on hash — for demo variety
        synth = 30 + (int(h[:2], 16) % 55)
        replay = 10 + (int(h[2:4], 16) % 55)
        consistency = round(0.5 + (int(h[4:6], 16) % 45) / 100, 2)
        return {
            "ok": True, "provider": self.provider, "simulated": True,
            "synthetic_media_score": synth,
            "replay_risk_score": replay,
            "speaker_consistency": consistency,
            "metadata_anomalies": [] if len(data) > 5000 else ["truncated_or_missing_metadata"],
            "verdict": _verdict(synth, replay, consistency),
            "note": "This is a mocked response. Wire Reality Defender / Pindrop keys to go live.",
        }


class RealityDefenderAdapter:
    provider = "reality_defender"
    live = True

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.realitydefender.com/v1"

    async def screen(self, data: bytes, mime: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.base_url}/detect/audio",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"media": ("clip", data, mime)},
                )
            r.raise_for_status()
            data_json = r.json()
            synth = int((data_json.get("scores", {}).get("synthetic", 0)) * 100)
            consistency = float(data_json.get("scores", {}).get("speaker_consistency", 0.5))
            replay = int((data_json.get("scores", {}).get("replay", 0)) * 100)
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "synthetic_media_score": synth,
                "replay_risk_score": replay,
                "speaker_consistency": consistency,
                "metadata_anomalies": data_json.get("metadata_anomalies") or [],
                "verdict": _verdict(synth, replay, consistency),
                "raw": data_json,
            }
        except Exception as e:
            logger.error(f"RealityDefender screen failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}


class PindropAdapter:
    provider = "pindrop"
    live = True

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pindrop.com/v1"

    async def screen(self, data: bytes, mime: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{self.base_url}/analyze",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files={"file": ("clip", data, mime)},
                )
            r.raise_for_status()
            j = r.json()
            synth = int(j.get("synthetic_probability", 0) * 100)
            replay = int(j.get("replay_probability", 0) * 100)
            consistency = float(j.get("speaker_consistency", 0.5))
            return {
                "ok": True, "provider": self.provider, "simulated": False,
                "synthetic_media_score": synth,
                "replay_risk_score": replay,
                "speaker_consistency": consistency,
                "metadata_anomalies": j.get("metadata_anomalies") or [],
                "verdict": _verdict(synth, replay, consistency),
                "raw": j,
            }
        except Exception as e:
            logger.error(f"Pindrop screen failed: {e}")
            return {"ok": False, "provider": self.provider, "error": str(e)}

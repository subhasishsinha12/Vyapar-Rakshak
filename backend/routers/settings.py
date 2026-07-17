"""System settings + integrations admin API."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import get_db, get_current_user
from adapters import registry

router = APIRouter(prefix="/settings", tags=["settings"])


SETTINGS_DOC_ID = "system_settings"


class GstCfg(BaseModel):
    provider: str = "mock"     # mock | karza | cleartax
    api_key: Optional[str] = None


class BankCfg(BaseModel):
    provider: str = "mock"     # mock | razorpay | cashfree
    key_id: Optional[str] = None
    key_secret: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class DeepfakeCfg(BaseModel):
    provider: str = "mock"     # mock | reality_defender | pindrop
    api_key: Optional[str] = None


class IntegrationsIn(BaseModel):
    gst: GstCfg
    bank: BankCfg
    deepfake: DeepfakeCfg


def _mask(s: Optional[str]) -> Optional[str]:
    if not s or len(s) < 4:
        return None
    return "•••••••" + s[-4:]


def _mask_cfg(cfg: dict) -> dict:
    out = {}
    for k in ("gst", "bank", "deepfake"):
        v = dict(cfg.get(k) or {})
        for keyname in ("api_key", "key_secret", "client_secret"):
            if v.get(keyname):
                v[keyname] = _mask(v[keyname])
        out[k] = v
    return out


async def _load(db) -> dict:
    doc = await db.system_settings.find_one({"id": SETTINGS_DOC_ID}, {"_id": 0})
    return doc.get("integrations", {}) if doc else {}


async def bootstrap_integrations(db):
    """Load integrations from DB into the adapter registry on startup."""
    cfg = await _load(db)
    registry.configure(cfg)


@router.get("/integrations")
async def get_integrations(db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Only admins can view integrations")
    cfg = await _load(db)
    return {
        "config": _mask_cfg(cfg),
        "snapshot": registry.snapshot(),
    }


@router.put("/integrations")
async def put_integrations(body: IntegrationsIn,
                            db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Only admins can update integrations")

    existing = await _load(db)
    new_cfg = {
        "gst": body.gst.model_dump(),
        "bank": body.bank.model_dump(),
        "deepfake": body.deepfake.model_dump(),
    }
    # Merge: if a secret field is None, preserve the existing one (so masked reads don't wipe).
    for k, v in new_cfg.items():
        prev = existing.get(k) or {}
        for kk, vv in list(v.items()):
            if vv in (None, ""):
                v[kk] = prev.get(kk)

    await db.system_settings.update_one(
        {"id": SETTINGS_DOC_ID},
        {"$set": {"id": SETTINGS_DOC_ID,
                  "integrations": new_cfg,
                  "updated_by": user["name"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    registry.configure(new_cfg)
    return {"ok": True, "snapshot": registry.snapshot()}


@router.post("/integrations/test/{kind}")
async def test_integration(kind: str, db=Depends(get_db), user=Depends(get_current_user)):
    if user["role"] not in ("admin", "owner"):
        raise HTTPException(403, "Only admins can test integrations")
    if kind == "gst":
        return await registry.gst.verify("24ABCDE1234F1Z5")
    if kind == "bank":
        return await registry.bank.penny_drop("50100234567890", "HDFC0000123", "TextilePro Mills Pvt Ltd")
    if kind == "deepfake":
        return await registry.deepfake.screen(b"\x00" * 6000, "audio/wav")
    raise HTTPException(400, "Unknown integration kind")

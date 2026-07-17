"""Voice / video verification – uses the DeepfakeAdapter registry."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from deps import get_db, get_current_user
from adapters import registry

router = APIRouter(prefix="/voice", tags=["voice"])

ALLOWED = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/webm",
           "audio/x-wav", "audio/ogg",
           "video/mp4", "video/webm", "video/quicktime"}


@router.post("/analyze")
async def analyze_voice(file: UploadFile = File(...),
                        db=Depends(get_db), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"Unsupported media type: {file.content_type}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    signals = await registry.deepfake.screen(data, file.content_type)

    result = {
        "id": str(uuid.uuid4()),
        "filename": file.filename, "mime": file.content_type, "size": len(data),
        "provider": signals.get("provider"),
        "simulated": signals.get("simulated", False),
        "synthetic_media_score": signals.get("synthetic_media_score"),
        "replay_risk_score": signals.get("replay_risk_score"),
        "speaker_consistency": signals.get("speaker_consistency"),
        "metadata_anomalies": signals.get("metadata_anomalies") or [],
        "verdict": signals.get("verdict"),
        "challenge_response_status": "not_performed",
        "independent_verification_status": "pending",
        "advisory_note": ("Deepfake screening is an advisory signal only. Always confirm with an "
                          "independent callback on a previously known number before releasing payment."),
        "raw_error": signals.get("error"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
    }
    await db.voice_scans.insert_one(result)
    result.pop("_id", None)
    return result


@router.get("")
async def list_scans(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.voice_scans.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return rows

"""Voice / video advisory verification (prototype)."""
import uuid
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from deps import get_db, get_current_user

router = APIRouter(prefix="/voice", tags=["voice"])

ALLOWED = {"audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4", "audio/webm",
           "video/mp4", "video/webm", "video/quicktime"}


@router.post("/analyze")
async def analyze_voice(file: UploadFile = File(...),
                        db=Depends(get_db), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED:
        raise HTTPException(400, f"Unsupported media type: {file.content_type}")
    data = await file.read()
    # Simulated advisory analysis
    # In production this would call a deepfake / speaker verification service.
    synthetic_score = random.randint(35, 82)
    replay_score = random.randint(10, 60)
    speaker_consistency = round(random.uniform(0.42, 0.95), 2)
    metadata_ok = len(data) > 5000
    result = {
        "id": str(uuid.uuid4()),
        "filename": file.filename, "mime": file.content_type, "size": len(data),
        "synthetic_media_score": synthetic_score,
        "replay_risk_score": replay_score,
        "speaker_consistency": speaker_consistency,
        "metadata_anomalies": [] if metadata_ok else ["truncated_or_missing_metadata"],
        "challenge_response_status": "not_performed",
        "independent_verification_status": "pending",
        "advisory_note": ("Deepfake screening is an advisory signal only. Always confirm with an "
                          "independent callback on a previously known number before releasing payment."),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "simulated": True,
    }
    await db.voice_scans.insert_one(result)
    result.pop("_id", None)
    return result


@router.get("")
async def list_scans(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.voice_scans.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return rows

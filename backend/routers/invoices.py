"""Smart Invoice Scanner – upload + LLM vision extraction + anomaly detection."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from deps import get_db, get_current_user
from ai_service import extract_invoice
from risk_engine import classify

router = APIRouter(prefix="/invoices", tags=["invoices"])

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}


@router.get("")
async def list_invoices(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.invoices.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


@router.post("/scan")
async def scan_invoice(file: UploadFile = File(...),
                       db=Depends(get_db), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Use PNG/JPEG/WebP.")
    data = await file.read()
    if len(data) < 200:
        raise HTTPException(400, "File too small")

    extracted = await extract_invoice(data, mime=file.content_type)

    # anomaly detection layer
    anomalies = []
    risk_score = 0
    if not extracted.get("ai_available"):
        anomalies.append({"code": "vision_unavailable",
                          "severity": "moderate",
                          "message": "AI vision extraction unavailable; manual review required."})
    else:
        taxable = extracted.get("taxable_amount") or 0
        c = extracted.get("cgst") or 0; s = extracted.get("sgst") or 0
        i = extracted.get("igst") or 0
        total = extracted.get("total_amount") or 0
        if total and taxable and abs((taxable + c + s + i) - total) > 1:
            anomalies.append({"code": "arithmetic_mismatch", "severity": "high",
                              "message": "Taxable + GST does not equal total."})
            risk_score += 20
        # GSTIN match
        gstin = (extracted.get("gstin") or "").strip().upper()
        if extracted.get("supplier_name"):
            v = await db.vendors.find_one({"name": {"$regex": extracted["supplier_name"], "$options": "i"}})
            if v and v.get("gstin") and gstin and v["gstin"].upper() != gstin:
                anomalies.append({"code": "gst_mismatch", "severity": "high",
                                  "message": f"GSTIN mismatch (vendor master: {v['gstin']})."})
                risk_score += 25
            if v:
                # bank match
                approved = [a["account_number"] for a in (v.get("approved_bank_accounts") or [])]
                if extracted.get("bank_account") and approved and extracted["bank_account"] not in approved:
                    anomalies.append({"code": "changed_bank_details", "severity": "critical",
                                      "message": "Bank account on invoice is not on the approved list."})
                    risk_score += 30
        # duplicate
        if extracted.get("invoice_number"):
            dup = await db.invoices.find_one({"invoice_number": extracted["invoice_number"]})
            if dup:
                anomalies.append({"code": "duplicate_invoice", "severity": "high",
                                  "message": f"Invoice number {extracted['invoice_number']} already exists in the system."})
                risk_score += 25
        # missing PO
        if not extracted.get("po_number"):
            anomalies.append({"code": "missing_po", "severity": "moderate",
                              "message": "Invoice does not reference a purchase-order number."})
            risk_score += 10

    risk_score = min(100, risk_score)

    # persist
    record = {
        "id": str(uuid.uuid4()),
        "uploaded_by": user["id"], "uploaded_by_name": user["name"],
        "filename": file.filename, "mime": file.content_type, "size": len(data),
        "extracted": extracted, "anomalies": anomalies,
        "risk_score": risk_score, "category": classify(risk_score),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.invoice_scans.insert_one(record)
    record.pop("_id", None)
    return record


@router.get("/scans")
async def list_scans(db=Depends(get_db), user=Depends(get_current_user)):
    rows = await db.invoice_scans.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows

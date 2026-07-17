"""Reports – downloadable summaries with JSON and PDF export."""
from fastapi import APIRouter, Depends, Response
from datetime import datetime, timezone, timedelta
from typing import Optional

from deps import get_db, get_current_user
from pdf_service import (
    render_report_pdf, REPORT_COLUMNS, REPORT_TITLES, flatten_payments,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _pdf_response(pdf: bytes, filename: str) -> Response:
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _daily_risk(db):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=1)).isoformat()
    rows = await db.payments.find({"requested_at": {"$gte": start}}, {"_id": 0}).to_list(500)
    return rows


async def _held(db):
    return await db.payments.find(
        {"status": {"$in": ["held", "clarification", "callback_pending"]}}, {"_id": 0}
    ).to_list(500)


async def _bank_changes(db):
    return await db.beneficiary_changes.find({}, {"_id": 0}).to_list(500)


async def _duplicates(db):
    return await db.invoices.find({"duplicate": True}, {"_id": 0}).to_list(500)


async def _hra(db):
    return await db.payments.aggregate([
        {"$match": {"risk.category": {"$in": ["high", "critical", "suspected_fraud"]}}},
        {"$group": {"_id": "$submitted_by_name", "count": {"$sum": 1},
                    "amount": {"$sum": "$amount"}}},
        {"$sort": {"amount": -1}}, {"$limit": 20},
    ]).to_list(20)


async def _loss(db):
    return await db.payments.aggregate([
        {"$match": {"status": {"$in": ["held", "rejected", "fraud"]}}},
        {"$group": {"_id": "$status", "amount": {"$sum": "$amount"}, "count": {"$sum": 1}}}
    ]).to_list(20)


async def _incidents(db):
    rows = await db.incidents.find({}, {"_id": 0}).to_list(200)
    now = datetime.now(timezone.utc)
    for r in rows:
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            r["ageing_hours"] = int((now - created).total_seconds() / 3600)
        except Exception:
            r["ageing_hours"] = 0
    return rows


async def _vendors(db):
    rows = await db.vendors.find({}, {"_id": 0}).to_list(200)
    return [{"name": r["name"], "trust_score": r.get("trust_score"),
             "blocked": "Yes" if r.get("blocked") else "No",
             "recent_account_change_at": r.get("recent_account_change_at")}
            for r in rows]


REPORT_FNS = {
    "daily-risk": _daily_risk,
    "payments-held": _held,
    "bank-changes": _bank_changes,
    "duplicate-invoices": _duplicates,
    "high-risk-approvers": _hra,
    "loss-prevented": _loss,
    "incident-ageing": _incidents,
    "vendor-risk-movement": _vendors,
}


async def _render_report(key: str, db, format: Optional[str] = None):
    if key not in REPORT_FNS:
        return None
    rows = await REPORT_FNS[key](db)
    # Flatten payments for tabular PDF rendering.
    if key in ("daily-risk", "payments-held"):
        rows = flatten_payments(rows)

    if format == "pdf":
        title, subtitle = REPORT_TITLES[key]
        summary_kv = None
        if key == "loss-prevented":
            summary_kv = [("Total prevented", f"₹{sum(r.get('amount', 0) for r in rows):,.0f}")]
        elif key == "high-risk-approvers":
            summary_kv = [("Approvers tracked", str(len(rows)))]
        pdf = render_report_pdf(title, subtitle,
                                REPORT_COLUMNS[key], rows,
                                summary_kv=summary_kv)
        return _pdf_response(pdf, f"vyaparrakshak-{key}-{datetime.now().date()}.pdf")

    # default JSON
    if key == "loss-prevented":
        return {"total_prevented": sum(r.get("amount", 0) for r in rows), "breakdown": rows}
    return {"count": len(rows), "items": rows}


@router.get("/daily-risk")
async def daily_risk(format: Optional[str] = None,
                     db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("daily-risk", db, format)


@router.get("/payments-held")
async def payments_held(format: Optional[str] = None,
                        db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("payments-held", db, format)


@router.get("/bank-changes")
async def bank_changes(format: Optional[str] = None,
                       db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("bank-changes", db, format)


@router.get("/duplicate-invoices")
async def duplicate_invoices(format: Optional[str] = None,
                             db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("duplicate-invoices", db, format)


@router.get("/high-risk-approvers")
async def high_risk_approvers(format: Optional[str] = None,
                              db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("high-risk-approvers", db, format)


@router.get("/loss-prevented")
async def loss_prevented(format: Optional[str] = None,
                         db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("loss-prevented", db, format)


@router.get("/incident-ageing")
async def incident_ageing(format: Optional[str] = None,
                          db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("incident-ageing", db, format)


@router.get("/vendor-risk-movement")
async def vendor_risk_movement(format: Optional[str] = None,
                                db=Depends(get_db), user=Depends(get_current_user)):
    return await _render_report("vendor-risk-movement", db, format)

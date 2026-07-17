"""PDF report generation using ReportLab.

Every backend report can be rendered as a branded PDF with a shared template.
"""
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)
from reportlab.pdfgen import canvas


BRAND_BLUE = colors.HexColor("#3B82F6")
BRAND_EMERALD = colors.HexColor("#10B981")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
BG_ROW = colors.HexColor("#F3F4F6")


def _format_inr(v):
    try:
        n = float(v)
    except Exception:
        return str(v) if v is not None else "—"
    # Indian grouping
    s = f"{n:,.0f}"
    # convert 1,234,567 → 12,34,567
    if len(s.replace(",", "")) > 3:
        raw = s.replace(",", "")
        # last 3 as-is, rest grouped in 2s
        first = raw[:-3]
        first = ",".join([first[max(i - 2, 0):i] for i in range(len(first), 0, -2)][::-1])
        s = first + "," + raw[-3:] if first else raw
    return f"₹{s}"


def _footer(canvas_obj: canvas.Canvas, doc):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(MUTED)
    canvas_obj.drawString(15 * mm, 10 * mm,
        "VyaparRakshak AI · Verify identity. Validate evidence. Protect every payment.")
    canvas_obj.drawRightString(doc.pagesize[0] - 15 * mm, 10 * mm,
        f"Page {doc.page}")
    canvas_obj.restoreState()


def _header(story, title: str, subtitle: str = ""):
    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle("brand", parent=styles["Normal"],
                                  fontName="Helvetica-Bold", fontSize=8,
                                  textColor=BRAND_BLUE, spaceAfter=2, leading=10)
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  fontName="Helvetica-Bold", fontSize=20,
                                  textColor=INK, spaceAfter=4, leading=24)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                                fontName="Helvetica", fontSize=9,
                                textColor=MUTED, spaceAfter=12, leading=11)
    story.append(Paragraph("VYAPARRAKSHAK AI  ·  FRAUD SHIELD", brand_style))
    story.append(Paragraph(title, title_style))
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    line = f"{subtitle}  ·  Generated {stamp}" if subtitle else f"Generated {stamp}"
    story.append(Paragraph(line, sub_style))


def render_report_pdf(title: str, subtitle: str, columns: List[Dict[str, Any]],
                      rows: List[Dict[str, Any]],
                      summary_kv: List[tuple] | None = None) -> bytes:
    """
    columns: [{"key": "amount", "label": "Amount", "kind": "money|text|date|number"}]
    rows: raw dicts
    summary_kv: [(label, value)] rendered as a top-of-page summary card.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=18 * mm,
                            title=title, author="VyaparRakshak AI")
    story = []
    _header(story, title, subtitle)

    if summary_kv:
        cells = [[Paragraph(f"<b>{k}</b>", getSampleStyleSheet()["Normal"]),
                  Paragraph(str(v), getSampleStyleSheet()["Normal"])]
                 for k, v in summary_kv]
        tbl = Table(cells, colWidths=[70 * mm, 100 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_ROW),
            ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 10))

    # Table
    if rows:
        header = [c["label"] for c in columns]
        body = []
        for r in rows:
            row_cells = []
            for c in columns:
                v = r.get(c["key"])
                kind = c.get("kind", "text")
                if v is None:
                    row_cells.append("—"); continue
                if kind == "money":
                    row_cells.append(_format_inr(v))
                elif kind == "date":
                    try:
                        row_cells.append(str(v)[:10])
                    except Exception:
                        row_cells.append(str(v))
                elif kind == "number":
                    row_cells.append(f"{v:,}" if isinstance(v, (int, float)) else str(v))
                else:
                    row_cells.append(str(v))
            body.append(row_cells)

        data = [header] + body
        col_widths = None
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_ROW]),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No records for the selected period.",
                                getSampleStyleSheet()["Italic"]))

    # Notice
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<i>Notice: External adapter results in this prototype may be simulated. "
        "Confirm adapter provider status in Settings → Integrations.</i>",
        ParagraphStyle("notice", parent=getSampleStyleSheet()["Normal"],
                       fontSize=8, textColor=MUTED)
    ))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# Column presets for each report
REPORT_COLUMNS = {
    "daily-risk": [
        {"key": "invoice_number", "label": "Invoice #", "kind": "text"},
        {"key": "vendor_name", "label": "Vendor", "kind": "text"},
        {"key": "amount", "label": "Amount", "kind": "money"},
        {"key": "mode", "label": "Mode", "kind": "text"},
        {"key": "status", "label": "Status", "kind": "text"},
        {"key": "risk_category", "label": "Risk", "kind": "text"},
        {"key": "risk_score", "label": "Score", "kind": "number"},
        {"key": "requested_at", "label": "Requested", "kind": "date"},
    ],
    "payments-held": [
        {"key": "invoice_number", "label": "Invoice #", "kind": "text"},
        {"key": "vendor_name", "label": "Vendor", "kind": "text"},
        {"key": "amount", "label": "Amount", "kind": "money"},
        {"key": "mode", "label": "Mode", "kind": "text"},
        {"key": "status", "label": "Status", "kind": "text"},
        {"key": "risk_category", "label": "Risk", "kind": "text"},
        {"key": "requested_at", "label": "Requested", "kind": "date"},
    ],
    "bank-changes": [
        {"key": "vendor_name", "label": "Vendor", "kind": "text"},
        {"key": "old_account_number", "label": "Old A/C", "kind": "text"},
        {"key": "new_account_number", "label": "New A/C", "kind": "text"},
        {"key": "new_ifsc", "label": "New IFSC", "kind": "text"},
        {"key": "requested_via", "label": "Via", "kind": "text"},
        {"key": "callback_status", "label": "Callback", "kind": "text"},
        {"key": "status", "label": "Status", "kind": "text"},
        {"key": "created_at", "label": "Requested", "kind": "date"},
    ],
    "duplicate-invoices": [
        {"key": "invoice_number", "label": "Invoice #", "kind": "text"},
        {"key": "vendor_name", "label": "Vendor", "kind": "text"},
        {"key": "amount", "label": "Amount", "kind": "money"},
        {"key": "invoice_date", "label": "Invoice date", "kind": "date"},
        {"key": "created_at", "label": "Detected", "kind": "date"},
    ],
    "high-risk-approvers": [
        {"key": "_id", "label": "Approver", "kind": "text"},
        {"key": "count", "label": "# payments", "kind": "number"},
        {"key": "amount", "label": "Amount", "kind": "money"},
    ],
    "loss-prevented": [
        {"key": "_id", "label": "Status", "kind": "text"},
        {"key": "count", "label": "# payments", "kind": "number"},
        {"key": "amount", "label": "Amount", "kind": "money"},
    ],
    "incident-ageing": [
        {"key": "incident_no", "label": "Incident #", "kind": "text"},
        {"key": "suspected_type", "label": "Suspected type", "kind": "text"},
        {"key": "amount_at_risk", "label": "At risk", "kind": "money"},
        {"key": "status", "label": "Status", "kind": "text"},
        {"key": "ageing_hours", "label": "Age (h)", "kind": "number"},
        {"key": "created_at", "label": "Opened", "kind": "date"},
    ],
    "vendor-risk-movement": [
        {"key": "name", "label": "Vendor", "kind": "text"},
        {"key": "trust_score", "label": "Trust score", "kind": "number"},
        {"key": "blocked", "label": "Blocked", "kind": "text"},
        {"key": "recent_account_change_at", "label": "Recent bank change", "kind": "date"},
    ],
}


REPORT_TITLES = {
    "daily-risk": ("Daily fraud-risk summary", "Payments in the last 24 hours"),
    "payments-held": ("Payments held & released", "Payments currently under hold or clarification"),
    "bank-changes": ("Vendor bank-account change log", "Every beneficiary account change with callback status"),
    "duplicate-invoices": ("Duplicate invoices", "Invoices flagged as potential duplicates"),
    "high-risk-approvers": ("High-risk approvers", "Users submitting the most high-risk payments"),
    "loss-prevented": ("Potential fraud loss prevented", "Held / rejected / fraud payments"),
    "incident-ageing": ("Incident ageing", "Age of open fraud incidents"),
    "vendor-risk-movement": ("Vendor risk movement", "Change in vendor trust scores"),
}


def flatten_payments(items):
    """Flatten nested risk block for tabular rendering."""
    out = []
    for p in items or []:
        r = p.get("risk") or {}
        out.append({**p,
                    "risk_category": r.get("category"),
                    "risk_score": r.get("score")})
    return out

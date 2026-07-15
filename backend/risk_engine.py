"""Deterministic + explainable risk engine for VyaparRakshak."""
from datetime import datetime, timezone
from typing import List, Dict, Any


CATEGORIES = {
    "low": (0, 25),
    "moderate": (25, 50),
    "high": (50, 75),
    "critical": (75, 90),
    "suspected_fraud": (90, 101),
}


def classify(score: int) -> str:
    for cat, (lo, hi) in CATEGORIES.items():
        if lo <= score < hi:
            return cat
    return "critical"


def score_payment(payment: Dict[str, Any], vendor: Dict[str, Any] | None,
                  invoice: Dict[str, Any] | None,
                  comms_risk: int = 0) -> Dict[str, Any]:
    """Return score + explainable red flags + component contributions."""
    flags: List[Dict[str, Any]] = []
    components: Dict[str, int] = {
        "invoice_anomaly": 0,
        "beneficiary_change": 0,
        "communication_risk": 0,
        "transaction_anomaly": 0,
        "document_manipulation": 0,
        "vendor_identity": 0,
        "user_approval_pattern": 0,
    }

    amt = float(payment.get("amount", 0))

    # Vendor identity
    if not vendor:
        components["vendor_identity"] += 25
        flags.append({"category": "vendor_identity", "severity": "high",
                      "title": "Vendor not registered", "reason":
                      "Payment is being made to a vendor that is not in the Vendor Trust registry."})
    else:
        if vendor.get("blocked"):
            components["vendor_identity"] += 60
            flags.append({"category": "vendor_identity", "severity": "critical",
                          "title": "Vendor is blocked / watchlisted",
                          "reason": vendor.get("block_reason") or "Vendor is on internal watchlist."})
        # Beneficiary check
        approved_accounts = vendor.get("approved_bank_accounts", [])
        recent_change = vendor.get("recent_account_change_at")
        beneficiary_acc = payment.get("account_number")
        if beneficiary_acc and approved_accounts and beneficiary_acc not in [a["account_number"] for a in approved_accounts]:
            components["beneficiary_change"] += 45
            flags.append({"category": "beneficiary_change", "severity": "critical",
                          "title": "Beneficiary account not on the approved list",
                          "reason": f"Payment routed to account {beneficiary_acc[-4:]} which is not in the vendor's approved list."})
        if recent_change:
            components["beneficiary_change"] += 25
            flags.append({"category": "beneficiary_change", "severity": "high",
                          "title": "Vendor bank details changed recently",
                          "reason": f"Account change recorded on {recent_change[:10]}. Independent callback required."})
        # Amount vs history
        avg = vendor.get("average_invoice_amount", 0)
        maxh = vendor.get("max_historical_amount", 0)
        if avg and amt > 3 * avg:
            components["transaction_anomaly"] += 30
            flags.append({"category": "transaction_anomaly", "severity": "high",
                          "title": "Amount is unusually high vs vendor history",
                          "reason": f"Amount ₹{amt:,.0f} is over 3× vendor's average ₹{avg:,.0f}."})
        if maxh and amt > 1.5 * maxh:
            components["transaction_anomaly"] += 15
            flags.append({"category": "transaction_anomaly", "severity": "moderate",
                          "title": "Amount exceeds highest previous invoice",
                          "reason": f"Historical max was ₹{maxh:,.0f}."})

    # Invoice-based flags
    if invoice:
        if invoice.get("duplicate"):
            components["invoice_anomaly"] += 40
            flags.append({"category": "invoice_anomaly", "severity": "critical",
                          "title": "Possible duplicate invoice",
                          "reason": "An invoice with a similar number was already paid."})
        if invoice.get("gst_mismatch"):
            components["invoice_anomaly"] += 20
            flags.append({"category": "invoice_anomaly", "severity": "moderate",
                          "title": "GSTIN mismatch on invoice",
                          "reason": "GSTIN on invoice does not match vendor master record."})
        if invoice.get("arithmetic_mismatch"):
            components["invoice_anomaly"] += 15
            flags.append({"category": "invoice_anomaly", "severity": "moderate",
                          "title": "Arithmetic mismatch",
                          "reason": "Sum of taxable + GST does not equal total."})
        if invoice.get("image_manipulation"):
            components["document_manipulation"] += 30
            flags.append({"category": "document_manipulation", "severity": "high",
                          "title": "Signs of image manipulation",
                          "reason": "Metadata / pixel anomalies suggest possible editing."})

    # Communication risk (from Communication Fraud Detector)
    if comms_risk:
        components["communication_risk"] += min(50, comms_risk)
        if comms_risk >= 25:
            flags.append({"category": "communication_risk", "severity": "high",
                          "title": "Suspicious communication signals",
                          "reason": "Related emails/WhatsApp messages contain fraud indicators."})

    # Approval pattern
    if payment.get("submitted_by") == payment.get("approved_by"):
        components["user_approval_pattern"] += 30
        flags.append({"category": "user_approval_pattern", "severity": "high",
                      "title": "Maker-checker violation",
                      "reason": "Same user attempted to create and approve the payment."})

    # Weekend / after-hours
    try:
        dt = datetime.fromisoformat(payment.get("requested_at").replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    if dt.weekday() >= 5:
        components["transaction_anomaly"] += 10
        flags.append({"category": "transaction_anomaly", "severity": "moderate",
                      "title": "Weekend payment request",
                      "reason": "Requests on Saturdays / Sundays warrant extra care."})

    # Split payment (round-tripped just under limit)
    if 90000 <= amt <= 100000 or 490000 <= amt <= 500000:
        components["transaction_anomaly"] += 10
        flags.append({"category": "transaction_anomaly", "severity": "moderate",
                      "title": "Amount just below approval threshold",
                      "reason": "Value is suspiciously close to an internal approval limit."})

    total = min(100, sum(components.values()))
    category = classify(total)
    recommended = _recommend(category, flags)

    return {
        "score": total,
        "category": category,
        "components": components,
        "flags": flags,
        "recommended_action": recommended["action"],
        "required_approvers": recommended["approvers"],
        "requires_callback": recommended["callback"],
        "cooling_period_hours": recommended["cooling"],
    }


def _recommend(category: str, flags):
    if category == "suspected_fraud":
        return {"action": "Hold payment and open fraud incident", "approvers": 3,
                "callback": True, "cooling": 24}
    if category == "critical":
        return {"action": "Independent callback + two approvers required",
                "approvers": 2, "callback": True, "cooling": 12}
    if category == "high":
        return {"action": "Send for clarification, verify evidence",
                "approvers": 2, "callback": True, "cooling": 4}
    if category == "moderate":
        return {"action": "Proceed with standard approval",
                "approvers": 2, "callback": False, "cooling": 0}
    return {"action": "Approve", "approvers": 1, "callback": False, "cooling": 0}


def analyse_comms(text: str) -> Dict[str, Any]:
    """Deterministic keyword-based fallback signal (also complements AI output)."""
    t = (text or "").lower()
    signals = []
    score = 0
    urgency_words = ["urgent", "asap", "immediately", "right now", "before eod", "critical"]
    secrecy_words = ["confidential", "don't tell", "keep this between us", "do not call", "no phone call", "don't call"]
    authority_words = ["ceo", "owner", "director", "chairman", "boss", "mother-in-law", "father"]
    bypass_words = ["skip approval", "no approval", "bypass", "override", "one-time exception"]
    new_bank_words = ["new account", "changed account", "new bank", "updated bank"]
    for w in urgency_words:
        if w in t:
            signals.append({"category": "urgency", "phrase": w, "severity": "high",
                            "reason": "Urgency pressure is a classic BEC pattern."})
            score += 8
    for w in secrecy_words:
        if w in t:
            signals.append({"category": "secrecy", "phrase": w, "severity": "critical",
                            "reason": "Requests for secrecy or 'do not call' are highly suspicious."})
            score += 15
    for w in authority_words:
        if w in t:
            signals.append({"category": "authority_impersonation", "phrase": w, "severity": "high",
                            "reason": "Impersonation of authority is common in CEO fraud."})
            score += 10
    for w in bypass_words:
        if w in t:
            signals.append({"category": "bypass_controls", "phrase": w, "severity": "critical",
                            "reason": "Requests to bypass controls should never be honoured."})
            score += 15
    for w in new_bank_words:
        if w in t:
            signals.append({"category": "new_beneficiary", "phrase": w, "severity": "high",
                            "reason": "Change of beneficiary requires independent callback."})
            score += 12
    # Look-alike domains
    if "@" in t:
        if any(dom in t for dom in ["rn.", ".ln", "0.com", "vv.", "textilepr0", "gooogle"]):
            signals.append({"category": "lookalike_domain", "phrase": "lookalike email",
                            "severity": "high", "reason": "Email domain contains letter/number swap."})
            score += 15
    score = min(100, score)
    return {"score": score, "category": classify(score), "signals": signals}

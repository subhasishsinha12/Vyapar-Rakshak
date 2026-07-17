"""Realistic demo data seeder for Indian MSME context."""
import uuid
from datetime import datetime, timezone, timedelta


def _iso(d: datetime) -> str:
    return d.isoformat()


VENDORS = [
    {
        "name": "TextilePro Mills Pvt Ltd", "gstin": "24ABCDE1234F1Z5", "pan": "ABCDE1234F",
        "category": "Textile Manufacturer",
        "address": "Plot 47, GIDC Industrial Estate, Surat, Gujarat 395007",
        "contacts": [{"name": "Arjun Patel", "phone": "+91 98250 12345",
                      "email": "arjun@textilepro.in", "verified": True}],
        "approved_bank_accounts": [
            {"account_number": "50100234567890", "ifsc": "HDFC0000123", "bank": "HDFC Bank",
             "verified_at": _iso(datetime.now(timezone.utc) - timedelta(days=380))}
        ],
        "average_invoice_amount": 245000, "max_historical_amount": 620000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=420)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=8)),
        "trust_score": 82, "blocked": False,
    },
    {
        "name": "Kirloskar Machinery Traders", "gstin": "27ABCMK5678L1Z2", "pan": "ABCMK5678L",
        "category": "Machinery Supplier",
        "address": "Shed 12, MIDC, Pune, Maharashtra 411019",
        "contacts": [{"name": "Nikhil Kulkarni", "phone": "+91 98220 55667",
                      "email": "nikhil@kirloskarmt.co.in", "verified": True}],
        "approved_bank_accounts": [
            {"account_number": "60100987654321", "ifsc": "ICIC0000456", "bank": "ICICI Bank",
             "verified_at": _iso(datetime.now(timezone.utc) - timedelta(days=290))}
        ],
        "average_invoice_amount": 485000, "max_historical_amount": 1150000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=300)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=15)),
        # Recent change today - the demo storyline vendor
        "recent_account_change_at": _iso(datetime.now(timezone.utc) - timedelta(hours=5)),
        "trust_score": 46, "blocked": False,
        "watchlist_reason": "Bank account change requested today; independent callback incomplete.",
    },
    {
        "name": "Bansal Packaging LLP", "gstin": "07BNSPL2345P1Z9", "pan": "BNSPL2345P",
        "category": "Packaging Vendor", "address": "F-14, Naraina, New Delhi 110028",
        "contacts": [{"name": "Deepak Bansal", "phone": "+91 98111 22334",
                      "email": "deepak@bansalpack.in", "verified": True}],
        "approved_bank_accounts": [
            {"account_number": "31200987654", "ifsc": "SBIN0004321", "bank": "SBI",
             "verified_at": _iso(datetime.now(timezone.utc) - timedelta(days=200))}
        ],
        "average_invoice_amount": 62000, "max_historical_amount": 140000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=210)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=3)),
        "trust_score": 88, "blocked": False,
    },
    {
        "name": "Sundaram Transport Co.", "gstin": "33SUNTR6789K1Z6", "pan": "SUNTR6789K",
        "category": "Transport Contractor", "address": "Ambattur Industrial Estate, Chennai 600058",
        "contacts": [{"name": "Ramanathan S", "phone": "+91 94444 66889",
                      "email": "rs@sundaramtrans.in", "verified": True}],
        "approved_bank_accounts": [
            {"account_number": "62100445533", "ifsc": "IOBA0000789", "bank": "Indian Overseas Bank",
             "verified_at": _iso(datetime.now(timezone.utc) - timedelta(days=150))}
        ],
        "average_invoice_amount": 38000, "max_historical_amount": 82000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=160)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=1)),
        "trust_score": 91, "blocked": False,
    },
    {
        "name": "Prakash & Co. Chartered Accountants", "gstin": "29PRACO8899E1Z3", "pan": "PRACO8899E",
        "category": "Professional Services",
        "address": "Indiranagar 2nd Stage, Bengaluru, Karnataka 560038",
        "contacts": [{"name": "CA Prakash Rao", "phone": "+91 99009 88776",
                      "email": "prakash@prakashcaindia.in", "verified": True}],
        "approved_bank_accounts": [
            {"account_number": "39820011223", "ifsc": "AXIS0000112", "bank": "Axis Bank",
             "verified_at": _iso(datetime.now(timezone.utc) - timedelta(days=520))}
        ],
        "average_invoice_amount": 55000, "max_historical_amount": 120000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=560)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=30)),
        "trust_score": 95, "blocked": False,
    },
    {
        "name": "Nordic Exports GmbH (Buyer)", "gstin": "-", "pan": "-",
        "category": "Export Customer",
        "address": "Frankfurter Str. 12, Hamburg, Germany",
        "contacts": [{"name": "Klaus Mueller", "phone": "+49 40 12345678",
                      "email": "klaus@nordicexports.de", "verified": True}],
        "approved_bank_accounts": [],
        "average_invoice_amount": 950000, "max_historical_amount": 2200000,
        "first_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=180)),
        "last_transaction_at": _iso(datetime.now(timezone.utc) - timedelta(days=12)),
        "trust_score": 78, "blocked": False,
    },
]


DEMO_PAYMENTS_TEMPLATES = [
    # THE CRITICAL DEMO PAYMENT
    {
        "vendor_name": "Kirloskar Machinery Traders",
        "invoice_number": "KMT/2026/00417",
        "invoice_date_offset": -1,
        "amount": 1875000, "mode": "RTGS",
        "beneficiary_name": "Kirloskar Machinery Traders",
        "account_number": "6099911223377",  # NEW, not in approved list
        "ifsc": "YESB0000199",
        "upi_id": None,
        "po_number": "PO/2026/0451",
        "grn_number": None,
        "due_date_offset": 2,
        "purpose": "Payment for CNC lathe delivery – urgent per WhatsApp instruction",
        "notes": "Received a WhatsApp from the vendor stating account changed today. Message asked not to call for verification.",
        "requested_offset_hours": -3,
        "status": "held",
        "communication_text": ("URGENT: Please transfer ₹18,75,000 to our new HDFC account today itself. "
                               "This is for the CNC lathe. Bank changed due to audit. Please DO NOT CALL, "
                               "I am in a meeting. Confidential. — Nikhil (from kirloskarmt.c0.in)"),
        "demo_critical": True,
    },
    # Normal textile payment
    {
        "vendor_name": "TextilePro Mills Pvt Ltd", "invoice_number": "TPM/25-26/1122",
        "invoice_date_offset": -10, "amount": 218500, "mode": "NEFT",
        "beneficiary_name": "TextilePro Mills Pvt Ltd",
        "account_number": "50100234567890", "ifsc": "HDFC0000123",
        "upi_id": None, "po_number": "PO/2026/0402", "grn_number": "GRN/2026/0389",
        "due_date_offset": 5, "purpose": "October cotton yarn supply",
        "requested_offset_hours": -20, "status": "approved",
    },
    # Duplicate invoice
    {
        "vendor_name": "Bansal Packaging LLP", "invoice_number": "BPL/2026/0231",
        "invoice_date_offset": -3, "amount": 68400, "mode": "NEFT",
        "beneficiary_name": "Bansal Packaging LLP",
        "account_number": "31200987654", "ifsc": "SBIN0004321",
        "upi_id": None, "po_number": "PO/2026/0431", "grn_number": "GRN/2026/0421",
        "due_date_offset": 3, "purpose": "Corrugated boxes September",
        "requested_offset_hours": -5, "status": "pending",
        "invoice_flags": {"duplicate": True},
    },
    # GST mismatch
    {
        "vendor_name": "TextilePro Mills Pvt Ltd", "invoice_number": "TPM/25-26/1150",
        "invoice_date_offset": -2, "amount": 342100, "mode": "NEFT",
        "beneficiary_name": "TextilePro Mills Pvt Ltd",
        "account_number": "50100234567890", "ifsc": "HDFC0000123",
        "po_number": "PO/2026/0448", "purpose": "Cotton yarn November batch",
        "requested_offset_hours": -8, "status": "pending",
        "invoice_flags": {"gst_mismatch": True, "arithmetic_mismatch": True},
    },
    # Fake bank change - lookalike
    {
        "vendor_name": "Sundaram Transport Co.", "invoice_number": "STC/2026/0088",
        "invoice_date_offset": -1, "amount": 41200, "mode": "IMPS",
        "beneficiary_name": "Sundaram Transport Company",
        "account_number": "62888112233", "ifsc": "IOBA0000789",
        "po_number": "PO/2026/0460", "purpose": "Container haulage – Chennai to Surat",
        "requested_offset_hours": -1, "status": "pending",
        "communication_text": ("Sir, please pay to new account 62888112233. Old account has technical issue. — Ramanathan"),
    },
    # CEO impersonation
    {
        "vendor_name": "Prakash & Co. Chartered Accountants", "invoice_number": "PCA/2026/044",
        "invoice_date_offset": -1, "amount": 90000, "mode": "IMPS",
        "beneficiary_name": "Prakash R",
        "account_number": "77712345678", "ifsc": "KKBK0000876",
        "po_number": None, "purpose": "Confidential CEO instruction",
        "requested_offset_hours": -2, "status": "held",
        "communication_text": ("Anita, this is Rajiv (CEO). Please transfer ₹90,000 immediately to the "
                               "personal account below. It is urgent and confidential. Do not call me, "
                               "I am in a board meeting. — Rajiv"),
    },
    # Weekend suspicious
    {
        "vendor_name": "TextilePro Mills Pvt Ltd", "invoice_number": "TPM/25-26/1177",
        "invoice_date_offset": -1, "amount": 495000, "mode": "RTGS",
        "beneficiary_name": "TextilePro Mills Pvt Ltd",
        "account_number": "50100234567890", "ifsc": "HDFC0000123",
        "po_number": "PO/2026/0480", "purpose": "Yarn – advance",
        "requested_offset_hours": -30, "status": "pending",
    },
]


async def seed_all(db):
    """Idempotent seed. Populates vendors, invoices, payments, comms, incidents,
    beneficiary changes and audit entries."""

    # Always ensure vendor user is linked (idempotent)
    async def _link_vendor_user():
        textile = await db.vendors.find_one({"name": "TextilePro Mills Pvt Ltd"}, {"id": 1})
        if textile:
            await db.users.update_one({"email": "vendor@textilepro.in"},
                                       {"$set": {"vendor_id": textile["id"]}})

    if await db.vendors.count_documents({}) >= len(VENDORS):
        await _link_vendor_user()
        return  # already seeded

    now = datetime.now(timezone.utc)

    # ---- vendors
    vendor_map = {}
    for v in VENDORS:
        vid = str(uuid.uuid4())
        v_doc = {**v, "id": vid, "created_at": _iso(now)}
        await db.vendors.insert_one(v_doc)
        vendor_map[v["name"]] = vid

    # Link the seeded vendor user to TextilePro Mills
    textile_id = vendor_map.get("TextilePro Mills Pvt Ltd")
    if textile_id:
        await db.users.update_one({"email": "vendor@textilepro.in"},
                                   {"$set": {"vendor_id": textile_id}})
        await db.vendor_kyc.insert_one({
            "id": str(uuid.uuid4()),
            "vendor_id": textile_id, "vendor_name": "TextilePro Mills Pvt Ltd",
            "kind": "gst_certificate", "notes": "GST certificate (seed sample)",
            "filename": "textilepro-gst.pdf", "mime": "application/pdf", "size": 128456,
            "storage_path": "seed://placeholder",
            "uploaded_by": None, "uploaded_by_name": "Arjun Patel",
            "uploaded_at": _iso(now - timedelta(days=180)),
            "status": "approved",
            "reviewed_by": "Anita Sharma",
            "reviewed_at": _iso(now - timedelta(days=178)),
        })

    # ---- payments (build 30+ items)
    payments = list(DEMO_PAYMENTS_TEMPLATES)
    # add generic to reach 30
    filler_vendors = ["TextilePro Mills Pvt Ltd", "Bansal Packaging LLP",
                      "Sundaram Transport Co.", "Prakash & Co. Chartered Accountants"]
    for i in range(25):
        v = filler_vendors[i % len(filler_vendors)]
        payments.append({
            "vendor_name": v,
            "invoice_number": f"AUTO/{2026}/{1000 + i:04d}",
            "invoice_date_offset": -(i % 20) - 1,
            "amount": [58000, 122000, 34500, 87000, 210000][i % 5],
            "mode": ["NEFT", "IMPS", "UPI", "RTGS"][i % 4],
            "beneficiary_name": v,
            "account_number": ["50100234567890", "31200987654", "62100445533", "39820011223"][filler_vendors.index(v)],
            "ifsc": ["HDFC0000123", "SBIN0004321", "IOBA0000789", "AXIS0000112"][filler_vendors.index(v)],
            "po_number": f"PO/2026/{500 + i:04d}",
            "purpose": "Routine purchase",
            "requested_offset_hours": -(i * 7 + 4),
            "status": ["approved", "pending", "approved", "approved"][i % 4],
        })

    # need to import risk engine to score
    from risk_engine import score_payment, analyse_comms

    seed_users_by_role = {}
    async for u in db.users.find({}):
        seed_users_by_role.setdefault(u["role"], []).append(u)

    maker = seed_users_by_role.get("maker", [{}])[0]
    checker = seed_users_by_role.get("checker", [{}])[0]

    for idx, p in enumerate(payments):
        pid = str(uuid.uuid4())
        vname = p["vendor_name"]
        vdoc = await db.vendors.find_one({"name": vname}, {"_id": 0})
        req_at = now + timedelta(hours=p.get("requested_offset_hours", -4))
        inv_date = now + timedelta(days=p.get("invoice_date_offset", -2))
        due_date = now + timedelta(days=p.get("due_date_offset", 5))

        # invoice doc
        inv_id = str(uuid.uuid4())
        invoice_flags = p.get("invoice_flags", {})
        inv_doc = {
            "id": inv_id,
            "invoice_number": p["invoice_number"],
            "vendor_id": vendor_map.get(vname),
            "vendor_name": vname,
            "invoice_date": _iso(inv_date),
            "amount": p["amount"],
            "gstin": (vdoc or {}).get("gstin"),
            **invoice_flags,
            "created_at": _iso(req_at),
        }
        await db.invoices.insert_one(inv_doc)

        payment_doc = {
            "id": pid,
            "vendor_id": vendor_map.get(vname), "vendor_name": vname,
            "invoice_id": inv_id, "invoice_number": p["invoice_number"],
            "invoice_date": _iso(inv_date),
            "amount": p["amount"], "currency": "INR",
            "mode": p["mode"],
            "beneficiary_name": p["beneficiary_name"],
            "account_number": p["account_number"], "ifsc": p["ifsc"],
            "upi_id": p.get("upi_id"),
            "po_number": p.get("po_number"), "grn_number": p.get("grn_number"),
            "due_date": _iso(due_date), "purpose": p["purpose"],
            "notes": p.get("notes"),
            "status": p["status"],  # pending / approved / held / rejected / fraud
            "submitted_by": maker.get("id"), "submitted_by_name": maker.get("name"),
            "requested_at": _iso(req_at),
            "created_at": _iso(req_at),
            "demo_critical": p.get("demo_critical", False),
            "evidence": [],
            "decision_log": [],
        }

        # community/comms fallback risk
        comms_risk = 0
        if p.get("communication_text"):
            c_res = analyse_comms(p["communication_text"])
            comms_risk = c_res["score"]
            # store comms
            await db.comms.insert_one({
                "id": str(uuid.uuid4()),
                "payment_id": pid,
                "channel": "whatsapp" if "whatsapp" in (p.get("notes", "") or "").lower() else "email",
                "content": p["communication_text"],
                "analysis": c_res,
                "created_at": _iso(req_at),
                "ai_available": False,
            })

        # score
        risk = score_payment(payment_doc, vdoc, inv_doc, comms_risk=comms_risk)
        payment_doc["risk"] = risk
        # override to critical for demo
        if p.get("demo_critical"):
            payment_doc["risk"]["score"] = max(payment_doc["risk"]["score"], 92)
            payment_doc["risk"]["category"] = "critical"

        await db.payments.insert_one(payment_doc)

        # audit entry - creation
        await db.audit_trail.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": maker.get("id"), "user_name": maker.get("name"),
            "user_role": "maker",
            "timestamp": _iso(req_at),
            "device": "web", "ip": "10.0.0.11",
            "action": "payment.create", "entity_type": "payment", "entity_id": pid,
            "previous": None,
            "new": {"amount": payment_doc["amount"], "vendor": vname},
            "reason": "Vendor invoice submitted for verification",
            "evidence": None,
        })

    # ---- Beneficiary change requests
    kirloskar_id = vendor_map.get("Kirloskar Machinery Traders")
    if kirloskar_id:
        await db.beneficiary_changes.insert_one({
            "id": str(uuid.uuid4()),
            "vendor_id": kirloskar_id,
            "vendor_name": "Kirloskar Machinery Traders",
            "old_account_number": "60100987654321", "old_ifsc": "ICIC0000456",
            "new_account_number": "6099911223377", "new_ifsc": "YESB0000199",
            "new_bank": "Yes Bank",
            "requested_via": "whatsapp",
            "requested_email_domain": "kirloskarmt.c0.in",
            "flags": ["email_domain_altered", "phone_new", "asked_not_to_call"],
            "callback_status": "pending",
            "verification_code": "VR-874521",
            "cooling_period_hours": 12,
            "approvals_required": 2, "approvals_received": 0,
            "status": "pending",
            "created_at": _iso(now - timedelta(hours=5)),
        })

    # ---- Incident (open one for the demo payment)
    demo_payment = await db.payments.find_one({"demo_critical": True})
    if demo_payment:
        await db.incidents.insert_one({
            "id": str(uuid.uuid4()),
            "incident_no": "INC-2026-0117",
            "payment_id": demo_payment["id"],
            "payment_reference": demo_payment["invoice_number"],
            "amount_at_risk": demo_payment["amount"],
            "suspected_type": "Vendor bank-account fraud (BEC + Deepfake risk)",
            "status": "under_investigation",
            "timeline": [
                {"at": _iso(now - timedelta(hours=6)),
                 "event": "WhatsApp from vendor requesting account change"},
                {"at": _iso(now - timedelta(hours=5, minutes=30)),
                 "event": "Beneficiary change request logged (status pending)"},
                {"at": _iso(now - timedelta(hours=4)),
                 "event": "Finance manager escalated to Verify Payment workflow"},
                {"at": _iso(now - timedelta(hours=3)),
                 "event": "Risk engine flagged Critical – payment held"},
            ],
            "people": [{"name": "Anita Sharma", "role": "Finance Manager"},
                       {"name": "Suresh Kumar", "role": "Payment Maker"},
                       {"name": "Priya Iyer", "role": "Payment Checker"}],
            "evidence_attachments": [],
            "bank_notification_status": "not_sent",
            "internal_escalation_status": "management_notified",
            "recovery_status": "not_started",
            "root_cause_analysis": "",
            "corrective_actions": [],
            "closure_approval": None,
            "created_at": _iso(now - timedelta(hours=3)),
        })

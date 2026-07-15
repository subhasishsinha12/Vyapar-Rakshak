# VyaparRakshak AI – Verify Before You Pay

## Original problem statement
Production-quality responsive web application to protect Indian MSMEs from fraudulent payment requests, fake vendor bank-account changes, duplicate invoices, business-email compromise, CEO impersonation, deepfake voice instructions, GST mismatches, and suspicious digital-payment activity. Sits before UPI / IMPS / NEFT / RTGS release.

Tagline: **Verify identity. Validate evidence. Protect every payment.**

## User choices (Iteration 1)
- Auth: JWT-based custom auth (email + password + RBAC)
- LLM: GPT-5.2 via Emergent Universal LLM Key
- OCR: LLM-vision (GPT-5.2) via emergentintegrations
- Uploads: Local disk (prototype)
- Scope: Full breadth – all 11 modules + 8 roles

## User personas / roles
Business Owner · Finance Manager · Payment Maker · Payment Checker · Procurement Officer · Internal Auditor · Vendor · System Administrator (maker-checker enforced)

## Architecture
- Backend: FastAPI + MongoDB (Motor), JWT (bcrypt hashes, HttpOnly cookies), Emergent LLM key for GPT-5.2 text + vision.
- Frontend: React + React-Router + shadcn/ui + Recharts + sonner. Cybersecurity-first dark theme, Outfit + IBM Plex Sans + IBM Plex Mono.
- 13 backend routers under `/api`: auth, dashboard, vendors, payments, invoices, beneficiaries, incidents, comms, voice, audit, reports, approvals, notifications.
- Deterministic risk engine (`risk_engine.py`) with 7 explainable components + AI narrative overlay.
- Seed generates 6 vendors, 30+ payments, beneficiary-change requests, comms records, 1 incident (INC-2026-0117).

## Implemented (2026-07-15) – V1
- JWT login + logout + `/me` + refresh, 8 seeded users, bcrypt, brute-force lockout after 5 tries.
- Dashboard with 10 KPI tiles, Today's Critical Decisions carousel, risk mix pie, 7-day payment risk trend, fraud exposure by vendor, payment value by status.
- Verify Payment 5-step workflow (info → evidence → automated checks → risk result with explainable red flags & component contributions → decision) with maker-checker separation (409 on same-user approve).
- Smart Invoice Scanner (drag & drop, GPT-5.2 vision, arithmetic + GST + bank + duplicate + PO anomaly detection with side-by-side preview).
- Vendor Trust Passport (0–100 trust score, contacts, approved bank accounts, historical range, blocked/watchlist).
- Beneficiary bank-change control (callback verification, cooling period, dual approval, random verification code, "do not use new contact" reminder).
- Communication Fraud Detector (paste email/WhatsApp/SMS, GPT-5.2 + rule engine, inline phrase highlighting, red-flag explanations).
- Voice / video verification prototype (advisory synthetic-media / replay / speaker-consistency indicators; clearly labelled simulation).
- Fraud Incident Room (INC-2026-0117 seeded, freeze / block beneficiary / notify bank / assign / escalate / close, downloadable JSON evidence pack, generated bank intimation .txt).
- Reports: daily-risk, payments-held, bank-changes, duplicate-invoices, high-risk-approvers, loss-prevented, incident-ageing, vendor-risk-movement (JSON + CSV download).
- Immutable-looking audit trail (user, timestamp, device, IP placeholder, action, previous, new, reason, evidence ref).
- Settings: approval rules, cooling period, DPDP consent + retention + deletion request, users list, integrations adapters (all clearly labelled `simulated`).
- Demo storyline live: ₹18,75,000 Kirloskar Machinery Traders CRITICAL + ₹90,000 CEO impersonation SUSPECTED_FRAUD.

## Testing
- Full backend regression: 25/25 pytest passing (`/app/backend/tests/backend_test.py`).
- Frontend flows verified end-to-end via automation.
- **MOCKED / SIMULATED**: Voice/deepfake screening (advisory only, labelled). External GST / bank verify / cybercrime reporting are adapter stubs.

## Backlog (P1)
- Wire real GST verification adapter (Cleartax / Karza / MCA).
- Real bank-account name-match adapter (Razorpay / RBL / Cashfree).
- Real deepfake voice screening (Reality Defender / Pindrop).
- Vendor portal (self-service KYC upload, view own payments).
- Email + WhatsApp adapter (Resend + WhatsApp Business API) for automated callback prompts and incident intimations.
- Object storage (Emergent Object Storage) instead of local disk for evidence.
- Multi-tenant / multi-org (org-scoped queries + RBAC per org).

## Backlog (P2)
- ML-based anomaly detection (Isolation Forest / Prophet) on historical payments.
- ERP / Tally / Zoho Books / Vyapar app connectors.
- PDF report generation (currently JSON + CSV).
- SSO (Google Workspace) via Emergent Google Auth.

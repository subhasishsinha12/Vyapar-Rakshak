# Image / Invoice Vision Testing Playbook

## Rules
- Send base64-encoded images.
- Accepted MIME: image/jpeg, image/png, image/webp only.
- Reject blank / solid-color images.
- If input is PDF, extract first page as PNG before sending to GPT-5.2.
- Resize large images to ≤ 1600px on the longest side.

## Endpoint
POST `/api/invoices/scan` (multipart form field: `file`)

Response JSON keys:
- extracted: { supplier_name, gstin, pan, invoice_number, invoice_date, taxable_amount, cgst, sgst, igst, total_amount, po_number, bank_account, ifsc, qr_data, line_items }
- anomalies: string[] of red flags (duplicate invoice, arithmetic mismatch, GST inconsistency, changed bank details, missing PO, invoice already paid, suspicious image editing, unusual amount, vendor-name mismatch, invalid date sequence)
- risk_score: 0-100
- confidence: 0-1

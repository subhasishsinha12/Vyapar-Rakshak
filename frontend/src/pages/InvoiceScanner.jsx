import React, { useCallback, useEffect, useState } from "react";
import { http } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { UploadCloud, FileText, AlertTriangle } from "lucide-react";

export default function InvoiceScanner() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [scans, setScans] = useState([]);
  const [preview, setPreview] = useState(null);

  async function loadScans() {
    try {
      const { data } = await http.get("/invoices/scans");
      setScans(data);
    } catch (_) {}
  }

  useEffect(() => { loadScans(); }, []);

  const onFile = useCallback(async (file) => {
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
      toast.error("Only PNG / JPEG / WebP images are supported in the prototype.");
      return;
    }
    setUploading(true);
    setPreview(URL.createObjectURL(file));
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await http.post("/invoices/scan", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      toast.success("Scan complete");
      loadScans();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Scan failed");
    } finally { setUploading(false); }
  }, []);

  const extracted = result?.extracted || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Smart Invoice Scanner</h1>
        <p className="text-sm text-muted-foreground">
          Drop an invoice image (PNG / JPEG / WebP). GPT-5.2 vision extracts fields and flags anomalies.
        </p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragOver(false);
          onFile(e.dataTransfer.files?.[0]);
        }}
        data-testid="scan-dropzone"
        className={`card-elev relative flex cursor-pointer flex-col items-center justify-center gap-2 border-2 border-dashed p-10 text-center transition-colors ${dragOver ? "border-blue-500 bg-blue-500/5" : "border-white/15"}`}
      >
        <UploadCloud className="h-8 w-8 text-blue-400" />
        <div className="text-sm">Drop invoice here or</div>
        <label className="pill-btn inline-flex cursor-pointer items-center bg-blue-500 px-5 py-2 text-sm font-semibold text-white">
          Choose file
          <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden"
                 data-testid="scan-file-input"
                 onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
        {uploading && <div className="text-xs text-muted-foreground">Analysing with GPT-5.2 vision…</div>}
      </div>

      {result && (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <div className="card-elev p-5">
            <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Original document</h3>
            {preview && (
              <img src={preview} alt="invoice" data-testid="scan-preview"
                   className="mt-3 max-h-[520px] w-full rounded-md border border-white/10 object-contain" />
            )}
            <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              <span>{result.filename} · {(result.size / 1024).toFixed(1)} KB · {result.mime}</span>
            </div>
          </div>

          <div className="card-elev p-5">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Extracted fields</h3>
              <RiskBadge category={result.category} score={result.risk_score} />
            </div>
            {!extracted.ai_available && (
              <div className="mb-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                AI vision was unavailable. Manual review required.
              </div>
            )}
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ["Supplier", extracted.supplier_name],
                ["GSTIN", extracted.gstin],
                ["PAN", extracted.pan],
                ["Invoice #", extracted.invoice_number],
                ["Invoice date", extracted.invoice_date],
                ["Taxable amount", extracted.taxable_amount != null ? formatINR(extracted.taxable_amount) : null],
                ["CGST", extracted.cgst != null ? formatINR(extracted.cgst) : null],
                ["SGST", extracted.sgst != null ? formatINR(extracted.sgst) : null],
                ["IGST", extracted.igst != null ? formatINR(extracted.igst) : null],
                ["Total", extracted.total_amount != null ? formatINR(extracted.total_amount) : null],
                ["PO number", extracted.po_number],
                ["Bank account", extracted.bank_account],
                ["IFSC", extracted.ifsc],
                ["QR data", extracted.qr_data],
              ].map(([k, v]) => (
                <div key={k} className="rounded-md border border-white/10 bg-white/5 p-2">
                  <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{k}</div>
                  <div className="mt-0.5 text-sm">{v ?? "—"}</div>
                </div>
              ))}
            </div>

            {extracted.line_items?.length > 0 && (
              <div className="mt-4">
                <div className="text-xs uppercase text-muted-foreground">Line items</div>
                <table className="mt-1 w-full text-xs">
                  <thead className="text-muted-foreground">
                    <tr><th className="text-left">Description</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>
                  </thead>
                  <tbody>
                    {extracted.line_items.map((li, i) => (
                      <tr key={i} className="border-t border-white/5">
                        <td className="py-1">{li.description}</td>
                        <td className="text-center">{li.qty}</td>
                        <td className="text-right">{li.rate}</td>
                        <td className="text-right">{li.amount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4">
              <div className="text-xs uppercase text-muted-foreground">Anomalies</div>
              {result.anomalies?.length ? (
                <ul className="mt-2 space-y-2">
                  {result.anomalies.map((a, i) => (
                    <li key={i} className="rounded-md border border-rose-500/20 bg-rose-500/5 p-2 text-xs">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
                        <RiskBadge category={a.severity === "critical" ? "critical" : a.severity === "high" ? "high" : "moderate"} />
                        <span>{a.code}</span>
                      </div>
                      <div className="mt-1 text-muted-foreground">{a.message}</div>
                    </li>
                  ))}
                </ul>
              ) : <div className="mt-2 text-sm text-emerald-400">No anomalies detected.</div>}
            </div>
          </div>
        </div>
      )}

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Recent scans</h3>
        <div className="mt-3 divide-y divide-white/5 text-sm">
          {scans.map((s) => (
            <div key={s.id} className="flex items-center justify-between py-2">
              <div>
                <div className="font-medium">{s.extracted?.supplier_name || s.filename}</div>
                <div className="text-xs text-muted-foreground">
                  {s.extracted?.invoice_number || "—"} · {fromNow(s.created_at)}
                </div>
              </div>
              <RiskBadge category={s.category} score={s.risk_score} />
            </div>
          ))}
          {!scans.length && <div className="py-2 text-sm text-muted-foreground">No scans yet.</div>}
        </div>
      </div>
    </div>
  );
}

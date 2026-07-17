import React, { useEffect, useState } from "react";
import { http } from "../../lib/api";
import { fromNow } from "../../lib/format";
import { toast } from "sonner";
import { Upload, FileText, CheckCircle2, Clock, XCircle } from "lucide-react";

const KIND_OPTIONS = [
  { v: "gst_certificate", label: "GST certificate" },
  { v: "pan_card", label: "PAN card" },
  { v: "cancelled_cheque", label: "Cancelled cheque" },
  { v: "bank_proof", label: "Bank proof (statement)" },
  { v: "incorporation", label: "Incorporation certificate" },
  { v: "address_proof", label: "Address proof" },
  { v: "other", label: "Other" },
];

export default function VendorKyc() {
  const [rows, setRows] = useState([]);
  const [kind, setKind] = useState("gst_certificate");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const { data } = await http.get("/vendor/me");
    setRows(data.kyc_documents || []);
  }
  useEffect(() => { load(); }, []);

  async function upload() {
    if (!file) { toast.error("Choose a file"); return; }
    if (file.size > 5 * 1024 * 1024) { toast.error("File too large (max 5 MB)"); return; }
    setBusy(true);
    const fd = new FormData();
    fd.append("kind", kind);
    fd.append("notes", notes);
    fd.append("file", file);
    try {
      await http.post("/vendor/kyc", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Document uploaded. It will be reviewed by the buyer's finance team.");
      setFile(null); setNotes(""); load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Upload failed");
    }
    setBusy(false);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">KYC documents</h1>
        <p className="text-sm text-muted-foreground">
          Upload GST, PAN, bank proof and incorporation documents. Approved documents raise your trust score.
        </p>
      </div>

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Upload new document</h3>
        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <label className="text-xs uppercase text-muted-foreground">Document kind</label>
            <select data-testid="kyc-kind" value={kind} onChange={(e) => setKind(e.target.value)}
                    className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
              {KIND_OPTIONS.map((k) => <option key={k.v} value={k.v}>{k.label}</option>)}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="text-xs uppercase text-muted-foreground">Notes (optional)</label>
            <input data-testid="kyc-notes" value={notes} onChange={(e) => setNotes(e.target.value)}
                   className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="mt-3">
          <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-white/15 bg-white/5 p-4 text-sm hover:border-emerald-500/40">
            <Upload className="h-4 w-4" />
            <span>{file ? file.name : "Choose file (max 5 MB, PDF / image)"}</span>
            <input type="file" data-testid="kyc-file" className="hidden"
                   onChange={(e) => setFile(e.target.files?.[0])} />
          </label>
        </div>
        <div className="mt-3 flex justify-end">
          <button onClick={upload} disabled={busy} data-testid="kyc-upload"
                  className="pill-btn bg-emerald-500 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {busy ? "Uploading…" : "Submit for review"}
          </button>
        </div>
      </div>

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Your documents</h3>
        <div className="mt-3 divide-y divide-white/5">
          {rows.map((r) => {
            const Icon = r.status === "approved" ? CheckCircle2 : r.status === "rejected" ? XCircle : Clock;
            const tone = r.status === "approved" ? "text-emerald-400" : r.status === "rejected" ? "text-rose-400" : "text-amber-400";
            return (
              <div key={r.id} data-testid={`kyc-row-${r.id}`}
                   className="flex items-center justify-between py-3 text-sm">
                <div className="flex items-start gap-3">
                  <FileText className="mt-0.5 h-4 w-4 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{KIND_OPTIONS.find((k) => k.v === r.kind)?.label || r.kind}</div>
                    <div className="text-xs text-muted-foreground">{r.filename} · {fromNow(r.uploaded_at)}</div>
                    {r.review_reason && <div className="mt-0.5 text-xs text-rose-300">Review: {r.review_reason}</div>}
                  </div>
                </div>
                <div className={`flex items-center gap-1 text-xs ${tone}`}>
                  <Icon className="h-3.5 w-3.5" />
                  <span className="uppercase">{r.status.replaceAll("_", " ")}</span>
                </div>
              </div>
            );
          })}
          {!rows.length && <div className="py-4 text-sm text-muted-foreground">No documents uploaded yet.</div>}
        </div>
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { http } from "../../lib/api";
import { fromNow, maskAccount } from "../../lib/format";
import { toast } from "sonner";
import { AlertTriangle } from "lucide-react";

export default function VendorBankChange() {
  const [form, setForm] = useState({
    new_account_number: "", new_ifsc: "", new_bank: "", contact_phone: "",
  });
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    const { data } = await http.get("/vendor/me");
    setRows(data.bank_change_requests || []);
  }
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await http.post("/vendor/bank-change", form);
      toast.success("Bank change requested. Buyer will independently verify with you before approval.");
      setForm({ new_account_number: "", new_ifsc: "", new_bank: "", contact_phone: "" });
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
    setBusy(false);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Request bank-account change</h1>
        <p className="text-sm text-muted-foreground">
          Every change goes through independent callback verification, cooling period and dual approval.
        </p>
      </div>

      <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
        <AlertTriangle className="mr-1 inline h-3.5 w-3.5" />
        The buyer will call you on your previously verified number. Do not accept callbacks on the phone number listed in this request.
      </div>

      <form onSubmit={submit} className="card-elev p-5">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Field label="New account number" value={form.new_account_number}
                 testId="new-acc" onChange={(v) => setForm({ ...form, new_account_number: v })} />
          <Field label="New IFSC" value={form.new_ifsc} testId="new-ifsc"
                 onChange={(v) => setForm({ ...form, new_ifsc: v.toUpperCase() })} />
          <Field label="Bank name" value={form.new_bank} testId="new-bank"
                 onChange={(v) => setForm({ ...form, new_bank: v })} />
          <Field label="Contact phone (for callback)" value={form.contact_phone}
                 testId="new-phone" onChange={(v) => setForm({ ...form, contact_phone: v })} />
        </div>
        <div className="mt-4 flex justify-end">
          <button disabled={busy} data-testid="bc-submit"
                  className="pill-btn bg-emerald-500 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
            {busy ? "Submitting…" : "Submit change request"}
          </button>
        </div>
      </form>

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Previous requests</h3>
        <div className="mt-3 divide-y divide-white/5 text-sm">
          {rows.map((r) => (
            <div key={r.id} className="py-3">
              <div className="flex items-center justify-between">
                <div className="font-medium">Change to {maskAccount(r.new_account_number)} · {r.new_ifsc}</div>
                <span className={`rounded-full px-2 py-0.5 text-xs uppercase ${
                  r.status === "approved" ? "bg-emerald-500/10 text-emerald-300" :
                  r.status === "rejected" ? "bg-rose-500/10 text-rose-300" :
                  "bg-amber-500/10 text-amber-300"}`}>{r.status}</span>
              </div>
              <div className="text-xs text-muted-foreground">
                {fromNow(r.created_at)} · callback {r.callback_status} · approvals {r.approvals_received}/{r.approvals_required}
              </div>
            </div>
          ))}
          {!rows.length && <div className="py-4 text-sm text-muted-foreground">No requests yet.</div>}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, testId }) {
  return (
    <div>
      <label className="text-xs uppercase text-muted-foreground">{label}</label>
      <input required value={value} onChange={(e) => onChange(e.target.value)}
             data-testid={testId}
             className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { maskAccount, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { PhoneCall, Check, X } from "lucide-react";

export default function Beneficiaries() {
  const [rows, setRows] = useState([]);

  async function load() {
    const { data } = await http.get("/beneficiary-changes");
    setRows(data);
  }
  useEffect(() => { load(); }, []);

  async function act(id, action) {
    try {
      await http.post(`/beneficiary-changes/${id}/decision`, { action });
      toast.success(`Recorded: ${action}`);
      load();
    } catch (_) { toast.error("Failed"); }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Beneficiary bank changes</h1>
        <p className="text-sm text-muted-foreground">
          Every account change requires callback verification, two approvals and a cooling period.
        </p>
      </div>

      <div className="space-y-3">
        {rows.map((r) => (
          <div key={r.id} data-testid={`ben-${r.id}`} className="card-elev p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground">Vendor</div>
                <div className="font-display text-lg font-semibold">{r.vendor_name}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(r.flags || []).map((f, i) => (
                    <span key={i} className="rounded-full bg-rose-500/10 px-2 py-0.5 text-xs text-rose-300">
                      ⚠ {f.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs uppercase text-muted-foreground">Requested</div>
                <div className="text-sm">{fromNow(r.created_at)}</div>
                <div className="mt-1 flex items-center justify-end gap-2 text-xs">
                  <span className={`rounded-full px-2 py-0.5 ${r.status === "pending" ? "bg-amber-500/10 text-amber-300" : r.status === "approved" ? "bg-emerald-500/10 text-emerald-300" : "bg-rose-500/10 text-rose-300"}`}>
                    {r.status}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-md border border-white/10 bg-white/5 p-3">
                <div className="text-xs uppercase text-muted-foreground">Old account</div>
                <div className="mt-1 font-mono text-sm">{maskAccount(r.old_account_number)} · {r.old_ifsc}</div>
              </div>
              <div className="rounded-md border border-rose-500/20 bg-rose-500/5 p-3">
                <div className="text-xs uppercase text-rose-300">New account (requested)</div>
                <div className="mt-1 font-mono text-sm">{maskAccount(r.new_account_number)} · {r.new_ifsc}</div>
                <div className="text-xs text-muted-foreground">Bank: {r.new_bank}</div>
                <div className="text-xs text-muted-foreground">Via: {r.requested_via} · from {r.requested_email_domain}</div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
              <Kv label="Callback" value={r.callback_status} />
              <Kv label="Approvals" value={`${r.approvals_received}/${r.approvals_required}`} />
              <Kv label="Cooling" value={`${r.cooling_period_hours}h`} />
              <Kv label="Code" value={r.verification_code} mono />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <BtnBen testId={`cb-verified-${r.id}`} onClick={() => act(r.id, "callback_verified")}>
                <PhoneCall className="mr-1 inline h-3.5 w-3.5" /> Mark callback verified
              </BtnBen>
              <BtnBen testId={`cb-failed-${r.id}`} tone="bad" onClick={() => act(r.id, "callback_failed")}>
                Callback failed / suspicious
              </BtnBen>
              <BtnBen testId={`approve-${r.id}`} tone="good" onClick={() => act(r.id, "approve")}>
                <Check className="mr-1 inline h-3.5 w-3.5" /> Approve
              </BtnBen>
              <BtnBen testId={`reject-${r.id}`} tone="bad" onClick={() => act(r.id, "reject")}>
                <X className="mr-1 inline h-3.5 w-3.5" /> Reject
              </BtnBen>
            </div>
            <div className="mt-2 text-[11px] text-muted-foreground">
              ℹ Never use contact details supplied in the new request. Use previously verified numbers only.
            </div>
          </div>
        ))}
        {!rows.length && <div className="text-sm text-muted-foreground">No pending beneficiary changes.</div>}
      </div>
    </div>
  );
}

function Kv({ label, value, mono }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-2">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className={`mt-0.5 text-sm ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
function BtnBen({ children, tone = "default", onClick, testId }) {
  const cls = {
    default: "border-white/10 bg-white/5 hover:border-blue-500/40",
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    bad: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  }[tone];
  return (
    <button onClick={onClick} data-testid={testId}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${cls}`}>{children}</button>
  );
}

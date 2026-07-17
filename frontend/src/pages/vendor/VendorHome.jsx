import React, { useEffect, useState } from "react";
import { http } from "../../lib/api";
import { formatINR, fromNow, maskAccount } from "../../lib/format";
import { Link } from "react-router-dom";
import { CheckCircle2, ShieldCheck, FileText } from "lucide-react";

export default function VendorHome() {
  const [profile, setProfile] = useState(null);
  useEffect(() => { (async () => {
    try { const { data } = await http.get("/vendor/me"); setProfile(data); }
    catch (_) { setProfile(false); }
  })(); }, []);

  if (profile === null) return <div className="text-muted-foreground">Loading vendor portal…</div>;
  if (profile === false) return (
    <div className="card-elev p-6">
      <div className="text-sm text-muted-foreground">
        Your account is not linked to a vendor profile. Please contact your buyer to link this login.
      </div>
    </div>
  );
  const v = profile.vendor;
  const kycApproved = (profile.kyc_documents || []).filter((k) => k.status === "approved").length;
  const kycPending = (profile.kyc_documents || []).filter((k) => k.status === "pending_review").length;
  const changePending = (profile.bank_change_requests || []).filter((c) => c.status === "pending").length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Welcome, {v.name}</h1>
        <p className="text-sm text-muted-foreground">
          Manage your KYC, track invoice status and request bank-account changes securely.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat icon={ShieldCheck} label="Trust score" value={`${v.trust_score}/100`} tone="good" testId="v-trust" />
        <Stat icon={FileText} label="KYC approved" value={kycApproved} testId="v-kyc-ok" />
        <Stat icon={FileText} label="KYC pending" value={kycPending} tone="warn" testId="v-kyc-pending" />
        <Stat icon={CheckCircle2} label="Bank changes pending" value={changePending} testId="v-bc-pending" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Approved bank accounts</h3>
          <div className="mt-3 space-y-2">
            {(v.approved_bank_accounts || []).map((a, i) => (
              <div key={i} className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2 text-sm">
                <div className="font-medium">{a.bank}</div>
                <div className="font-mono text-xs">{maskAccount(a.account_number)} · {a.ifsc}</div>
                <div className="text-xs text-muted-foreground">Verified {fromNow(a.verified_at)}</div>
              </div>
            ))}
            {v.recent_account_change_at && (
              <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300">
                Recent change {fromNow(v.recent_account_change_at)} — under callback verification.
              </div>
            )}
          </div>
          <Link to="/vendor/bank-change" data-testid="cta-bank-change"
                className="mt-3 inline-block text-xs text-emerald-400 hover:text-emerald-300">
            Request bank-account change →
          </Link>
        </div>

        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Vendor identity</h3>
          <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
            <Kv label="GSTIN" value={v.gstin} mono />
            <Kv label="PAN" value={v.pan} mono />
            <Kv label="Category" value={v.category} />
            <Kv label="Avg invoice" value={formatINR(v.average_invoice_amount)} />
            <Kv label="Address" value={v.address} full />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, tone = "default", testId }) {
  const cls = tone === "good" ? "text-emerald-400" : tone === "warn" ? "text-amber-400" : "text-foreground";
  return (
    <div className="card-elev p-4" data-testid={testId}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted-foreground">
        <Icon className="h-3.5 w-3.5" /> {label}
      </div>
      <div className={`mt-2 font-display text-2xl font-semibold ${cls}`}>{value}</div>
    </div>
  );
}
function Kv({ label, value, mono, full }) {
  return (
    <div className={`rounded-md border border-white/10 bg-white/5 p-2 ${full ? "col-span-2" : ""}`}>
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className={`mt-0.5 text-sm ${mono ? "font-mono" : ""}`}>{value || "—"}</div>
    </div>
  );
}

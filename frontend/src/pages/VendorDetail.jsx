import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, maskAccount, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { ArrowLeft, Ban, ShieldCheck, Landmark } from "lucide-react";

export default function VendorDetail() {
  const { id } = useParams();
  const [v, setV] = useState(null);
  const [gst, setGst] = useState(null);
  const [bankChecks, setBankChecks] = useState({});
  const [busy, setBusy] = useState(null);

  async function load() {
    const { data } = await http.get(`/vendors/${id}`);
    setV(data);
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function block() {
    const reason = prompt("Reason for blocking?");
    if (!reason) return;
    try {
      await http.post(`/vendors/${id}/block`, { reason });
      toast.success("Vendor blocked");
      load();
    } catch (_) { toast.error("Failed"); }
  }

  async function verifyGst() {
    setBusy("gst");
    try {
      const { data } = await http.post(`/vendors/${id}/verify-gst`);
      setGst({ result: data, checked_at: new Date().toISOString() });
      if (data.ok) toast.success(`GST verified via ${data.provider}${data.simulated ? " (simulated)" : ""}`);
      else toast.error(data.error || "GST verification failed");
    } catch (_) { toast.error("Failed"); }
    setBusy(null);
  }

  async function verifyBank(acc) {
    const key = acc.account_number;
    setBusy(`bank-${key}`);
    try {
      const { data } = await http.post(`/vendors/${id}/verify-bank`,
        { account_number: acc.account_number, ifsc: acc.ifsc, expected_name: v.name });
      setBankChecks((s) => ({ ...s, [key]: data }));
      if (data.ok) toast.success(`Bank check ${data.verdict} via ${data.provider}${data.simulated ? " (simulated)" : ""}`);
      else toast.error(data.error || "Bank verification failed");
    } catch (_) { toast.error("Failed"); }
    setBusy(null);
  }

  if (!v) return <div className="text-muted-foreground">Loading vendor passport…</div>;

  const trustCat = v.trust_score >= 85 ? "low" : v.trust_score >= 65 ? "moderate" : v.trust_score >= 45 ? "high" : "critical";

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/vendors" className="text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="inline h-4 w-4" /> Back
        </Link>
      </div>

      <div className="card-elev p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-muted-foreground">{v.category}</div>
            <h1 className="font-display text-3xl font-semibold tracking-tight">{v.name}</h1>
            <div className="mt-1 text-xs text-muted-foreground">GSTIN {v.gstin} · PAN {v.pan}</div>
            <div className="mt-1 max-w-xl text-xs text-muted-foreground">{v.address}</div>
            {gst?.result && (
              <div className="mt-3 rounded-md border border-white/10 bg-white/5 p-3 text-xs">
                <div className="flex items-center gap-2">
                  <ShieldCheck className={`h-3.5 w-3.5 ${gst.result.ok ? "text-emerald-400" : "text-rose-400"}`} />
                  <span className="font-medium">GST · {gst.result.provider}{gst.result.simulated ? " (simulated)" : ""}</span>
                </div>
                <div className="mt-1 grid grid-cols-2 gap-2 md:grid-cols-3">
                  <span className="text-muted-foreground">Legal name: <span className="text-foreground">{gst.result.legal_name || "—"}</span></span>
                  <span className="text-muted-foreground">Status: <span className="text-foreground">{gst.result.status || "—"}</span></span>
                  <span className="text-muted-foreground">Filing: <span className="text-foreground">{gst.result.filing_status || "—"}</span></span>
                </div>
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
            <RiskBadge category={trustCat} score={v.trust_score} />
            <button data-testid="verify-gst" onClick={verifyGst} disabled={busy === "gst"}
                    className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs text-blue-300 hover:border-blue-500/50 disabled:opacity-50">
              <ShieldCheck className="mr-1 inline h-3 w-3" />
              {busy === "gst" ? "Verifying…" : "Verify GST via adapter"}
            </button>
            {!v.blocked && (
              <button data-testid="block-vendor" onClick={block}
                      className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs text-rose-300 hover:border-rose-500/50">
                <Ban className="mr-1 inline h-3 w-3" /> Block vendor
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Contacts</h3>
          <div className="mt-3 space-y-2">
            {(v.contacts || []).map((c, i) => (
              <div key={i} className="rounded-md border border-white/10 bg-white/5 p-2 text-xs">
                <div className="font-medium">{c.name} {c.verified && <span className="ml-1 text-emerald-400">✓ verified</span>}</div>
                <div className="text-muted-foreground">{c.phone}</div>
                <div className="text-muted-foreground">{c.email}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Approved bank accounts</h3>
          <div className="mt-3 space-y-2">
            {(v.approved_bank_accounts || []).map((a, i) => {
              const check = bankChecks[a.account_number];
              return (
                <div key={i} className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{a.bank}</div>
                      <div>{maskAccount(a.account_number)} · {a.ifsc}</div>
                      <div className="text-muted-foreground">Verified {fromNow(a.verified_at)}</div>
                    </div>
                    <button onClick={() => verifyBank(a)} disabled={busy === `bank-${a.account_number}`}
                            data-testid={`verify-bank-${i}`}
                            className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-[10px] text-blue-300 hover:border-blue-500/50 disabled:opacity-50">
                      <Landmark className="mr-1 inline h-3 w-3" />
                      {busy === `bank-${a.account_number}` ? "Checking…" : "Penny-drop"}
                    </button>
                  </div>
                  {check && (
                    <div className="mt-2 rounded border border-white/10 bg-black/30 p-2">
                      <div className="flex items-center justify-between">
                        <div>Name at bank: <span className="text-foreground">{check.name_at_bank || "—"}</span></div>
                        <span className={`rounded-full px-2 py-0.5 uppercase ${
                          check.verdict === "match" ? "bg-emerald-500/10 text-emerald-300" :
                          check.verdict === "partial" ? "bg-amber-500/10 text-amber-300" :
                          "bg-rose-500/10 text-rose-300"}`}>{check.verdict}</span>
                      </div>
                      <div className="text-muted-foreground">
                        Provider: {check.provider}{check.simulated ? " (simulated)" : ""} · match score {check.name_match_score ?? "—"}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {v.recent_account_change_at && (
              <div className="rounded-md border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
                ⚠ Recent change {fromNow(v.recent_account_change_at)} — pending independent callback
              </div>
            )}
          </div>
        </div>
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">History</h3>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            <Stat label="First txn" value={fromNow(v.first_transaction_at)} />
            <Stat label="Last txn" value={fromNow(v.last_transaction_at)} />
            <Stat label="Avg invoice" value={formatINR(v.average_invoice_amount)} />
            <Stat label="Max historical" value={formatINR(v.max_historical_amount)} />
          </div>
          {v.watchlist_reason && (
            <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-300">
              Watchlist: {v.watchlist_reason}
            </div>
          )}
        </div>
      </div>

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Payment history</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-widest text-muted-foreground">
              <tr>
                <th className="py-2">Invoice</th><th>Amount</th><th>Mode</th>
                <th>Status</th><th>Risk</th><th>When</th>
              </tr>
            </thead>
            <tbody>
              {(v.payment_history || []).map((p) => (
                <tr key={p.id} className="border-t border-white/5">
                  <td className="py-2"><Link to={`/verify/${p.id}`} className="hover:text-blue-400">{p.invoice_number}</Link></td>
                  <td>{formatINR(p.amount)}</td>
                  <td className="text-xs">{p.mode}</td>
                  <td className="text-xs uppercase">{p.status}</td>
                  <td><RiskBadge category={p.risk?.category} score={p.risk?.score} /></td>
                  <td className="text-xs text-muted-foreground">{fromNow(p.requested_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-2">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm">{value}</div>
    </div>
  );
}

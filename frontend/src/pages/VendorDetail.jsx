import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, maskAccount, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { ArrowLeft, Ban } from "lucide-react";

export default function VendorDetail() {
  const { id } = useParams();
  const [v, setV] = useState(null);

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
          </div>
          <div className="flex flex-col items-end gap-2">
            <RiskBadge category={trustCat} score={v.trust_score} />
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
            {(v.approved_bank_accounts || []).map((a, i) => (
              <div key={i} className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-2 text-xs">
                <div className="font-medium">{a.bank}</div>
                <div>{maskAccount(a.account_number)} · {a.ifsc}</div>
                <div className="text-muted-foreground">Verified {fromNow(a.verified_at)}</div>
              </div>
            ))}
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

import React, { useEffect, useState } from "react";
import { http } from "../../lib/api";
import { formatINR, fromNow } from "../../lib/format";

const STATUSES = ["", "pending", "approved", "held", "rejected", "clarification"];

export default function VendorPayments() {
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");

  async function load() {
    const { data } = await http.get("/vendor/payments", {
      params: status ? { status } : {}
    });
    setRows(data.items || []);
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status]);

  const statusColor = (s) => ({
    approved: "text-emerald-400",
    pending: "text-amber-400",
    held: "text-amber-300",
    rejected: "text-rose-400",
    clarification: "text-blue-400",
    fraud: "text-rose-400",
  }[s] || "text-muted-foreground");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">My payments</h1>
        <p className="text-sm text-muted-foreground">
          Real-time status of every invoice you have submitted to this buyer.
        </p>
      </div>

      <div className="card-elev p-3">
        <select data-testid="vp-status" value={status} onChange={(e) => setStatus(e.target.value)}
                className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
          {STATUSES.map((s) => <option key={s} value={s}>{s || "All statuses"}</option>)}
        </select>
      </div>

      <div className="card-elev overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-widest text-muted-foreground">
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3">Mode</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Submitted</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} data-testid={`vp-row-${p.id}`} className="border-t border-white/5">
                <td className="px-4 py-3 font-mono text-xs">{p.invoice_number}</td>
                <td className="px-4 py-3 text-right">{formatINR(p.amount)}</td>
                <td className="px-4 py-3 text-xs">{p.mode}</td>
                <td className={`px-4 py-3 text-xs uppercase ${statusColor(p.status)}`}>{p.status}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{fromNow(p.requested_at)}</td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={5} className="px-4 py-10 text-center text-sm text-muted-foreground">
                No invoices found for the selected status.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

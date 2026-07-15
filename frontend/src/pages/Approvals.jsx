import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";

export default function Approvals() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [params] = useSearchParams();

  async function load() {
    const { data } = await http.get("/payments", {
      params: {
        q: q || params.get("q") || undefined,
        category: category || undefined,
        status: status || undefined,
        limit: 100,
      }
    });
    setRows(data.items);
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q, category, status]);
  useEffect(() => { if (params.get("q")) setQ(params.get("q")); }, [params]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Approvals queue</h1>
        <p className="text-sm text-muted-foreground">
          Maker-checker separation enforced. Sorted by risk × amount.
        </p>
      </div>

      <div className="card-elev p-4">
        <div className="flex flex-wrap gap-2">
          <input
            data-testid="approvals-q"
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="Search invoice / vendor…"
            className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
          />
          <select data-testid="approvals-category" value={category} onChange={(e) => setCategory(e.target.value)}
                  className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
            <option value="">All risk</option>
            <option>low</option><option>moderate</option><option>high</option><option>critical</option><option>suspected_fraud</option>
          </select>
          <select data-testid="approvals-status" value={status} onChange={(e) => setStatus(e.target.value)}
                  className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
            <option value="">All status</option>
            <option>pending</option><option>held</option><option>approved</option><option>rejected</option>
            <option>clarification</option><option>callback_pending</option><option>escalated</option>
          </select>
        </div>
      </div>

      <div className="card-elev overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs uppercase tracking-widest text-muted-foreground">
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Vendor</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3">Mode</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">When</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} data-testid={`row-${p.id}`} className="border-t border-white/5 hover:bg-white/5">
                <td className="px-4 py-3 font-mono text-xs">{p.invoice_number}</td>
                <td className="px-4 py-3">{p.vendor_name}</td>
                <td className="px-4 py-3 text-right font-medium">{formatINR(p.amount)}</td>
                <td className="px-4 py-3 text-xs">{p.mode}</td>
                <td className="px-4 py-3 text-xs uppercase">{p.status}</td>
                <td className="px-4 py-3"><RiskBadge category={p.risk?.category} score={p.risk?.score} /></td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{fromNow(p.requested_at)}</td>
                <td className="px-4 py-3">
                  <Link to={`/verify/${p.id}`} className="text-xs text-blue-400 hover:text-blue-300"
                        data-testid={`open-${p.id}`}>Review →</Link>
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={8} className="px-4 py-10 text-center text-sm text-muted-foreground">
                No payments match your filters.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

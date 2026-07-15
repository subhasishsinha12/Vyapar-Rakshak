import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { fromNow } from "../lib/format";

export default function AuditTrail() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");

  async function load() {
    const { data } = await http.get("/audit", { params: { q: q || undefined, limit: 200 } });
    setRows(data.items);
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Audit trail</h1>
        <p className="text-sm text-muted-foreground">
          Immutable-looking log of every user action. Filter by user, action or reason.
        </p>
      </div>
      <div className="card-elev p-3">
        <input value={q} onChange={(e) => setQ(e.target.value)}
               data-testid="audit-q"
               placeholder="Filter by user, action or reason…"
               className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
      </div>
      <div className="card-elev overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10 text-left uppercase tracking-widest text-muted-foreground">
              <th className="px-3 py-2">When</th>
              <th className="px-3 py-2">User</th>
              <th className="px-3 py-2">Role</th>
              <th className="px-3 py-2">Action</th>
              <th className="px-3 py-2">Entity</th>
              <th className="px-3 py-2">Reason</th>
              <th className="px-3 py-2">Device / IP</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid={`audit-${r.id}`} className="border-t border-white/5 hover:bg-white/5">
                <td className="px-3 py-2 text-muted-foreground">{fromNow(r.timestamp)}</td>
                <td className="px-3 py-2 font-medium">{r.user_name}</td>
                <td className="px-3 py-2">{r.user_role}</td>
                <td className="px-3 py-2 font-mono">{r.action}</td>
                <td className="px-3 py-2 text-muted-foreground">{r.entity_type} · {r.entity_id?.slice(0, 8)}</td>
                <td className="px-3 py-2 text-muted-foreground">{r.reason || "—"}</td>
                <td className="px-3 py-2 text-muted-foreground">{r.device} · {r.ip}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

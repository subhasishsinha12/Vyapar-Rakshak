import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";

export default function IncidentRoom() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    (async () => {
      const { data } = await http.get("/incidents");
      setRows(data);
    })();
  }, []);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Fraud Incident Room</h1>
        <p className="text-sm text-muted-foreground">
          Investigate, escalate and preserve every fraud incident with a full evidence pack.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {rows.map((r) => (
          <Link key={r.id} to={`/incidents/${r.id}`}
                data-testid={`incident-${r.id}`}
                className="card-elev hoverable p-5">
            <div className="flex items-center justify-between">
              <div className="font-mono text-xs text-muted-foreground">{r.incident_no}</div>
              <span className={`rounded-full px-2 py-0.5 text-xs uppercase ${
                r.status === "closed" ? "bg-emerald-500/10 text-emerald-300" :
                r.status === "frozen" ? "bg-amber-500/10 text-amber-300" :
                "bg-rose-500/10 text-rose-300"
              }`}>
                {r.status}
              </span>
            </div>
            <div className="mt-2 font-display text-lg font-semibold">{r.suspected_type}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              Payment ref {r.payment_reference || "—"} · opened {fromNow(r.created_at)}
            </div>
            <div className="mt-3 flex items-center justify-between">
              <div>
                <div className="text-[10px] uppercase text-muted-foreground">Amount at risk</div>
                <div className="text-xl font-semibold">{formatINR(r.amount_at_risk)}</div>
              </div>
              <div className="text-[10px] uppercase text-muted-foreground">
                {r.timeline?.length || 0} timeline events
              </div>
            </div>
          </Link>
        ))}
        {!rows.length && <div className="text-sm text-muted-foreground">No incidents open.</div>}
      </div>
    </div>
  );
}

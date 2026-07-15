import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { AlertOctagon } from "lucide-react";

export default function FraudAlerts() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    (async () => {
      const { data } = await http.get("/payments", { params: {
        category: "critical", limit: 100,
      }});
      const { data: susp } = await http.get("/payments", { params: {
        category: "suspected_fraud", limit: 100,
      }});
      setItems([...(susp.items || []), ...(data.items || [])]);
    })();
  }, []);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Fraud alerts</h1>
        <p className="text-sm text-muted-foreground">
          Every payment classified Critical or Suspected Fraud lands here.
        </p>
      </div>
      <div className="space-y-3">
        {items.map((p) => (
          <Link
            key={p.id} to={`/verify/${p.id}`}
            data-testid={`alert-${p.id}`}
            className="card-elev hoverable flex items-center justify-between border-l-4 border-rose-500 p-4"
          >
            <div className="flex items-start gap-3">
              <AlertOctagon className="mt-0.5 h-5 w-5 text-rose-400" />
              <div>
                <div className="font-medium">{formatINR(p.amount)} · {p.vendor_name}</div>
                <div className="text-xs text-muted-foreground">
                  {p.invoice_number} · {p.mode} · {fromNow(p.requested_at)}
                </div>
                {p.risk?.flags?.[0] && (
                  <div className="mt-1 text-xs text-rose-300">
                    Top flag: {p.risk.flags[0].title}
                  </div>
                )}
              </div>
            </div>
            <RiskBadge category={p.risk?.category} score={p.risk?.score} />
          </Link>
        ))}
        {!items.length && <div className="text-sm text-muted-foreground">No active fraud alerts.</div>}
      </div>
    </div>
  );
}

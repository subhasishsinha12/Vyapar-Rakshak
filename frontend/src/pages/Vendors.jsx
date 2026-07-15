import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { http } from "../lib/api";
import RiskBadge from "../components/RiskBadge";
import { formatINR } from "../lib/format";
import { ShieldAlert, ShieldCheck } from "lucide-react";

export default function Vendors() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      const { data } = await http.get("/vendors");
      setRows(data);
    })();
  }, []);

  const filtered = rows.filter((v) =>
    !q || v.name.toLowerCase().includes(q.toLowerCase()) ||
    (v.gstin || "").toLowerCase().includes(q.toLowerCase())
  );

  function trustCategory(score) {
    if (score >= 85) return "low";
    if (score >= 65) return "moderate";
    if (score >= 45) return "high";
    return "critical";
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Vendor Trust Passports</h1>
          <p className="text-sm text-muted-foreground">
            Every vendor gets a live trust score 0–100 with a full audit history.
          </p>
        </div>
        <input
          data-testid="vendor-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or GSTIN…"
          className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((v) => {
          const tc = trustCategory(v.trust_score || 0);
          const isRisk = tc === "critical" || tc === "high";
          return (
            <Link
              key={v.id}
              to={`/vendors/${v.id}`}
              data-testid={`vendor-card-${v.id}`}
              className="card-elev hoverable block p-5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isRisk ? (
                    <ShieldAlert className="h-4 w-4 text-rose-400" />
                  ) : (
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  )}
                  <span className="text-xs uppercase tracking-widest text-muted-foreground">
                    {v.category}
                  </span>
                </div>
                <RiskBadge category={tc} score={v.trust_score} />
              </div>
              <div className="mt-3 font-display text-lg font-semibold">{v.name}</div>
              <div className="mt-0.5 text-xs text-muted-foreground">{v.gstin || "—"}</div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5">
                  <div className="text-[10px] uppercase text-muted-foreground">Avg invoice</div>
                  <div className="text-sm">{formatINR(v.average_invoice_amount)}</div>
                </div>
                <div className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5">
                  <div className="text-[10px] uppercase text-muted-foreground">Max historical</div>
                  <div className="text-sm">{formatINR(v.max_historical_amount)}</div>
                </div>
              </div>
              {v.recent_account_change_at && (
                <div className="mt-3 rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-300">
                  ⚠ Bank details changed recently
                </div>
              )}
              {v.blocked && (
                <div className="mt-2 rounded-md bg-rose-500/20 px-3 py-1.5 text-xs text-rose-300">
                  🚫 Blocked · {v.block_reason}
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}

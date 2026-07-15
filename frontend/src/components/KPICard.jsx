import React from "react";
import { formatINRShort } from "../lib/format";

export function KPICard({ label, value, hint, tone = "default", testId, isCurrency = false }) {
  const toneMap = {
    default: "text-foreground",
    good: "text-emerald-400",
    warn: "text-amber-400",
    bad: "text-rose-400",
  };
  const display = isCurrency ? formatINRShort(value) : value;
  return (
    <div
      data-testid={testId}
      className="card-elev hoverable relative overflow-hidden p-5"
    >
      <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className={`mt-2 font-display text-3xl font-semibold ${toneMap[tone]}`}>
        {display ?? "—"}
      </div>
      {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export default KPICard;

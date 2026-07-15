import React from "react";
import { RISK_LABEL } from "../lib/format";

export function RiskBadge({ category, score, size = "sm" }) {
  const cls = `risk-${category || "low"}`;
  const label = RISK_LABEL[category] || "Low";
  return (
    <span
      data-testid={`risk-badge-${category}`}
      className={`${cls} inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
      {typeof score === "number" && (
        <span className="ml-1 font-mono text-[11px] font-normal opacity-80">
          {score}/100
        </span>
      )}
    </span>
  );
}

export default RiskBadge;

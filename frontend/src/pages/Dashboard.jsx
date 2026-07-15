import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity, ArrowRight, ShieldAlert, TrendingUp, Wallet, Users, Clock,
  AlertTriangle,
} from "lucide-react";
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis,
  Tooltip, CartesianGrid, LineChart, Line, Legend,
} from "recharts";
import KPICard from "../components/KPICard";
import RiskBadge from "../components/RiskBadge";
import { formatINR, formatINRShort, fromNow } from "../lib/format";
import { http } from "../lib/api";

const RISK_COLOR = {
  low: "#34D399", moderate: "#FBBF24", high: "#FB923C",
  critical: "#F87171", suspected_fraud: "#F43F5E", unknown: "#64748B",
};

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await http.get("/dashboard/summary");
        setData(data);
      } catch (_) {}
      setLoading(false);
    })();
  }, []);

  if (loading || !data) {
    return <div className="text-muted-foreground">Loading command center…</div>;
  }

  const k = data.kpis;
  const riskPie = (data.risk_by_category || []).map((r) => ({
    name: r._id || "unknown", value: r.count, amount: r.total,
  }));
  const statusBar = (data.payment_by_status || []).map((r) => ({
    status: r._id || "n/a", amount: r.total, count: r.count,
  }));
  const vendorExp = (data.top_vendors_exposure || []).map((r) => ({
    vendor: (r._id || "").slice(0, 24), amount: r.total,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            Command Center
          </h1>
          <p className="text-sm text-muted-foreground">
            Verify identity. Validate evidence. Protect every payment.
          </p>
        </div>
        <Link
          to="/verify"
          data-testid="cta-verify-payment"
          className="pill-btn inline-flex w-max items-center gap-2 bg-blue-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-400"
        >
          Verify a new payment
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {/* Today's Critical Decisions */}
      {data.critical_decisions?.length > 0 && (
        <section className="card-elev overflow-hidden">
          <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            <h2 className="font-display text-sm font-semibold uppercase tracking-widest">
              Today's Critical Decisions
            </h2>
            <span className="ml-auto text-xs text-muted-foreground">
              {data.critical_decisions.length} needing action
            </span>
          </div>
          <div className="grid grid-cols-1 gap-4 p-5 md:grid-cols-2 xl:grid-cols-3">
            {data.critical_decisions.map((p) => (
              <div
                key={p.id}
                data-testid={`critical-card-${p.id}`}
                className="hoverable rounded-lg border border-rose-500/20 bg-rose-500/5 p-4"
              >
                <div className="flex items-center justify-between">
                  <RiskBadge category={p.risk?.category} score={p.risk?.score} />
                  <span className="text-[11px] text-muted-foreground">{fromNow(p.requested_at)}</span>
                </div>
                <div className="mt-3 font-display text-2xl font-semibold">
                  {formatINR(p.amount)}
                </div>
                <div className="mt-1 text-sm">{p.vendor_name}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {p.invoice_number} · {p.mode}
                </div>
                <div className="mt-3 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-xs text-muted-foreground">
                  Recommended: <span className="text-foreground">{p.risk?.recommended_action}</span>
                </div>
                <Link
                  to={`/verify/${p.id}`}
                  data-testid={`review-${p.id}`}
                  className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300"
                >
                  Review evidence <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* KPI Row */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <KPICard testId="kpi-pending" label="Awaiting approval" value={k.payments_pending} />
        <KPICard testId="kpi-held"    label="Payments held"    value={k.payments_held} tone="warn" />
        <KPICard testId="kpi-highrisk" label="High-risk amount" value={k.high_risk_amount} isCurrency tone="bad" />
        <KPICard testId="kpi-prevented" label="Loss prevented" value={k.potential_loss_prevented} isCurrency tone="good" />
        <KPICard testId="kpi-ben"     label="New beneficiaries" value={k.new_beneficiary_requests} />
        <KPICard testId="kpi-dup"     label="Duplicate invoices" value={k.duplicate_invoice_alerts} tone="warn" />
        <KPICard testId="kpi-accch"   label="Account changes"   value={k.account_change_requests} />
        <KPICard testId="kpi-commalert" label="Comm. alerts"    value={k.communication_alerts} />
        <KPICard testId="kpi-avgtime" label="Avg verify time"   value={`${k.avg_verification_hours}h`} />
        <KPICard testId="kpi-sla"     label="SLA breaches"      value={k.sla_breaches} tone="bad" />
      </section>

      {/* Charts */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="card-elev p-5 xl:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold uppercase tracking-widest">
              Payment risk trend · last 7 days
            </h3>
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> live
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data.risk_trend}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="day" stroke="#9CA3AF" fontSize={11} />
              <YAxis stroke="#9CA3AF" fontSize={11}
                     tickFormatter={(v) => formatINRShort(v)} width={70} />
              <Tooltip contentStyle={{ background: "#0F1424", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                       formatter={(v) => formatINR(v)} />
              <Legend />
              <Line type="monotone" dataKey="critical" stroke={RISK_COLOR.critical} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="high"     stroke={RISK_COLOR.high}     strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="moderate" stroke={RISK_COLOR.moderate} strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="low"      stroke={RISK_COLOR.low}      strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card-elev p-5">
          <h3 className="mb-3 font-display text-sm font-semibold uppercase tracking-widest">
            Risk mix
          </h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={riskPie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                {riskPie.map((e, i) => (
                  <Cell key={i} fill={RISK_COLOR[e.name] || "#64748B"} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#0F1424", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1 text-xs">
            {riskPie.map((e) => (
              <div key={e.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: RISK_COLOR[e.name] || "#64748B" }} />
                  <span className="capitalize">{(e.name || "").replace("_", " ")}</span>
                </div>
                <span className="font-mono">{e.value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card-elev p-5 xl:col-span-2">
          <h3 className="mb-3 font-display text-sm font-semibold uppercase tracking-widest">
            Fraud exposure by vendor
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={vendorExp} layout="vertical" margin={{ left: 60 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" stroke="#9CA3AF" fontSize={11}
                     tickFormatter={(v) => formatINRShort(v)} />
              <YAxis type="category" dataKey="vendor" stroke="#9CA3AF" fontSize={11} width={160} />
              <Tooltip contentStyle={{ background: "#0F1424", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                       formatter={(v) => formatINR(v)} />
              <Bar dataKey="amount" fill="#3B82F6" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card-elev p-5">
          <h3 className="mb-3 font-display text-sm font-semibold uppercase tracking-widest">
            Payment value by status
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={statusBar}>
              <CartesianGrid stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="status" stroke="#9CA3AF" fontSize={11} />
              <YAxis stroke="#9CA3AF" fontSize={11}
                     tickFormatter={(v) => formatINRShort(v)} width={70} />
              <Tooltip contentStyle={{ background: "#0F1424", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                       formatter={(v) => formatINR(v)} />
              <Bar dataKey="amount" fill="#10B981" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}

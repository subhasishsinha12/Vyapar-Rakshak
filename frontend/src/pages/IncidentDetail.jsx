import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { http, API } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import { toast } from "sonner";
import {
  ArrowLeft, Snowflake, Ban, Landmark, Download, UserPlus, TrendingUp, CheckCircle2,
} from "lucide-react";

export default function IncidentDetail() {
  const { id } = useParams();
  const [inc, setInc] = useState(null);

  async function load() {
    const { data } = await http.get(`/incidents/${id}`);
    setInc(data);
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function act(action, extras = {}) {
    try {
      await http.post(`/incidents/${id}/action`, { action, ...extras });
      toast.success(`Action recorded: ${action}`);
      load();
    } catch (_) { toast.error("Failed"); }
  }

  async function downloadPack() {
    try {
      const { data } = await http.get(`/incidents/${id}/evidence-pack`);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `${inc.incident_no}-evidence-pack.json`; a.click();
      URL.revokeObjectURL(url);
    } catch (_) { toast.error("Download failed"); }
  }

  function bankIntimation() {
    if (!inc?.payment) return;
    const p = inc.payment;
    const text = `To: The Nodal Officer, Cyber Fraud Cell
From: Shree Textiles Pvt Ltd

Subject: Urgent request to freeze suspicious beneficiary account

Sir / Ma'am,

We wish to report a suspected fraud in respect of a proposed payment that our organisation has held internally on our fraud-prevention layer VyaparRakshak AI.

Details:
- Incident number     : ${inc.incident_no}
- Suspected type      : ${inc.suspected_type}
- Amount at risk      : ${formatINR(inc.amount_at_risk)}
- Beneficiary name    : ${p.beneficiary_name}
- Beneficiary account : ${p.account_number}
- IFSC                : ${p.ifsc}
- Payment mode        : ${p.mode}
- Invoice reference   : ${p.invoice_number}

The payment has been held internally and no funds have been released. Please advise appropriate action.

For and on behalf of Shree Textiles Pvt Ltd.
`;
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${inc.incident_no}-bank-intimation.txt`; a.click();
    URL.revokeObjectURL(url);
    act("notify_bank");
  }

  if (!inc) return <div className="text-muted-foreground">Loading incident…</div>;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/incidents" className="text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="inline h-4 w-4" /> Back
        </Link>
        <span className="font-mono text-xs text-muted-foreground">{inc.incident_no}</span>
      </div>

      <div className="card-elev p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-muted-foreground">{inc.status}</div>
            <h1 className="mt-1 font-display text-2xl font-semibold">{inc.suspected_type}</h1>
            <div className="mt-1 text-xs text-muted-foreground">Opened {fromNow(inc.created_at)}</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase text-muted-foreground">Amount at risk</div>
            <div className="font-display text-3xl font-semibold text-rose-300">{formatINR(inc.amount_at_risk)}</div>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <ActionBtn testId="inc-freeze" onClick={() => act("freeze")}><Snowflake className="mr-1 inline h-3.5 w-3.5" /> Freeze internal approval</ActionBtn>
          <ActionBtn testId="inc-block-benef" onClick={() => act("block_beneficiary")}><Ban className="mr-1 inline h-3.5 w-3.5" /> Block beneficiary internally</ActionBtn>
          <ActionBtn testId="inc-bank" onClick={bankIntimation}><Landmark className="mr-1 inline h-3.5 w-3.5" /> Generate bank intimation</ActionBtn>
          <ActionBtn testId="inc-download" onClick={downloadPack}><Download className="mr-1 inline h-3.5 w-3.5" /> Evidence pack</ActionBtn>
          <ActionBtn testId="inc-assign" onClick={() => { const a = prompt("Assignee name?"); if (a) act("assign", { assignee: a }); }}>
            <UserPlus className="mr-1 inline h-3.5 w-3.5" /> Assign investigator
          </ActionBtn>
          <ActionBtn testId="inc-escalate" onClick={() => act("escalate")}><TrendingUp className="mr-1 inline h-3.5 w-3.5" /> Escalate</ActionBtn>
          <ActionBtn testId="inc-close" tone="good"
            onClick={() => { const r = prompt("Closure reason?"); if (r) act("close", { reason: r }); }}>
            <CheckCircle2 className="mr-1 inline h-3.5 w-3.5" /> Close incident
          </ActionBtn>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="card-elev p-5 lg:col-span-2">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Timeline</h3>
          <ol className="mt-3 space-y-3">
            {(inc.timeline || []).map((t, i) => (
              <li key={i} className="relative pl-5 text-sm">
                <span className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-blue-500" />
                <div>{t.event}</div>
                <div className="text-xs text-muted-foreground">{fromNow(t.at)}</div>
              </li>
            ))}
          </ol>
        </div>
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">People</h3>
          <div className="mt-3 space-y-2">
            {(inc.people || []).map((p, i) => (
              <div key={i} className="rounded-md border border-white/10 bg-white/5 p-2 text-xs">
                <div className="font-medium">{p.name}</div>
                <div className="text-muted-foreground">{p.role}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <Kv label="Bank notified" value={inc.bank_notification_status} />
            <Kv label="Recovery" value={inc.recovery_status} />
            <Kv label="Escalation" value={inc.internal_escalation_status} />
            <Kv label="Assignee" value={inc.assignee || "—"} />
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionBtn({ children, tone = "default", onClick, testId }) {
  const cls = tone === "good"
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
    : "border-white/10 bg-white/5 hover:border-blue-500/40";
  return (
    <button onClick={onClick} data-testid={testId}
      className={`rounded-full border px-3 py-1.5 text-xs font-medium ${cls}`}>
      {children}
    </button>
  );
}
function Kv({ label, value }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-2">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm">{value}</div>
    </div>
  );
}

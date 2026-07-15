import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, fromNow, maskAccount } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { ArrowLeft, PhoneCall, Ban, Flag } from "lucide-react";

export default function PaymentDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [reason, setReason] = useState("");
  const [callback, setCallback] = useState({ called_number: "", spoke_with: "", result: "verified", notes: "" });
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const { data } = await http.get(`/payments/${id}`);
      setP(data);
    } catch (_) { toast.error("Failed to load payment"); }
    setLoading(false);
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  async function decide(action) {
    try {
      await http.post(`/payments/${id}/decision`, { decision: action, reason: reason || action });
      toast.success(`Recorded: ${action}`);
      setReason(""); load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
  }

  async function sendCallback() {
    try {
      await http.post(`/payments/${id}/callback`, callback);
      toast.success("Callback recorded");
      setCallback({ called_number: "", spoke_with: "", result: "verified", notes: "" });
      load();
    } catch (_) { toast.error("Failed"); }
  }

  async function openIncident() {
    try {
      const { data } = await http.post("/incidents", {
        payment_id: id, payment_reference: p.invoice_number,
        amount_at_risk: p.amount,
        suspected_type: "Suspected vendor bank-account fraud",
        description: "Opened from payment review",
      });
      toast.success(`Incident ${data.incident_no} opened`);
    } catch (_) { toast.error("Failed"); }
  }

  if (loading || !p) return <div className="text-muted-foreground">Loading…</div>;

  const flags = p.risk?.flags || [];
  const v = p.vendor;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/verify" className="text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="inline h-4 w-4" /> Back
        </Link>
        <span className="text-xs text-muted-foreground">Payment #{p.id.slice(0, 8)}</span>
        <span className="ml-auto"><RiskBadge category={p.risk?.category} score={p.risk?.score} /></span>
      </div>

      <div className="card-elev p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-muted-foreground">Amount</div>
            <div className="font-display text-4xl font-semibold" data-testid="payment-amount">
              {formatINR(p.amount)}
            </div>
            <div className="mt-1 text-sm">{p.vendor_name} · {p.invoice_number}</div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {p.mode} · {fromNow(p.requested_at)} · submitted by {p.submitted_by_name}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs md:grid-cols-4">
            <Stat label="Status" value={p.status} />
            <Stat label="Beneficiary" value={p.beneficiary_name} />
            <Stat label="Account" value={maskAccount(p.account_number)} />
            <Stat label="IFSC" value={p.ifsc || "—"} />
            <Stat label="PO" value={p.po_number || "—"} />
            <Stat label="GRN" value={p.grn_number || "—"} />
            <Stat label="Due" value={p.due_date ? p.due_date.slice(0, 10) : "—"} />
            <Stat label="Purpose" value={p.purpose || "—"} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="card-elev p-6 lg:col-span-2">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Red flags</h3>
          {flags.length ? (
            <ul className="mt-3 space-y-2">
              {flags.map((f, i) => (
                <li key={i} data-testid={`flag-${i}`} className="rounded-md border border-white/10 bg-white/5 p-3">
                  <div className="flex items-center gap-2">
                    <RiskBadge category={f.severity === "critical" ? "critical" : f.severity === "high" ? "high" : "moderate"} />
                    <span className="text-sm font-medium">{f.title}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{f.reason}</div>
                </li>
              ))}
            </ul>
          ) : <div className="mt-3 text-sm text-emerald-400">No red flags detected.</div>}
        </div>

        <div className="card-elev p-6">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Independent callback</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Never use contact details contained only in the new request. Use previously verified numbers only.
          </p>
          {v?.contacts?.length > 0 && (
            <div className="mt-2 rounded-md border border-white/10 bg-white/5 p-2 text-xs">
              Verified contact: <span className="text-foreground">{v.contacts[0].name} · {v.contacts[0].phone}</span>
            </div>
          )}
          <div className="mt-3 space-y-2">
            <input placeholder="Called number" value={callback.called_number}
                   data-testid="cb-number"
                   onChange={(e) => setCallback({ ...callback, called_number: e.target.value })}
                   className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
            <input placeholder="Spoke with" value={callback.spoke_with}
                   data-testid="cb-spoke"
                   onChange={(e) => setCallback({ ...callback, spoke_with: e.target.value })}
                   className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
            <select value={callback.result}
                    data-testid="cb-result"
                    onChange={(e) => setCallback({ ...callback, result: e.target.value })}
                    className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
              <option value="verified">Verified</option>
              <option value="suspicious">Suspicious</option>
              <option value="no_answer">No answer</option>
            </select>
            <textarea placeholder="Notes" rows={2} value={callback.notes}
                      data-testid="cb-notes"
                      onChange={(e) => setCallback({ ...callback, notes: e.target.value })}
                      className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
            <button onClick={sendCallback}
                    data-testid="cb-submit"
                    className="pill-btn w-full bg-blue-500 px-4 py-2 text-sm font-semibold text-white">
              <PhoneCall className="mr-1 inline h-3.5 w-3.5" /> Record callback
            </button>
          </div>
          {p.callbacks?.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs uppercase text-muted-foreground">History</div>
              {p.callbacks.map((c, i) => (
                <div key={i} className="rounded border border-white/5 bg-white/5 p-2 text-xs">
                  {c.result} · {c.spoke_with} · {c.called_number} · {fromNow(c.at)}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Decision panel */}
      <div className="card-elev p-6">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Decision</h3>
        <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                  placeholder="Reason for decision"
                  data-testid="decision-reason-detail"
                  className="mt-2 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
        <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          <BtnDetail testId="d-approve" tone="good" onClick={() => decide("approve")}>Approve</BtnDetail>
          <BtnDetail testId="d-clarify" onClick={() => decide("clarification")}>Clarification</BtnDetail>
          <BtnDetail testId="d-callback" onClick={() => decide("callback")}>Request callback</BtnDetail>
          <BtnDetail testId="d-escalate" onClick={() => decide("escalate")}>Escalate</BtnDetail>
          <BtnDetail testId="d-hold" tone="warn" onClick={() => decide("hold")}>Hold</BtnDetail>
          <BtnDetail testId="d-reject" tone="bad" onClick={() => decide("reject")}>Reject</BtnDetail>
          <BtnDetail testId="d-fraud" tone="bad" onClick={() => decide("fraud")}>
            <Flag className="mr-1 inline h-3.5 w-3.5" /> Report fraud
          </BtnDetail>
          <BtnDetail testId="d-open-incident" tone="bad" onClick={openIncident}>
            <Ban className="mr-1 inline h-3.5 w-3.5" /> Open incident
          </BtnDetail>
        </div>
      </div>

      {p.comms?.length > 0 && (
        <div className="card-elev p-6">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Related communications</h3>
          <div className="mt-3 space-y-3">
            {p.comms.map((c) => (
              <div key={c.id} className="rounded-md border border-white/10 bg-white/5 p-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-white/10 px-2 py-0.5 text-xs uppercase">{c.channel}</span>
                  <RiskBadge category={c.analysis?.category} score={c.analysis?.score} />
                </div>
                <div className="mt-2 whitespace-pre-wrap text-muted-foreground">{c.content}</div>
                {c.analysis?.signals?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {c.analysis.signals.map((s, i) => (
                      <span key={i} className="rounded-full bg-rose-500/10 px-2 py-0.5 text-xs text-rose-300">
                        {s.category}: {s.phrase}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit */}
      <div className="card-elev p-6">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Audit trail</h3>
        <div className="mt-3 space-y-1 text-xs">
          {(p.audit || []).map((a) => (
            <div key={a.id} className="rounded border border-white/5 bg-white/5 px-3 py-2">
              <span className="text-muted-foreground">{fromNow(a.timestamp)}</span> ·
              <span className="ml-1 font-medium">{a.user_name}</span>
              <span className="ml-1 text-muted-foreground">({a.user_role})</span> ·
              <span className="ml-1">{a.action}</span>
              {a.reason && <span className="ml-1 text-muted-foreground">— {a.reason}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-sm">{value || "—"}</div>
    </div>
  );
}
function BtnDetail({ children, tone = "default", onClick, testId }) {
  const cls = {
    default: "border-white/10 bg-white/5 hover:border-blue-500/40",
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:border-emerald-500/50",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-300 hover:border-amber-500/50",
    bad: "border-rose-500/30 bg-rose-500/10 text-rose-300 hover:border-rose-500/50",
  }[tone];
  return (
    <button onClick={onClick} data-testid={testId}
      className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${cls}`}>
      {children}
    </button>
  );
}

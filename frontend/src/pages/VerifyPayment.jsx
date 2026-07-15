import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { http } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { ArrowRight, Upload, X } from "lucide-react";

const STEPS = [
  "Payment info", "Evidence", "Automated checks", "Risk result", "Decision"
];

const CHECK_ITEMS = [
  "Document extraction",
  "Vendor identity match",
  "GST verification",
  "Bank-account comparison",
  "Duplicate invoice detection",
  "PO – GRN – invoice matching",
  "Communication-risk analysis",
  "Transaction anomaly analysis",
  "Deepfake / impersonation screening",
  "Approval-authority check",
];

export default function VerifyPayment() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [vendors, setVendors] = useState([]);
  const [heldList, setHeldList] = useState([]);
  const [form, setForm] = useState({
    vendor_id: "", vendor_name: "", invoice_number: "", invoice_date: "",
    amount: "", mode: "NEFT", beneficiary_name: "",
    account_number: "", ifsc: "", upi_id: "",
    po_number: "", grn_number: "", due_date: "", purpose: "", notes: "",
  });
  const [evidence, setEvidence] = useState([]);
  const [checkProgress, setCheckProgress] = useState({});
  const [risk, setRisk] = useState(null);
  const [creating, setCreating] = useState(false);
  const [createdId, setCreatedId] = useState(null);
  const [decisionReason, setDecisionReason] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [v, held] = await Promise.all([
          http.get("/vendors"),
          http.get("/approvals/queue"),
        ]);
        setVendors(v.data);
        setHeldList(held.data.filter((p) => ["critical","suspected_fraud","high"].includes(p.risk?.category)).slice(0, 5));
      } catch (_) {}
    })();
  }, []);

  function set(k, v) { setForm((f) => ({ ...f, [k]: v })); }

  function onVendorSelect(id) {
    const v = vendors.find((x) => x.id === id);
    if (v) {
      set("vendor_id", v.id);
      set("vendor_name", v.name);
      set("beneficiary_name", v.name);
      const a = (v.approved_bank_accounts || [])[0];
      if (a) { set("account_number", a.account_number); set("ifsc", a.ifsc); }
    }
  }

  function addEvidence(kind, file) {
    setEvidence((e) => [...e, { kind, filename: file.name, size: file.size }]);
    toast.success(`${kind} attached: ${file.name}`);
  }

  async function runChecks() {
    setStep(3); setCheckProgress({});
    for (let i = 0; i < CHECK_ITEMS.length; i++) {
      await new Promise((r) => setTimeout(r, 250));
      setCheckProgress((p) => ({ ...p, [CHECK_ITEMS[i]]: "done" }));
    }
    await submit();
  }

  async function submit() {
    setCreating(true);
    try {
      const { data } = await http.post("/payments", {
        ...form,
        amount: Number(form.amount || 0),
        evidence,
      });
      setCreatedId(data.id);
      setRisk(data.risk);
      setStep(4);
    } catch (e) {
      toast.error("Failed to submit for verification");
    } finally { setCreating(false); }
  }

  async function decide(action, reason) {
    if (!createdId) return;
    try {
      await http.post(`/payments/${createdId}/decision`,
        { decision: action, reason: reason || decisionReason || action, digital_confirmation: true });
      toast.success(`Decision recorded: ${action}`);
      nav(`/verify/${createdId}`);
    } catch (e) {
      const msg = e.response?.data?.detail || "Failed";
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Verify Payment</h1>
          <p className="text-sm text-muted-foreground">
            5-step verification workflow · required before releasing funds.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">
          Step {step} of {STEPS.length}: <span className="text-foreground">{STEPS[step - 1]}</span>
        </div>
      </div>

      {/* Stepper */}
      <div className="card-elev p-4">
        <div className="flex items-center gap-2">
          {STEPS.map((s, i) => {
            const n = i + 1;
            const active = n === step;
            const done = n < step;
            return (
              <React.Fragment key={s}>
                <div
                  data-testid={`step-${n}`}
                  className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${active ? "border-blue-500/60 bg-blue-500/10 text-blue-300" : done ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-white/10 text-muted-foreground"}`}
                >
                  <span className={`grid h-5 w-5 place-items-center rounded-full text-[10px] font-bold ${active ? "bg-blue-500 text-white" : done ? "bg-emerald-500 text-white" : "bg-white/10"}`}>
                    {n}
                  </span>
                  <span>{s}</span>
                </div>
                {i < STEPS.length - 1 && <span className="h-px flex-1 bg-white/10" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {step === 1 && (
        <div className="card-elev p-6">
          <h2 className="font-display text-lg font-semibold">Payment information</h2>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Vendor">
              <select
                data-testid="vendor-select"
                className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
                value={form.vendor_id}
                onChange={(e) => onVendorSelect(e.target.value)}
              >
                <option value="">Select vendor…</option>
                {vendors.map((v) => (
                  <option key={v.id} value={v.id}>{v.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Invoice number">
              <Input testId="invoice-number" value={form.invoice_number} onChange={(v) => set("invoice_number", v)} />
            </Field>
            <Field label="Invoice date">
              <Input testId="invoice-date" type="date" value={form.invoice_date} onChange={(v) => set("invoice_date", v)} />
            </Field>
            <Field label="Payment amount (₹)">
              <Input testId="amount" type="number" value={form.amount} onChange={(v) => set("amount", v)} />
            </Field>
            <Field label="Payment mode">
              <select
                data-testid="mode-select"
                value={form.mode} onChange={(e) => set("mode", e.target.value)}
                className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
              >
                {["NEFT", "RTGS", "IMPS", "UPI"].map((m) => <option key={m}>{m}</option>)}
              </select>
            </Field>
            <Field label="Beneficiary name">
              <Input testId="beneficiary" value={form.beneficiary_name} onChange={(v) => set("beneficiary_name", v)} />
            </Field>
            <Field label="Account number">
              <Input testId="account" value={form.account_number} onChange={(v) => set("account_number", v)} />
            </Field>
            <Field label="IFSC">
              <Input testId="ifsc" value={form.ifsc} onChange={(v) => set("ifsc", v)} />
            </Field>
            <Field label="UPI ID (optional)">
              <Input testId="upi" value={form.upi_id} onChange={(v) => set("upi_id", v)} />
            </Field>
            <Field label="PO number">
              <Input testId="po" value={form.po_number} onChange={(v) => set("po_number", v)} />
            </Field>
            <Field label="GRN number">
              <Input testId="grn" value={form.grn_number} onChange={(v) => set("grn_number", v)} />
            </Field>
            <Field label="Due date">
              <Input testId="due-date" type="date" value={form.due_date} onChange={(v) => set("due_date", v)} />
            </Field>
            <Field label="Payment purpose" full>
              <Input testId="purpose" value={form.purpose} onChange={(v) => set("purpose", v)} />
            </Field>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              data-testid="step-1-next"
              onClick={() => setStep(2)}
              disabled={!form.vendor_name || !form.invoice_number || !form.amount}
              className="pill-btn bg-blue-500 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Next: Evidence
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card-elev p-6">
          <h2 className="font-display text-lg font-semibold">Evidence upload</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Attach the documents you received. Files are held locally in the prototype.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[
              "Invoice PDF or image", "Purchase order", "Goods receipt",
              "Delivery challan", "Email screenshot", "WhatsApp screenshot",
              "Voice note", "Bank-account-change letter", "Cancelled cheque"
            ].map((kind) => (
              <label
                key={kind}
                className="hoverable flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-white/15 bg-white/5 p-4 text-center text-xs"
                data-testid={`evidence-${kind.toLowerCase().replace(/[^a-z]+/g, "-")}`}
              >
                <Upload className="mb-1.5 h-4 w-4 text-muted-foreground" />
                <span className="text-foreground">{kind}</span>
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && addEvidence(kind, e.target.files[0])}
                />
              </label>
            ))}
          </div>
          {evidence.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {evidence.map((e, i) => (
                <span key={i} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs">
                  {e.kind} · {e.filename}
                </span>
              ))}
            </div>
          )}
          <div className="mt-6 flex justify-between">
            <button onClick={() => setStep(1)} className="text-sm text-muted-foreground hover:text-foreground">
              ← Back
            </button>
            <button
              data-testid="step-2-next"
              onClick={runChecks}
              className="pill-btn bg-blue-500 px-5 py-2 text-sm font-semibold text-white"
            >
              Run automated checks
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="card-elev p-6">
          <h2 className="font-display text-lg font-semibold">Automated checks in progress</h2>
          <div className="mt-4 space-y-2">
            {CHECK_ITEMS.map((c) => {
              const done = checkProgress[c] === "done";
              return (
                <div key={c} className="flex items-center gap-3 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
                  <span className={`h-2 w-2 rounded-full ${done ? "bg-emerald-400" : "animate-pulse bg-blue-400"}`} />
                  <span>{c}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {done ? "Simulated · complete" : "Running…"}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            External checks (GST portal, bank verification) are simulated in this prototype.
          </p>
        </div>
      )}

      {step === 4 && risk && (
        <div className="space-y-4">
          <div className="card-elev p-6">
            <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
              <div>
                <div className="text-xs uppercase tracking-widest text-muted-foreground">Overall risk score</div>
                <div className="mt-2 flex items-end gap-3">
                  <div className="font-display text-5xl font-semibold">{risk.score}<span className="text-muted-foreground">/100</span></div>
                  <RiskBadge category={risk.category} />
                </div>
                <div className="mt-2 max-w-xl text-sm text-muted-foreground">
                  Recommended action: <span className="text-foreground">{risk.recommended_action}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-3">
                <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                  Required approvers <div className="font-display text-xl">{risk.required_approvers}</div>
                </div>
                <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                  Callback needed <div className="font-display text-xl">{risk.requires_callback ? "Yes" : "No"}</div>
                </div>
                <div className="rounded-md border border-white/10 bg-white/5 px-3 py-2">
                  Cooling period <div className="font-display text-xl">{risk.cooling_period_hours}h</div>
                </div>
              </div>
            </div>
          </div>

          <div className="card-elev p-6">
            <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Red flags & explainability</h3>
            {risk.flags?.length ? (
              <ul className="mt-3 space-y-2">
                {risk.flags.map((f, i) => (
                  <li key={i} className="rounded-md border border-white/10 bg-white/5 p-3">
                    <div className="flex items-center gap-2">
                      <RiskBadge category={f.severity === "critical" ? "critical" : f.severity === "high" ? "high" : "moderate"} />
                      <span className="text-sm font-medium">{f.title}</span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">{f.reason}</div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-2 text-sm text-emerald-400">No significant red flags detected.</div>
            )}
          </div>

          <div className="card-elev p-6">
            <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Component contribution</h3>
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(risk.components).map(([k, v]) => (
                <div key={k} className="rounded-md border border-white/10 bg-white/5 p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="capitalize text-muted-foreground">{k.replaceAll("_", " ")}</span>
                    <span className="font-mono">+{v}</span>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full bg-blue-500" style={{ width: `${Math.min(100, v)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              data-testid="step-4-next"
              onClick={() => setStep(5)}
              className="pill-btn bg-blue-500 px-5 py-2 text-sm font-semibold text-white"
            >
              Continue to decision <ArrowRight className="ml-1 inline h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {step === 5 && (
        <div className="card-elev p-6">
          <h2 className="font-display text-lg font-semibold">Decision</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter a reason. Every decision is recorded in the audit trail with your digital confirmation.
          </p>
          <textarea
            data-testid="decision-reason"
            className="mt-3 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm"
            rows={3}
            placeholder="Provide a reason for your decision…"
            value={decisionReason}
            onChange={(e) => setDecisionReason(e.target.value)}
          />
          <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
            <DecisionBtn testId="decide-approve" label="Approve" tone="good" onClick={() => decide("approve")} />
            <DecisionBtn testId="decide-clarify" label="Send for clarification" onClick={() => decide("clarification")} />
            <DecisionBtn testId="decide-callback" label="Request callback" onClick={() => decide("callback")} />
            <DecisionBtn testId="decide-escalate" label="Escalate" onClick={() => decide("escalate")} />
            <DecisionBtn testId="decide-hold" label="Hold payment" tone="warn" onClick={() => decide("hold")} />
            <DecisionBtn testId="decide-reject" label="Reject" tone="bad" onClick={() => decide("reject")} />
            <DecisionBtn testId="decide-fraud" label="Report suspected fraud" tone="bad" onClick={() => decide("fraud")} />
          </div>
        </div>
      )}

      {heldList.length > 0 && step === 1 && (
        <div className="card-elev p-6">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">
            Ongoing high-risk payments
          </h3>
          <div className="mt-3 divide-y divide-white/5">
            {heldList.map((p) => (
              <Link
                key={p.id}
                to={`/verify/${p.id}`}
                className="flex items-center justify-between py-2 text-sm hover:text-blue-400"
                data-testid={`held-item-${p.id}`}
              >
                <div>
                  <div className="font-medium">{formatINR(p.amount)} · {p.vendor_name}</div>
                  <div className="text-xs text-muted-foreground">{p.invoice_number} · {fromNow(p.requested_at)}</div>
                </div>
                <RiskBadge category={p.risk?.category} score={p.risk?.score} />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children, full }) {
  return (
    <div className={full ? "md:col-span-2" : ""}>
      <label className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{label}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}

function Input({ value, onChange, type = "text", testId }) {
  return (
    <input
      type={type} value={value || ""} onChange={(e) => onChange(e.target.value)}
      data-testid={testId}
      className="w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-blue-500/50"
    />
  );
}

function DecisionBtn({ label, tone = "default", onClick, testId }) {
  const cls = {
    default: "border-white/10 bg-white/5 hover:border-blue-500/40",
    good: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:border-emerald-500/50",
    warn: "border-amber-500/30 bg-amber-500/10 text-amber-300 hover:border-amber-500/50",
    bad: "border-rose-500/30 bg-rose-500/10 text-rose-300 hover:border-rose-500/50",
  }[tone];
  return (
    <button data-testid={testId} onClick={onClick}
      className={`rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors ${cls}`}>
      {label}
    </button>
  );
}

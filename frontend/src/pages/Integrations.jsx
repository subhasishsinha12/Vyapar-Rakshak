import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { toast } from "sonner";
import { Plug, TestTube2, CheckCircle2, Circle } from "lucide-react";

const GST_PROVIDERS = ["mock", "karza", "cleartax"];
const BANK_PROVIDERS = ["mock", "razorpay", "cashfree"];
const DEEPFAKE_PROVIDERS = ["mock", "reality_defender", "pindrop"];

export default function Integrations() {
  const [snap, setSnap] = useState(null);
  const [config, setConfig] = useState({
    gst: { provider: "mock", api_key: "" },
    bank: { provider: "mock", key_id: "", key_secret: "", client_id: "", client_secret: "" },
    deepfake: { provider: "mock", api_key: "" },
  });
  const [busy, setBusy] = useState(false);
  const [tests, setTests] = useState({});

  async function load() {
    try {
      const { data } = await http.get("/settings/integrations");
      setSnap(data.snapshot);
      // hydrate provider selections from config (secrets stay masked)
      setConfig((c) => ({
        gst: { provider: data.config?.gst?.provider || "mock", api_key: "" },
        bank: {
          provider: data.config?.bank?.provider || "mock",
          key_id: "", key_secret: "", client_id: "", client_secret: "",
        },
        deepfake: { provider: data.config?.deepfake?.provider || "mock", api_key: "" },
      }));
    } catch (e) {
      toast.error(e.response?.data?.detail || "Only admin / owner can view integrations");
    }
  }
  useEffect(() => { load(); }, []);

  async function save() {
    setBusy(true);
    try {
      const payload = {
        gst: cleanBlanks(config.gst),
        bank: cleanBlanks(config.bank),
        deepfake: cleanBlanks(config.deepfake),
      };
      const { data } = await http.put("/settings/integrations", payload);
      setSnap(data.snapshot);
      toast.success("Integrations updated");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed");
    }
    setBusy(false);
  }

  async function runTest(kind) {
    setTests((t) => ({ ...t, [kind]: { loading: true } }));
    try {
      const { data } = await http.post(`/settings/integrations/test/${kind}`);
      setTests((t) => ({ ...t, [kind]: { result: data } }));
    } catch (e) {
      setTests((t) => ({ ...t, [kind]: { error: e.response?.data?.detail || "Failed" } }));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Integrations</h1>
        <p className="text-sm text-muted-foreground">
          Replaceable adapters for GST, bank verification and deepfake screening. Live keys are masked once saved.
        </p>
      </div>

      {snap && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <StatusChip name="GST" info={snap.gst} testId="chip-gst" />
          <StatusChip name="Bank verify" info={snap.bank} testId="chip-bank" />
          <StatusChip name="Deepfake" info={snap.deepfake} testId="chip-deepfake" />
        </div>
      )}

      {/* GST */}
      <Section title="GST verification" subtitle="Verify GSTIN legal name, filing status and registration"
               kind="gst" onTest={runTest} test={tests.gst}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ProviderSelect testId="gst-provider" options={GST_PROVIDERS}
                          value={config.gst.provider}
                          onChange={(v) => setConfig({ ...config, gst: { ...config.gst, provider: v }})} />
          {config.gst.provider !== "mock" && (
            <SecretInput label="API key" testId="gst-key"
                         value={config.gst.api_key}
                         onChange={(v) => setConfig({ ...config, gst: { ...config.gst, api_key: v }})} />
          )}
        </div>
      </Section>

      {/* Bank */}
      <Section title="Bank account verification" subtitle="Penny-drop / name-match on beneficiary accounts"
               kind="bank" onTest={runTest} test={tests.bank}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ProviderSelect testId="bank-provider" options={BANK_PROVIDERS}
                          value={config.bank.provider}
                          onChange={(v) => setConfig({ ...config, bank: { ...config.bank, provider: v }})} />
          {config.bank.provider === "razorpay" && (
            <>
              <SecretInput label="Razorpay key id" testId="bank-key-id"
                           value={config.bank.key_id}
                           onChange={(v) => setConfig({ ...config, bank: { ...config.bank, key_id: v }})} />
              <SecretInput label="Razorpay key secret" testId="bank-key-secret"
                           value={config.bank.key_secret}
                           onChange={(v) => setConfig({ ...config, bank: { ...config.bank, key_secret: v }})} />
            </>
          )}
          {config.bank.provider === "cashfree" && (
            <>
              <SecretInput label="Cashfree client id" testId="bank-client-id"
                           value={config.bank.client_id}
                           onChange={(v) => setConfig({ ...config, bank: { ...config.bank, client_id: v }})} />
              <SecretInput label="Cashfree client secret" testId="bank-client-secret"
                           value={config.bank.client_secret}
                           onChange={(v) => setConfig({ ...config, bank: { ...config.bank, client_secret: v }})} />
            </>
          )}
        </div>
      </Section>

      {/* Deepfake */}
      <Section title="Deepfake / synthetic-media screening" subtitle="Advisory signals only — never conclusive"
               kind="deepfake" onTest={runTest} test={tests.deepfake}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <ProviderSelect testId="df-provider" options={DEEPFAKE_PROVIDERS}
                          value={config.deepfake.provider}
                          onChange={(v) => setConfig({ ...config, deepfake: { ...config.deepfake, provider: v }})} />
          {config.deepfake.provider !== "mock" && (
            <SecretInput label="API key" testId="df-key"
                         value={config.deepfake.api_key}
                         onChange={(v) => setConfig({ ...config, deepfake: { ...config.deepfake, api_key: v }})} />
          )}
        </div>
      </Section>

      <div className="flex justify-end">
        <button onClick={save} disabled={busy} data-testid="save-integrations"
                className="pill-btn bg-blue-500 px-6 py-2.5 text-sm font-semibold text-white disabled:opacity-60">
          {busy ? "Saving…" : "Save integrations"}
        </button>
      </div>
    </div>
  );
}

function cleanBlanks(obj) {
  const out = { ...obj };
  Object.keys(out).forEach((k) => { if (out[k] === "") out[k] = null; });
  return out;
}

function StatusChip({ name, info, testId }) {
  return (
    <div className="card-elev p-4" data-testid={testId}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted-foreground">
        <Plug className="h-3.5 w-3.5" /> {name}
      </div>
      <div className="mt-2 flex items-center gap-2">
        {info.live ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Circle className="h-4 w-4 text-amber-400" />}
        <span className="font-display text-lg capitalize">{info.provider.replaceAll("_", " ")}</span>
      </div>
      <div className="mt-1 text-[10px] uppercase text-muted-foreground">
        {info.live ? "Live provider" : "Mock (simulated)"}
      </div>
    </div>
  );
}

function Section({ title, subtitle, children, kind, onTest, test }) {
  return (
    <div className="card-elev p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold">{title}</h3>
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <button onClick={() => onTest(kind)} data-testid={`test-${kind}`}
                className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs hover:border-blue-500/40">
          <TestTube2 className="mr-1 inline h-3.5 w-3.5" /> Run test call
        </button>
      </div>
      <div className="mt-4">{children}</div>
      {test?.result && (
        <pre className="mt-3 max-h-64 overflow-auto rounded-md border border-white/10 bg-black/30 p-3 text-[11px]">
          {JSON.stringify(test.result, null, 2)}
        </pre>
      )}
      {test?.error && (
        <div className="mt-3 rounded-md border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300">
          {test.error}
        </div>
      )}
    </div>
  );
}

function ProviderSelect({ options, value, onChange, testId }) {
  return (
    <div>
      <label className="text-xs uppercase text-muted-foreground">Provider</label>
      <select data-testid={testId} value={value} onChange={(e) => onChange(e.target.value)}
              className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
        {options.map((o) => <option key={o} value={o}>{o.replaceAll("_", " ")}</option>)}
      </select>
    </div>
  );
}
function SecretInput({ label, value, onChange, testId }) {
  return (
    <div>
      <label className="text-xs uppercase text-muted-foreground">{label}</label>
      <input type="password" value={value} onChange={(e) => onChange(e.target.value)}
             data-testid={testId} placeholder="•••••••••• (leave blank to keep existing)"
             className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
    </div>
  );
}

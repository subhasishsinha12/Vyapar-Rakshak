import React, { useState } from "react";
import { http } from "../lib/api";
import RiskBadge from "../components/RiskBadge";
import { toast } from "sonner";
import { Sparkles } from "lucide-react";

const EXAMPLES = [
  {
    label: "CEO impersonation",
    text: `Anita, this is Rajiv (CEO). Please transfer ₹90,000 immediately to the personal account below. It is urgent and confidential. Do not call me, I am in a board meeting. — Rajiv`,
  },
  {
    label: "Fake bank change (lookalike)",
    text: `URGENT: Please transfer ₹18,75,000 to our new HDFC account today itself. Bank changed due to audit. Please DO NOT CALL, I am in a meeting. — Nikhil (from kirloskarmt.c0.in)`,
  },
  {
    label: "Normal invoice reminder",
    text: `Dear Sir, gentle reminder to release payment against our invoice TPM/25-26/1122 by end of this week. Regards, Arjun`,
  },
];

export default function CommDetector() {
  const [text, setText] = useState(EXAMPLES[1].text);
  const [channel, setChannel] = useState("whatsapp");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function analyze() {
    setBusy(true);
    try {
      const { data } = await http.post("/comms/analyze", { content: text, channel });
      setResult(data);
    } catch (_) { toast.error("Analysis failed"); }
    setBusy(false);
  }

  function highlight(t, signals) {
    if (!signals?.length) return t;
    let out = t;
    signals.forEach((s) => {
      if (!s.phrase) return;
      const re = new RegExp(`(${s.phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "ig");
      out = out.replace(re, `\u0000${s.phrase}\u0000`);
    });
    return out.split("\u0000").map((chunk, i) =>
      i % 2 === 1 ? (
        <mark key={i} className="rounded-sm bg-rose-500/25 px-1 text-rose-100">{chunk}</mark>
      ) : (<span key={i}>{chunk}</span>)
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Communication Fraud Detector</h1>
        <p className="text-sm text-muted-foreground">
          Paste an email, WhatsApp or SMS. GPT-5.2 + rule engine explain every red flag.
        </p>
      </div>

      <div className="card-elev p-5">
        <div className="flex flex-wrap items-center gap-2">
          <select value={channel} onChange={(e) => setChannel(e.target.value)}
                  data-testid="comm-channel"
                  className="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm">
            <option value="email">Email</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="sms">SMS</option>
          </select>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((e) => (
              <button key={e.label} data-testid={`example-${e.label}`}
                      onClick={() => setText(e.text)}
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs hover:border-blue-500/40">
                {e.label}
              </button>
            ))}
          </div>
        </div>
        <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)}
                  data-testid="comm-input"
                  className="mt-3 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm" />
        <div className="mt-3 flex justify-end">
          <button onClick={analyze} disabled={busy}
                  data-testid="comm-analyze"
                  className="pill-btn bg-blue-500 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60">
            <Sparkles className="mr-1 inline h-4 w-4" /> {busy ? "Analysing…" : "Analyse with GPT-5.2"}
          </button>
        </div>
      </div>

      {result && (
        <div className="card-elev p-5">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Result</h3>
            <RiskBadge category={result.analysis.category} score={result.analysis.score} />
          </div>
          {result.analysis.summary && (
            <div className="mt-2 rounded-md border border-white/10 bg-white/5 p-3 text-sm text-muted-foreground">
              {result.analysis.summary}
            </div>
          )}
          <div className="mt-3 whitespace-pre-wrap rounded-md border border-white/10 bg-black/30 p-3 text-sm leading-relaxed">
            {highlight(result.content, result.analysis.signals)}
          </div>
          {result.analysis.signals?.length > 0 && (
            <div className="mt-3">
              <div className="text-xs uppercase text-muted-foreground">Signals</div>
              <ul className="mt-2 space-y-2">
                {result.analysis.signals.map((s, i) => (
                  <li key={i} className="rounded-md border border-white/10 bg-white/5 p-2 text-sm">
                    <div className="flex items-center gap-2">
                      <RiskBadge category={s.severity === "critical" ? "critical" : s.severity === "high" ? "high" : "moderate"} />
                      <span className="font-medium">{s.category}</span>
                      <span className="text-muted-foreground">— "{s.phrase}"</span>
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">{s.reason}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!result.analysis.ai_available && (
            <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              AI narrative unavailable — showing deterministic rule-engine signals only.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

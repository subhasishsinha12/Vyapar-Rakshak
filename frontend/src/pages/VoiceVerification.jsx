import React, { useEffect, useState } from "react";
import { http } from "../lib/api";
import { fromNow } from "../lib/format";
import { toast } from "sonner";
import { Mic2, Upload } from "lucide-react";

export default function VoiceVerification() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [rows, setRows] = useState([]);

  async function load() {
    try {
      const { data } = await http.get("/voice");
      setRows(data);
    } catch (_) {}
  }
  useEffect(() => { load(); }, []);

  async function onFile(f) {
    if (!f) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const { data } = await http.post("/voice/analyze", fd, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setResult(data);
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Analysis failed");
    }
    setBusy(false);
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Voice / video verification</h1>
        <p className="text-sm text-muted-foreground">
          Advisory deepfake screening. This is a prototype signal — always confirm with an independent callback.
        </p>
      </div>

      <div className="card-elev grain relative flex flex-col items-center gap-2 border-2 border-dashed border-white/15 p-8 text-center">
        <Mic2 className="h-6 w-6 text-blue-400" />
        <div className="text-sm">Upload a voice note or video instruction</div>
        <label className="pill-btn inline-flex cursor-pointer items-center bg-blue-500 px-5 py-2 text-sm font-semibold text-white">
          <Upload className="mr-1 h-4 w-4" /> Choose media
          <input type="file" accept="audio/*,video/*" className="hidden"
                 data-testid="voice-file"
                 onChange={(e) => onFile(e.target.files?.[0])} />
        </label>
        {busy && <div className="text-xs text-muted-foreground">Running advisory screening…</div>}
      </div>

      {result && (
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Advisory result</h3>
          <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kv label="Synthetic media" value={`${result.synthetic_media_score}/100`} tone="warn" />
            <Kv label="Replay risk" value={`${result.replay_risk_score}/100`} />
            <Kv label="Speaker consistency" value={result.speaker_consistency} />
            <Kv label="Metadata" value={result.metadata_anomalies?.length ? "anomalies" : "ok"} />
            <Kv label="Challenge-response" value={result.challenge_response_status} />
            <Kv label="Independent verify" value={result.independent_verification_status} />
          </div>
          <div className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300">
            {result.advisory_note}
          </div>
        </div>
      )}

      <div className="card-elev p-5">
        <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Recent screenings</h3>
        <div className="mt-3 divide-y divide-white/5 text-sm">
          {rows.map((r) => (
            <div key={r.id} className="flex items-center justify-between py-2">
              <div>
                <div className="font-medium">{r.filename}</div>
                <div className="text-xs text-muted-foreground">
                  Synth {r.synthetic_media_score} · Replay {r.replay_risk_score} · {fromNow(r.created_at)}
                </div>
              </div>
              <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">Advisory</span>
            </div>
          ))}
          {!rows.length && <div className="text-sm text-muted-foreground">No screenings yet.</div>}
        </div>
      </div>
    </div>
  );
}

function Kv({ label, value, tone }) {
  const cls = tone === "warn" ? "text-amber-300" : "";
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-3">
      <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
      <div className={`mt-0.5 text-sm ${cls}`}>{value}</div>
    </div>
  );
}

import React, { useState } from "react";
import { http, API } from "../lib/api";
import { formatINR, fromNow } from "../lib/format";
import { Download, FileBarChart, FileText } from "lucide-react";
import { toast } from "sonner";

const REPORTS = [
  { key: "daily-risk",        title: "Daily fraud-risk summary",         desc: "Last 24 hours of payment risk activity." },
  { key: "payments-held",     title: "Payments held & released",         desc: "Every payment currently held for review." },
  { key: "bank-changes",      title: "Vendor bank-account changes",      desc: "All beneficiary account-change requests." },
  { key: "duplicate-invoices", title: "Duplicate invoices",              desc: "Invoices flagged as duplicates." },
  { key: "high-risk-approvers", title: "High-risk approvers",            desc: "Users submitting the most high-risk payments." },
  { key: "loss-prevented",    title: "Potential loss prevented",         desc: "Sum of held / rejected / fraud amounts." },
  { key: "incident-ageing",   title: "Incident ageing",                  desc: "Age of open fraud incidents." },
  { key: "vendor-risk-movement", title: "Vendor risk movement",          desc: "Change in vendor trust scores over time." },
];

export default function Reports() {
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  async function open(key) {
    setActive(key); setLoading(true);
    try {
      const { data } = await http.get(`/reports/${key}`);
      setData(data);
    } catch (_) { toast.error("Failed to load report"); }
    setLoading(false);
  }

  function download() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `${active}.json`; a.click();
    URL.revokeObjectURL(a.href);
  }

  function csv() {
    if (!data?.items?.length) return;
    const rows = data.items;
    const keys = Object.keys(rows[0]).filter((k) => typeof rows[0][k] !== "object");
    const header = keys.join(",");
    const body = rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? "")).join(",")).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `${active}.csv`; a.click();
    URL.revokeObjectURL(a.href);
  }

  async function pdf() {
    if (!active) return;
    try {
      const res = await http.get(`/reports/${active}`, {
        params: { format: "pdf" }, responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${active}.pdf`; a.click();
      URL.revokeObjectURL(a.href);
    } catch (_) { toast.error("PDF download failed"); }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">
          Regulator-ready exports. Every report is downloadable as JSON or CSV.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {REPORTS.map((r) => (
          <button key={r.key} onClick={() => open(r.key)}
                  data-testid={`report-${r.key}`}
                  className={`card-elev hoverable p-4 text-left ${active === r.key ? "border-blue-500/40" : ""}`}>
            <FileBarChart className="h-4 w-4 text-blue-400" />
            <div className="mt-2 text-sm font-semibold">{r.title}</div>
            <div className="mt-0.5 text-xs text-muted-foreground">{r.desc}</div>
          </button>
        ))}
      </div>

      {active && (
        <div className="card-elev p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="font-display text-lg font-semibold">
              {REPORTS.find((x) => x.key === active).title}
            </div>
            <div className="flex gap-2">
              <button onClick={pdf} data-testid="dl-pdf"
                      className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-200 hover:border-rose-500/50">
                <FileText className="mr-1 inline h-3.5 w-3.5" /> PDF
              </button>
              <button onClick={download} data-testid="dl-json"
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs hover:border-blue-500/40">
                <Download className="mr-1 inline h-3.5 w-3.5" /> JSON
              </button>
              <button onClick={csv} data-testid="dl-csv"
                      className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs hover:border-blue-500/40">
                <Download className="mr-1 inline h-3.5 w-3.5" /> CSV
              </button>
            </div>
          </div>
          {loading && <div className="text-sm text-muted-foreground">Loading…</div>}
          {!loading && data && (
            <>
              {data.items && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="text-left text-muted-foreground">
                      <tr>
                        {Object.keys(data.items[0] || {}).filter((k) => typeof (data.items[0] || {})[k] !== "object")
                          .map((k) => <th key={k} className="py-2 pr-3">{k}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {data.items.map((row, i) => (
                        <tr key={i} className="border-t border-white/5">
                          {Object.keys(data.items[0]).filter((k) => typeof (data.items[0])[k] !== "object")
                            .map((k) => (
                              <td key={k} className="py-2 pr-3">
                                {typeof row[k] === "number" && k.includes("amount") ? formatINR(row[k]) : String(row[k] ?? "—")}
                              </td>
                            ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {!data.items && (
                <pre className="max-h-96 overflow-auto rounded-md border border-white/10 bg-black/40 p-3 text-xs">
                  {JSON.stringify(data, null, 2)}
                </pre>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

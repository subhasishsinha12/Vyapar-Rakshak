import React, { useEffect, useState } from "react";
import { useAuth } from "../lib/AuthContext";
import { http } from "../lib/api";

export default function Settings() {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [prefs, setPrefs] = useState({
    approval_threshold: 100000,
    cooling_period_hours: 12,
    require_two_approvers_above: 500000,
    mask_pii: true,
    retention_days: 2555, // 7 years
    consent_recorded: true,
  });

  useEffect(() => {
    (async () => {
      try {
        const { data } = await http.get("/auth/users");
        setUsers(data);
      } catch (_) {}
    })();
  }, []);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Configure approval thresholds, cooling periods and Indian data-protection preferences.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Approval rules</h3>
          <div className="mt-3 space-y-3 text-sm">
            <Row label="Standard approval threshold (₹)" value={prefs.approval_threshold}
                 onChange={(v) => setPrefs({ ...prefs, approval_threshold: v })} />
            <Row label="Cooling period after account change (hours)" value={prefs.cooling_period_hours}
                 onChange={(v) => setPrefs({ ...prefs, cooling_period_hours: v })} />
            <Row label="Require two approvers above (₹)" value={prefs.require_two_approvers_above}
                 onChange={(v) => setPrefs({ ...prefs, require_two_approvers_above: v })} />
          </div>
        </div>

        <div className="card-elev p-5">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Data protection (DPDP)</h3>
          <div className="mt-3 space-y-3 text-sm">
            <Toggle label="Mask account numbers & PAN by default" value={prefs.mask_pii}
                    onChange={(v) => setPrefs({ ...prefs, mask_pii: v })} />
            <Row label="Data retention (days)" value={prefs.retention_days}
                 onChange={(v) => setPrefs({ ...prefs, retention_days: v })} />
            <Toggle label="Consent for processing recorded" value={prefs.consent_recorded}
                    onChange={(v) => setPrefs({ ...prefs, consent_recorded: v })} />
            <button data-testid="deletion-request" className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs hover:border-blue-500/40">
              Raise deletion request (DPDP §12)
            </button>
          </div>
        </div>

        <div className="card-elev p-5 lg:col-span-2">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Users & roles</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-widest text-muted-foreground">
                <tr>
                  <th className="py-2">Name</th><th>Email</th><th>Role</th><th>Title</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-white/5">
                    <td className="py-2">{u.name}</td>
                    <td className="text-muted-foreground">{u.email}</td>
                    <td className="font-mono text-xs">{u.role}</td>
                    <td className="text-muted-foreground">{u.title}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">
            Signed in as <span className="text-foreground">{user?.name} ({user?.role})</span>
          </div>
        </div>

        <div className="card-elev p-5 lg:col-span-2">
          <h3 className="font-display text-sm font-semibold uppercase tracking-widest">Integrations (replaceable adapters)</h3>
          <div className="mt-3 grid grid-cols-2 gap-3 text-xs md:grid-cols-3">
            {["GST portal", "Bank account verification", "Email provider", "Accounting software",
              "ERP system", "UPI / banking API", "Cybercrime reporting"].map((k) => (
              <div key={k} className="rounded-md border border-white/10 bg-white/5 p-3">
                <div className="text-sm font-medium">{k}</div>
                <div className="text-muted-foreground">Adapter status: simulated</div>
                <div className="mt-1 text-[10px] uppercase text-amber-400">
                  Not live — connect production keys before go-live.
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, onChange }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex-1 text-muted-foreground">{label}</span>
      <input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))}
             className="w-40 rounded-md border border-white/10 bg-white/5 px-2 py-1 text-right text-sm" />
    </div>
  );
}
function Toggle({ label, value, onChange }) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <input type="checkbox" checked={value} onChange={(e) => onChange(e.target.checked)}
             className="h-4 w-4 accent-blue-500" />
      <span className="text-muted-foreground">{label}</span>
    </label>
  );
}

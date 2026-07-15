import React, { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ShieldCheck, ScanLine, Users, Wallet, CheckSquare,
  Bell, AlertOctagon, FileBarChart, ScrollText, Settings, LogOut,
  Search, Menu, X, Radio, MessageSquareWarning, Mic2,
} from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import { http } from "../lib/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, id: "nav-dashboard" },
  { to: "/verify", label: "Verify Payment", icon: ShieldCheck, id: "nav-verify" },
  { to: "/scanner", label: "Invoice Scanner", icon: ScanLine, id: "nav-scanner" },
  { to: "/vendors", label: "Vendors", icon: Users, id: "nav-vendors" },
  { to: "/beneficiaries", label: "Beneficiaries", icon: Wallet, id: "nav-beneficiaries" },
  { to: "/approvals", label: "Approvals", icon: CheckSquare, id: "nav-approvals" },
  { to: "/alerts", label: "Fraud Alerts", icon: Bell, id: "nav-alerts" },
  { to: "/incidents", label: "Incident Room", icon: AlertOctagon, id: "nav-incidents" },
  { to: "/comms", label: "Comm. Detector", icon: MessageSquareWarning, id: "nav-comms" },
  { to: "/voice", label: "Voice Verify", icon: Mic2, id: "nav-voice" },
  { to: "/reports", label: "Reports", icon: FileBarChart, id: "nav-reports" },
  { to: "/audit", label: "Audit Trail", icon: ScrollText, id: "nav-audit" },
  { to: "/settings", label: "Settings", icon: Settings, id: "nav-settings" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [notifs, setNotifs] = useState({ total: 0, critical_payments: 0, open_incidents: 0, pending_beneficiary_changes: 0 });
  const [org, setOrg] = useState("Shree Textiles Pvt Ltd");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const { data } = await http.get("/notifications");
        if (alive) setNotifs(data);
      } catch (_) {}
    }
    poll();
    const t = setInterval(poll, 20000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  function onSearch(e) {
    e.preventDefault();
    if (query.trim()) nav(`/approvals?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <div className="App relative flex min-h-screen">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-white/10 bg-[#0F1424]/95 backdrop-blur transition-transform lg:relative lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-gradient-to-br from-blue-500 to-emerald-500 shadow-lg shadow-blue-500/30">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="font-display text-lg font-semibold tracking-tight">VyaparRakshak</div>
            <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              AI · fraud shield
            </div>
          </div>
        </div>
        <div className="px-5 pb-3 text-[11px] leading-tight text-muted-foreground">
          Verify identity. Validate evidence. Protect every payment.
        </div>
        <nav className="mt-2 flex-1 space-y-0.5 overflow-y-auto px-3 pb-6">
          {NAV.map(({ to, label, icon: Icon, id }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              data-testid={id}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-blue-500/15 text-blue-300 ring-1 ring-blue-500/25"
                    : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 px-4 py-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Radio className="h-3.5 w-3.5 text-emerald-400" />
            <span data-testid="system-status">System healthy · rules v1.2</span>
          </div>
        </div>
      </aside>

      {/* Right column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top ribbon */}
        <header className="sticky top-0 z-30 flex flex-col gap-3 border-b border-white/10 bg-[#0B0F19]/85 px-5 py-3 backdrop-blur lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <button
              className="rounded-md p-2 text-muted-foreground hover:bg-white/5 lg:hidden"
              onClick={() => setOpen((v) => !v)}
              data-testid="mobile-menu-btn"
              aria-label="Open menu"
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <form onSubmit={onSearch} className="flex items-center rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
              <Search className="mr-2 h-4 w-4 text-muted-foreground" />
              <input
                data-testid="global-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search invoice, vendor, beneficiary…"
                className="w-56 bg-transparent text-sm outline-none placeholder:text-muted-foreground sm:w-80"
              />
            </form>
          </div>
          <div className="flex items-center gap-4">
            <select
              data-testid="org-selector"
              className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-foreground"
              value={org}
              onChange={(e) => setOrg(e.target.value)}
            >
              <option>Shree Textiles Pvt Ltd</option>
              <option>Kirloskar Traders (Group)</option>
              <option>Bansal Packaging LLP</option>
            </select>
            <Link
              to="/alerts"
              data-testid="notif-bell"
              className="relative rounded-full border border-white/10 bg-white/5 p-2 hover:border-blue-500/40"
            >
              <Bell className="h-4 w-4" />
              {notifs.total > 0 && (
                <span
                  data-testid="notif-count"
                  className="absolute -right-1 -top-1 grid h-5 min-w-[20px] place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white"
                >
                  {notifs.total}
                </span>
              )}
            </Link>
            <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1">
              <div className="grid h-7 w-7 place-items-center rounded-full bg-gradient-to-br from-blue-500 to-emerald-500 text-xs font-bold text-white">
                {user?.name?.charAt(0) || "U"}
              </div>
              <div className="hidden text-xs leading-tight sm:block">
                <div className="font-medium">{user?.name}</div>
                <div className="text-muted-foreground">
                  {user?.title || user?.role}
                </div>
              </div>
              <button
                onClick={async () => { await logout(); nav("/login"); }}
                data-testid="logout-btn"
                className="ml-2 rounded-full p-1 text-muted-foreground hover:text-rose-400"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import { Outlet, Navigate, NavLink, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { http } from "../lib/api";
import {
  LayoutDashboard, FileText, Wallet, ShieldCheck, LogOut, ScrollText,
} from "lucide-react";

const NAV = [
  { to: "/vendor", label: "Overview", icon: LayoutDashboard, id: "vnav-home", end: true },
  { to: "/vendor/kyc", label: "KYC Documents", icon: FileText, id: "vnav-kyc" },
  { to: "/vendor/payments", label: "My Payments", icon: ScrollText, id: "vnav-payments" },
  { to: "/vendor/bank-change", label: "Bank Change", icon: Wallet, id: "vnav-bank" },
];

export default function VendorLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await http.get("/vendor/me");
        setProfile(data);
      } catch (_) { setProfile(false); }
    })();
  }, []);

  if (user && user.role !== "vendor") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-white/10 bg-[#0F1424]/95 backdrop-blur lg:relative">
        <div className="flex items-center gap-2 px-5 py-5">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-gradient-to-br from-emerald-500 to-blue-500 shadow">
            <ShieldCheck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="font-display text-base font-semibold">Vendor Portal</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">VyaparRakshak</div>
          </div>
        </div>
        <nav className="mt-2 flex-1 space-y-0.5 px-3 pb-6">
          {NAV.map(({ to, label, icon: Icon, id, end }) => (
            <NavLink key={to} to={to} end={end} data-testid={id}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                  isActive ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/25"
                          : "text-muted-foreground hover:bg-white/5 hover:text-foreground"}`}>
              <Icon className="h-4 w-4" /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/10 px-4 py-3 text-xs">
          <div className="text-muted-foreground">Signed in as</div>
          <div className="mt-0.5 font-medium">{user?.name}</div>
          <div className="text-muted-foreground">{user?.email}</div>
          <button data-testid="vlogout"
            onClick={async () => { await logout(); nav("/login"); }}
            className="mt-3 inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs hover:border-rose-500/40 hover:text-rose-300">
            <LogOut className="h-3 w-3" /> Logout
          </button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-white/10 bg-[#0B0F19]/85 px-5 py-3 backdrop-blur">
          <div className="text-xs text-muted-foreground">
            {profile?.vendor?.name ?? "Vendor Portal"}
          </div>
          <div className="text-[11px] text-muted-foreground">
            Buyer: <span className="text-foreground">Shree Textiles Pvt Ltd</span>
          </div>
        </header>
        <main className="min-w-0 flex-1 px-5 py-6 lg:px-8">
          <Outlet context={{ profile }} />
        </main>
      </div>
    </div>
  );
}

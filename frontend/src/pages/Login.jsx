import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { ShieldCheck, LockKeyhole } from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import { toast } from "sonner";

const DEMO_USERS = [
  { email: "owner@vyaparrakshak.in", role: "Business Owner" },
  { email: "finance@vyaparrakshak.in", role: "Finance Manager" },
  { email: "maker@vyaparrakshak.in", role: "Payment Maker" },
  { email: "checker@vyaparrakshak.in", role: "Payment Checker" },
  { email: "auditor@vyaparrakshak.in", role: "Internal Auditor" },
];

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("owner@vyaparrakshak.in");
  const [password, setPassword] = useState("Owner@123");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    const res = await login(email, password);
    setBusy(false);
    if (res.ok) { toast.success("Welcome back"); nav("/"); }
    else { setError(res.error); toast.error(res.error); }
  }

  return (
    <div className="relative flex min-h-screen items-stretch">
      {/* Left – branding panel */}
      <div className="relative hidden flex-1 flex-col justify-between overflow-hidden border-r border-white/10 p-10 lg:flex">
        <div className="gridpattern absolute inset-0 opacity-40" />
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-emerald-500/10" />
        <div className="relative">
          <div className="flex items-center gap-2">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-gradient-to-br from-blue-500 to-emerald-500">
              <ShieldCheck className="h-6 w-6 text-white" />
            </div>
            <div>
              <div className="font-display text-xl font-semibold">VyaparRakshak AI</div>
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
                for Indian MSMEs
              </div>
            </div>
          </div>
        </div>
        <div className="relative">
          <div className="font-display text-4xl font-semibold leading-[1.1] lg:text-5xl">
            Verify identity.<br />
            Validate evidence.<br />
            <span className="text-emerald-400">Protect every payment.</span>
          </div>
          <p className="mt-5 max-w-lg text-sm text-muted-foreground">
            A payment-verification and fraud-prevention layer that sits between your team and every UPI, IMPS, NEFT or RTGS you release.
          </p>
          <div className="mt-8 grid max-w-md grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-emerald-400">₹1.96 Cr</div>
              <div className="text-muted-foreground">simulated loss prevented</div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-3">
              <div className="text-blue-400">30+</div>
              <div className="text-muted-foreground">sample payments seeded</div>
            </div>
          </div>
        </div>
        <div className="relative text-[11px] text-muted-foreground">
          Prototype build. External checks (GST, bank, cybercrime intimation) are simulated.
        </div>
      </div>

      {/* Right – form */}
      <div className="flex flex-1 items-center justify-center px-6 py-10">
        <div className="card-elev grain relative w-full max-w-md p-8">
          <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
            <LockKeyhole className="h-4 w-4" />
            <span>Secure sign-in · JWT · HttpOnly cookies</span>
          </div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">Sign in</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your organisation credentials to continue.
          </p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Email</label>
              <input
                data-testid="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              />
            </div>
            <div>
              <label className="text-xs font-medium uppercase tracking-widest text-muted-foreground">Password</label>
              <input
                data-testid="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="mt-1 w-full rounded-md border border-white/10 bg-white/5 px-3 py-2 text-sm outline-none focus:border-blue-500/50"
              />
            </div>
            {error && (
              <div className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300" data-testid="login-error">
                {error}
              </div>
            )}
            <button
              data-testid="login-submit-btn"
              disabled={busy}
              className="pill-btn w-full bg-blue-500 py-2.5 text-sm font-semibold text-white hover:bg-blue-400 disabled:opacity-60"
            >
              {busy ? "Signing in…" : "Sign in securely"}
            </button>
          </form>

          <div className="mt-6 border-t border-white/10 pt-4">
            <div className="mb-2 text-[11px] uppercase tracking-widest text-muted-foreground">Demo accounts (password: Owner@123)</div>
            <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.email}
                  type="button"
                  onClick={() => { setEmail(u.email); setPassword("Owner@123"); }}
                  data-testid={`demo-user-${u.role.toLowerCase().replace(/\s+/g, "-")}`}
                  className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5 text-left text-xs hover:border-blue-500/40"
                >
                  <div className="font-medium">{u.role}</div>
                  <div className="truncate text-muted-foreground">{u.email}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

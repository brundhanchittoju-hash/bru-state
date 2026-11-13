import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  ArrowRight,
  Lock,
  Mail,
  AlertCircle,
  Eye,
  EyeOff,
  CheckCircle2,
  FileCheck2,
  KeyRound,
  Building2,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const isDemoLoginEnabled = import.meta.env.VITE_ENABLE_DEMO_LOGIN === "true";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.getModifierState) {
      setCapsLockActive(e.getModifierState("CapsLock"));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!email || !password) {
      setErrorMessage("Please enter both email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email, password });
      toast.success("Authentication successful. Welcome to State Audit AI.");
      navigate("/dashboard");
    } catch (err: any) {
      const msg = err.message || "Invalid credentials or account locked.";
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const setDemoAccount = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setErrorMessage(null);
  };

  return (
    <div className="relative flex min-h-screen w-full items-center justify-center overflow-x-hidden bg-slate-950 font-sans text-slate-100 antialiased selection:bg-indigo-500 selection:text-white">
      {/* Background Ambience & Grid */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.14),transparent_50%),radial-gradient(circle_at_bottom,_rgba(99,102,241,0.08),transparent_50%)]" />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.035]"
        style={{
          backgroundImage: `linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)`,
          backgroundSize: "32px 32px",
        }}
        aria-hidden="true"
      />

      <div className="relative z-10 mx-auto flex w-full max-w-5xl flex-col lg:flex-row items-stretch justify-center gap-6 p-4 sm:p-6 lg:p-8">
        
        {/* Left / Hero Departmental Trust Panel (visible on lg+) */}
        <div className="hidden lg:flex lg:w-5/12 flex-col justify-between rounded-3xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 via-slate-900/60 to-slate-950/90 p-8 shadow-2xl backdrop-blur-xl">
          <div className="space-y-6">
            {/* Departmental Emblem & Header */}
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 text-white shadow-lg shadow-indigo-500/25 ring-1 ring-white/20">
                <ShieldCheck className="h-6 w-6 stroke-[2.2]" />
              </div>
              <div>
                <p className="text-[11px] font-bold tracking-widest text-indigo-400 uppercase">
                  Government of Karnataka
                </p>
                <h2 className="text-base font-extrabold tracking-tight text-white">
                  State Audit Department
                </h2>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-[11px] font-medium text-indigo-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Statutory Audit Portal • Production Gateway
              </span>
              <h1 className="text-2xl font-extrabold tracking-tight text-white">
                Intelligent Financial Audit & Verification Workspace
              </h1>
              <p className="text-xs leading-relaxed text-slate-400">
                Statutory inspection platform for Karnataka State Local Bodies, Panchayati Raj Institutions, and Urban Local Authorities.
              </p>
            </div>

            {/* Institutional Security Pillars */}
            <div className="space-y-3 pt-3">
              <div className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <KeyRound className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">Strict Role-Based Access (RBAC)</h4>
                  <p className="text-[11px] text-slate-400">Dedicated statutory workspaces for Administrator, Audit Officer, Senior Auditor, and Field Auditor.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <FileCheck2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">Tamper-Evident SHA-256 Audit Trail</h4>
                  <p className="text-[11px] text-slate-400">Every voucher analysis, finding review, and status transition is immutably hash-chained.</p>
                </div>
              </div>

              <div className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <Building2 className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-semibold text-slate-200">State & Panchayat Jurisdiction</h4>
                  <p className="text-[11px] text-slate-400">Integrated reconciliation against Karnataka Treasury rules, KTPP Act 1999, and GFR 2017.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Security Badge */}
          <div className="border-t border-slate-800/80 pt-4 flex items-center justify-between text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              256-bit TLS Encrypted
            </span>
            <span className="font-mono text-[10px] text-slate-400">v1.0.0 • KSAD</span>
          </div>
        </div>

        {/* Right / Sign-In Card */}
        <div className="w-full lg:w-7/12 flex flex-col justify-center">
          <div className="w-full rounded-3xl border border-slate-800 bg-slate-900/95 p-6 sm:p-9 shadow-2xl backdrop-blur-xl space-y-6">
            
            {/* Header (visible on mobile / tablet or as card header) */}
            <div className="space-y-1.5 text-center lg:text-left">
              <div className="flex items-center justify-center lg:justify-start gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 ring-1 ring-indigo-500/30">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-xl font-extrabold tracking-tight text-white">
                    STATE AUDIT AI
                  </h1>
                </div>
              </div>
              <h2 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 pt-1">
                Sign in to your account
              </h2>
              <p className="text-xs text-slate-400">
                Enter your official departmental email and password to access the audit workbench.
              </p>
            </div>

            {/* Error Notification */}
            {errorMessage && (
              <div
                role="alert"
                className="flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-200 animate-fade-in"
              >
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
                <div className="flex-1 font-medium">{errorMessage}</div>
              </div>
            )}

            {/* Caps Lock Alert */}
            {capsLockActive && (
              <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                <span>Caps Lock is ON. Passwords are case-sensitive.</span>
              </div>
            )}

            {/* Credentials Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="login-email"
                  className="text-xs font-semibold text-slate-300"
                >
                  Official Departmental Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                  <Input
                    id="login-email"
                    name="email"
                    type="email"
                    placeholder="name@stateaudit.kar.gov.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10 h-11 rounded-xl bg-slate-950/70 border-slate-700/80 text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500"
                    autoComplete="email"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="login-password"
                    className="text-xs font-semibold text-slate-300"
                  >
                    Password
                  </label>
                  <span className="text-[11px] text-slate-400 font-medium">
                    Min 12 chars
                  </span>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                  <Input
                    id="login-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onKeyUp={handleKeyDown}
                    className="pl-10 pr-10 h-11 rounded-xl bg-slate-950/70 border-slate-700/80 text-slate-100 placeholder:text-slate-500 focus:border-indigo-500 focus:ring-indigo-500"
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    className="absolute right-3.5 top-3 text-slate-400 hover:text-slate-200 transition-colors focus:outline-none"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold gap-2 shadow-lg shadow-indigo-600/25 transition-all focus:ring-2 focus:ring-indigo-400"
              >
                {isSubmitting ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span>Verifying Credentials...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Audit System</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Quick Demo Credentials Switcher (Only in Demo Mode) */}
            {isDemoLoginEnabled && (
              <div className="border-t border-slate-800 pt-5 space-y-3 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-300">
                    Quick Login (Demo Accounts)
                  </span>
                  <Badge variant="signal" className="text-[10px] uppercase tracking-wider">
                    DEMO DATA
                  </Badge>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDemoAccount("admin@stateaudit.kar.gov.in", "AdminPassword@2024")}
                    className="flex flex-col text-left p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-indigo-500/50 hover:bg-indigo-950/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <span className="font-semibold text-slate-200 text-xs">Administrator</span>
                    <span className="font-mono text-[10px] text-slate-400 truncate w-full">
                      admin@stateaudit.kar.gov.in
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDemoAccount("officer@stateaudit.kar.gov.in", "OfficerPassword@2024")}
                    className="flex flex-col text-left p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-indigo-500/50 hover:bg-indigo-950/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <span className="font-semibold text-slate-200 text-xs">Audit Officer</span>
                    <span className="font-mono text-[10px] text-slate-400 truncate w-full">
                      officer@stateaudit.kar.gov.in
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDemoAccount("senior.auditor@stateaudit.kar.gov.in", "SeniorPassword@2024")}
                    className="flex flex-col text-left p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-indigo-500/50 hover:bg-indigo-950/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <span className="font-semibold text-slate-200 text-xs">Senior Auditor</span>
                    <span className="font-mono text-[10px] text-slate-400 truncate w-full">
                      senior.auditor@stateaudit.kar.gov.in
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDemoAccount("auditor@stateaudit.kar.gov.in", "AuditorPassword@2024")}
                    className="flex flex-col text-left p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-indigo-500/50 hover:bg-indigo-950/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                  >
                    <span className="font-semibold text-slate-200 text-xs">Auditor</span>
                    <span className="font-mono text-[10px] text-slate-400 truncate w-full">
                      auditor@stateaudit.kar.gov.in
                    </span>
                  </button>
                </div>
              </div>
            )}

            {/* Official Statutory Notice Footer */}
            <div className="border-t border-slate-800/80 pt-4 space-y-1.5">
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <strong className="text-slate-300 font-semibold">Statutory Notice:</strong> This system is reserved solely for authorized audit personnel of the Government of Karnataka. All activities, sessions, and voucher analyses are immutably logged with SHA-256 cryptographic chaining. Unauthorized access attempts are monitored and subject to legal prosecution under the Information Technology Act.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

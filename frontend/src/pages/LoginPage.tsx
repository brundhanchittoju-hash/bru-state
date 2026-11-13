import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, ArrowRight, Lock, Mail, AlertCircle } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const isDemoLoginEnabled = import.meta.env.VITE_ENABLE_DEMO_LOGIN === "true";

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
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-[radial-gradient(ellipse_at_top,_#E0E7FF_0%,_#F6F7F9_50%,_#EBF0F7_100%)] dark:bg-[radial-gradient(ellipse_at_top,_#1E1B4B_0%,_#0D0F14_55%,_#090B0F_100%)] px-4 py-10 text-foreground">
      {/* Subtle workspace canvas dot grid */}
      <div className="pointer-events-none absolute inset-0 canvas-dot-grid opacity-60" aria-hidden="true" />

      <div className="relative z-10 w-full max-w-[440px] space-y-7">
        {/* Centered Large Wordmark */}
        <div className="flex flex-col items-center text-center space-y-2.5">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
            <ShieldCheck className="h-6 w-6 stroke-[2.1]" />
          </div>
          <div>
            <h1 className="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
              STATE AUDIT AI
            </h1>
            <p className="mt-1 text-xs font-medium tracking-wide text-muted-foreground">
              Karnataka State Audit Department • Financial Audit Workspace
            </p>
          </div>
        </div>

        {/* Single Centered Sign-In Card */}
        <div className="rounded-2xl border border-border bg-card/95 backdrop-blur-md p-6 sm:p-8 shadow-xl shadow-graphite-900/[0.06] dark:shadow-black/40 space-y-6">
          <div className="space-y-1 text-center">
            <h2 className="font-display text-xl font-bold tracking-tight text-foreground">
              Sign in to your account
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Enter your official departmental email and password.
            </p>
          </div>

          {errorMessage && (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-xl border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/50 p-3 text-xs text-rose-800 dark:text-rose-200 animate-fade-in"
            >
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div className="flex-1">{errorMessage}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="login-email"
                className="text-xs font-semibold text-foreground/85"
              >
                Official Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="login-email"
                  name="email"
                  type="email"
                  placeholder="name@stateaudit.kar.gov.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9 h-10 rounded-xl"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="login-password"
                className="text-xs font-semibold text-foreground/85"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="login-password"
                  name="password"
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 h-10 rounded-xl"
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-10 rounded-xl font-semibold gap-2"
            >
              {isSubmitting ? "Authenticating..." : "Sign In to Audit System"}
              {!isSubmitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          {/* Quick Demo Credentials Switcher */}
          {isDemoLoginEnabled && (
            <div className="border-t border-border pt-5 space-y-2.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-foreground/85">
                  Quick Login (Demo Accounts)
                </span>
                <Badge variant="signal" className="text-[10px] uppercase tracking-wider">
                  DEMO DATA
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setDemoAccount("admin@stateaudit.kar.gov.in", "AdminPassword@2024")}
                  className="flex flex-col text-left p-2.5 rounded-xl border border-border bg-muted/40 hover:border-primary/60 hover:bg-accent/70 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="font-semibold text-foreground">Administrator</span>
                  <span className="font-mono text-[10px] text-muted-foreground truncate w-full">
                    admin@stateaudit.kar.gov.in
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setDemoAccount("officer@stateaudit.kar.gov.in", "OfficerPassword@2024")}
                  className="flex flex-col text-left p-2.5 rounded-xl border border-border bg-muted/40 hover:border-primary/60 hover:bg-accent/70 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="font-semibold text-foreground">Audit Officer</span>
                  <span className="font-mono text-[10px] text-muted-foreground truncate w-full">
                    officer@stateaudit.kar.gov.in
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setDemoAccount("senior.auditor@stateaudit.kar.gov.in", "SeniorPassword@2024")}
                  className="flex flex-col text-left p-2.5 rounded-xl border border-border bg-muted/40 hover:border-primary/60 hover:bg-accent/70 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="font-semibold text-foreground">Senior Auditor</span>
                  <span className="font-mono text-[10px] text-muted-foreground truncate w-full">
                    senior.auditor@stateaudit.kar.gov.in
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setDemoAccount("auditor@stateaudit.kar.gov.in", "AuditorPassword@2024")}
                  className="flex flex-col text-left p-2.5 rounded-xl border border-border bg-muted/40 hover:border-primary/60 hover:bg-accent/70 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="font-semibold text-foreground">Auditor</span>
                  <span className="font-mono text-[10px] text-muted-foreground truncate w-full">
                    auditor@stateaudit.kar.gov.in
                  </span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer Integrity Note */}
        <p className="text-center text-[11px] text-muted-foreground leading-relaxed">
          Human-in-the-loop audit workbench • SHA-256 tamper-evident trail • Strictly &ldquo;flagged for review&rdquo;
        </p>
      </div>
    </div>
  );
};

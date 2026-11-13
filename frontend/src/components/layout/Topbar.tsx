import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ChevronRight,
  LogOut,
  Moon,
  Search,
  ShieldCheck,
  Sun,
  User as UserIcon,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { AuditTrailVerifyResponse } from "@/types";
import { toast } from "sonner";

export const Topbar: React.FC<{ onOpenCommand?: () => void }> = ({ onOpenCommand }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const [verifyModalOpen, setVerifyModalOpen] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyData, setVerifyData] = useState<AuditTrailVerifyResponse | null>(null);

  const pathSegments = location.pathname.split("/").filter(Boolean);
  const breadcrumbs = pathSegments.map((segment, index) => {
    const url = `/${pathSegments.slice(0, index + 1).join("/")}`;
    const name = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
    return { name, url };
  });

  const handleVerifyAuditTrail = async () => {
    setIsVerifying(true);
    setVerifyModalOpen(true);
    try {
      const res = await api.get<AuditTrailVerifyResponse>("/audit-trail/verify");
      setVerifyData(res);
      if (res.verified) {
        toast.success("Cryptographic ledger verified successfully.");
      } else {
        toast.error(`Audit chain broken at sequence ${res.broken_at_sequence}`);
      }
    } catch {
      toast.error("Failed to verify audit trail cryptographic chain.");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between gap-4 border-b border-border bg-card/85 backdrop-blur-md px-5 md:px-6">
        {/* Left: Breadcrumbs */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-muted-foreground min-w-0 shrink">
          <span className="text-xs font-medium text-muted-foreground hidden lg:inline whitespace-nowrap">
            Karnataka Audit
          </span>
          {breadcrumbs.map((crumb, idx) => (
            <React.Fragment key={crumb.url}>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60 hidden lg:inline shrink-0" />
              <button
                type="button"
                onClick={() => navigate(crumb.url)}
                className={
                  idx === breadcrumbs.length - 1
                    ? "font-display text-sm font-semibold text-foreground truncate"
                    : "text-xs font-medium hover:text-foreground transition-colors truncate"
                }
              >
                {crumb.name}
              </button>
            </React.Fragment>
          ))}
        </nav>

        {/* Center: Wide Command Search (Ctrl/Cmd+K) */}
        <div className="flex-1 max-w-xl hidden sm:flex justify-center">
          <button
            type="button"
            onClick={onOpenCommand}
            className="flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-muted/50 px-3.5 py-2 text-xs text-muted-foreground hover:border-primary/45 hover:bg-card hover:text-foreground transition-all"
          >
            <span className="flex items-center gap-2 truncate">
              <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className="truncate">Search audit cases, findings, vendors, vouchers, or jump to page...</span>
            </span>
            <kbd className="rounded-md border border-border bg-card px-1.5 py-0.5 text-[10px] font-mono font-semibold text-foreground shrink-0">
              Ctrl K
            </kbd>
          </button>
        </div>

        {/* Right: Actions, Verified Badge, Demo Badge, Theme Toggle, User Profile */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Compact Search button on xs */}
          <Button
            variant="outline"
            size="icon"
            onClick={onOpenCommand}
            className="h-9 w-9 sm:hidden rounded-xl"
            aria-label="Open command search"
          >
            <Search className="h-4 w-4" />
          </Button>

          {/* Cryptographic Audit Trail Verified Indicator */}
          <button
            type="button"
            data-testid="audit-trail-verified-btn"
            onClick={handleVerifyAuditTrail}
            className="flex items-center gap-1.5 rounded-full border border-emerald-500/35 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-800 dark:text-emerald-300 hover:bg-emerald-500/15 transition-colors"
            title="Click to re-verify cryptographic hash chain"
          >
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700 dark:text-emerald-400" />
            <span className="hidden xl:inline">Audit trail verified</span>
            <span className="xl:hidden">Verified</span>
            <span aria-hidden="true">✓</span>
          </button>

          {/* Persistent DEMO DATA Badge */}
          <Badge variant="signal" className="text-[10px] uppercase tracking-wider font-bold hidden md:inline-flex">
            DEMO DATA
          </Badge>

          {/* Theme Toggle */}
          <Button
            variant="outline"
            size="icon"
            onClick={toggleTheme}
            className="h-9 w-9 rounded-xl"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4 text-amber-400" />
            ) : (
              <Moon className="h-4 w-4 text-foreground/80" />
            )}
          </Button>

          {/* User Profile Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                data-testid="user-menu-trigger"
                className="flex items-center gap-2 rounded-xl border border-transparent p-1 hover:border-border hover:bg-muted/60 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-display font-bold text-xs">
                  {user?.full_name?.charAt(0) || "U"}
                </div>
                <div className="hidden text-left 2xl:block pr-1">
                  <p className="text-xs font-semibold text-foreground leading-tight">
                    {user?.full_name}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono">
                    {user?.role?.name || "Auditor"}
                  </p>
                </div>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="p-2.5 border-b border-border">
                <p className="text-sm font-semibold truncate text-foreground">{user?.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                <Badge variant="secondary" className="mt-1.5 text-[10px] uppercase font-mono">
                  {user?.role?.name}
                </Badge>
              </div>
              <DropdownMenuItem onClick={() => navigate("/settings")} className="gap-2 mt-1">
                <UserIcon className="h-4 w-4 text-muted-foreground" />
                Settings &amp; Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                data-testid="logout-menu-item"
                onClick={logout}
                className="gap-2 text-rose-700 dark:text-rose-400 focus:text-rose-700"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Audit Trail Cryptographic Verification Dialog */}
      <Dialog open={verifyModalOpen} onOpenChange={setVerifyModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              <DialogTitle>Audit Trail Cryptographic Verification</DialogTitle>
            </div>
            <DialogDescription className="text-xs pt-1">
              Deterministic SHA-256 hash-chain verification for the State of Karnataka Audit Office.
            </DialogDescription>
          </DialogHeader>

          {isVerifying ? (
            <div className="py-8 text-center space-y-3">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-primary border-r-transparent" />
              <p className="text-sm text-muted-foreground">
                Traversing activity ledger from genesis record...
              </p>
            </div>
          ) : verifyData ? (
            <div className="space-y-4 py-2">
              <div
                className={`flex items-center gap-3 p-4 rounded-xl border ${
                  verifyData.verified
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200"
                    : "bg-rose-500/10 border-rose-500/30 text-rose-900 dark:text-rose-200"
                }`}
              >
                {verifyData.verified ? (
                  <CheckCircle2 className="h-7 w-7 text-emerald-700 dark:text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-7 w-7 text-rose-700 dark:text-rose-400 shrink-0" />
                )}
                <div>
                  <h4 className="font-display font-semibold text-sm">
                    {verifyData.verified ? "Ledger Verified & Intact" : "Tampering Detected"}
                  </h4>
                  <p className="text-xs mt-0.5 opacity-90">
                    {verifyData.verified
                      ? `All ${verifyData.total_records} activity entries match cryptographic hash signatures.`
                      : verifyData.error}
                  </p>
                </div>
              </div>

              <div className="text-xs space-y-2 bg-muted/60 p-3.5 rounded-xl border border-border font-mono tabular-nums">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Total Entries</span>
                  <span className="font-bold text-foreground">{verifyData.total_records}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hash Algorithm</span>
                  <span className="text-foreground">SHA-256 (Canonical JSON)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Genesis Hash</span>
                  <span className="truncate max-w-[180px] text-foreground">000000000000...0000</span>
                </div>
                {verifyData.last_verified_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Verified At</span>
                    <span className="text-[11px] text-foreground">
                      {new Date(verifyData.last_verified_at).toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
};

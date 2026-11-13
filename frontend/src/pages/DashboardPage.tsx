import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Briefcase,
  CheckCircle2,
  FileText,
  AlertTriangle,
  Clock,
  Calendar as CalendarIcon,
  Plus,
  Trash2,
  Filter,
  ShieldAlert,
  UserCheck,
  Info,
  Layers,
  ChevronRight,
  Lock,
  ArrowUpRight,
  IndianRupee,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";
import { Drawer } from "@/components/shared/Drawer";
import { Timeline, TimelineItem } from "@/components/shared/Timeline";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { AuditCase } from "@/types";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface DashboardStats {
  total_cases: number;
  open_cases: number;
  completed_cases: number;
  documents_uploaded: number;
  documents_processed: number;
  pending_findings: number;
  high_risk_findings: number;
  medium_risk_findings: number;
  low_risk_findings: number;
  critical_risk_findings: number;
  r001_duplicate_payments: number;
  r003_amount_mismatches: number;
  r008_missing_documents: number;
  pending_approvals_count: number;
  total_flagged_amount: number;
}

interface PriorityFinding {
  id: string;
  finding_number: string;
  title: string;
  case_id: string;
  case_number?: string;
  district?: string;
  scheme?: string;
  rule_code?: string;
  risk_score: number;
  severity: string;
  amount: number;
  status: string;
  created_at: string;
}

interface ScheduledEvent {
  id: string;
  title: string;
  event_date: string;
  case_id?: string;
  case_number?: string;
  created_by_name: string;
  description?: string;
  event_type: string;
  created_at: string;
}

interface RecentActivity {
  id: string;
  action: string;
  entity_type: string;
  entity_id?: string;
  actor_name: string;
  created_at: string;
  payload_summary?: string;
}

const CASE_BOARD_COLUMNS: {
  key: string;
  label: string;
  stageIndex: number;
  progressPct: number;
  accentDot: string;
}[] = [
  { key: "draft", label: "Draft", stageIndex: 1, progressPct: 14, accentDot: "bg-slate-400" },
  { key: "documents_uploaded", label: "Documents Uploaded", stageIndex: 2, progressPct: 29, accentDot: "bg-sky-500" },
  { key: "processing", label: "Processing", stageIndex: 3, progressPct: 43, accentDot: "bg-indigo-500" },
  { key: "verification", label: "Verification", stageIndex: 4, progressPct: 57, accentDot: "bg-violet-500" },
  { key: "review", label: "Review", stageIndex: 5, progressPct: 71, accentDot: "bg-amber-500" },
  { key: "approved", label: "Approved", stageIndex: 6, progressPct: 86, accentDot: "bg-emerald-500" },
  { key: "closed", label: "Closed", stageIndex: 7, progressPct: 100, accentDot: "bg-emerald-700 dark:bg-emerald-400" },
];

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { hasRole } = useAuth();

  // Filters from URL
  const selectedFy = searchParams.get("fy") || "2024-25";
  const selectedDistrict = searchParams.get("district") || "";
  const [assignedOnly, setAssignedOnly] = useState<boolean>(false);

  // Data states
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [cases, setCases] = useState<AuditCase[]>([]);
  const [priorityQueue, setPriorityQueue] = useState<PriorityFinding[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<ScheduledEvent[]>([]);
  const [activities, setActivities] = useState<RecentActivity[]>([]);
  const [recentReports, setRecentReports] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Calendar Event Modal
  const [isEventModalOpen, setIsEventModalOpen] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>("");
  const [newDate, setNewDate] = useState<string>("");
  const [newEventType, setNewEventType] = useState<string>("audit_deadline");
  const [newDesc, setNewDesc] = useState<string>("");
  const [isSavingEvent, setIsSavingEvent] = useState<boolean>(false);

  // Priority Queue Drawer state
  const [isQueueDrawerOpen, setIsQueueDrawerOpen] = useState<boolean>(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const q = new URLSearchParams();
      if (selectedFy) q.append("financial_year", selectedFy);
      if (selectedDistrict) q.append("district", selectedDistrict);
      if (assignedOnly) q.append("assigned_only", "true");

      const casesQ = new URLSearchParams();
      if (selectedFy) casesQ.append("financial_year", selectedFy);
      if (selectedDistrict) casesQ.append("district", selectedDistrict);

      const [statsRes, casesRes, pqRes, calRes, actRes, repRes] = await Promise.all([
        api.get<DashboardStats>(`/dashboard/stats?${q.toString()}`).catch(() => null),
        api.get<AuditCase[]>(`/cases?${casesQ.toString()}`).catch(() => []),
        api.get<PriorityFinding[]>("/dashboard/priority-queue").catch(() => []),
        api.get<ScheduledEvent[]>("/dashboard/calendar").catch(() => []),
        api.get<RecentActivity[]>("/dashboard/recent-activity").catch(() => []),
        api.get<any>("/reports?page=1&page_size=4").catch(() => null),
      ]);

      if (statsRes) setStats(statsRes);
      setCases(Array.isArray(casesRes) ? casesRes : []);
      setPriorityQueue(Array.isArray(pqRes) ? pqRes : []);
      setCalendarEvents(Array.isArray(calRes) ? calRes : []);
      setActivities(Array.isArray(actRes) ? actRes : []);
      if (repRes && Array.isArray(repRes.items)) setRecentReports(repRes.items);
    } catch {
      toast.error("Failed to load dashboard metrics.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedFy, selectedDistrict, assignedOnly]);

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDate) {
      toast.error("Title and date are required.");
      return;
    }
    setIsSavingEvent(true);
    try {
      await api.post("/dashboard/calendar", {
        title: newTitle.trim(),
        event_date: newDate,
        event_type: newEventType,
        description: newDesc.trim() || undefined,
      });
      toast.success("Statutory deadline created.");
      setIsEventModalOpen(false);
      setNewTitle("");
      setNewDate("");
      setNewDesc("");
      loadData();
    } catch {
      toast.error("Failed to create calendar event.");
    } finally {
      setIsSavingEvent(false);
    }
  };

  const handleDeleteEvent = async (eventId: string) => {
    try {
      await api.delete(`/dashboard/calendar/${eventId}`);
      toast.success("Event removed from calendar.");
      setCalendarEvents((prev) => prev.filter((ev) => ev.id !== eventId));
    } catch {
      toast.error("Failed to delete event.");
    }
  };

  const updateFilter = (key: string, val: string) => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set(key, val);
    else next.delete(key);
    setSearchParams(next);
  };

  const activityTimelineItems: TimelineItem[] = activities.map((a) => ({
    id: a.id,
    title: a.action.replace(/_/g, " "),
    meta: `${a.actor_name} • ${new Date(a.created_at).toLocaleDateString("en-IN")}`,
    detail: a.payload_summary,
    accent: a.action.includes("approve")
      ? "success"
      : a.action.includes("flag")
      ? "signal"
      : "primary",
  }));

  return (
    <div className="space-y-6">
      {/* Workspace Header */}
      <PageHeader
        title="Audit Executive Dashboard"
        description="Live audit case workflow board, flagged attention queue, and statutory KPIs across Karnataka Local Bodies."
        badge={
          <Badge variant="secondary" className="font-mono text-xs">
            Karnataka SAC • FY {selectedFy}
          </Badge>
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          {hasRole(["senior_auditor", "audit_officer", "administrator"]) && (stats?.pending_approvals_count ?? 0) > 0 && (
            <Button
              variant="signal"
              size="sm"
              onClick={() => navigate("/findings?status=pending_approval")}
              className="gap-1.5"
            >
              <AlertTriangle className="h-4 w-4" />
              <span className="font-mono text-xs tabular-nums">
                Approval Queue ({stats?.pending_approvals_count})
              </span>
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsQueueDrawerOpen(true)}
            className="gap-1.5 border-primary/35 text-primary hover:bg-accent"
          >
            <ShieldAlert className="h-4 w-4" />
            <span className="font-mono text-xs tabular-nums">
              Priority Queue ({priorityQueue.length})
            </span>
          </Button>

          <Button size="sm" onClick={() => setIsEventModalOpen(true)} className="gap-1.5">
            <Plus className="h-4 w-4" />
            <span>Add Deadline</span>
          </Button>
        </div>
      </PageHeader>

      {/* Workspace Scope Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-2.5 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
            <Filter className="h-3.5 w-3.5 text-primary" />
            <span>Workspace Scope</span>
          </div>

          <select
            aria-label="Filter by Financial Year"
            value={selectedFy}
            onChange={(e) => updateFilter("fy", e.target.value)}
            className="h-8 rounded-lg border border-input bg-background px-2.5 font-mono text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="2024-25">FY 2024-25</option>
            <option value="2023-24">FY 2023-24</option>
          </select>

          <select
            aria-label="Filter by District"
            value={selectedDistrict}
            onChange={(e) => updateFilter("district", e.target.value)}
            className="h-8 rounded-lg border border-input bg-background px-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All Demo Districts</option>
            <option value="Mysuru">Mysuru</option>
            <option value="Belagavi">Belagavi</option>
            <option value="Dharwad">Dharwad</option>
            <option value="Tumakuru">Tumakuru</option>
            <option value="Kalaburagi">Kalaburagi</option>
          </select>

          {hasRole(["auditor"]) && (
            <button
              type="button"
              onClick={() => setAssignedOnly(!assignedOnly)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border",
                assignedOnly
                  ? "bg-accent text-accent-foreground border-primary/40"
                  : "bg-muted/60 text-muted-foreground border-border hover:text-foreground"
              )}
            >
              <UserCheck className="h-3.5 w-3.5" />
              <span>Assigned to Me Only</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground tabular-nums">
          <IndianRupee className="h-3.5 w-3.5 text-signal" />
          <span>Flagged Value:</span>
          <span className="font-semibold text-foreground">
            {isLoading
              ? "..."
              : `₹${(stats?.total_flagged_amount ?? 0).toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`}
          </span>
        </div>
      </div>

      {/* 1. "Needs Attention" Strip (Built from Priority Queue API) */}
      <section aria-label="Needs attention priority strip" className="rounded-2xl border border-signal-border bg-signal-surface/45 dark:bg-card p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-signal text-signal-foreground">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <div>
              <h2 className="font-display text-sm font-bold text-foreground">
                Needs Attention
              </h2>
              <p className="text-[11px] text-muted-foreground">
                Top priority findings flagged for review from active audit dockets
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsQueueDrawerOpen(true)}
            className="text-xs text-primary hover:text-primary gap-1"
          >
            <span>Inspect All ({priorityQueue.length})</span>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>

        {priorityQueue.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-card/70 px-4 py-4 text-xs text-muted-foreground flex items-center justify-between">
            <span>No open high-risk or critical-risk findings currently awaiting immediate review.</span>
            <Button variant="outline" size="sm" onClick={() => navigate("/findings")} className="text-xs h-7">
              Browse Findings
            </Button>
          </div>
        ) : isQueueDrawerOpen ? (
          <div className="rounded-xl border border-border bg-card/70 px-4 py-4 text-xs text-muted-foreground">
            Inspecting {priorityQueue.length} priority finding(s) in the review drawer...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {priorityQueue.slice(0, 4).map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => navigate(`/findings/${item.id}`)}
                className="group text-left rounded-xl border border-border bg-card p-3.5 shadow-sm hover:border-primary/50 hover:shadow-md transition-all space-y-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-[11px] font-semibold text-primary">
                    {item.finding_number}
                  </span>
                  <RiskBadge level={item.severity} />
                </div>
                <p className="text-xs font-semibold text-foreground line-clamp-2 group-hover:text-primary transition-colors">
                  {item.title}
                </p>
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-border/70">
                  <StatusPill status={item.status} className="text-[10px] px-2 py-0" />
                  <span className="font-mono text-[11px] font-semibold text-foreground tabular-nums">
                    ₹{item.amount.toLocaleString("en-IN")}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* 2. Audit Case Board (7 Workflow Columns) */}
      <section aria-label="Audit case status board" className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-lg font-bold tracking-tight text-foreground">
              Audit Case Board
            </h2>
            <p className="text-xs text-muted-foreground">
              Cases grouped across statutory lifecycle stages ({cases.length} matching current scope)
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate("/cases")} className="gap-1.5 text-xs">
            <span>All Audit Cases</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </div>

        <div className="flex gap-3.5 overflow-x-auto pb-3 snap-x">
          {CASE_BOARD_COLUMNS.map((col) => {
            const colCases = cases.filter(
              (c) => (c.status || "draft").toLowerCase() === col.key
            );

            return (
              <div
                key={col.key}
                className="flex w-[268px] shrink-0 flex-col rounded-2xl border border-border bg-muted/45 p-3 snap-start"
              >
                {/* Column Header */}
                <div className="flex items-center justify-between gap-2 pb-2.5 mb-2.5 border-b border-border/80">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={cn("h-2 w-2 rounded-full shrink-0", col.accentDot)} aria-hidden="true" />
                    <h3 className="font-display text-xs font-bold text-foreground truncate">
                      {col.label}
                    </h3>
                  </div>
                  <span className="rounded-full bg-card border border-border px-2 py-0.5 font-mono text-[10px] font-semibold text-foreground tabular-nums">
                    {colCases.length}
                  </span>
                </div>

                {/* Case Cards Stack */}
                <div className="flex-1 space-y-2.5 min-h-[160px] max-h-[380px] overflow-y-auto pr-0.5">
                  {isLoading ? (
                    <div className="rounded-xl border border-border bg-card p-3 space-y-2 animate-pulse">
                      <div className="h-3 w-20 bg-muted rounded" />
                      <div className="h-4 w-full bg-muted rounded" />
                      <div className="h-2 w-full bg-muted rounded" />
                    </div>
                  ) : colCases.length === 0 ? (
                    <div className="flex h-36 items-center justify-center rounded-xl border border-dashed border-border/80 bg-background/40 px-3 text-center text-[11px] text-muted-foreground">
                      No cases in {col.label}
                    </div>
                  ) : (
                    colCases.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => navigate(`/cases/${c.id}`)}
                        className="w-full text-left rounded-xl border border-border bg-card p-3 shadow-xs hover:border-primary/50 hover:shadow-md transition-all space-y-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-[11px] font-semibold text-primary truncate">
                            {c.case_number}
                          </span>
                          {c.is_locked && (
                            <span title="Case approved and locked" className="text-muted-foreground">
                              <Lock className="h-3 w-3" />
                            </span>
                          )}
                        </div>

                        <div className="space-y-0.5">
                          <p className="text-xs font-semibold text-foreground line-clamp-2 leading-snug">
                            {c.title}
                          </p>
                          <p className="text-[11px] text-muted-foreground truncate">
                            {c.district || "Karnataka"} • {c.scheme_name || "Statutory"}
                          </p>
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <RiskBadge level={c.risk_level || "low"} />
                          <span className="font-mono text-[10px] text-muted-foreground tabular-nums">
                            {c.document_count ?? 0} docs
                          </span>
                        </div>

                        {/* Deterministic Workflow Stage Progress */}
                        <div className="space-y-1 pt-1 border-t border-border/60">
                          <div className="flex items-center justify-between font-mono text-[10px] text-muted-foreground tabular-nums">
                            <span>Stage {col.stageIndex}/7</span>
                            <span>{col.progressPct}%</span>
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <div
                              style={{ width: `${col.progressPct}%` }}
                              className={cn(
                                "h-full rounded-full transition-all",
                                col.stageIndex === 7 ? "bg-emerald-600 dark:bg-emerald-400" : "bg-primary"
                              )}
                            />
                          </div>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 3. Live Statutory KPIs & Rule Signals */}
      <section aria-label="Live statutory metrics" className="space-y-3">
        <h2 className="font-display text-lg font-bold tracking-tight text-foreground">
          Statutory Oversight &amp; Rule Signals
        </h2>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Total Audit Cases"
            value={isLoading ? "..." : String(stats?.total_cases ?? 0)}
            description="Sanctioned local body audits"
            icon={<Briefcase className="h-5 w-5" />}
            onClick={() => navigate("/cases")}
          />
          <StatCard
            title="Open Cases"
            value={isLoading ? "..." : String(stats?.open_cases ?? 0)}
            description="In draft, upload, or review"
            icon={<Clock className="h-5 w-5" />}
            onClick={() => navigate("/cases?status=review")}
          />
          <StatCard
            title="Completed Cases"
            value={isLoading ? "..." : String(stats?.completed_cases ?? 0)}
            description="Officially approved & locked"
            icon={<CheckCircle2 className="h-5 w-5" />}
            onClick={() => navigate("/cases?status=approved")}
          />
          <StatCard
            title="Documents Uploaded"
            value={isLoading ? "..." : String(stats?.documents_uploaded ?? 0)}
            description="Vouchers, bills, passbooks ingested"
            icon={<FileText className="h-5 w-5" />}
            onClick={() => navigate("/documents")}
          />
          <StatCard
            title="Documents Processed"
            value={isLoading ? "..." : String(stats?.documents_processed ?? 0)}
            description="OCR & extracted data ledger entries"
            icon={<CheckCircle2 className="h-5 w-5" />}
            onClick={() => navigate("/documents?status=processed")}
          />
          <StatCard
            title="Pending Findings"
            value={isLoading ? "..." : String(stats?.pending_findings ?? 0)}
            description="Awaiting auditor or officer review"
            icon={<AlertTriangle className="h-5 w-5" />}
            onClick={() => navigate("/findings?status=open")}
          />
        </div>

        {/* Risk Bands (4-up) */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Critical Risk Findings"
            value={isLoading ? "..." : String(stats?.critical_risk_findings ?? 0)}
            description="Score 80-100 • Priority review"
            icon={<ShieldAlert className="h-5 w-5 text-rose-600 dark:text-rose-400" />}
            onClick={() => navigate("/findings?risk_level=critical")}
          />
          <StatCard
            title="High Risk Findings"
            value={isLoading ? "..." : String(stats?.high_risk_findings ?? 0)}
            description="Score 60-79 • Requires Senior Approval"
            icon={<ShieldAlert className="h-5 w-5 text-orange-600 dark:text-orange-400" />}
            onClick={() => navigate("/findings?risk_level=high")}
          />
          <StatCard
            title="Medium Risk Findings"
            value={isLoading ? "..." : String(stats?.medium_risk_findings ?? 0)}
            description="Score 40-59 • Operational variance"
            icon={<AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />}
            onClick={() => navigate("/findings?risk_level=medium")}
          />
          <StatCard
            title="Low Risk Findings"
            value={isLoading ? "..." : String(stats?.low_risk_findings ?? 0)}
            description="Score 0-39 • Minor discrepancies"
            icon={<Info className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />}
            onClick={() => navigate("/findings?risk_level=low")}
          />
        </div>

        {/* Key Verification Rules (3-up) */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="R-001 Duplicate Payments"
            value={isLoading ? "..." : String(stats?.r001_duplicate_payments ?? 0)}
            description="Exact voucher & payee match"
            icon={<Layers className="h-5 w-5" />}
            onClick={() => navigate("/findings?rule_code=R-001")}
          />
          <StatCard
            title="R-003 Amount Mismatches"
            value={isLoading ? "..." : String(stats?.r003_amount_mismatches ?? 0)}
            description="Bill vs Voucher vs Passbook delta"
            icon={<AlertTriangle className="h-5 w-5" />}
            onClick={() => navigate("/findings?rule_code=R-003")}
          />
          <StatCard
            title="R-008 Missing Documents"
            value={isLoading ? "..." : String(stats?.r008_missing_documents ?? 0)}
            description="Statutory checklists incomplete"
            icon={<FileText className="h-5 w-5" />}
            onClick={() => navigate("/findings?rule_code=R-008")}
          />
        </div>
      </section>

      {/* 4. Bottom Dock: Calendar + Activity Timeline + Recent Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Audit Calendar (2 cols) */}
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <CalendarIcon className="h-4 w-4 text-primary" />
              <h3 className="font-display text-base font-semibold text-foreground">
                Statutory Audit Calendar &amp; Deadlines
              </h3>
            </div>
            <Badge variant="secondary" className="font-mono text-xs tabular-nums">
              {calendarEvents.length} Scheduled
            </Badge>
          </div>

          {calendarEvents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-muted/30 py-8 px-4 text-center space-y-3">
              <p className="font-display text-sm font-semibold text-foreground">
                No statutory deadlines scheduled
              </p>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Add Gram Panchayat hearings, submission cutoffs, or officer review milestones for this financial year.
              </p>
              <Button size="sm" variant="outline" onClick={() => setIsEventModalOpen(true)} className="gap-1.5">
                <Plus className="h-3.5 w-3.5" />
                <span>Schedule Deadline</span>
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-border/80 max-h-72 overflow-y-auto">
              {calendarEvents.map((ev) => (
                <div key={ev.id} className="py-2.5 flex items-center justify-between gap-3 text-xs">
                  <div className="flex items-start gap-3 min-w-0">
                    <span className="rounded-lg bg-muted px-2.5 py-1 font-mono text-[11px] font-semibold text-foreground tabular-nums shrink-0">
                      {ev.event_date}
                    </span>
                    <div className="space-y-0.5 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-foreground">{ev.title}</span>
                        <Badge variant="secondary" className="text-[10px] uppercase">
                          {ev.event_type.replace("_", " ")}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground text-[11px] truncate">
                        {ev.case_number ? `Case: ${ev.case_number} • ` : ""}
                        By {ev.created_by_name}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteEvent(ev.id)}
                    aria-label={`Remove deadline ${ev.title}`}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-rose-600 shrink-0"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity Timeline (1 col) */}
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <h3 className="font-display text-base font-semibold text-foreground">
              Live Audit Trail
            </h3>
            <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-700 dark:text-emerald-300">
              Hash verified ✓
            </span>
          </div>

          <div className="max-h-72 overflow-y-auto pr-1">
            <Timeline items={activityTimelineItems} emptyMessage="No recent logged actions." />
          </div>
        </div>
      </div>

      {/* Recent Statutory Reports */}
      {recentReports.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" />
              <h3 className="font-display text-base font-semibold text-foreground">
                Recent Statutory Audit Reports
              </h3>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/reports")}
              className="text-xs text-primary hover:text-primary gap-1"
            >
              <span>View All Reports</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {recentReports.map((r) => (
              <div
                key={r.id}
                onClick={() => navigate("/reports")}
                className="p-3.5 rounded-xl border border-border hover:border-primary/50 bg-muted/35 hover:bg-card cursor-pointer space-y-2 transition-all"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-primary truncate">
                    {r.report_number}
                  </span>
                  <StatusPill status={r.status} />
                </div>
                <h4 className="font-display text-xs font-semibold text-foreground truncate">
                  {r.report_title}
                </h4>
                <p className="text-[11px] text-muted-foreground font-mono tabular-nums">
                  {r.case_number} • v{r.current_version}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Priority Review Queue Slide-Over Drawer */}
      <Drawer
        open={isQueueDrawerOpen}
        onOpenChange={setIsQueueDrawerOpen}
        title={
          <>
            <ShieldAlert className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <span>Priority Review Queue (Top Risk Findings)</span>
          </>
        }
        description="Deterministic rule findings ranked by severity and amount at risk."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsQueueDrawerOpen(false)}>
              Close
            </Button>
            <Button size="sm" onClick={() => { setIsQueueDrawerOpen(false); navigate("/findings"); }}>
              View All Findings
            </Button>
          </>
        }
      >
        <div className="divide-y divide-border">
          {priorityQueue.length === 0 ? (
            <p className="text-center py-10 text-xs text-muted-foreground">
              No open high-risk findings pending review.
            </p>
          ) : (
            priorityQueue.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  setIsQueueDrawerOpen(false);
                  navigate(`/findings/${item.id}`);
                }}
                className="py-3.5 px-2 -mx-2 rounded-xl hover:bg-muted/60 cursor-pointer flex items-center justify-between gap-3 text-xs transition-colors"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-foreground">
                      <span className="font-mono text-primary">{item.finding_number}</span>: {item.title}
                    </span>
                    <RiskBadge level={item.severity} />
                    <StatusPill status={item.status} />
                  </div>
                  <p className="font-mono text-muted-foreground text-[11px] tabular-nums">
                    {item.case_number ? `${item.case_number} • ` : ""}
                    {item.district ? `${item.district} • ` : ""}
                    Flagged: ₹{item.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
              </div>
            ))
          )}
        </div>
      </Drawer>

      {/* Add Calendar Event Modal */}
      <Dialog open={isEventModalOpen} onOpenChange={setIsEventModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add Statutory Deadline / Event</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateEvent} className="space-y-3 py-2 text-xs">
            <div>
              <label className="block font-medium text-foreground/85 mb-1">
                Event Title *
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="e.g. Gram Panchayat Hearing on MGNREGA"
                required
                className="w-full h-9 px-3 rounded-lg border border-input bg-card text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block font-medium text-foreground/85 mb-1">
                Event Date *
              </label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                required
                className="w-full h-9 px-3 rounded-lg border border-input bg-card text-foreground font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="block font-medium text-foreground/85 mb-1">
                Event Type
              </label>
              <select
                value={newEventType}
                onChange={(e) => setNewEventType(e.target.value)}
                className="w-full h-9 px-3 rounded-lg border border-input bg-card text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="audit_deadline">Statutory Audit Deadline</option>
                <option value="hearing">Formal Hearing</option>
                <option value="submission">Document Submission</option>
                <option value="review">Officer Review</option>
              </select>
            </div>
            <div>
              <label className="block font-medium text-foreground/85 mb-1">
                Description / Notes
              </label>
              <textarea
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-input bg-card text-foreground text-xs focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsEventModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isSavingEvent}>
                {isSavingEvent ? "Saving..." : "Save Deadline"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Briefcase,
  Upload,
  FileText,
  Calendar,
  ShieldAlert,
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Lock,
  Unlock,
  Printer,
  ChevronRight,
  Play,
  FileSpreadsheet,
} from "lucide-react";
import { StatusPill } from "@/components/shared/StatusPill";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatCard } from "@/components/shared/StatCard";
import { Timeline } from "@/components/shared/Timeline";
import { EmptyState } from "@/components/shared/EmptyState";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { DocumentUploadModal } from "@/components/documents/DocumentUploadModal";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { ConfidenceBadge } from "@/components/documents/ConfidenceBadge";
import { ReportGenerateModal } from "@/components/reporting/ReportGenerateModal";
import { ReportPreviewModal } from "@/components/reporting/ReportPreviewModal";
import { ReportApproveModal } from "@/components/reporting/ReportApproveModal";
import { AuditCase, DocumentItem } from "@/types";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const STATUS_STEPS = [
  "draft",
  "documents_uploaded",
  "processing",
  "verification",
  "review",
  "approved",
  "closed",
];

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  documents_uploaded: "Docs Uploaded",
  processing: "Processing",
  verification: "Verification",
  review: "Review",
  approved: "Approved",
  closed: "Closed",
};

export const AuditCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const [auditCase, setAuditCase] = useState<AuditCase | null>(null);
  const [caseDetail, setCaseDetail] = useState<any | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [caseFindings, setCaseFindings] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"overview" | "documents" | "extracted" | "verification" | "findings" | "reports" | "timeline">("overview");

  // Modals
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Status transition & reopen modals
  const [isReopenModalOpen, setIsReopenModalOpen] = useState<boolean>(false);
  const [reopenReason, setReopenReason] = useState<string>("");
  const [isReopening, setIsReopening] = useState<boolean>(false);

  // Blocker modal for Approval
  const [blockingFindings, setBlockingFindings] = useState<any[]>([]);
  const [isBlockerModalOpen, setIsBlockerModalOpen] = useState<boolean>(false);
  const [isTransitioning, setIsTransitioning] = useState<boolean>(false);

  // Print view modal
  const [isPrintModalOpen, setIsPrintModalOpen] = useState<boolean>(false);

  // Reports state
  const [caseReports, setCaseReports] = useState<any[]>([]);
  const [isGenerateReportModalOpen, setIsGenerateReportModalOpen] = useState<boolean>(false);
  const [selectedPreviewReport, setSelectedPreviewReport] = useState<any | null>(null);
  const [selectedApproveReport, setSelectedApproveReport] = useState<any | null>(null);

  const loadCaseReports = async () => {
    if (!id) return;
    try {
      const res = await api.get<any[]>(`/cases/${id}/reports`);
      setCaseReports(res || []);
    } catch {}
  };

  const loadCaseData = async (initial = false) => {
    if (!id) return;
    if (initial) setIsLoading(true);
    try {
      const [caseData, detailData, docsData, findingsRes, reportsRes] = await Promise.all([
        api.get<AuditCase>(`/cases/${id}`),
        api.get<any>(`/cases/${id}/detail`).catch(() => null),
        api.get<DocumentItem[]>(`/documents?case_id=${id}`).catch(() => []),
        api.get<any>(`/findings?case_id=${id}&page_size=50`).catch(() => ({ items: [] })),
        api.get<any[]>(`/cases/${id}/reports`).catch(() => []),
      ]);
      setAuditCase(caseData);
      setCaseDetail(detailData);
      setDocuments(docsData);
      setCaseFindings(findingsRes.items || []);
      setCaseReports(reportsRes || []);
    } catch {
      toast.error("Failed to load audit case details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCaseData(true);
  }, [id]);

  const handleNextStatus = async () => {
    if (!auditCase) return;
    const currIdx = STATUS_STEPS.indexOf(auditCase.status.toLowerCase());
    if (currIdx === -1 || currIdx >= STATUS_STEPS.length - 1) return;

    const nextStatus = STATUS_STEPS[currIdx + 1];
    setIsTransitioning(true);
    try {
      await api.post(`/cases/${auditCase.id}/status`, {
        to_status: nextStatus,
        notes: `Advanced to ${STATUS_LABELS[nextStatus]} via dashboard action.`,
      });
      toast.success(`Case transitioned to ${STATUS_LABELS[nextStatus]}.`);
      loadCaseData(false);
    } catch (err: any) {
      if (err.data && err.data.detail && err.data.detail.blocking_findings) {
        setBlockingFindings(err.data.detail.blocking_findings);
        setIsBlockerModalOpen(true);
      } else {
        toast.error(err.data?.detail || "Status transition blocked.");
      }
    } finally {
      setIsTransitioning(false);
    }
  };

  const handleReopen = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reopenReason.trim() || reopenReason.trim().length < 10) {
      toast.error("Please provide a substantive justification (min 10 characters).");
      return;
    }
    setIsReopening(true);
    try {
      await api.post(`/cases/${auditCase?.id}/reopen`, { reason: reopenReason.trim() });
      toast.success("Case unlocked and returned to Review status.");
      setIsReopenModalOpen(false);
      setReopenReason("");
      loadCaseData(false);
    } catch (err: any) {
      toast.error(err.data?.detail || "Failed to reopen audit case.");
    } finally {
      setIsReopening(false);
    }
  };

  const handleTriggerVerification = async () => {
    if (!auditCase) return;
    try {
      toast.info("Executing statutory verification rules engine...");
      const res = await api.post<any>(`/cases/${auditCase.id}/verify`, {});
      toast.success(res.message || "Verification completed.");
      loadCaseData(false);
    } catch (err: any) {
      toast.error(err.data?.detail || "Failed to run verification.");
    }
  };

  if (isLoading || !auditCase) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <div className="h-8 w-8 rounded-full border-4 border-primary border-r-transparent animate-spin" />
        <p className="text-xs text-muted-foreground font-mono">Loading Audit Case {id}...</p>
      </div>
    );
  }

  const isLocked = auditCase.is_locked || ["approved", "closed"].includes((auditCase.status || "").toLowerCase());
  const currStepIdx = STATUS_STEPS.indexOf((auditCase.status || "draft").toLowerCase());
  const timelineItems = (caseDetail?.status_history || []).map((h: any) => ({
    id: String(h.id),
    title: `Status: ${String(h.to_status || "").replace(/_/g, " ")}`,
    meta: `By ${h.changed_by} • ${new Date(h.created_at).toLocaleString()}`,
    detail: h.notes,
    accent: "primary" as const,
  }));

  return (
    <div className="space-y-6">
      {/* Back button and breadcrumb */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => navigate("/cases")}
            className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5 mr-1" />
            Back to Cases
          </Button>
          <span>/</span>
          <span className="font-mono text-primary font-medium">
            {auditCase.case_number}
          </span>
          {auditCase.version && auditCase.version > 1 && (
            <Badge variant="secondary" className="text-[10px] bg-signal-surface text-signal border border-signal-border">
              v{auditCase.version}
            </Badge>
          )}
        </div>

        <Button variant="outline" size="sm" onClick={() => setIsPrintModalOpen(true)} className="h-7 text-xs gap-1.5">
          <Printer className="h-3.5 w-3.5" />
          <span>Print Summary</span>
        </Button>
      </div>

      {/* Case Header Card */}
      <div className="p-6 rounded-2xl border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-md font-mono text-xs font-semibold bg-primary text-primary-foreground shadow-sm">
                {auditCase.case_number}
              </span>
              <h2 className="font-display text-xl font-bold text-foreground">
                {auditCase.title}
              </h2>
            </div>
            <p className="text-xs text-muted-foreground">
              {auditCase.gram_panchayat ? `${auditCase.gram_panchayat} GP, ` : ""}
              {auditCase.taluk ? `${auditCase.taluk} Taluk, ` : ""}
              {auditCase.district || "Karnataka"} • Scheme:{" "}
              <span className="font-semibold text-foreground">{auditCase.scheme_name || "General"}</span> • FY:{" "}
              <span className="font-mono font-medium text-foreground">{auditCase.financial_year}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <RiskBadge level={auditCase.risk_level || "low"} />
            <StatusPill status={auditCase.status} />
          </div>
        </div>

        {/* 7-State Lifecycle Stepper */}
        <div className="pt-3 border-t border-border">
          <div className="flex items-center justify-between gap-1 overflow-x-auto py-1">
            {STATUS_STEPS.map((step, idx) => {
              const isPassed = idx < currStepIdx;
              const isCurrent = idx === currStepIdx;
              return (
                <div key={step} className="flex items-center gap-1.5 min-w-[96px]">
                  <div
                    className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${
                      isCurrent
                        ? "bg-primary text-primary-foreground ring-2 ring-primary/25"
                        : isPassed
                        ? "bg-emerald-600 text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {isPassed ? "✓" : idx + 1}
                  </div>
                  <span
                    className={`text-[11px] font-medium whitespace-nowrap ${
                      isCurrent
                        ? "text-primary font-bold"
                        : isPassed
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    {STATUS_LABELS[step]}
                  </span>
                  {idx < STATUS_STEPS.length - 1 && (
                    <ChevronRight className="h-3 w-3 text-muted-foreground/50 mx-1 shrink-0" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Action Controls & Lock Status */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            {!isLocked && currStepIdx < STATUS_STEPS.length - 1 && (
              <Button
                size="sm"
                onClick={handleNextStatus}
                disabled={isTransitioning}
                className="text-xs gap-1.5"
              >
                <span>Advance to {STATUS_LABELS[STATUS_STEPS[currStepIdx + 1]]}</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            )}

            {isLocked && hasRole(["audit_officer", "administrator"]) && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsReopenModalOpen(true)}
                className="text-signal border-signal-border bg-signal-surface/40 text-xs gap-1.5"
              >
                <Unlock className="h-3.5 w-3.5" />
                <span>Reopen Case (Audit Officer)</span>
              </Button>
            )}

            {!isLocked && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleTriggerVerification}
                className="text-xs gap-1.5"
              >
                <Play className="h-3.5 w-3.5 text-primary" />
                <span>Run Verification Rules</span>
              </Button>
            )}
          </div>

          {isLocked && (
            <div className="flex items-center gap-2 text-xs text-signal font-medium">
              <Lock className="h-3.5 w-3.5" />
              <span>Audit Case is Locked ({STATUS_LABELS[auditCase.status.toLowerCase()] || auditCase.status})</span>
            </div>
          )}
        </div>
      </div>

      {/* Lock Warning Banner */}
      {isLocked && (
        <div className="p-3.5 rounded-xl border border-signal-border bg-signal-surface text-signal flex items-center gap-3 text-xs">
          <Lock className="h-4 w-4 shrink-0" />
          <div className="flex-1">
            <span className="font-semibold">Case Locked:</span> Document uploads, field overrides, and verification re-runs are disabled.
            Only an Audit Officer can reopen this case with formal recorded justification.
          </div>
        </div>
      )}

      {/* 7 Functional Tabs Navigation */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)} className="space-y-4">
        <TabsList className="w-full justify-start overflow-x-auto h-auto flex-wrap gap-1 p-1">
          {[
            { key: "overview", label: "Overview & Team", icon: Briefcase },
            { key: "documents", label: `Evidence Docs (${documents.length})`, icon: FileText },
            { key: "extracted", label: "Extracted Data", icon: FileSpreadsheet },
            { key: "verification", label: `Rule Runs (${caseDetail?.verification_summary?.total_runs || 0})`, icon: Play },
            { key: "findings", label: `Findings (${caseFindings.length})`, icon: ShieldAlert },
            { key: "reports", label: "Statutory Reports", icon: Clock },
            { key: "timeline", label: "Case Timeline", icon: Calendar },
          ].map(({ key, label, icon: Icon }) => (
            <TabsTrigger key={key} value={key} className="gap-1.5">
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Sanctioned Budget"
              value={`₹${(caseDetail?.financial_summary?.sanctioned_amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              description="Approved government allocation"
              icon={<Briefcase className="h-5 w-5" />}
            />
            <StatCard
              title="Actual Expenditure"
              value={`₹${(caseDetail?.financial_summary?.actual_expenditure || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              description="Vouchers presented for audit"
              icon={<FileText className="h-5 w-5" />}
            />
            <StatCard
              title="Budget Variance"
              value={`₹${(caseDetail?.financial_summary?.variance || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              description="Unspent or excess expenditure"
              icon={<AlertTriangle className="h-5 w-5" />}
              tone="signal"
            />
            <StatCard
              title="Budget Utilization"
              value={`${caseDetail?.financial_summary?.budget_utilization_pct || 0}%`}
              description="Expenditure vs Allocation"
              icon={<CheckCircle2 className="h-5 w-5" />}
              tone="emerald"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 rounded-2xl border border-border bg-card space-y-3 text-xs shadow-sm">
              <h3 className="font-display font-semibold text-sm border-b border-border pb-2 text-foreground">
                Institutional Identification
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Department:</span>
                  <span className="font-medium text-foreground">{auditCase.department_name || "RDPR Karnataka"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Zilla Panchayat:</span>
                  <span className="font-medium text-foreground">{auditCase.district || "Mysuru"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Taluk:</span>
                  <span className="font-medium text-foreground">{auditCase.taluk || "Nanjangud"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Gram Panchayat:</span>
                  <span className="font-medium text-foreground">{auditCase.gram_panchayat || "Hullahalli"}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Audit Type:</span>
                  <span className="font-medium text-foreground">{auditCase.audit_type || "Statutory"}</span>
                </div>
              </div>
            </div>

            <div className="p-5 rounded-2xl border border-border bg-card space-y-3 text-xs shadow-sm">
              <h3 className="font-display font-semibold text-sm border-b border-border pb-2 text-foreground">
                Assigned Team & Schedule
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Lead Auditor:</span>
                  <span className="font-semibold text-primary">
                    {auditCase.lead_auditor_name || "Assigned Auditor"}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Planned Start:</span>
                  <span className="font-mono text-foreground">{auditCase.planned_start_date || "2024-04-01"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Statutory Due Date:</span>
                  <span className="font-mono text-foreground">{auditCase.due_date || "2025-03-31"}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Priority:</span>
                  <span className="font-medium capitalize text-foreground">{auditCase.priority || "medium"}</span>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold text-foreground">Evidence Documents Repository</h3>
            {!isLocked && (
              <Button size="sm" onClick={() => setIsUploadModalOpen(true)} className="gap-1.5 text-xs">
                <Upload className="h-3.5 w-3.5" />
                <span>Upload New Evidence</span>
              </Button>
            )}
          </div>

          {selectedDocId ? (
            <DocumentViewer
              documentId={selectedDocId}
              onClose={() => setSelectedDocId(null)}
              onRefresh={() => loadCaseData(false)}
            />
          ) : documents.length === 0 ? (
            <EmptyState
              title="No evidence documents uploaded"
              description="Upload statutory vouchers, bills, sanction orders, or bank statements to run automated OCR and cross-document checks."
              actionLabel={!isLocked ? "Upload Evidence Document" : undefined}
              onAction={!isLocked ? () => setIsUploadModalOpen(true) : undefined}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map((doc) => (
                <Card
                  key={doc.id}
                  data-testid="open-viewer-btn"
                  onClick={() => setSelectedDocId(doc.id)}
                  className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group"
                >
                  <CardHeader className="p-4 pb-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="text-[11px]">
                        {doc.document_type || "Unknown"}
                      </Badge>
                      <ConfidenceBadge confidence={doc.classification_confidence} compact />
                    </div>
                    <CardTitle className="text-sm font-semibold pt-2 truncate">
                      {doc.title || doc.original_filename}
                    </CardTitle>
                    <p className="text-[11px] text-muted-foreground font-mono truncate">{doc.original_filename}</p>
                  </CardHeader>
                  <CardContent className="p-4 pt-2">
                    <p className="text-[11px] text-muted-foreground font-mono">Pages: {doc.page_count} • Version: {doc.current_version}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="extracted">
          <div className="p-5 rounded-2xl border border-border bg-card space-y-3 shadow-sm">
            <h3 className="font-display text-sm font-semibold text-foreground">Structured Financial Record Ledger</h3>
            <p className="text-xs text-muted-foreground">Extracted voucher fields with effective value resolution and provenance.</p>
            <div className="py-6 text-center text-xs text-muted-foreground">
              Select a document in the Evidence Docs tab to view granular field overrides and bounding box overlays.
            </div>
          </div>
        </TabsContent>

        <TabsContent value="verification">
          <div className="p-5 rounded-2xl border border-border bg-card space-y-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-sm font-semibold text-foreground">Verification Rule Runs</h3>
                <p className="text-xs text-muted-foreground">History of automated rule evaluations on this audit case.</p>
              </div>
              {!isLocked && (
                <Button size="sm" onClick={handleTriggerVerification} className="gap-1.5 text-xs">
                  <Play className="h-3.5 w-3.5" />
                  <span>Re-run Verification</span>
                </Button>
              )}
            </div>

            <div className="divide-y divide-border text-xs">
              <div className="py-3 flex justify-between">
                <span className="font-medium text-muted-foreground">Total Verification Runs:</span>
                <span className="font-mono font-bold text-foreground tabular-nums">{caseDetail?.verification_summary?.total_runs || 0}</span>
              </div>
              <div className="py-3 flex justify-between">
                <span className="font-medium text-muted-foreground">Last Execution Timestamp:</span>
                <span className="font-mono text-foreground">{caseDetail?.verification_summary?.last_run_at ? new Date(caseDetail.verification_summary.last_run_at).toLocaleString() : "Never"}</span>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="findings" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display text-sm font-semibold text-foreground">Audit Findings Scoped to Case ({caseFindings.length})</h3>
            <Button size="sm" variant="outline" onClick={() => navigate("/findings")} className="text-xs">
              View All Findings
            </Button>
          </div>

          {caseFindings.length === 0 ? (
            <EmptyState
              title="No findings flagged for review"
              description="No anomalies were flagged during automated verification for this case."
            />
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {caseFindings.map((f) => (
                <div
                  key={f.id}
                  onClick={() => navigate(`/findings/${f.id}`)}
                  className="p-3.5 rounded-xl border border-border bg-card hover:border-primary/50 hover:shadow-sm transition-all cursor-pointer flex items-center justify-between text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono font-semibold text-primary">{f.finding_number}</span>
                      <span className="font-medium text-foreground">{f.title}</span>
                      <RiskBadge level={f.risk_level || "low"} />
                      <StatusPill status={f.status} />
                    </div>
                    <p className="text-muted-foreground font-mono text-[11px] tabular-nums">
                      Flagged Amount: ₹{(f.amount_at_risk || 0).toLocaleString("en-IN")}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="reports" className="space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div>
              <h3 className="font-display text-sm font-semibold text-foreground">
                Statutory Audit Reports & Certificates
              </h3>
              <p className="text-xs text-muted-foreground">
                Tamper-evident, cryptographically hash-chained reports with dual-custody approval.
              </p>
            </div>
            {hasRole(["auditor", "senior_auditor", "audit_officer", "administrator"]) && (
              <Button
                size="sm"
                onClick={() => setIsGenerateReportModalOpen(true)}
                className="gap-1.5 text-xs"
              >
                <FileText className="h-3.5 w-3.5" />
                Generate Report
              </Button>
            )}
          </div>

          {caseReports.length === 0 ? (
            <EmptyState
              title="No reports generated yet"
              description="Generate the preliminary or interim audit report to review findings, questioned amounts, and recommendations."
              actionLabel={
                hasRole(["auditor", "senior_auditor", "audit_officer", "administrator"])
                  ? "Generate First Report"
                  : undefined
              }
              onAction={
                hasRole(["auditor", "senior_auditor", "audit_officer", "administrator"])
                  ? () => setIsGenerateReportModalOpen(true)
                  : undefined
              }
            />
          ) : (
            <div className="space-y-4">
              {caseReports.map((rep) => (
                <div
                  key={rep.id}
                  className="rounded-2xl border border-border bg-card p-4 space-y-3 shadow-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-primary">
                          {rep.report_number}
                        </span>
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-foreground">
                          v{rep.current_version}.0
                        </span>
                        <StatusPill status={rep.status} />
                      </div>
                      <h4 className="text-sm font-medium text-foreground">
                        {rep.report_title}
                      </h4>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedPreviewReport(rep)}
                        className="text-xs gap-1.5"
                      >
                        Preview PDF
                      </Button>
                      <a
                        href={`${API_BASE}/reports/${rep.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-muted text-foreground"
                      >
                        Download
                      </a>
                      <a
                        href={`/verify/${rep.report_number}?v=${rep.current_version}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-accent text-accent-foreground border border-primary/20"
                      >
                        Public Seal
                      </a>
                      {hasRole(["senior_auditor", "audit_officer", "administrator"]) &&
                        rep.status !== "Approved" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setSelectedApproveReport(rep)}
                            className="text-xs gap-1.5 border-primary text-primary"
                          >
                            Sign & Approve
                          </Button>
                        )}
                    </div>
                  </div>

                  {rep.versions && rep.versions.length > 0 && (
                    <div className="pt-2 border-t border-border">
                      <p className="text-[11px] font-semibold text-muted-foreground mb-1.5">Version History:</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                        {rep.versions.map((ver: any) => (
                          <div
                            key={ver.id}
                            className="p-2 rounded-xl bg-muted/50 border border-border flex items-center justify-between"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[11px] font-semibold text-foreground">
                                v{ver.version_number}
                              </span>
                              <StatusPill status={ver.status} />
                              <span className="text-[11px] text-muted-foreground truncate max-w-[120px]">
                                By {ver.generated_by_name}
                              </span>
                            </div>
                            <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[110px]" title={ver.pdf_sha256}>
                              {ver.pdf_sha256?.substring(0, 10)}...
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="timeline">
          <div className="p-5 rounded-2xl border border-border bg-card space-y-4 shadow-sm">
            <h3 className="font-display text-sm font-semibold text-foreground">Case Status History & Audit Trail</h3>
            <Timeline items={timelineItems} emptyMessage="No status transitions recorded for this case yet." />
          </div>
        </TabsContent>
      </Tabs>

      {/* Blocker Modal when attempting Approval with Open High/Critical Findings */}
      <Dialog open={isBlockerModalOpen} onOpenChange={setIsBlockerModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
              <AlertTriangle className="h-5 w-5" />
              <span>Approval Blocked by Statutory Gate</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <p className="text-muted-foreground">
              This case cannot be transitioned to <strong>Approved</strong> because there are unresolved High or Critical findings.
              All High and Critical findings must be Confirmed or Dismissed before sign-off.
            </p>
            <div className="p-3 rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 space-y-2">
              <span className="font-semibold text-rose-800 dark:text-rose-300">Blocking Findings ({blockingFindings.length}):</span>
              <ul className="list-disc pl-4 space-y-1 text-foreground">
                {blockingFindings.map((b) => (
                  <li key={b.id}>
                    <strong>{b.finding_number}:</strong> {b.title} ({b.severity} • {b.status})
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <DialogFooter>
            <Button size="sm" onClick={() => { setIsBlockerModalOpen(false); navigate("/findings"); }}>
              Go to Review Findings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reopen Modal for Audit Officer */}
      <Dialog open={isReopenModalOpen} onOpenChange={setIsReopenModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-signal">
              <Unlock className="h-5 w-5" />
              <span>Reopen Audit Case</span>
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleReopen} className="space-y-3 py-2 text-xs">
            <p className="text-muted-foreground">
              Reopening will unlock the case, increment its version number, and return it to <strong>Review</strong> status.
              A detailed audit log entry will be permanently appended to the cryptographic ledger.
            </p>
            <div>
              <label className="block font-medium mb-1 text-foreground">Substantive Justification / Reason *</label>
              <textarea
                value={reopenReason}
                onChange={(e) => setReopenReason(e.target.value)}
                placeholder="e.g. Additional payment vouchers submitted by Taluk Panchayat officer for review."
                rows={3}
                required
                className="w-full px-2.5 py-1.5 rounded-lg border border-input bg-background text-foreground text-xs"
              />
            </div>
            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setIsReopenModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={isReopening}>
                {isReopening ? "Unlocking..." : "Confirm & Reopen Case"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Printable Summary Modal */}
      <Dialog open={isPrintModalOpen} onOpenChange={setIsPrintModalOpen}>
        <DialogContent className="max-w-2xl text-xs print:p-0 print:border-none">
          <DialogHeader className="print:hidden">
            <DialogTitle>Printable Case Summary</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 p-4 border border-border rounded-lg print:border-none print:p-0">
            <div className="text-center border-b border-border pb-3">
              <h2 className="font-display text-base font-bold uppercase tracking-wider">Government of Karnataka</h2>
              <p className="text-xs text-muted-foreground">State Audit & Compliance Department</p>
              <p className="text-[11px] font-mono text-muted-foreground">Case ID: {auditCase.case_number} • Version: {auditCase.version || 1}</p>
            </div>

            <div className="grid grid-cols-2 gap-4 text-[11px]">
              <div>
                <p><strong>Case Title:</strong> {auditCase.title}</p>
                <p><strong>District:</strong> {auditCase.district || "Mysuru"}</p>
                <p><strong>Scheme:</strong> {auditCase.scheme_name || "MGNREGA"}</p>
                <p><strong>Status:</strong> {STATUS_LABELS[auditCase.status.toLowerCase()] || auditCase.status}</p>
              </div>
              <div>
                <p><strong>Financial Year:</strong> {auditCase.financial_year}</p>
                <p><strong>Sanctioned:</strong> ₹{(caseDetail?.financial_summary?.sanctioned_amount || 0).toLocaleString("en-IN")}</p>
                <p><strong>Actual Spend:</strong> ₹{(caseDetail?.financial_summary?.actual_expenditure || 0).toLocaleString("en-IN")}</p>
                <p><strong>Lead Auditor:</strong> {auditCase.lead_auditor_name || "Assigned Auditor"}</p>
              </div>
            </div>

            <div className="border-t border-border pt-3">
              <h4 className="font-bold mb-1">Finding Severity Breakdown</h4>
              <p>Total Findings: {caseDetail?.findings_summary?.total_findings || 0} • Flagged Amount: ₹{(caseDetail?.findings_summary?.total_flagged_amount || 0).toLocaleString("en-IN")}</p>
            </div>

            {/* Signature Block */}
            <div className="pt-8 grid grid-cols-2 gap-8 text-[11px] border-t border-border mt-4">
              <div className="space-y-8">
                <p className="text-muted-foreground">Auditor Signature</p>
                <div className="border-t border-border pt-1">
                  <p className="font-semibold">{auditCase.lead_auditor_name || "Lead Auditor"}</p>
                  <p className="text-muted-foreground">Auditor-in-Charge</p>
                </div>
              </div>
              <div className="space-y-8">
                <p className="text-muted-foreground">Reviewing Officer Signature</p>
                <div className="border-t border-border pt-1">
                  <p className="font-semibold">Audit Officer</p>
                  <p className="text-muted-foreground">State Audit Directorate</p>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter className="print:hidden">
            <Button variant="outline" size="sm" onClick={() => setIsPrintModalOpen(false)}>
              Close
            </Button>
            <Button size="sm" onClick={() => window.print()}>
              Print Document
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Upload Document Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        caseId={auditCase.id}
        onUploadSuccess={() => loadCaseData(false)}
      />

      {/* Report Generation Modal */}
      <ReportGenerateModal
        isOpen={isGenerateReportModalOpen}
        onClose={() => setIsGenerateReportModalOpen(false)}
        caseId={auditCase.id}
        caseNumber={auditCase.case_number}
        caseTitle={auditCase.title}
        onGenerated={() => loadCaseReports()}
      />

      {/* Report Preview Modal */}
      {selectedPreviewReport && (
        <ReportPreviewModal
          isOpen={!!selectedPreviewReport}
          onClose={() => setSelectedPreviewReport(null)}
          reportId={selectedPreviewReport.id}
          reportNumber={selectedPreviewReport.report_number}
          versionNumber={selectedPreviewReport.current_version}
          reportTitle={selectedPreviewReport.report_title}
          onDownload={() => {
            window.open(`${API_BASE}/reports/${selectedPreviewReport.id}/download`, "_blank");
          }}
        />
      )}

      {/* Report Approve Modal */}
      {selectedApproveReport && (
        <ReportApproveModal
          isOpen={!!selectedApproveReport}
          onClose={() => setSelectedApproveReport(null)}
          reportId={selectedApproveReport.id}
          reportNumber={selectedApproveReport.report_number}
          onApproved={() => loadCaseReports()}
        />
      )}
    </div>
  );
};

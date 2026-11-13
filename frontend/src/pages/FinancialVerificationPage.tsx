import React, { useEffect, useState } from "react";
import {
  Play,
  RotateCw,
  Search,
  AlertTriangle,
  ShieldAlert,
  Building2,
  Layers,
  Sliders,
  Calendar,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { RiskScoreGauge } from "@/components/verification/RiskScoreGauge";
import { ReconciliationMatrix } from "@/components/verification/ReconciliationMatrix";
import { RuleSummaryGrid } from "@/components/verification/RuleSummaryGrid";
import { VendorConcentrationCard } from "@/components/verification/VendorConcentrationCard";
import { FindingDetailDrawer } from "@/components/verification/FindingDetailDrawer";
import { VerificationHistoryTable } from "@/components/verification/VerificationHistoryTable";
import {
  AuditCase,
  CaseVerificationSummary,
  Finding,
  RuleRunItem
} from "@/types";
import { apiClient } from "@/lib/api";

export const FinancialVerificationPage: React.FC = () => {
  const [cases, setCases] = useState<AuditCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [summary, setSummary] = useState<CaseVerificationSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [ruleRuns, setRuleRuns] = useState<RuleRunItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyProgress, setVerifyProgress] = useState<number>(0);
  const [verifyMessage, setVerifyMessage] = useState<string | null>(null);

  // Active workspace tab
  const [activeTab, setActiveTab] = useState<"findings" | "reconciliation" | "rules" | "vendors" | "history">("findings");

  // Findings table filters
  const [selectedRuleFilter, setSelectedRuleFilter] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Slide-over finding detail drawer
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  // Load audit cases
  useEffect(() => {
    async function loadCases() {
      try {
        const data = await apiClient<AuditCase[]>("/cases");
        setCases(data);
        if (data.length > 0) {
          // Default to CAS-2024-MYS-002 or first case
          const defaultCase = data.find((c) => c.case_number === "CAS-2024-MYS-002") || data[0];
          setSelectedCaseId(defaultCase.id);
        }
      } catch (err) {
        console.error("Failed to load audit cases:", err);
      } finally {
        setLoading(false);
      }
    }
    loadCases();
  }, []);

  // Load case verification data when selectedCaseId changes
  useEffect(() => {
    if (!selectedCaseId) return;

    async function loadCaseData() {
      setLoading(true);
      try {
        const [sumRes, fndRes, runsRes] = await Promise.all([
          apiClient<CaseVerificationSummary>(`/cases/${selectedCaseId}/verification-summary`),
          apiClient<Finding[]>(`/cases/${selectedCaseId}/findings`),
          apiClient<RuleRunItem[]>(`/cases/${selectedCaseId}/rule-runs`),
        ]);
        setSummary(sumRes);
        setFindings(fndRes);
        setRuleRuns(runsRes);
      } catch (err) {
        console.error("Failed to load verification summary:", err);
      } finally {
        setLoading(false);
      }
    }

    loadCaseData();
  }, [selectedCaseId]);

  // Trigger verification runner
  const handleRunVerification = async () => {
    if (!selectedCaseId) return;
    setVerifying(true);
    setVerifyProgress(15);
    setVerifyMessage("Reconstructing Normalized Financial Records layer...");

    const progressTimer = setInterval(() => {
      setVerifyProgress((prev) => {
        if (prev < 40) {
          setVerifyMessage("Linking payment chains (Sanction → Work Order → Bill → Voucher → Bank)...");
          return prev + 15;
        } else if (prev < 80) {
          setVerifyMessage("Evaluating 16 Statutory Verification Rules & calculating risk score...");
          return prev + 20;
        }
        return prev;
      });
    }, 250);

    try {
      await apiClient<any>(`/cases/${selectedCaseId}/verify`, {
        method: "POST",
      });

      setVerifyProgress(100);
      setVerifyMessage("Verification complete! Refreshing active findings...");

      // Reload fresh data
      const [freshSummary, freshFindings, freshRuns] = await Promise.all([
        apiClient<CaseVerificationSummary>(`/cases/${selectedCaseId}/verification-summary`),
        apiClient<Finding[]>(`/cases/${selectedCaseId}/findings`),
        apiClient<RuleRunItem[]>(`/cases/${selectedCaseId}/rule-runs`),
      ]);
      setSummary(freshSummary);
      setFindings(freshFindings);
      setRuleRuns(freshRuns);
    } catch (err: any) {
      alert("Verification failed: " + (err.message || "Unknown error"));
    } finally {
      clearInterval(progressTimer);
      setTimeout(() => {
        setVerifying(false);
        setVerifyProgress(0);
        setVerifyMessage(null);
      }, 500);
    }
  };

  // Format currency
  const formatCurrency = (amt?: number | null) => {
    if (amt === undefined || amt === null) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amt);
  };

  const selectedCase = cases.find((c) => c.id === selectedCaseId);

  // Filter findings
  const filteredFindings = findings.filter((f) => {
    if (selectedRuleFilter && f.rule_id !== selectedRuleFilter) return false;
    if (severityFilter !== "all" && f.risk_level !== severityFilter) return false;
    if (statusFilter !== "all" && f.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchNum = f.finding_number.toLowerCase().includes(q);
      const matchTitle = f.title.toLowerCase().includes(q);
      const matchDesc = f.description.toLowerCase().includes(q);
      const matchRule = f.rule_id.toLowerCase().includes(q);
      return matchNum || matchTitle || matchDesc || matchRule;
    }
    return true;
  });

  const totalAmountAtRisk = findings
    .filter((f) => f.status !== "Dismissed" && !f.status.startsWith("Auto-resolved"))
    .reduce((sum, f) => sum + (f.amount_at_risk || 0), 0);

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="Financial Verification & Rule Engine"
        description="Statutory audit verification workspace for Karnataka State Audit Department and Zilla Panchayat directorates."
      />

      {/* Case Selector and Action Ribbon */}
      <div className="bg-card border border-border rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-wrap">
          <label className="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-wider shrink-0">
            Audit Case:
          </label>
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            className="bg-background border border-input rounded-lg px-3 py-1.5 text-xs font-semibold text-foreground focus:outline-none focus:ring-2 focus:ring-ring max-w-xs"
          >
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.case_number} — {c.title.slice(0, 35)}...
              </option>
            ))}
          </select>

          {selectedCase && (
            <div className="flex items-center gap-2 text-xs flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full bg-muted text-foreground font-medium">
                {selectedCase.scheme_name || "Statutory Scheme"}
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-muted text-muted-foreground font-mono font-medium tabular-nums">
                FY {selectedCase.financial_year}
              </span>
              <RiskBadge level={selectedCase.risk_level} />
            </div>
          )}
        </div>

        {/* Verification Trigger Button */}
        <div className="flex items-center space-x-3">
          <Button
            onClick={handleRunVerification}
            disabled={verifying}
            size="sm"
          >
            {verifying ? (
              <>
                <RotateCw className="h-4 w-4 mr-1.5 animate-spin" />
                <span>Running Statutory Rules...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-1.5 fill-current" />
                <span>Run Verification</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Verification Live Progress Bar */}
      {verifying && (
        <div className="p-4 bg-accent/60 border border-primary/25 rounded-xl space-y-2 animate-in fade-in">
          <div className="flex items-center justify-between text-xs font-semibold text-primary">
            <span>{verifyMessage}</span>
            <span className="font-mono tabular-nums">{verifyProgress}%</span>
          </div>
          <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${verifyProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Loading state indicator */}
      {loading && !summary && (
        <div className="p-8 text-center text-xs text-muted-foreground">
          Loading verification intelligence for selected audit case...
        </div>
      )}

      {/* Executive KPI Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Composite Risk Score"
            value={`${summary.risk_score.toFixed(1)} / 100`}
            description="Statutory 7-factor weighted calibration"
            tone={
              summary.risk_band === "critical" || summary.risk_band === "high"
                ? "danger"
                : summary.risk_band === "medium"
                ? "signal"
                : "emerald"
            }
          />
          <StatCard
            title="Active Findings"
            value={summary.active_findings_count}
            description={`Flagged for review • ${summary.total_findings} total (${summary.auto_resolved_count} cleared)`}
            tone="signal"
          />
          <StatCard
            title="Cumulative Amount at Risk"
            value={formatCurrency(totalAmountAtRisk)}
            description="Across active non-compliances & variances"
            tone="danger"
          />
          {(() => {
            const total = summary.reconciliation_matrix.length;
            const matched = summary.reconciliation_matrix.filter(
              (m) => m.status === "fully_matched"
            ).length;
            const rate = total > 0 ? Math.round((matched / total) * 100) : 100;
            return (
              <StatCard
                title="Reconciliation Rate"
                value={`${rate}%`}
                description={`Bill → Voucher → Bank (${matched}/${total} chains)`}
                tone="primary"
              />
            );
          })()}
        </div>
      )}

      {/* Risk Score Gauge Component */}
      {summary && (
        <RiskScoreGauge
          score={summary.risk_score}
          band={summary.risk_band}
          breakdown={summary.factor_breakdown}
        />
      )}

      {/* Main Workspace Navigation Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="findings" className="gap-2">
            <ShieldAlert className="h-4 w-4" />
            <span>Active Findings ({findings.length})</span>
          </TabsTrigger>
          <TabsTrigger value="reconciliation" className="gap-2">
            <Layers className="h-4 w-4" />
            <span>Reconciliation Matrix</span>
          </TabsTrigger>
          <TabsTrigger value="rules" className="gap-2">
            <Sliders className="h-4 w-4" />
            <span>16 Statutory Rules</span>
          </TabsTrigger>
          <TabsTrigger value="vendors" className="gap-2">
            <Building2 className="h-4 w-4" />
            <span>Vendor Exposure</span>
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-2">
            <Calendar className="h-4 w-4" />
            <span>Run History ({ruleRuns.length})</span>
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Tab 1: Findings Table */}
      {activeTab === "findings" && (
        <div className="space-y-4">
          {/* Findings Filter Bar */}
          <div className="bg-card border border-border rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="relative w-64">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter by title, number, or rule..."
                  className="w-full pl-8 pr-3 py-1.5 bg-background border border-input rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              {/* Severity filter */}
              <div className="flex items-center space-x-1.5">
                <span className="text-muted-foreground font-medium">Severity:</span>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-background border border-input rounded-lg px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              {/* Status filter */}
              <div className="flex items-center space-x-1.5">
                <span className="text-muted-foreground font-medium">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-background border border-input rounded-lg px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="all">All Statuses</option>
                  <option value="Open">Open</option>
                  <option value="Under Review">Under Review</option>
                  <option value="Confirmed">Confirmed</option>
                  <option value="Dismissed">Dismissed</option>
                  <option value="Escalated">Escalated</option>
                  <option value="Auto-resolved (condition no longer detected)">Auto-resolved</option>
                </select>
              </div>

              {selectedRuleFilter && (
                <div className="flex items-center space-x-1 px-2.5 py-1 bg-accent text-accent-foreground rounded-lg font-mono border border-primary/25">
                  <span>Rule: {selectedRuleFilter}</span>
                  <button
                    onClick={() => setSelectedRuleFilter(null)}
                    className="ml-1 hover:text-primary font-bold"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>

            <div className="text-muted-foreground font-mono tabular-nums text-[11px]">
              Showing {filteredFindings.length} of {findings.length} findings
            </div>
          </div>

          {/* Findings Table */}
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
                  <tr>
                    <th className="py-3 px-4">Finding ID</th>
                    <th className="py-3 px-3">Rule</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Observation Title</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4 text-right">Amount at Risk</th>
                    <th className="py-3 px-4">Review Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/70">
                  {filteredFindings.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-muted-foreground">
                        No findings match the selected filters.
                      </td>
                    </tr>
                  ) : (
                    filteredFindings.map((finding) => (
                      <tr
                        key={finding.id}
                        onClick={() => setSelectedFinding(finding)}
                        className="hover:bg-muted/40 cursor-pointer transition-colors"
                      >
                        <td className="py-3 px-4 font-mono font-semibold text-foreground">
                          {finding.finding_number}
                        </td>
                        <td className="py-3 px-3 font-mono text-muted-foreground font-semibold">
                          {finding.rule_id}
                        </td>
                        <td className="py-3 px-4">
                          <RiskBadge level={finding.risk_level} />
                        </td>
                        <td className="py-3 px-4 font-semibold text-foreground max-w-sm truncate">
                          {finding.title}
                          {finding.data_changed_since_review && (
                            <span className="ml-2 inline-flex items-center text-[10px] font-bold text-signal">
                              <AlertTriangle className="h-3 w-3 mr-0.5 inline" />
                              Data Modified
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 capitalize text-muted-foreground">
                          {finding.category}
                        </td>
                        <td className="py-3 px-4 text-right font-mono tabular-nums font-bold text-foreground">
                          {formatCurrency(finding.amount_at_risk)}
                        </td>
                        <td className="py-3 px-4">
                          <StatusPill status={finding.status} />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Reconciliation Matrix */}
      {activeTab === "reconciliation" && summary && (
        <ReconciliationMatrix items={summary.reconciliation_matrix} />
      )}

      {/* Tab 3: 16 Statutory Rules */}
      {activeTab === "rules" && summary && (
        <RuleSummaryGrid
          rules={summary.rules_summary}
          selectedRuleId={selectedRuleFilter}
          onSelectRule={(rId) => {
            setSelectedRuleFilter(rId);
            setActiveTab("findings");
          }}
        />
      )}

      {/* Tab 4: Vendor Concentration */}
      {activeTab === "vendors" && summary && (
        <VendorConcentrationCard
          vendors={summary.vendor_concentration}
          totalExpenditure={summary.total_expenditure}
        />
      )}

      {/* Tab 5: Run History */}
      {activeTab === "history" && (
        <VerificationHistoryTable runs={ruleRuns} />
      )}

      {/* Slide-over Finding Detail Drawer */}
      <FindingDetailDrawer
        finding={selectedFinding}
        onClose={() => setSelectedFinding(null)}
        onStatusUpdated={(updated) => {
          setSelectedFinding(updated);
          setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
        }}
      />
    </div>
  );
};

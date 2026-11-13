import React, { useEffect, useState, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Download,
  Users,
  MessageSquare,
  Bookmark,
} from "lucide-react";
import { toast } from "sonner";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { DataTable } from "@/components/shared/DataTable";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const FindingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  // Tab: "all" vs "pending_approval"
  const [activeTab, setActiveTab] = useState<"all" | "pending_approval">(
    searchParams.get("tab") === "pending_approval" ? "pending_approval" : "all"
  );

  // Findings list and summary state
  const [findings, setFindings] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>({
    by_status: {},
    by_risk: {},
    total_amount_at_risk: 0,
  });
  const [pendingApprovalQueue, setPendingApprovalQueue] = useState<any[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Saved Filters
  const [savedFilters, setSavedFilters] = useState<any[]>([]);
  const [isSaveFilterOpen, setIsSaveFilterOpen] = useState(false);
  const [newFilterName, setNewFilterName] = useState("");

  // Bulk Actions
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAssignOpen, setIsBulkAssignOpen] = useState(false);
  const [isBulkClarifyOpen, setIsBulkClarifyOpen] = useState(false);
  const [auditorList, setAuditorList] = useState<any[]>([]);
  const [selectedAuditorId, setSelectedAuditorId] = useState("");
  const [bulkClarifyComment, setBulkClarifyComment] = useState("");

  // Table options
  const [density, setDensity] = useState<"compact" | "standard" | "relaxed">("standard");
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>({
    rule_id: true,
    confidence: false,
  });

  // Filter values from URL
  const currentRisk = searchParams.get("risk") || "";
  const currentStatus = searchParams.get("status") || "";
  const currentFY = searchParams.get("fy") || "";
  const currentDistrict = searchParams.get("district") || "";
  const searchQuery = searchParams.get("search") || "";

  const isSeniorOrAbove = ["senior_auditor", "audit_officer", "administrator"].includes(
    user?.role?.code?.toLowerCase() || ""
  );

  // Fetch Findings
  const fetchFindings = async () => {
    setIsLoading(true);
    try {
      const qParams = new URLSearchParams();
      qParams.set("page", "1");
      qParams.set("page_size", "100");
      if (currentRisk) qParams.set("risk_level", currentRisk);
      if (currentStatus) qParams.set("status", currentStatus);
      if (currentFY) qParams.set("financial_year", currentFY);
      if (currentDistrict) qParams.set("district", currentDistrict);
      if (searchQuery) qParams.set("search", searchQuery);

      const data = await api.get<any>(`/findings?${qParams.toString()}`);
      setFindings(data.items || []);
      if (data.summary) {
        setSummary(data.summary);
      }

      // If senior or above, also fetch pending approval queue
      if (isSeniorOrAbove) {
        const pData = await api.get<any>("/findings/pending-approval");
        setPendingApprovalQueue(pData.items || []);
        setPendingCount(pData.count || 0);
      }
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to load findings.");
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch Saved Filters
  const fetchSavedFilters = async () => {
    try {
      const data = await api.get<any[]>("/filters/saved?entity_type=findings");
      setSavedFilters(data || []);
    } catch (e) {
      // ignore
    }
  };

  // Fetch Users for assignment
  const fetchAuditors = async () => {
    try {
      const data = await api.get<any[]>("/users");
      setAuditorList(data || []);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    fetchFindings();
    fetchSavedFilters();
    fetchAuditors();
  }, [currentRisk, currentStatus, currentFY, currentDistrict, searchQuery]);

  const updateFilters = (newParams: Record<string, string>) => {
    const params = new URLSearchParams(searchParams);
    Object.entries(newParams).forEach(([k, v]) => {
      if (v) params.set(k, v);
      else params.delete(k);
    });
    setSearchParams(params);
  };

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams(searchParams);
      window.open(`${API_BASE}/findings/export?${params.toString()}`, "_blank");
      toast.success("CSV export initiated. Recorded in audit trail.");
    } catch (err: any) {
      toast.error("CSV export failed.");
    }
  };

  const handleSaveFilter = async () => {
    if (!newFilterName.trim()) return;
    try {
      const filterState = {
        risk: currentRisk,
        status: currentStatus,
        fy: currentFY,
        district: currentDistrict,
        search: searchQuery,
      };
      await api.post("/filters/saved", {
        name: newFilterName.trim(),
        entity_type: "findings",
        filter_json: JSON.stringify(filterState),
      });
      toast.success("Filter saved.");
      setNewFilterName("");
      setIsSaveFilterOpen(false);
      fetchSavedFilters();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to save filter.");
    }
  };

  const handleApplySavedFilter = (sf: any) => {
    try {
      const parsed = JSON.parse(sf.filter_json);
      updateFilters(parsed);
      toast.info(`Applied filter: ${sf.name}`);
    } catch (e) {
      toast.error("Invalid saved filter.");
    }
  };

  const handleBulkAssign = async () => {
    if (!selectedAuditorId || selectedIds.length === 0) return;
    try {
      const res = await api.post<any>("/findings/bulk/assign", {
        finding_ids: selectedIds,
        assigned_auditor_id: selectedAuditorId,
      });
      toast.success(res.message);
      setIsBulkAssignOpen(false);
      setSelectedIds([]);
      fetchFindings();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Bulk assignment failed.");
    }
  };

  const handleBulkClarify = async () => {
    if (!bulkClarifyComment.trim() || selectedIds.length === 0) return;
    try {
      const res = await api.post<any>("/findings/bulk/clarify", {
        finding_ids: selectedIds,
        comment: bulkClarifyComment.trim(),
      });
      toast.success(res.message);
      setIsBulkClarifyOpen(false);
      setBulkClarifyComment("");
      setSelectedIds([]);
      fetchFindings();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Bulk clarification failed.");
    }
  };

  // TanStack columns
  const columns = useMemo(
    () => [
      {
        id: "select",
        header: () => (
          <input
            type="checkbox"
            checked={selectedIds.length === findings.length && findings.length > 0}
            onChange={(e) =>
              setSelectedIds(e.target.checked ? findings.map((f) => f.id) : [])
            }
            className="rounded accent-primary focus:ring-ring"
          />
        ),
        cell: ({ row }: any) => (
          <input
            type="checkbox"
            checked={selectedIds.includes(row.original.id)}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              e.stopPropagation();
              setSelectedIds((prev) =>
                e.target.checked
                  ? [...prev, row.original.id]
                  : prev.filter((id) => id !== row.original.id)
              );
            }}
            className="rounded accent-primary focus:ring-ring"
          />
        ),
      },
      {
        accessorKey: "finding_number",
        header: "Finding ID",
        cell: ({ row }: any) => (
          <span className="font-mono font-bold text-primary">
            {row.original.finding_number}
          </span>
        ),
      },
      {
        accessorKey: "case_number",
        header: "Case",
        cell: ({ row }: any) => (
          <div>
            <div className="font-mono text-xs font-semibold text-foreground">{row.original.case_number}</div>
            <div className="text-[11px] text-muted-foreground truncate max-w-[160px]">
              {row.original.case_title}
            </div>
          </div>
        ),
      },
      {
        accessorKey: "risk_level",
        header: "Risk",
        cell: ({ row }: any) => <RiskBadge level={row.original.risk_level} />,
      },
      ...(visibleColumns.rule_id
        ? [
            {
              accessorKey: "rule_code",
              header: "Rule",
              cell: ({ row }: any) => (
                <span className="font-mono text-xs text-muted-foreground">
                  {row.original.rule_code || row.original.rule_id}
                </span>
              ),
            },
          ]
        : []),
      ...(visibleColumns.confidence
        ? [
            {
              accessorKey: "confidence",
              header: "Confidence",
              cell: ({ row }: any) => (
                <span className="font-mono text-xs tabular-nums">{row.original.confidence}%</span>
              ),
            },
          ]
        : []),
      {
        accessorKey: "title",
        header: "Finding Title",
        cell: ({ row }: any) => (
          <div className="font-medium text-foreground max-w-[280px] line-clamp-1">
            {row.original.title}
          </div>
        ),
      },
      {
        accessorKey: "amount_at_risk",
        header: "Amount (₹)",
        cell: ({ row }: any) => (
          <span className="font-mono font-semibold tabular-nums">
            ₹{Number(row.original.amount_at_risk).toLocaleString("en-IN")}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }: any) => <StatusPill status={row.original.status} />,
      },
      {
        accessorKey: "assigned_auditor_name",
        header: "Assigned Auditor",
        cell: ({ row }: any) => (
          <span className="text-xs text-muted-foreground">
            {row.original.assigned_auditor_name || "Unassigned"}
          </span>
        ),
      },
    ],
    [findings, selectedIds, visibleColumns]
  );

  const selectCls =
    "h-9 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
  const modalInputCls =
    "w-full text-xs p-2 border border-input rounded-lg mt-1 bg-background text-foreground";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Findings Register"
        description="Statutory review workbench. Every anomaly is flagged for auditor review and dual-custody verification."
      >
        <Button
          size="sm"
          variant="outline"
          onClick={handleExportCSV}
          className="text-xs"
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Export CSV
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setIsSaveFilterOpen(true)}
          className="text-xs"
        >
          <Bookmark className="h-3.5 w-3.5 mr-1.5" />
          Save Current Filter
        </Button>
      </PageHeader>

      {/* Summary KPI Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard
          title="Total Open"
          value={summary.by_status?.Open || 0}
          description="Pending determination"
          className="cursor-pointer"
          onClick={() => updateFilters({ status: "Open" })}
        />
        <StatCard
          title="Pending Approval"
          value={summary.by_status?.["Pending Approval"] || 0}
          description="Maker-checker queue"
          className="cursor-pointer"
          tone="signal"
          onClick={() => {
            setActiveTab("pending_approval");
            updateFilters({ tab: "pending_approval" });
          }}
        />
        <StatCard
          title="Needs Clarification"
          value={summary.by_status?.["Needs Clarification"] || 0}
          description="Auditee inquiries"
          className="cursor-pointer"
          tone="signal"
          onClick={() => updateFilters({ status: "Needs Clarification" })}
        />
        <StatCard
          title="Confirmed"
          value={summary.by_status?.Confirmed || 0}
          description="Substantiated"
          className="cursor-pointer"
          tone="emerald"
          onClick={() => updateFilters({ status: "Confirmed" })}
        />
        <StatCard
          title="Critical Risk"
          value={summary.by_risk?.critical || 0}
          description="Statutory floor ≥85"
          className="cursor-pointer"
          tone="danger"
          onClick={() => updateFilters({ risk: "critical" })}
        />
        <StatCard
          title="High Risk"
          value={summary.by_risk?.high || 0}
          description="Requires senior signoff"
          className="cursor-pointer"
          tone="signal"
          onClick={() => updateFilters({ risk: "high" })}
        />
        <StatCard
          title="Total Exposure"
          value={`₹${(summary.total_amount_at_risk / 100000).toFixed(1)}L`}
          description="Cumulative amount"
        />
      </div>

      {/* Tab bar for Senior Auditor Approval Queue */}
      {isSeniorOrAbove && (
        <div className="inline-flex rounded-xl border border-border bg-muted p-1 text-xs">
          <button
            onClick={() => {
              setActiveTab("all");
              updateFilters({ tab: "" });
            }}
            className={`rounded-lg px-3 py-1.5 font-semibold transition ${
              activeTab === "all"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All Registered Findings ({findings.length})
          </button>
          <button
            onClick={() => {
              setActiveTab("pending_approval");
              updateFilters({ tab: "pending_approval" });
            }}
            className={`rounded-lg px-3 py-1.5 font-semibold transition flex items-center gap-1.5 ${
              activeTab === "pending_approval"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span>Maker-Checker Approval Queue</span>
            {pendingCount > 0 && (
              <span className="bg-amber-600 text-white rounded-full px-2 py-0.2 text-[10px] font-bold font-mono tabular-nums">
                {pendingCount}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Filter Bar & Saved Filter Chips */}
      <div className="bg-card p-3.5 rounded-2xl border border-border space-y-3 shadow-sm">
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            type="text"
            placeholder="Search finding ID, title, or case..."
            value={searchQuery}
            onChange={(e) => updateFilters({ search: e.target.value })}
            className="text-xs h-9 px-3 border border-input rounded-lg bg-background text-foreground w-64 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />

          <select
            value={currentRisk}
            onChange={(e) => updateFilters({ risk: e.target.value })}
            className={selectCls}
          >
            <option value="">All Risk Bands</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            value={currentStatus}
            onChange={(e) => updateFilters({ status: e.target.value })}
            className={selectCls}
          >
            <option value="">All Statuses</option>
            <option value="Open">Open</option>
            <option value="Pending Approval">Pending Approval</option>
            <option value="Needs Clarification">Needs Clarification</option>
            <option value="Confirmed">Confirmed</option>
            <option value="Dismissed">Dismissed</option>
            <option value="Escalated">Escalated</option>
            <option value="Auto-resolved">Auto-resolved</option>
          </select>

          <select
            value={currentDistrict}
            onChange={(e) => updateFilters({ district: e.target.value })}
            className={selectCls}
          >
            <option value="">All Districts</option>
            <option value="Mysuru">Mysuru</option>
            <option value="Belagavi">Belagavi</option>
            <option value="Dharwad">Dharwad</option>
            <option value="Tumakuru">Tumakuru</option>
            <option value="Kalaburagi">Kalaburagi</option>
          </select>

          {(currentRisk || currentStatus || currentDistrict || searchQuery) && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => updateFilters({ risk: "", status: "", district: "", search: "" })}
              className="text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700"
            >
              Clear Filters
            </Button>
          )}

          {/* Density & Column Visibility Toggles */}
          <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <span>Columns:</span>
              <button
                onClick={() =>
                  setVisibleColumns((prev) => ({ ...prev, rule_id: !prev.rule_id }))
                }
                className={`px-2 py-0.5 rounded text-[11px] font-mono border border-border ${
                  visibleColumns.rule_id
                    ? "bg-muted text-foreground font-bold"
                    : "opacity-60"
                }`}
              >
                Rule
              </button>
              <button
                onClick={() =>
                  setVisibleColumns((prev) => ({ ...prev, confidence: !prev.confidence }))
                }
                className={`px-2 py-0.5 rounded text-[11px] font-mono border border-border ${
                  visibleColumns.confidence
                    ? "bg-muted text-foreground font-bold"
                    : "opacity-60"
                }`}
              >
                Confidence
              </button>
            </div>
            <div className="flex items-center gap-1">
              <span>Density:</span>
              {(["compact", "standard", "relaxed"] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setDensity(d)}
                  className={`px-2 py-0.5 rounded capitalize ${
                    density === d
                      ? "bg-accent text-accent-foreground font-bold"
                      : "hover:bg-muted"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Saved Filter Chips */}
        {savedFilters.length > 0 && (
          <div className="flex items-center gap-2 pt-1 overflow-x-auto text-xs">
            <span className="text-[11px] font-semibold text-muted-foreground shrink-0">Saved Presets:</span>
            {savedFilters.map((sf) => (
              <button
                key={sf.id}
                onClick={() => handleApplySavedFilter(sf)}
                className="px-2.5 py-1 rounded-full bg-muted hover:bg-accent text-foreground border border-border text-[11px] shrink-0 font-medium transition-colors"
              >
                {sf.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Bulk Action Bar when items selected */}
      {selectedIds.length > 0 && (
        <div className="flex items-center justify-between p-3 bg-accent/70 border border-primary/25 rounded-xl text-xs">
          <span className="font-semibold text-accent-foreground">
            {selectedIds.length} findings selected
          </span>
          <div className="flex items-center gap-2">
            {isSeniorOrAbove && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsBulkAssignOpen(true)}
                className="text-xs bg-card"
              >
                <Users className="h-3.5 w-3.5 mr-1" />
                Bulk Assign to Auditor
              </Button>
            )}
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsBulkClarifyOpen(true)}
              className="text-xs bg-card border-signal-border text-signal"
            >
              <MessageSquare className="h-3.5 w-3.5 mr-1" />
              Request Clarification
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setSelectedIds([])}
              className="text-xs text-muted-foreground"
            >
              Deselect All
            </Button>
          </div>
        </div>
      )}

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={activeTab === "pending_approval" ? pendingApprovalQueue : findings}
        isLoading={isLoading}
        onRowClick={(row) => navigate(`/findings/${row.id}`)}
        emptyMessage={
          activeTab === "pending_approval"
            ? "No findings currently pending maker-checker dual approval."
            : "No findings match the current filter criteria."
        }
      />

      {/* Save Filter Modal */}
      <Dialog open={isSaveFilterOpen} onOpenChange={setIsSaveFilterOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold font-display">Save Current Filter Preset</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs font-semibold text-foreground">
              Preset Name
            </label>
            <input
              type="text"
              placeholder="e.g. Mysuru High Risk Open"
              value={newFilterName}
              onChange={(e) => setNewFilterName(e.target.value)}
              className={modalInputCls}
            />
          </div>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setIsSaveFilterOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSaveFilter}>
              Save Preset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Assign Modal */}
      <Dialog open={isBulkAssignOpen} onOpenChange={setIsBulkAssignOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold font-display">
              Bulk Assign {selectedIds.length} Findings
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs font-semibold text-foreground">
              Select Auditor
            </label>
            <select
              value={selectedAuditorId}
              onChange={(e) => setSelectedAuditorId(e.target.value)}
              className={modalInputCls}
            >
              <option value="">Select Auditor...</option>
              {auditorList.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.full_name} ({a.role?.name || "Auditor"})
                </option>
              ))}
            </select>
          </div>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setIsBulkAssignOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleBulkAssign}>
              Assign Findings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Clarify Modal */}
      <Dialog open={isBulkClarifyOpen} onOpenChange={setIsBulkClarifyOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold font-display">
              Request Clarification for {selectedIds.length} Findings
            </DialogTitle>
          </DialogHeader>
          <div className="py-2 space-y-1">
            <label className="text-xs font-semibold text-foreground">
              Audit Inquiry / Clarification Question <span className="text-rose-500">*</span>
            </label>
            <textarea
              value={bulkClarifyComment}
              onChange={(e) => setBulkClarifyComment(e.target.value)}
              placeholder="State the missing information or verification required..."
              rows={3}
              className={modalInputCls}
            />
          </div>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setIsBulkClarifyOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={bulkClarifyComment.trim().length < 5}
              onClick={handleBulkClarify}
              className="bg-amber-600 hover:bg-amber-700 text-white"
            >
              Send Requests
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

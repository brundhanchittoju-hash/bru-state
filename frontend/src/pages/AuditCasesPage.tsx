import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ColumnDef } from "@tanstack/react-table";
import { Plus, Briefcase, ArrowRight, LayoutGrid, List } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { FilterBar } from "@/components/shared/FilterBar";
import { DataTable } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AuditCase } from "@/types";
import { api } from "@/lib/api";
import { toast } from "sonner";

const CASE_STATUS_COLUMNS = [
  { key: "draft", label: "Draft" },
  { key: "documents_uploaded", label: "Documents Uploaded" },
  { key: "processing", label: "Processing" },
  { key: "verification", label: "Verification" },
  { key: "review", label: "Review" },
  { key: "approved", label: "Approved" },
  { key: "closed", label: "Closed" },
];

export const AuditCasesPage: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<AuditCase[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<"table" | "board">("table");

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [districtFilter, setDistrictFilter] = useState<string>("");
  const [schemeFilter, setSchemeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Create Case Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [newTitle, setNewTitle] = useState<string>("");
  const [newDistrict, setNewDistrict] = useState<string>("Mysuru");
  const [newTaluk, setNewTaluk] = useState<string>("");
  const [newGramPanchayat, setNewGramPanchayat] = useState<string>("");
  const [newScheme, setNewScheme] = useState<string>("MGNREGA");
  const [newFinancialYear, setNewFinancialYear] = useState<string>("2024-25");
  const [newAuditType, setNewAuditType] = useState<string>("Statutory");
  const [newPriority, setNewPriority] = useState<string>("medium");
  const [newEstimatedCost, setNewEstimatedCost] = useState<string>("");
  const [newRemarks, setNewRemarks] = useState<string>("");

  const loadCases = async () => {
    setIsLoading(true);
    try {
      const url = "/cases?";
      const params = new URLSearchParams();
      if (searchQuery) params.append("search", searchQuery);
      if (districtFilter) params.append("district", districtFilter);
      if (schemeFilter) params.append("scheme", schemeFilter);
      if (statusFilter) params.append("status", statusFilter);

      const res = await api.get<AuditCase[]>(url + params.toString());
      setCases(res);
    } catch {
      toast.error("Failed to load audit cases.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [searchQuery, districtFilter, schemeFilter, statusFilter]);

  const handleCreateCase = async () => {
    if (!newTitle.trim()) {
      toast.error("Case title is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        title: newTitle.trim(),
        district: newDistrict,
        taluk: newTaluk.trim() || undefined,
        gram_panchayat: newGramPanchayat.trim() || undefined,
        scheme_name: newScheme,
        financial_year: newFinancialYear,
        audit_type: newAuditType,
        priority: newPriority,
        estimated_cost: newEstimatedCost ? parseFloat(newEstimatedCost) : undefined,
        remarks: newRemarks.trim() || undefined,
      };

      const res = await api.post<AuditCase>("/cases", payload);
      toast.success(`Audit Case ${res.case_number} initiated successfully.`);
      setIsCreateModalOpen(false);
      resetForm();
      loadCases();
      navigate(`/cases/${res.id}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to create audit case.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setNewTitle("");
    setNewDistrict("Mysuru");
    setNewTaluk("");
    setNewGramPanchayat("");
    setNewScheme("MGNREGA");
    setNewFinancialYear("2024-25");
    setNewAuditType("Statutory");
    setNewPriority("medium");
    setNewEstimatedCost("");
    setNewRemarks("");
  };

  const resetFilters = () => {
    setSearchQuery("");
    setDistrictFilter("");
    setSchemeFilter("");
    setStatusFilter("");
  };

  const columns: ColumnDef<AuditCase>[] = [
    {
      accessorKey: "case_number",
      header: "Case ID",
      cell: ({ row }) => (
        <span className="font-mono text-xs font-semibold text-primary">
          {row.getValue("case_number")}
        </span>
      ),
    },
    {
      accessorKey: "title",
      header: "Audit Title & Local Body",
      cell: ({ row }) => (
        <div className="space-y-0.5 max-w-md">
          <p className="font-medium text-foreground text-xs">
            {row.getValue("title")}
          </p>
          <p className="text-[11px] text-muted-foreground">
            {row.original.gram_panchayat ? `${row.original.gram_panchayat} GP • ` : ""}
            {row.original.taluk ? `${row.original.taluk} Taluk • ` : ""}
            {row.original.district || "Karnataka"}
          </p>
        </div>
      ),
    },
    {
      accessorKey: "scheme_name",
      header: "Scheme & FY",
      cell: ({ row }) => (
        <div className="text-xs space-y-0.5">
          <Badge variant="outline" className="text-[11px]">
            {row.original.scheme_name || "General"}
          </Badge>
          <p className="text-[11px] text-muted-foreground font-mono">{row.original.financial_year}</p>
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusPill status={row.getValue("status")} />,
    },
    {
      accessorKey: "risk_level",
      header: "Risk Level",
      cell: ({ row }) => <RiskBadge level={row.getValue("risk_level") || "low"} />,
    },
    {
      accessorKey: "document_count",
      header: "Documents",
      cell: ({ row }) => (
        <span className="font-mono text-xs font-medium text-muted-foreground tabular-nums">
          {row.original.document_count || 0} files
        </span>
      ),
    },
    {
      id: "actions",
      header: "Action",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/cases/${row.original.id}`);
          }}
          className="h-7 text-xs text-primary hover:text-primary"
        >
          View Case
          <ArrowRight className="h-3 w-3 ml-1" />
        </Button>
      ),
    },
  ];

  const selectCls =
    "h-9 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
  const modalInputCls =
    "w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="space-y-5">
      <PageHeader
        title="Audit Case Management"
        description="Statutory audit engagements across Karnataka Panchayati Raj institutions (Zilla, Taluk, and Gram Panchayats)."
        badge={
          <Badge variant="secondary" className="font-mono text-[11px] tabular-nums">
            {cases.length} cases
          </Badge>
        }
      >
        <div className="inline-flex rounded-lg border border-border bg-muted p-0.5">
          <button
            type="button"
            onClick={() => setViewMode("table")}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "table"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <List className="h-3.5 w-3.5" />
            Table
          </button>
          <button
            type="button"
            onClick={() => setViewMode("board")}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              viewMode === "board"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Board
          </button>
        </div>

        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-1.5" />
          New Audit Case
        </Button>
      </PageHeader>

      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Search case #, title, or project..."
        onReset={searchQuery || districtFilter || schemeFilter || statusFilter ? resetFilters : undefined}
      >
        <select
          value={districtFilter}
          onChange={(e) => setDistrictFilter(e.target.value)}
          className={selectCls}
          aria-label="Filter by district"
        >
          <option value="">All Districts</option>
          <option value="Mysuru">Mysuru</option>
          <option value="Mandya">Mandya</option>
          <option value="Bengaluru Rural">Bengaluru Rural</option>
          <option value="Belagavi">Belagavi</option>
          <option value="Kalaburagi">Kalaburagi</option>
          <option value="Dharwad">Dharwad</option>
        </select>

        <select
          value={schemeFilter}
          onChange={(e) => setSchemeFilter(e.target.value)}
          className={selectCls}
          aria-label="Filter by scheme"
        >
          <option value="">All Schemes</option>
          <option value="MGNREGA">MGNREGA</option>
          <option value="15th Finance Commission">15th Finance Commission</option>
          <option value="Jal Jeevan Mission">Jal Jeevan Mission</option>
          <option value="PMAY-G">PMAY-G</option>
          <option value="Swachh Bharat Mission">Swachh Bharat Mission</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={selectCls}
          aria-label="Filter by status"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="documents_uploaded">Documents Uploaded</option>
          <option value="processing">Processing</option>
          <option value="verification">Verification</option>
          <option value="review">Review</option>
          <option value="approved">Approved</option>
          <option value="closed">Closed</option>
        </select>
      </FilterBar>

      {viewMode === "table" ? (
        <DataTable
          columns={columns}
          data={cases}
          isLoading={isLoading}
          emptyMessage="No audit cases found matching current filters."
          onRowClick={(c: AuditCase) => navigate(`/cases/${c.id}`)}
        />
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {CASE_STATUS_COLUMNS.map((col) => {
            const colCases = cases.filter(
              (c) => (c.status || "draft").toLowerCase() === col.key
            );
            return (
              <div
                key={col.key}
                className="flex w-[260px] shrink-0 flex-col rounded-xl border border-border bg-muted/40 p-2.5"
              >
                <div className="mb-2 flex items-center justify-between px-1">
                  <span className="text-xs font-semibold text-foreground">{col.label}</span>
                  <Badge variant="secondary" className="font-mono text-[10px] tabular-nums">
                    {colCases.length}
                  </Badge>
                </div>
                <div className="space-y-2">
                  {colCases.length === 0 ? (
                    <div className="rounded-lg border border-dashed border-border py-6 text-center text-[11px] text-muted-foreground">
                      No cases
                    </div>
                  ) : (
                    colCases.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => navigate(`/cases/${c.id}`)}
                        className="w-full rounded-lg border border-border bg-card p-3 text-left shadow-sm transition-all hover:border-primary/50 hover:shadow"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-[11px] font-semibold text-primary">
                            {c.case_number}
                          </span>
                          <RiskBadge level={c.risk_level || "low"} />
                        </div>
                        <p className="mt-1.5 line-clamp-2 text-xs font-medium text-foreground">
                          {c.title}
                        </p>
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {c.district || "Karnataka"} • {c.financial_year}
                        </p>
                      </button>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Case Modal Dialog */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-display">
              <Briefcase className="h-5 w-5 text-primary" />
              <span>Initiate Statutory Audit Case</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                Audit Engagement Title *
              </label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="e.g. Mandya ZP Water Infrastructure Audit FY 2024-25"
                className={`${modalInputCls} font-medium`}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-foreground">District *</label>
                <select
                  value={newDistrict}
                  onChange={(e) => setNewDistrict(e.target.value)}
                  className={modalInputCls}
                >
                  <option value="Mysuru">Mysuru</option>
                  <option value="Mandya">Mandya</option>
                  <option value="Bengaluru Rural">Bengaluru Rural</option>
                  <option value="Belagavi">Belagavi</option>
                  <option value="Kalaburagi">Kalaburagi</option>
                  <option value="Dharwad">Dharwad</option>
                  <option value="Ballari">Ballari</option>
                  <option value="Hassan">Hassan</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Taluk</label>
                <input
                  type="text"
                  value={newTaluk}
                  onChange={(e) => setNewTaluk(e.target.value)}
                  placeholder="e.g. Hunsur"
                  className={modalInputCls}
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Gram Panchayat</label>
                <input
                  type="text"
                  value={newGramPanchayat}
                  onChange={(e) => setNewGramPanchayat(e.target.value)}
                  placeholder="e.g. Bilikere"
                  className={modalInputCls}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-foreground">Scheme *</label>
                <select
                  value={newScheme}
                  onChange={(e) => setNewScheme(e.target.value)}
                  className={modalInputCls}
                >
                  <option value="MGNREGA">MGNREGA</option>
                  <option value="15th Finance Commission">15th Finance Commission</option>
                  <option value="Jal Jeevan Mission">Jal Jeevan Mission</option>
                  <option value="PMAY-G">PMAY-G</option>
                  <option value="Swachh Bharat Mission">Swachh Bharat Mission</option>
                  <option value="Gram Swaraj">Gram Swaraj</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Financial Year *</label>
                <select
                  value={newFinancialYear}
                  onChange={(e) => setNewFinancialYear(e.target.value)}
                  className={`${modalInputCls} font-mono`}
                >
                  <option value="2024-25">2024-25</option>
                  <option value="2023-24">2023-24</option>
                  <option value="2022-23">2022-23</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className={modalInputCls}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                Estimated Scheme Outlay (₹)
              </label>
              <input
                type="number"
                value={newEstimatedCost}
                onChange={(e) => setNewEstimatedCost(e.target.value)}
                placeholder="e.g. 5000000"
                className={`${modalInputCls} font-mono`}
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">Audit Scope & Remarks</label>
              <textarea
                rows={2}
                value={newRemarks}
                onChange={(e) => setNewRemarks(e.target.value)}
                placeholder="Statutory compliance review of untied grant expenditures and muster rolls..."
                className={modalInputCls}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateCase}
              disabled={isSubmitting || !newTitle.trim()}
            >
              {isSubmitting ? "Creating..." : "Create Audit Case"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

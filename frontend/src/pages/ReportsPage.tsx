import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Copy,
  Download,
  Eye,
  FileCheck2,
  FileText,
  Lock,
  QrCode,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { ColumnDef } from "@tanstack/react-table";
import { PageHeader } from "@/components/shared/PageHeader";
import { StatCard } from "@/components/shared/StatCard";
import { FilterBar } from "@/components/shared/FilterBar";
import { DataTable } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { API_BASE, getAccessToken } from "@/lib/api";
import { ReportPreviewModal } from "@/components/reporting/ReportPreviewModal";
import { ReportApproveModal } from "@/components/reporting/ReportApproveModal";

interface ReportItem {
  id: string;
  report_number: string;
  report_title: string;
  report_type: string;
  current_version: number;
  status: string;
  case_id: string;
  case_number: string;
  case_title: string;
  department: string;
  district: string;
  financial_year: string;
  generated_by_name: string;
  approved_by_name: string | null;
  approved_at: string | null;
  page_count: number;
  pdf_sha256: string;
  created_at: string;
}

export const ReportsPage: React.FC = () => {
  const { user } = useAuth();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [summary, setSummary] = useState({ Draft: 0, Approved: 0, Final: 0, Superseded: 0 });

  // Filters
  const [financialYear, setFinancialYear] = useState("");
  const [district, setDistrict] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Modals state
  const [previewReport, setPreviewReport] = useState<ReportItem | null>(null);
  const [approveReport, setApproveReport] = useState<ReportItem | null>(null);
  const [qrModalReport, setQrModalReport] = useState<ReportItem | null>(null);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const token = getAccessToken();
      const params = new URLSearchParams();
      if (financialYear) params.append("financial_year", financialYear);
      if (district) params.append("district", district);
      if (statusFilter) params.append("status", statusFilter);
      if (search) params.append("search", search);
      params.append("page", page.toString());
      params.append("page_size", "15");

      const res = await fetch(`${API_BASE}/reports?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setReports(data.items || []);
        setTotal(data.total || 0);
        if (data.status_summary) {
          setSummary(data.status_summary);
        }
      }
    } catch {
      toast.error("Failed to load statutory reports.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [financialYear, district, statusFilter, search, page]);

  const handleDownload = async (report: ReportItem) => {
    try {
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/reports/${report.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Report_${report.report_number}_v${report.current_version}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Downloaded ${report.report_number}`);
    } catch {
      toast.error("Failed to download report PDF.");
    }
  };

  const copyVerifyLink = (report: ReportItem) => {
    const url = `${window.location.origin}/verify/${report.report_number}?v=${report.current_version}`;
    navigator.clipboard.writeText(url);
    toast.success("Public verification URL copied to clipboard!");
  };

  const columns: ColumnDef<ReportItem, any>[] = [
    {
      id: "report_number",
      header: "Report ID",
      accessorKey: "report_number",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-mono text-xs font-semibold text-primary">
            {row.original.report_number}
          </span>
          <span className="text-[11px] text-muted-foreground capitalize font-mono tabular-nums">
            {row.original.report_type} • v{row.original.current_version}
          </span>
        </div>
      ),
    },
    {
      id: "case_particulars",
      header: "Case Particulars",
      accessorKey: "case_number",
      cell: ({ row }) => (
        <div className="flex flex-col max-w-xs">
          <span className="font-medium text-xs text-foreground truncate">
            {row.original.case_title || row.original.report_title}
          </span>
          <span className="font-mono text-[11px] text-muted-foreground">
            {row.original.case_number} • {row.original.district}
          </span>
        </div>
      ),
    },
    {
      id: "department",
      header: "Department / FY",
      accessorKey: "department",
      cell: ({ row }) => (
        <div className="flex flex-col text-xs text-muted-foreground">
          <span className="truncate max-w-[180px] text-foreground/90">{row.original.department}</span>
          <span className="text-[11px] font-mono tabular-nums text-muted-foreground">FY {row.original.financial_year}</span>
        </div>
      ),
    },
    {
      id: "status",
      header: "Status",
      accessorKey: "status",
      cell: ({ row }) => <StatusPill status={row.original.status} />,
    },
    {
      id: "audit_team",
      header: "Audit Team & Sign-off",
      accessorKey: "generated_by_name",
      cell: ({ row }) => (
        <div className="flex flex-col text-xs">
          <span className="text-foreground/90">By: {row.original.generated_by_name}</span>
          <span className="text-[11px] text-muted-foreground">
            {row.original.approved_by_name ? `Approved: ${row.original.approved_by_name}` : "Pending Dual Custody"}
          </span>
        </div>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => {
        const item = row.original;
        const canApprove =
          ["senior_auditor", "audit_officer", "administrator"].includes(user?.role?.code || "") &&
          item.status !== "Approved" &&
          item.generated_by_name !== user?.full_name;

        return (
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPreviewReport(item)}
              className="h-7 text-xs px-2 gap-1"
              title="Preview PDF"
            >
              <Eye className="h-3 w-3" />
              Preview
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleDownload(item)}
              className="h-7 w-7 p-0"
              title="Download PDF"
            >
              <Download className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setQrModalReport(item)}
              className="h-7 w-7 p-0"
              title="QR & Public Verification Seal"
            >
              <QrCode className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            {canApprove && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setApproveReport(item)}
                className="h-7 text-xs px-2 gap-1 border-primary/40 text-primary hover:bg-accent"
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                Sign
              </Button>
            )}
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Statutory Audit Reports"
        description="Official audit paras, compliance certifications, and tamper-evident PDF reports sealed with SHA-256 and QR verification."
      />

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Reports"
          value={total}
          icon={<FileText className="h-4 w-4 text-primary" />}
          description="Generated audit reports"
          tone="primary"
        />
        <StatCard
          title="Statutory Approved"
          value={summary.Approved || 0}
          icon={<CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />}
          description="Signed via dual-custody"
          tone="emerald"
        />
        <StatCard
          title="Final Reports"
          value={summary.Final || 0}
          icon={<FileCheck2 className="h-4 w-4 text-primary" />}
          description="Pre-requisites satisfied"
          tone="primary"
        />
        <StatCard
          title="Draft Revisions"
          value={summary.Draft || 0}
          icon={<Lock className="h-4 w-4 text-signal" />}
          description="Under auditor review"
          tone="signal"
        />
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchQuery={search}
        onSearchChange={setSearch}
        placeholder="Filter by report ID, case number, or title..."
        onReset={() => {
          setFinancialYear("");
          setDistrict("");
          setStatusFilter("");
          setSearch("");
          setPage(1);
        }}
      >
        <select
          value={financialYear}
          onChange={(e) => setFinancialYear(e.target.value)}
          className="h-9 text-xs rounded-lg border border-input bg-background px-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All Financial Years</option>
          <option value="2024-25">2024-25</option>
          <option value="2023-24">2023-24</option>
        </select>

        <select
          value={district}
          onChange={(e) => setDistrict(e.target.value)}
          className="h-9 text-xs rounded-lg border border-input bg-background px-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All Districts</option>
          <option value="Mysuru">Mysuru</option>
          <option value="Belagavi">Belagavi</option>
          <option value="Dharwad">Dharwad</option>
          <option value="Tumakuru">Tumakuru</option>
          <option value="Kalaburagi">Kalaburagi</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-9 text-xs rounded-lg border border-input bg-background px-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">All Statuses</option>
          <option value="Draft">Draft</option>
          <option value="Approved">Approved</option>
          <option value="Final">Final</option>
          <option value="Superseded">Superseded</option>
        </select>
      </FilterBar>

      {/* Reports Table */}
      <DataTable
        columns={columns}
        data={reports}
        isLoading={isLoading}
        emptyMessage="No statutory audit reports found matching current filters."
      />

      {/* Preview Modal */}
      {previewReport && (
        <ReportPreviewModal
          isOpen={!!previewReport}
          onClose={() => setPreviewReport(null)}
          reportId={previewReport.id}
          reportNumber={previewReport.report_number}
          versionNumber={previewReport.current_version}
          reportTitle={previewReport.report_title}
          onDownload={() => handleDownload(previewReport)}
        />
      )}

      {/* Approve Modal */}
      {approveReport && (
        <ReportApproveModal
          isOpen={!!approveReport}
          onClose={() => setApproveReport(null)}
          reportId={approveReport.id}
          reportNumber={approveReport.report_number}
          onApproved={() => fetchReports()}
        />
      )}

      {/* QR & Public Link Dialog */}
      {qrModalReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md bg-card rounded-2xl shadow-2xl border border-border p-6 space-y-5">
            <div className="text-center space-y-2">
              <div className="h-12 w-12 rounded-2xl bg-accent text-primary flex items-center justify-center mx-auto border border-primary/20">
                <QrCode className="h-6 w-6" />
              </div>
              <h3 className="font-display text-base font-semibold text-foreground">
                Public Verification Seal
              </h3>
              <p className="text-xs text-muted-foreground font-mono tabular-nums">
                {qrModalReport.report_number} • Version {qrModalReport.current_version}
              </p>
            </div>

            <div className="p-3 bg-muted/40 rounded-xl space-y-2 text-xs border border-border">
              <span className="font-semibold text-foreground block">
                Public Verification Link:
              </span>
              <div className="p-2 bg-card rounded-lg border border-border text-muted-foreground break-all font-mono text-[11px]">
                {window.location.origin}/verify/{qrModalReport.report_number}?v=
                {qrModalReport.current_version}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyVerifyLink(qrModalReport)}
                className="w-full text-xs gap-1.5"
              >
                <Copy className="h-3.5 w-3.5" />
                Copy Verification Link
              </Button>
            </div>

            <div className="space-y-1 text-xs">
              <span className="font-semibold text-foreground">
                SHA-256 Checksum:
              </span>
              <p className="font-mono text-[10px] p-2 bg-muted rounded-lg break-all text-foreground select-all border border-border">
                {qrModalReport.pdf_sha256}
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setQrModalReport(null)}>
                Close
              </Button>
              <a
                href={`/verify/${qrModalReport.report_number}?v=${qrModalReport.current_version}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground transition-colors"
              >
                Open Verification Page
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  BarChart3,
  Download,
  Table as TableIcon,
  Filter,
  PieChart as PieIcon,
  TrendingUp,
  ShieldAlert,
  FileCheck2,
  Building,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "sonner";

const COLORS = ["#4338CA", "#D97706", "#E11D48", "#6366F1", "#0284C7", "#10B981", "#7C3AED"];

interface AnalyticsData {
  department_breakdown: Array<{
    department_name: string;
    findings_count: number;
    flagged_amount: number;
    cases_count: number;
  }>;
  risk_distribution: Array<{
    category: string;
    critical: number;
    high: number;
    medium: number;
    low: number;
    total: number;
  }>;
  monthly_findings_trend: Array<{
    month: string;
    findings_count: number;
    flagged_amount: number;
  }>;
  document_types_processed: Array<{
    document_type: string;
    count: number;
    processed_count: number;
  }>;
  case_completion_rate: Array<{
    district: string;
    total_cases: number;
    completed_cases: number;
    completion_rate_pct: number;
  }>;
  top_rules_triggered: Array<{
    rule_code: string;
    rule_name: string;
    category: string;
    findings_count: number;
    total_amount: number;
    avg_risk_score: number;
  }>;
  missing_documents_analysis: Array<{
    scheme_name: string;
    missing_count: number;
  }>;
  vendor_analysis: Array<{
    vendor_name: string;
    findings_count: number;
    total_flagged_amount: number;
    max_risk_score: number;
  }>;
}

export const AnalyticsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedFy = searchParams.get("fy") || "2024-25";
  const selectedDistrict = searchParams.get("district") || "";

  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Toggle for table view per chart
  const [showTable, setShowTable] = useState<Record<string, boolean>>({});

  const toggleTable = (chartKey: string) => {
    setShowTable((prev) => ({ ...prev, [chartKey]: !prev[chartKey] }));
  };

  const exportCSV = (filename: string, rows: Record<string, any>[]) => {
    if (!rows || rows.length === 0) {
      toast.error("No data available to export.");
      return;
    }
    const headers = Object.keys(rows[0]);
    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${filename}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success(`Exported ${filename}.csv`);
  };

  const loadAnalytics = async () => {
    setIsLoading(true);
    try {
      const q = new URLSearchParams();
      if (selectedFy) q.append("financial_year", selectedFy);
      if (selectedDistrict) q.append("district", selectedDistrict);

      const res = await api.get<AnalyticsData>(`/analytics/aggregations?${q.toString()}`);
      setData(res);
    } catch {
      toast.error("Failed to load analytics aggregations.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [selectedFy, selectedDistrict]);

  const updateFilter = (key: string, val: string) => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set(key, val);
    else next.delete(key);
    setSearchParams(next);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Analytics & Intelligence"
        description="Multi-dimensional visualization of compliance trends, risk patterns, rule frequency, and expenditure variances across Karnataka local bodies."
        badge={
          <Badge variant="outline" className="text-xs border-primary/30 text-primary font-mono tabular-nums">
            FY {selectedFy} • 8 Interactive Models
          </Badge>
        }
      />

      {/* Global Filter Bar synced to URL */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl border border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-muted-foreground uppercase tracking-wider">
            <Filter className="h-3.5 w-3.5" />
            <span>Scope Filter:</span>
          </div>

          <select
            value={selectedFy}
            onChange={(e) => updateFilter("fy", e.target.value)}
            className="h-8 rounded-lg border border-input bg-background px-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label="Filter by financial year"
          >
            <option value="">All Financial Years</option>
            <option value="2024-25">FY 2024-25</option>
            <option value="2023-24">FY 2023-24</option>
          </select>

          <select
            value={selectedDistrict}
            onChange={(e) => updateFilter("district", e.target.value)}
            className="h-8 rounded-lg border border-input bg-background px-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">All Karnataka Districts</option>
            <option value="Mysuru">Mysuru</option>
            <option value="Belagavi">Belagavi</option>
            <option value="Dharwad">Dharwad</option>
            <option value="Tumakuru">Tumakuru</option>
            <option value="Kalaburagi">Kalaburagi</option>
          </select>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            if (data) {
              exportCSV("karnataka_audit_analytics_summary", data.department_breakdown);
            }
          }}
          className="h-8 gap-1.5 text-xs"
        >
          <Download className="h-3.5 w-3.5" />
          <span>Export Summary Dataset</span>
        </Button>
      </div>

      {isLoading ? (
        <div className="py-20 text-center text-sm text-muted-foreground">Loading audit visualizations...</div>
      ) : !data ? (
        <div className="py-20 text-center text-sm text-muted-foreground">No aggregation data available.</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Chart 1: Department Breakdown */}
          <ChartCard
            title="1. Department Breakdown (Findings & Flagged ₹)"
            icon={<Building className="h-4 w-4 text-primary" />}
            onToggleTable={() => toggleTable("dept")}
            onExport={() => exportCSV("department_breakdown", data.department_breakdown)}
            isTableShown={showTable["dept"]}
            tableContent={
              <DataTableSimple
                headers={["Department", "Findings", "Flagged Amount (₹)", "Cases"]}
                rows={data.department_breakdown.map((d) => [
                  d.department_name,
                  d.findings_count,
                  `₹${(d.flagged_amount ?? 0).toLocaleString("en-IN")}`,
                  d.cases_count,
                ])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.department_breakdown} aria-label="Department Breakdown Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="department_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="findings_count" name="Findings Count" fill="#4338CA" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 2: Risk Distribution by Scheme */}
          <ChartCard
            title="2. Risk Distribution by Statutory Scheme"
            icon={<ShieldAlert className="h-4 w-4 text-rose-600 dark:text-rose-400" />}
            onToggleTable={() => toggleTable("risk")}
            onExport={() => exportCSV("risk_distribution_by_scheme", data.risk_distribution)}
            isTableShown={showTable["risk"]}
            tableContent={
              <DataTableSimple
                headers={["Scheme", "Critical", "High", "Medium", "Low", "Total"]}
                rows={data.risk_distribution.map((r) => [r.category, r.critical, r.high, r.medium, r.low, r.total])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.risk_distribution} aria-label="Risk Distribution by Scheme Stacked Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="critical" stackId="a" name="Critical Risk" fill="#9333EA" />
                <Bar dataKey="high" stackId="a" name="High Risk" fill="#E11D48" />
                <Bar dataKey="medium" stackId="a" name="Medium Risk" fill="#D97706" />
                <Bar dataKey="low" stackId="a" name="Low Risk" fill="#10B981" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 3: Monthly Findings Trend */}
          <ChartCard
            title="3. Monthly Findings Trend (Past 12 Months)"
            icon={<TrendingUp className="h-4 w-4 text-primary" />}
            onToggleTable={() => toggleTable("monthly")}
            onExport={() => exportCSV("monthly_findings_trend", data.monthly_findings_trend)}
            isTableShown={showTable["monthly"]}
            tableContent={
              <DataTableSimple
                headers={["Month", "Findings Count", "Flagged Amount (₹)"]}
                rows={data.monthly_findings_trend.map((m) => [m.month, m.findings_count, `₹${m.flagged_amount.toLocaleString("en-IN")}`])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.monthly_findings_trend} aria-label="Monthly Findings Trend Line Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="findings_count" name="Findings Detected" stroke="#4F46E5" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 4: Document Types Processed */}
          <ChartCard
            title="4. Ingested Document Types Breakdown"
            icon={<PieIcon className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />}
            onToggleTable={() => toggleTable("docs")}
            onExport={() => exportCSV("document_types_processed", data.document_types_processed)}
            isTableShown={showTable["docs"]}
            tableContent={
              <DataTableSimple
                headers={["Document Type", "Total Ingested", "Processed"]}
                rows={data.document_types_processed.map((d) => [d.document_type, d.count, d.processed_count])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <PieChart aria-label="Document Types Processed Pie Chart">
                <Pie
                  data={data.document_types_processed}
                  dataKey="count"
                  nameKey="document_type"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(entry) => `${entry.document_type}: ${entry.count}`}
                >
                  {data.document_types_processed.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 5: Case Completion Rate by District */}
          <ChartCard
            title="5. Case Completion Rate by District"
            icon={<FileCheck2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />}
            onToggleTable={() => toggleTable("completion")}
            onExport={() => exportCSV("case_completion_by_district", data.case_completion_rate)}
            isTableShown={showTable["completion"]}
            tableContent={
              <DataTableSimple
                headers={["District", "Total Cases", "Completed", "Completion %"]}
                rows={data.case_completion_rate.map((c) => [c.district, c.total_cases, c.completed_cases, `${c.completion_rate_pct}%`])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.case_completion_rate} aria-label="Case Completion Rate Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="district" tick={{ fontSize: 11 }} />
                <YAxis unit="%" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="completion_rate_pct" name="Completion Rate (%)" fill="#059669" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 6: Top Rules Triggered */}
          <ChartCard
            title="6. Top Verification Rules Triggered"
            icon={<BarChart3 className="h-4 w-4 text-signal" />}
            onToggleTable={() => toggleTable("rules")}
            onExport={() => exportCSV("top_rules_triggered", data.top_rules_triggered)}
            isTableShown={showTable["rules"]}
            tableContent={
              <DataTableSimple
                headers={["Rule Code", "Rule Name", "Category", "Count", "Total Flagged ₹"]}
                rows={data.top_rules_triggered.map((r) => [r.rule_code, r.rule_name, r.category, r.findings_count, `₹${(r.total_amount ?? 0).toLocaleString("en-IN")}`])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.top_rules_triggered} layout="vertical" aria-label="Top Rules Triggered Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="rule_code" type="category" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="findings_count" name="Frequency" fill="#D97706" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 7: Missing Documents Analysis */}
          <ChartCard
            title="7. Missing Mandatory Documents by Scheme (R-008)"
            icon={<FileCheck2 className="h-4 w-4 text-rose-600 dark:text-rose-400" />}
            onToggleTable={() => toggleTable("missing")}
            onExport={() => exportCSV("missing_documents_by_scheme", data.missing_documents_analysis)}
            isTableShown={showTable["missing"]}
            tableContent={
              <DataTableSimple
                headers={["Scheme", "Missing Documents Count"]}
                rows={data.missing_documents_analysis.map((m) => [m.scheme_name, m.missing_count])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.missing_documents_analysis} aria-label="Missing Documents Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="scheme_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="missing_count" name="Checklist Deficiencies" fill="#E11D48" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Chart 8: Vendor Analysis */}
          <ChartCard
            title="8. Vendor Risk & Spend Concentration"
            icon={<Building className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />}
            onToggleTable={() => toggleTable("vendor")}
            onExport={() => exportCSV("vendor_analysis", data.vendor_analysis)}
            isTableShown={showTable["vendor"]}
            tableContent={
              <DataTableSimple
                headers={["Vendor Name", "Flagged Amount (₹)", "Findings Count"]}
                rows={data.vendor_analysis.map((v) => [v.vendor_name, `₹${(v.total_flagged_amount ?? 0).toLocaleString("en-IN")}`, v.findings_count])}
              />
            }
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.vendor_analysis} aria-label="Vendor Risk Bar Chart">
                <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                <XAxis dataKey="vendor_name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="total_flagged_amount" name="Total Flagged ₹" fill="#6366F1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}
    </div>
  );
};

// Reusable Chart Card Wrapper with Accessible Table Toggle & CSV Export
interface ChartCardProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  onToggleTable: () => void;
  onExport: () => void;
  isTableShown?: boolean;
  tableContent?: React.ReactNode;
}

const ChartCard: React.FC<ChartCardProps> = ({
  title,
  icon,
  children,
  onToggleTable,
  onExport,
  isTableShown,
  tableContent,
}) => {
  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-3">
      <div className="flex items-center justify-between border-b border-border pb-3">
        <div className="flex items-center gap-2">
          {icon}
          <h4 className="font-display text-sm font-semibold text-foreground">{title}</h4>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleTable}
            className="h-7 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground"
          >
            <TableIcon className="h-3.5 w-3.5" />
            <span>{isTableShown ? "Hide Table" : "Data Table"}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onExport}
            className="h-7 px-2 text-[11px] gap-1 text-muted-foreground hover:text-foreground"
          >
            <Download className="h-3.5 w-3.5" />
            <span>CSV</span>
          </Button>
        </div>
      </div>

      <div className="pt-2">{isTableShown ? tableContent : children}</div>
    </div>
  );
};

const DataTableSimple: React.FC<{ headers: string[]; rows: (string | number)[][] }> = ({ headers, rows }) => {
  return (
    <div className="h-[260px] overflow-auto border border-border rounded-lg">
      <table className="w-full text-xs text-left">
        <thead className="bg-muted/60 sticky top-0 border-b border-border">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="px-3 py-2 font-semibold text-muted-foreground">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/70">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={headers.length} className="px-3 py-4 text-center text-muted-foreground">
                No data available.
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <tr key={i} className="hover:bg-muted/40">
                {row.map((cell, j) => (
                  <td key={j} className="px-3 py-1.5 font-mono tabular-nums text-[11px] text-foreground">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { DashboardPage } from "@/pages/DashboardPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { SearchPage } from "@/pages/SearchPage";
import { VendorDetailPage } from "@/pages/VendorDetailPage";
import { api } from "@/lib/api";

// Mock api
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock AuthContext
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "u1", name: "Senior Auditor", role: "senior_auditor" },
    hasRole: (roles: string[]) => roles.includes("senior_auditor") || roles.includes("auditor"),
  }),
}));

// Mock Recharts responsive container which needs DOM measurements in jsdom
vi.mock("recharts", async () => {
  const actual: any = await vi.importActual("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: any) => <div style={{ width: 500, height: 300 }}>{children}</div>,
  };
});

describe("Phase 5 Dashboard & Analytics Vitest Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Dashboard 12 Live KPI Cards & Priority Queue
  it("renders Dashboard live KPIs, updates filters, and opens priority review queue", async () => {
    (api.get as any).mockImplementation((url: string) => {
      if (url.includes("/dashboard/stats")) {
        return Promise.resolve({
          total_cases: 5,
          open_cases: 3,
          completed_cases: 2,
          documents_uploaded: 24,
          documents_processed: 22,
          pending_findings: 18,
          high_risk_findings: 4,
          medium_risk_findings: 9,
          low_risk_findings: 5,
          critical_risk_findings: 2,
          r001_duplicate_payments: 3,
          r003_amount_mismatches: 5,
          r008_missing_documents: 2,
          pending_approvals_count: 3,
          total_flagged_amount: 1450000,
        });
      }
      if (url.includes("/dashboard/priority-queue")) {
        return Promise.resolve([
          {
            id: "f1",
            finding_number: "F-2025-001",
            title: "Suspected Duplicate Payment Disbursement",
            case_id: "c1",
            case_number: "CAS-2024-MYS-001",
            district: "Mysuru",
            scheme: "MGNREGA",
            rule_code: "R-001",
            risk_score: 92,
            severity: "critical",
            amount: 125000,
            status: "Open",
            created_at: "2025-01-10T10:00:00Z",
          },
        ]);
      }
      if (url.includes("/dashboard/calendar")) {
        return Promise.resolve([]);
      }
      if (url.includes("/dashboard/recent-activity")) {
        return Promise.resolve([]);
      }
      return Promise.resolve({});
    });

    render(
      <MemoryRouter initialEntries={["/dashboard?fy=2024-25&district=Mysuru"]}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Verify PageHeader
    expect(screen.getByText("Audit Executive Dashboard")).toBeInTheDocument();

    // Wait for API stats to load and display
    await waitFor(() => {
      expect(screen.getByText("Total Audit Cases")).toBeInTheDocument();
      expect(screen.getAllByText("5").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Critical Risk Findings")).toBeInTheDocument();
      expect(screen.getByText("High Risk Findings")).toBeInTheDocument();
      expect(screen.getByText("R-001 Duplicate Payments")).toBeInTheDocument();
      expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
    });

    // Priority Queue button
    const priorityBtn = screen.getByText(/Priority Queue \(1\)/i);
    expect(priorityBtn).toBeInTheDocument();
    fireEvent.click(priorityBtn);

    // Verify finding appears in drawer
    await waitFor(() => {
      expect(screen.getByText(/Suspected Duplicate Payment Disbursement/i)).toBeInTheDocument();
      expect(screen.getByText(/F-2025-001/i)).toBeInTheDocument();
    });
  });

  // 2. Analytics 8 Charts: Data Table Toggle and CSV Export
  it("toggles accessible data tables and triggers CSV export in Analytics", async () => {
    (api.get as any).mockResolvedValue({
      department_breakdown: [
        { department_name: "Rural Development & Panchayat Raj", cases_count: 8, findings_count: 22, flagged_amount: 3400000 },
        { department_name: "Health & Family Welfare", cases_count: 4, findings_count: 10, flagged_amount: 1200000 },
      ],
      risk_distribution: [
        { category: "MGNREGA", critical: 2, high: 5, medium: 8, low: 3, total: 18 },
      ],
      monthly_findings_trend: [],
      document_types_processed: [],
      case_completion_rate: [],
      top_rules_triggered: [
        { rule_code: "R-001", rule_name: "Duplicate Payment", category: "Payments", findings_count: 12, total_amount: 1500000, avg_risk_score: 88 },
      ],
      missing_documents_analysis: [],
      vendor_analysis: [
        { vendor_name: "Cauvery Infra Projects", findings_count: 5, total_flagged_amount: 850000, max_risk_score: 95 },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/analytics?fy=2024-25"]}>
        <Routes>
          <Route path="/analytics" element={<AnalyticsPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for analytics data
    await waitFor(() => {
      expect(screen.getByText("Audit Analytics & Intelligence")).toBeInTheDocument();
      expect(screen.getByText(/Department Breakdown/i)).toBeInTheDocument();
    });

    // Toggle Data Table for Department Breakdown
    const tableToggles = screen.getAllByText("Data Table");
    expect(tableToggles.length).toBeGreaterThan(0);
    fireEvent.click(tableToggles[0]);

    // Check that accessible table headers are revealed
    await waitFor(() => {
      expect(screen.getByText("Rural Development & Panchayat Raj")).toBeInTheDocument();
      expect(screen.getByText("Health & Family Welfare")).toBeInTheDocument();
    });

    // Check CSV Export button
    const csvExportButtons = screen.getAllByText("CSV");
    expect(csvExportButtons.length).toBeGreaterThan(0);

    // Mock document.createElement and click for CSV download
    const clickSpy = vi.fn();
    const origCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName === "a") {
        el.click = clickSpy;
      }
      return el;
    });

    fireEvent.click(csvExportButtons[0]);
    expect(clickSpy).toHaveBeenCalled();
  });

  // 3. Universal Search Page with basic search mode badge
  it("performs multi-entity universal search and renders results", async () => {
    (api.get as any).mockResolvedValue({
      query: "Cauvery",
      basic_search_mode: true,
      total_results: 2,
      results: {
        cases: [
          {
            id: "c-101",
            entity_type: "cases",
            title: "Cauvery Water Supply Phase II",
            subtitle: "Rural Development | Mysuru",
            badge: "review",
            link: "/cases/c-101",
          },
        ],
        vendors: [
          {
            id: "v-202",
            entity_type: "vendors",
            title: "Cauvery Infra Projects Pvt Ltd",
            subtitle: "PAN: AABCC1234F | GSTIN: 29AABCC1234F1Z5",
            badge: "Flagged",
            link: "/vendors/v-202",
          },
        ],
        departments: [],
        vouchers: [],
        bills: [],
        findings: [],
        reports: [],
      },
    });

    render(
      <MemoryRouter initialEntries={["/search?q=Cauvery"]}>
        <Routes>
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for search results
    await waitFor(() => {
      expect(screen.getByText("Universal Audit Search")).toBeInTheDocument();
      expect(screen.getByText(/Basic Search Mode/i)).toBeInTheDocument();
      expect(screen.getByText("Cauvery Water Supply Phase II")).toBeInTheDocument();
      expect(screen.getByText("Cauvery Infra Projects Pvt Ltd")).toBeInTheDocument();
    });

    // Check entity filter tabs
    expect(screen.getByText(/Cases \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Vendors \(1\)/i)).toBeInTheDocument();
  });

  // 4. Vendor Dossier Page with PAN/GSTIN validity badges
  it("renders Vendor dossier with regex PAN/GSTIN checks and linked findings", async () => {
    (api.get as any).mockResolvedValue({
      id: "v1",
      canonical_name: "Cauvery Infra Projects Pvt Ltd",
      pan: "AABCC1234F",
      gstin: "29AABCC1234F1Z5",
      is_pan_valid: true,
      is_gstin_valid: true,
      is_flagged: true,
      risk_level: "High",
      bank_account_number: "987654321012",
      ifsc_code: "SBIN0001234",
      total_spend: 3450000,
      total_records: 12,
      total_findings: 1,
      aliases: [
        { id: "a1", raw_name: "Cauvery Infra Projects", confidence_score: 0.95, source: "Invoice" },
      ],
      recent_transactions: [
        { id: "t1", record_type: "Voucher", record_number: "VOU-001", record_date: "2024-08-15", amount: 450000, case_number: "CAS-2024-MYS-001" },
      ],
      findings: [
        { id: "f1", finding_number: "F-2025-001", title: "Duplicate Bill Submission", severity: "High", risk_score: 85, amount: 150000, status: "Open", case_number: "CAS-2024-MYS-001", created_at: "2024-08-16T10:00:00Z" },
      ],
    });

    render(
      <MemoryRouter initialEntries={["/vendors/v1"]}>
        <Routes>
          <Route path="/vendors/:id" element={<VendorDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    // Verify vendor details
    await waitFor(() => {
      expect(screen.getByText("Cauvery Infra Projects Pvt Ltd")).toBeInTheDocument();
      expect(screen.getAllByText("Valid").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText("Duplicate Bill Submission")).toBeInTheDocument();
      expect(screen.getByText("VOU-001")).toBeInTheDocument();
    });
  });
});

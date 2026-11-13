import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ReportPreviewModal } from "@/components/reporting/ReportPreviewModal";
import { ReportApproveModal } from "@/components/reporting/ReportApproveModal";
import { ReportVerifyPage } from "@/pages/ReportVerifyPage";
import { ReportsPage } from "@/pages/ReportsPage";
import { AuthProvider } from "@/context/AuthContext";

describe("Phase 6 Statutory Reports Vitest Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  // 1. Report Preview Modal
  it("renders ReportPreviewModal with embedded PDF viewer and download trigger", () => {
    const mockClose = vi.fn();
    const mockDownload = vi.fn();

    render(
      <ReportPreviewModal
        isOpen={true}
        onClose={mockClose}
        reportId="rep-123"
        reportNumber="RPT-2025-0001"
        versionNumber={1}
        reportTitle="MGNREGA Statutory Audit Report"
        onDownload={mockDownload}
      />
    );

    expect(screen.getByText(/RPT-2025-0001 • v1/i)).toBeInTheDocument();
    expect(screen.getByText("MGNREGA Statutory Audit Report")).toBeInTheDocument();
    expect(screen.getByText("Download PDF")).toBeInTheDocument();

    const iframe = screen.getByTitle("RPT-2025-0001");
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute("src", "/api/reports/rep-123/preview?version=1");

    fireEvent.click(screen.getByText("Download PDF"));
    expect(mockDownload).toHaveBeenCalledTimes(1);
  });

  // 2. Report Approval Modal with Maker-Checker Certification
  it("renders ReportApproveModal with dual-custody statement and comment requirement", async () => {
    const mockClose = vi.fn();
    const mockApproved = vi.fn();

    render(
      <ReportApproveModal
        isOpen={true}
        onClose={mockClose}
        reportId="rep-123"
        reportNumber="RPT-2025-0001"
        onApproved={mockApproved}
      />
    );

    expect(screen.getByText("Statutory Report Dual Sign-off")).toBeInTheDocument();
    expect(screen.getByText(/Dual-Custody Certification Statement/i)).toBeInTheDocument();

    const signBtn = screen.getByText("Confirm & Sign Report");
    expect(signBtn).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Scrutinized all high-risk items/i);
    fireEvent.change(textarea, { target: { value: "Full audit compliance verified." } });
    expect(signBtn).not.toBeDisabled();
  });

  // 3. Public Zero-Knowledge Verification Portal
  it("renders public zero-knowledge verification seal and dropzone", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        valid: true,
        report_number: "RPT-2025-0042",
        version_number: 1,
        status: "Approved",
        report_title: "Statutory Financial Audit Report — Bilikere GP",
        case_number: "CAS-2024-MYS-001",
        case_title: "Bilikere Gram Panchayat Audit",
        department: "Rural Development & Panchayat Raj",
        district: "Mysuru",
        financial_year: "2024-25",
        generated_at: "2026-10-30T10:00:00Z",
        approved_at: "2026-10-30T11:00:00Z",
        approver_name: "Smt. Roopa H.S.",
        pdf_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        is_demo_data: true,
        page_count: 12,
      }),
    });

    render(
      <MemoryRouter initialEntries={["/verify/RPT-2025-0042"]}>
        <Routes>
          <Route path="/verify/:reportId" element={<ReportVerifyPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("RPT-2025-0042")).toBeInTheDocument();
      expect(screen.getByText("CAS-2024-MYS-001")).toBeInTheDocument();
      expect(screen.getByText("DEMO DATA")).toBeInTheDocument();
      expect(screen.getByText("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")).toBeInTheDocument();
      expect(screen.getByText("Zero-Knowledge Guarantee:")).toBeInTheDocument();
      expect(screen.getByText("Verify Document Authenticity")).toBeInTheDocument();
    });
  });

  // 4. Reports List Page
  it("renders ReportsPage with counters, filters and data table", async () => {
    (global.fetch as any).mockImplementation((url: string) => {
      if (url.includes("/api/reports")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: [
              {
                id: "r1",
                report_number: "RPT-2025-0001",
                report_title: "Mysuru GP Audit",
                report_type: "preliminary",
                current_version: 1,
                status: "Approved",
                case_id: "c1",
                case_number: "CAS-2024-001",
                case_title: "Mysuru Rural Case",
                department: "Panchayat Raj",
                district: "Mysuru",
                financial_year: "2024-25",
                generated_by_name: "Auditor Anand",
                approved_by_name: "Officer Roopa",
                approved_at: "2026-10-30T10:00:00Z",
                page_count: 8,
                pdf_sha256: "abc123def456",
                created_at: "2026-10-30T09:00:00Z",
              },
            ],
            total: 1,
            status_summary: { Draft: 0, Approved: 1, Final: 0, Superseded: 0 },
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: "u1", email: "auditor@stateaudit.kar.gov.in", role: { code: "auditor" } }),
      });
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <ReportsPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Statutory Audit Reports")).toBeInTheDocument();
    });
    // Let's check table or loading
    await waitFor(() => {
      expect(screen.getByText(/RPT-2025-0001/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ComparisonTab } from "@/components/findings/ComparisonTab";
import { FindingActionDialogs } from "@/components/findings/FindingActionDialogs";
import { computeBBoxPixels } from "@/components/documents/BBoxOverlay";

describe("Phase 4 Findings & Evidence Vitest Suite", () => {
  // 1. Comparison Table Difference Highlighting
  it("renders reconciliation comparison table with difference highlighting", () => {
    const comparisonData = [
      {
        stage: "Bill / Invoice",
        amount: 125000,
        difference: 0,
        percentage_variance: 0,
        is_variance: false,
      },
      {
        stage: "Voucher Disbursement",
        amount: 140000,
        difference: 15000,
        percentage_variance: 12.0,
        is_variance: true,
      },
    ];

    render(<ComparisonTab comparisonData={comparisonData} />);

    expect(screen.getByText("Bill / Invoice")).toBeInTheDocument();
    expect(screen.getByText("Voucher Disbursement")).toBeInTheDocument();
    expect(screen.getByText("Matched")).toBeInTheDocument();
    expect(screen.getByText("Discrepancy")).toBeInTheDocument();
    expect(screen.getByText("+₹15,000.00")).toBeInTheDocument();
    expect(screen.getByText("+12%")).toBeInTheDocument();
  });

  // 2. Review Dialog Validation
  it("validates mandatory justification comment of minimum 5 characters", async () => {
    const mockSubmit = vi.fn();
    const mockClose = vi.fn();

    render(
      <FindingActionDialogs
        actionType="confirm"
        findingNumber="F-2025-001"
        isHighOrCritical={true}
        currentUserRole="auditor"
        isOpen={true}
        onClose={mockClose}
        onSubmit={mockSubmit}
      />
    );

    expect(screen.getByText("Confirm Finding F-2025-001")).toBeInTheDocument();
    // Maker-checker notice for Auditor on High/Critical finding
    expect(screen.getByText(/Pending Approval/i)).toBeInTheDocument();

    const submitBtn = screen.getByText("Submit Determination");
    expect(submitBtn).toBeDisabled();

    const textarea = screen.getByPlaceholderText(/Document detailed statutory justification/i);

    // Type 3 chars -> still disabled
    fireEvent.change(textarea, { target: { value: "abc" } });
    expect(submitBtn).toBeDisabled();

    // Type valid comment -> enabled and callable
    fireEvent.change(textarea, { target: { value: "Duplicate payment confirmed from bank ledger." } });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);
    expect(mockSubmit).toHaveBeenCalledWith(
      "confirm",
      "Duplicate payment confirmed from bank ledger.",
      "Confirmed"
    );
  });

  // 3. Bounding Box Overlay Coordinate Calculations on Evidence Viewer
  it("computes bbox pixel transformation across rotation and zoom", () => {
    // Normal 0 deg
    const rect0 = computeBBoxPixels([0.1, 0.2, 0.5, 0.6], 595, 842, 1.0, 0);
    expect(rect0.left).toBeCloseTo(59.5, 1);
    expect(rect0.top).toBeCloseTo(168.4, 1);
    expect(rect0.width).toBeCloseTo(238.0, 1);
    expect(rect0.height).toBeCloseTo(336.8, 1);

    // 90 deg clockwise
    const rect90 = computeBBoxPixels([0.1, 0.2, 0.5, 0.6], 595, 842, 1.0, 90);
    expect(rect90.width).toBeCloseTo((0.6 - 0.2) * 842, 1);
    expect(rect90.height).toBeCloseTo((0.5 - 0.1) * 595, 1);

    // 2.0x zoom
    const rectZoom = computeBBoxPixels([0.1, 0.2, 0.5, 0.6], 595, 842, 2.0, 0);
    expect(rectZoom.left).toBeCloseTo(59.5 * 2.0, 1);
    expect(rectZoom.width).toBeCloseTo(238.0 * 2.0, 1);
  });
});


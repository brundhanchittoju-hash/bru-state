import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RiskScoreGauge } from "@/components/verification/RiskScoreGauge";
import { ReconciliationMatrix } from "@/components/verification/ReconciliationMatrix";
import { RuleSummaryGrid } from "@/components/verification/RuleSummaryGrid";
import { VendorConcentrationCard } from "@/components/verification/VendorConcentrationCard";
import { ReconciliationMatrixItem, RuleSummaryItem, VendorConcentrationItem } from "@/types";

describe("RiskScoreGauge Component", () => {
  const dummyBreakdown = {
    missing_documents: 0.8,
    amount_difference: 0.5,
    duplicate_signals: 1.0,
    vendor_concentration: 0.4,
    unusual_amount: 0.0,
    record_incompleteness: 0.3,
    date_anomalies: 0.6,
  };

  it("renders risk score, out of 100 label, and critical risk badge", () => {
    render(
      <RiskScoreGauge
        score={85.0}
        band="critical"
        breakdown={dummyBreakdown}
      />
    );

    expect(screen.getByText("85.0")).toBeInTheDocument();
    expect(screen.getByText("out of 100")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL RISK")).toBeInTheDocument();
    expect(screen.getByText("Missing Statutory Documents")).toBeInTheDocument();
  });

  it("opens calculation formula modal on click", () => {
    render(
      <RiskScoreGauge
        score={15.0}
        band="low"
        breakdown={dummyBreakdown}
      />
    );

    const helpBtn = screen.getByText("How is this calculated?");
    expect(helpBtn).toBeInTheDocument();

    fireEvent.click(helpBtn);

    expect(screen.getByText("Composite Risk Score Calculation")).toBeInTheDocument();
    expect(screen.getByText(/Statutory Severity Override Rule:/i)).toBeInTheDocument();

    const closeBtn = screen.getByText("Close Explanation");
    fireEvent.click(closeBtn);

    expect(screen.queryByText("Composite Risk Score Calculation")).not.toBeInTheDocument();
  });
});

describe("ReconciliationMatrix Component", () => {
  const dummyItems: ReconciliationMatrixItem[] = [
    {
      bill_id: "b1",
      bill_number: "INV-101",
      bill_amount: 50000,
      voucher_id: "v1",
      voucher_number: "VR-01",
      voucher_amount: 50000,
      bank_id: "k1",
      bank_reference: "RTGS-999",
      bank_amount: 50000,
      status: "fully_matched",
    },
    {
      bill_id: "b2",
      bill_number: "INV-102",
      bill_amount: 25000,
      voucher_id: "v2",
      voucher_number: "VR-02",
      voucher_amount: 25000,
      bank_id: null,
      bank_reference: null,
      bank_amount: null,
      status: "partially_matched",
    },
    {
      bill_id: "b3",
      bill_number: "INV-103",
      bill_amount: 15000,
      voucher_id: null,
      voucher_number: null,
      voucher_amount: null,
      bank_id: null,
      bank_reference: null,
      bank_amount: null,
      status: "unmatched",
    },
  ];

  it("renders reconciliation rate and stages correctly", () => {
    render(<ReconciliationMatrix items={dummyItems} />);

    // 1 of 3 fully matched = 33%
    expect(screen.getByText("33% Reconciled")).toBeInTheDocument();
    expect(screen.getByText("INV-101")).toBeInTheDocument();
    expect(screen.getByText("VR-01")).toBeInTheDocument();
    expect(screen.getByText("RTGS-999")).toBeInTheDocument();
    expect(screen.getAllByText("Uncleared in Bank").length).toBe(2);
  });

  it("filters items by status buttons", () => {
    render(<ReconciliationMatrix items={dummyItems} />);

    const matchedFilterBtn = screen.getByText("Matched (1)");
    fireEvent.click(matchedFilterBtn);

    expect(screen.getByText("INV-101")).toBeInTheDocument();
    expect(screen.queryByText("INV-102")).not.toBeInTheDocument();
    expect(screen.queryByText("INV-103")).not.toBeInTheDocument();
  });
});

describe("RuleSummaryGrid Component", () => {
  const dummyRules: RuleSummaryItem[] = [
    {
      rule_id: "R-001",
      name: "Duplicate Payment Detection",
      category: "duplicate",
      status: "flagged",
      findings_count: 2,
      default_severity: "critical",
    },
    {
      rule_id: "R-002",
      name: "Duplicate Invoice Number",
      category: "duplicate",
      status: "pass",
      findings_count: 0,
      default_severity: "high",
    },
  ];

  it("renders rule cards with Pass / Flagged badges and triggers rule select", () => {
    const onSelect = vi.fn();
    render(
      <RuleSummaryGrid
        rules={dummyRules}
        selectedRuleId={null}
        onSelectRule={onSelect}
      />
    );

    expect(screen.getByText("R-001")).toBeInTheDocument();
    expect(screen.getByText("Duplicate Payment Detection")).toBeInTheDocument();
    expect(screen.getByText("2 Flagged")).toBeInTheDocument();
    expect(screen.getByText("Pass")).toBeInTheDocument();

    const card = screen.getByText("Duplicate Payment Detection");
    fireEvent.click(card);

    expect(onSelect).toHaveBeenCalledWith("R-001");
  });
});

describe("VendorConcentrationCard Component", () => {
  const dummyVendors: VendorConcentrationItem[] = [
    {
      vendor_id: "v1",
      vendor_name: "Cauvery Infrastructure Pvt Ltd",
      total_spend: 850000,
      payment_count: 3,
      spend_share_pct: 55.0,
      is_flagged: false,
    },
    {
      vendor_id: "v2",
      vendor_name: "Chamundi Power Solutions",
      total_spend: 300000,
      payment_count: 2,
      spend_share_pct: 19.5,
      is_flagged: false,
    },
  ];

  it("renders vendor ranking and concentration alert if single vendor >= 40%", () => {
    render(
      <VendorConcentrationCard
        vendors={dummyVendors}
        totalExpenditure={1545000}
      />
    );

    expect(screen.getByText("Concentration Alert (>40%)")).toBeInTheDocument();
    expect(screen.getByText("Cauvery Infrastructure Pvt Ltd")).toBeInTheDocument();
    expect(screen.getByText("55.0%")).toBeInTheDocument();
  });
});

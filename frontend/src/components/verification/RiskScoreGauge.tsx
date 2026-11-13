import React, { useState } from "react";
import { Info, HelpCircle, X, ShieldAlert, AlertTriangle, ShieldCheck } from "lucide-react";
import { FactorBreakdown, RiskLevel } from "@/types";

interface RiskScoreGaugeProps {
  score: number;
  band: RiskLevel;
  breakdown: FactorBreakdown;
  weights?: Record<string, number>;
}

const DEFAULT_WEIGHTS: Record<string, number> = {
  missing_documents: 25,
  amount_difference: 20,
  duplicate_signals: 15,
  vendor_concentration: 10,
  unusual_amount: 10,
  record_incompleteness: 10,
  date_anomalies: 10,
};

const FACTOR_LABELS: Record<string, { label: string; desc: string }> = {
  missing_documents: {
    label: "Missing Statutory Documents",
    desc: "Absence of mandatory sanction, work order, MB, or completion certs",
  },
  amount_difference: {
    label: "Payment Chain Amount Mismatches",
    desc: "Variance across bill, voucher, bank debit, or sanction ceilings",
  },
  duplicate_signals: {
    label: "Duplicate Invoices & Payments",
    desc: "Identical amounts, duplicate invoice numbers, or duplicate vouchers",
  },
  vendor_concentration: {
    label: "High Vendor Concentration",
    desc: "Single vendor exceeding 40% or top 3 vendors exceeding 70% spend",
  },
  unusual_amount: {
    label: "Large / Outlier Discrepancies",
    desc: "Statistical anomalies >3 IQR or round number clustering",
  },
  record_incompleteness: {
    label: "Data Incompleteness & Gaps",
    desc: "Missing UTR references, unregistered vendors, or sequence breaks",
  },
  date_anomalies: {
    label: "Date & Timing Irregularities",
    desc: "Chronological reversals, holiday or fiscal year-end payments",
  },
};

export const RiskScoreGauge: React.FC<RiskScoreGaugeProps> = ({
  score,
  band,
  breakdown,
  weights = DEFAULT_WEIGHTS,
}) => {
  const [showFormulaModal, setShowFormulaModal] = useState(false);

  // Band visual properties
  const getBandStyles = (b: RiskLevel) => {
    switch (b) {
      case "critical":
        return {
          textColor: "text-red-600 dark:text-red-400",
          bgColor: "bg-red-500/10",
          borderColor: "border-red-500/30",
          strokeColor: "#dc2626",
          glow: "none",
          badge: "bg-red-600 text-white",
          label: "CRITICAL RISK",
          icon: <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-400" />,
        };
      case "high":
        return {
          textColor: "text-orange-600 dark:text-orange-400",
          bgColor: "bg-orange-500/10",
          borderColor: "border-orange-500/30",
          strokeColor: "#ea580c",
          glow: "none",
          badge: "bg-orange-600 text-white",
          label: "HIGH RISK",
          icon: <AlertTriangle className="h-5 w-5 text-orange-600 dark:text-orange-400" />,
        };
      case "medium":
        return {
          textColor: "text-signal",
          bgColor: "bg-signal-surface",
          borderColor: "border-signal/30",
          strokeColor: "#b45309",
          glow: "none",
          badge: "bg-amber-600 text-white",
          label: "MEDIUM RISK",
          icon: <AlertTriangle className="h-5 w-5 text-signal" />,
        };
      case "low":
      default:
        return {
          textColor: "text-emerald-600 dark:text-emerald-400",
          bgColor: "bg-emerald-500/10",
          borderColor: "border-emerald-500/30",
          strokeColor: "#059669",
          glow: "none",
          badge: "bg-emerald-600 text-white",
          label: "LOW RISK",
          icon: <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />,
        };
    }
  };

  const style = getBandStyles(band);

  // SVG Gauge calculations (semi-circle / 260 deg arc)
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  // Arc covering 240 degrees (from 150 to 390)
  const arcLength = circumference * (240 / 360);
  const strokeOffset = arcLength - (arcLength * Math.min(100, Math.max(0, score))) / 100;

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div className="flex items-center space-x-2">
          {style.icon}
          <h3 className="font-display font-semibold text-foreground text-base">
            Composite Case Risk Gauge
          </h3>
        </div>
        <button
          onClick={() => setShowFormulaModal(true)}
          className="inline-flex items-center text-xs font-medium text-primary hover:underline space-x-1"
          title="Inspect statutory formula and weighting calculation"
        >
          <HelpCircle className="h-3.5 w-3.5" />
          <span>How is this calculated?</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center pt-6">
        {/* Radial Arc Gauge */}
        <div className="md:col-span-5 flex flex-col items-center justify-center relative">
          <div className="relative w-48 h-48 flex items-center justify-center">
            <svg className="w-full h-full transform -rotate-210" viewBox="0 0 160 160">
              {/* Background Arc */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                className="stroke-muted"
                strokeWidth="12"
                strokeDasharray={`${arcLength} ${circumference}`}
                strokeLinecap="round"
                fill="none"
              />
              {/* Dynamic Value Arc */}
              <circle
                cx="80"
                cy="80"
                r={radius}
                stroke={style.strokeColor}
                strokeWidth="12"
                strokeDasharray={`${arcLength} ${circumference}`}
                strokeDashoffset={strokeOffset}
                strokeLinecap="round"
                fill="none"
                style={{
                  filter: style.glow,
                  transition: "stroke-dashoffset 0.8s ease-in-out, stroke 0.4s ease",
                }}
              />
            </svg>

            {/* Inner Content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center text-center pt-2">
              <span className={`font-mono text-4xl font-bold tabular-nums tracking-tight ${style.textColor}`}>
                {score.toFixed(1)}
              </span>
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                out of 100
              </span>
              <span
                className={`mt-2 px-2.5 py-0.5 rounded-full text-xs font-bold tracking-wide uppercase ${style.badge}`}
              >
                {style.label}
              </span>
            </div>
          </div>

          <p className="text-xs text-muted-foreground text-center mt-2 max-w-[220px]">
            Statutory composite risk index calibrated according to Karnataka State Audit guidelines.
          </p>
        </div>

        {/* 7-Factor Breakdown Bars */}
        <div className="md:col-span-7 space-y-3">
          <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground pb-1 border-b border-border">
            <span>Risk Factor (7 Weighted Dimensions)</span>
            <span>Weight / Signal</span>
          </div>

          {Object.entries(FACTOR_LABELS).map(([factorKey, meta]) => {
            const rawVal = breakdown[factorKey] || 0;
            const weight = weights[factorKey] ?? 10;
            const pct = Math.min(100, Math.round(rawVal * 100));

            return (
              <div key={factorKey} className="group">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="font-medium text-foreground group-hover:text-primary transition-colors">
                    {meta.label}
                  </span>
                  <div className="flex items-center space-x-2">
                    <span className="text-muted-foreground font-mono text-[11px] tabular-nums">wt: {weight}%</span>
                    <span
                      className={`font-mono font-semibold text-xs tabular-nums ${
                        pct >= 70
                          ? "text-red-600 dark:text-red-400"
                          : pct >= 35
                          ? "text-signal"
                          : "text-muted-foreground"
                      }`}
                    >
                      {pct}%
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      pct >= 70
                        ? "bg-red-500"
                        : pct >= 40
                        ? "bg-amber-500"
                        : pct > 0
                        ? "bg-primary"
                        : "bg-border"
                    }`}
                    style={{ width: `${Math.max(pct, pct > 0 ? 3 : 0)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Formula Modal */}
      {showFormulaModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-lg w-full overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div className="flex items-center space-x-2">
                <Info className="h-5 w-5 text-primary" />
                <h4 className="font-display font-semibold text-foreground text-base">
                  Composite Risk Score Calculation
                </h4>
              </div>
              <button
                onClick={() => setShowFormulaModal(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs text-muted-foreground max-h-[70vh] overflow-y-auto">
              <div className="bg-accent/50 p-3 rounded-lg font-mono text-[11px] text-primary border border-primary/20">
                Score = Σ (Factor_i × Weight_i)
                <br />
                Where Σ Weight_i = 100%
              </div>

              <div>
                <h5 className="font-semibold text-foreground text-sm mb-2">
                  Factor Weighting Matrix:
                </h5>
                <ul className="space-y-1.5 list-disc pl-5">
                  <li>
                    <strong className="text-foreground">25% - Missing Mandatory Documents:</strong>{" "}
                    Statutory absence of Sanctions, Work Orders, MBs, or Utilization Certificates.
                  </li>
                  <li>
                    <strong className="text-foreground">20% - Amount Difference:</strong> Variance
                    between sanctioned ceilings, approved bills, vouchers, and bank passbooks.
                  </li>
                  <li>
                    <strong className="text-foreground">15% - Duplicate Signals:</strong> Identical
                    invoice numbers or voucher disbursement amounts.
                  </li>
                  <li>
                    <strong className="text-foreground">10% - Vendor Concentration:</strong> Single
                    vendor &gt;40% or top 3 vendors &gt;70% share of total scheme expenditure.
                  </li>
                  <li>
                    <strong className="text-foreground">10% - Unusual Amounts:</strong> Benford&apos;s
                    law deviations and statistical outliers (&gt;3 IQR).
                  </li>
                  <li>
                    <strong className="text-foreground">10% - Record Incompleteness:</strong> Unlinked
                    transactions and gaps in voucher registers.
                  </li>
                  <li>
                    <strong className="text-foreground">10% - Date &amp; Timing Anomalies:</strong>{" "}
                    Backdated vouchers, holiday transactions, and year-end rush expenditures.
                  </li>
                </ul>
              </div>

              <div className="border-t border-border pt-3">
                <h5 className="font-semibold text-foreground text-sm mb-1">
                  Statutory Severity Override Rule:
                </h5>
                <p>
                  To ensure that high-impact statutory non-compliances are never masked by high volumes of clean records,
                  the engine enforces a statutory floor:
                </p>
                <div className="mt-2 space-y-1 font-mono text-[11px] bg-muted/50 text-foreground p-2.5 rounded-lg border border-border">
                  <div>If any active finding is CRITICAL: Final Score ≥ 85.0 (Critical Band)</div>
                  <div>If any active finding is HIGH: Final Score ≥ 60.0 (High Band)</div>
                </div>
              </div>

              <div className="border-t border-border pt-3 flex items-center justify-between text-muted-foreground">
                <span>Karnataka Financial Code &bull; KTPP Act</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-medium">Statutory Default</span>
              </div>
            </div>

            <div className="p-4 bg-muted/30 border-t border-border flex justify-end">
              <button
                onClick={() => setShowFormulaModal(false)}
                className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-xs font-semibold transition-colors"
              >
                Close Explanation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

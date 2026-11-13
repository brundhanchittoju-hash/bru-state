import React, { useState } from "react";
import { CheckCircle2, AlertTriangle, SkipForward, ArrowUpRight } from "lucide-react";
import { RuleSummaryItem } from "@/types";

interface RuleSummaryGridProps {
  rules: RuleSummaryItem[];
  selectedRuleId?: string | null;
  onSelectRule: (ruleId: string | null) => void;
}

const CATEGORY_NAMES: Record<string, string> = {
  all: "All Rules (16)",
  duplicate: "Duplicate Detection",
  reconciliation: "Payment Reconciliation",
  sanction: "Sanction Compliance",
  tax: "Tax & GST Slabs",
  arithmetic: "Arithmetic Validation",
  document: "Mandatory Documents",
  date_logic: "Chronological Logic",
  compliance: "Voucher Continuity",
  vendor: "Vendor Exposure",
  procurement: "Procurement & KTPP",
  statistical: "Forensic & Benford",
  timing: "Statutory Timing",
};

export const RuleSummaryGrid: React.FC<RuleSummaryGridProps> = ({
  rules,
  selectedRuleId,
  onSelectRule,
}) => {
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const categories = ["all", ...Array.from(new Set(rules.map((r) => r.category)))];

  const filteredRules = rules.filter((r) => {
    if (activeCategory === "all") return true;
    return r.category === activeCategory;
  });

  const flaggedCount = rules.filter((r) => r.status === "flagged").length;
  const passedCount = rules.filter((r) => r.status === "pass").length;
  const skippedCount = rules.filter((r) => r.status === "skipped").length;

  return (
    <div className="bg-card border border-border rounded-xl p-6 space-y-6">
      {/* Header and Summary Counters */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h3 className="font-display font-semibold text-foreground text-base">
            16 Statutory Verification Rules Overview
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Deterministic rule matrix implementing Karnataka Financial Code, KTPP Act, and Panchayat Raj rules.
          </p>
        </div>

        {/* Status Pills */}
        <div className="flex items-center space-x-2 text-xs tabular-nums">
          <span className="px-2.5 py-1 rounded-md font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            {passedCount} Passed
          </span>
          <span className="px-2.5 py-1 rounded-md font-semibold bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/20">
            {flaggedCount} Flagged
          </span>
          {skippedCount > 0 && (
            <span className="px-2.5 py-1 rounded-md font-semibold bg-muted text-muted-foreground">
              {skippedCount} Skipped
            </span>
          )}
        </div>
      </div>

      {/* Category Filter Chips */}
      <div className="flex flex-wrap gap-1.5 text-xs">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 rounded-lg font-medium transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            {CATEGORY_NAMES[cat] || cat.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Grid of 16 Rule Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {filteredRules.map((r) => {
          const isSelected = selectedRuleId === r.rule_id;
          const isFlagged = r.status === "flagged";
          const isPassed = r.status === "pass";
          const isSkipped = r.status === "skipped";

          return (
            <div
              key={r.rule_id}
              onClick={() => onSelectRule(isSelected ? null : r.rule_id)}
              className={`p-4 rounded-xl border text-left cursor-pointer transition-all duration-200 flex flex-col justify-between relative group ${
                isSelected
                  ? "ring-2 ring-primary border-primary bg-accent/40 shadow-sm"
                  : isFlagged
                  ? "border-red-500/30 bg-red-500/5 hover:border-red-500/50"
                  : isPassed
                  ? "border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50"
                  : "border-border bg-muted/30 opacity-80"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs font-bold text-foreground bg-muted px-2 py-0.5 rounded">
                    {r.rule_id}
                  </span>

                  {isFlagged && (
                    <span className="inline-flex items-center text-[11px] font-bold text-red-700 dark:text-red-300 bg-red-500/10 px-2 py-0.5 rounded-full">
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      {r.findings_count} Flagged
                    </span>
                  )}
                  {isPassed && (
                    <span className="inline-flex items-center text-[11px] font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      Pass
                    </span>
                  )}
                  {isSkipped && (
                    <span className="inline-flex items-center text-[11px] font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                      <SkipForward className="h-3 w-3 mr-1" />
                      Skipped
                    </span>
                  )}
                </div>

                <h4 className="text-xs font-semibold text-foreground leading-snug group-hover:text-primary transition-colors">
                  {r.name}
                </h4>

                {isSkipped && r.skipped_reason && (
                  <p className="text-[11px] text-muted-foreground italic mt-1 leading-tight">
                    {r.skipped_reason}
                  </p>
                )}
              </div>

              <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="capitalize">{r.category}</span>
                <span className="inline-flex items-center text-primary font-medium group-hover:underline">
                  {isSelected ? "Clear filter" : "Filter findings"}
                  <ArrowUpRight className="h-3 w-3 ml-0.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

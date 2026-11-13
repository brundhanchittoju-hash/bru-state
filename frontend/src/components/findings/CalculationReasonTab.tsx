import React from "react";
import { Calculator, Sparkles, Info } from "lucide-react";

interface CalculationReasonTabProps {
  finding: {
    calculation?: string;
    reason?: string;
    rule_description?: string;
    inputs_used?: Record<string, any>;
    thresholds_used?: Record<string, any>;
    risk_factors?: Array<{ factor: string; weight: number; contribution: number }>;
    ai_summary?: string;
    ai_summary_badge?: string;
  };
}

export const CalculationReasonTab: React.FC<CalculationReasonTabProps> = ({ finding }) => {
  return (
    <div className="space-y-5 text-xs">
      {/* AI Summary Badge & Card */}
      <div className="bg-accent/50 border border-primary/25 p-4 rounded-xl space-y-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 font-semibold text-primary text-xs">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>Deterministic Explainability Summary</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-card border border-primary/20 text-accent-foreground font-medium">
            {finding.ai_summary_badge || "AI summary: template mode"}
          </span>
        </div>
        <p className="text-foreground/90 leading-relaxed">
          {finding.ai_summary || finding.reason || "Flagged for auditor review based on deterministic statutory rules."}
        </p>
      </div>

      {/* Human-Readable Calculation */}
      <div className="border border-border rounded-xl p-4 space-y-2.5 bg-card">
        <div className="flex items-center gap-2 font-semibold text-foreground">
          <Calculator className="h-4 w-4 text-primary" />
          <span>Statutory Calculation & Logic</span>
        </div>
        <div className="p-3 bg-muted/50 rounded-lg font-mono text-[11px] leading-relaxed text-foreground border border-border">
          {finding.calculation || "Deterministic comparison executed between source document records."}
        </div>
        {finding.rule_description && (
          <p className="text-muted-foreground text-[11px] mt-1 flex items-start gap-1.5">
            <Info className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
            <span>Rule Benchmark: {finding.rule_description}</span>
          </p>
        )}
      </div>

      {/* Inputs & Thresholds Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Inputs Used */}
        <div className="border border-border rounded-xl p-3.5 bg-card">
          <h4 className="font-semibold text-foreground mb-2.5">Inputs Evaluated</h4>
          {finding.inputs_used && Object.keys(finding.inputs_used).length > 0 ? (
            <div className="space-y-1.5 font-mono text-[11px]">
              {Object.entries(finding.inputs_used).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 border-b border-border/60 pb-1">
                  <span className="text-muted-foreground">{k}:</span>
                  <span className="font-medium text-foreground tabular-nums">{String(v)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-[11px]">No custom input payload recorded.</p>
          )}
        </div>

        {/* Thresholds Used */}
        <div className="border border-border rounded-xl p-3.5 bg-card">
          <h4 className="font-semibold text-foreground mb-2.5">Statutory Thresholds Applied</h4>
          {finding.thresholds_used && Object.keys(finding.thresholds_used).length > 0 ? (
            <div className="space-y-1.5 font-mono text-[11px]">
              {Object.entries(finding.thresholds_used).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 border-b border-border/60 pb-1">
                  <span className="text-muted-foreground">{k}:</span>
                  <span className="font-medium text-foreground tabular-nums">{String(v)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-[11px]">Standard statutory tolerance: 0% variance threshold.</p>
          )}
        </div>
      </div>

      {/* 7-Factor Risk Score Breakdown */}
      {finding.risk_factors && (
        <div className="border border-border rounded-xl p-4 bg-card space-y-3">
          <h4 className="font-semibold text-foreground">
            7-Factor Risk Score Formula Contribution
          </h4>
          <div className="space-y-2.5">
            {finding.risk_factors.map((rf, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex justify-between text-[11px] gap-2">
                  <span className="text-muted-foreground">{rf.factor}</span>
                  <span className="font-mono text-foreground tabular-nums">
                    Weight: {rf.weight}% (Active: {rf.contribution} pts)
                  </span>
                </div>
                <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${Math.min(100, rf.contribution > 0 ? 100 : rf.weight)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-muted-foreground font-mono pt-1">
            Statutory Override Rule: Critical ≥ 85, High ≥ 60 floor guarantee.
          </p>
        </div>
      )}
    </div>
  );
};

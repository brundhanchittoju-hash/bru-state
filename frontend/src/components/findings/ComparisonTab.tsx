import React from "react";
import { CheckCircle2, AlertTriangle, ArrowRightLeft } from "lucide-react";

interface ComparisonTabProps {
  comparisonData: Array<{
    stage: string;
    amount: number;
    difference: number;
    percentage_variance: number;
    is_variance: boolean;
  }>;
}

export const ComparisonTab: React.FC<ComparisonTabProps> = ({ comparisonData }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <ArrowRightLeft className="h-4 w-4 text-primary" />
        <span>Multi-stage payment chain reconciliation (Bill → Voucher → Ledger → Bank Debit).</span>
      </div>

      <div className="overflow-x-auto border border-border rounded-xl">
        <table className="w-full text-xs text-left">
          <thead className="bg-muted text-muted-foreground font-semibold border-b border-border">
            <tr>
              <th className="p-3">Accounting Stage</th>
              <th className="p-3 text-right">Recorded Amount (₹)</th>
              <th className="p-3 text-right">Variance (₹)</th>
              <th className="p-3 text-right">Variance (%)</th>
              <th className="p-3 text-center">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {comparisonData.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-4 text-center text-muted-foreground">
                  No multi-stage comparison values recorded for this finding.
                </td>
              </tr>
            ) : (
              comparisonData.map((row, idx) => (
                <tr
                  key={idx}
                  className={
                    row.is_variance
                      ? "bg-signal-surface/40 font-medium"
                      : "hover:bg-muted/40"
                  }
                >
                  <td className="p-3 font-medium text-foreground">
                    {row.stage}
                  </td>
                  <td className="p-3 text-right font-mono font-semibold text-foreground tabular-nums">
                    ₹{row.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </td>
                  <td
                    className={`p-3 text-right font-mono tabular-nums ${
                      row.is_variance
                        ? "text-rose-600 dark:text-rose-400 font-bold"
                        : "text-muted-foreground"
                    }`}
                  >
                    {row.difference > 0 ? `+₹${row.difference.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : row.difference < 0 ? `-₹${Math.abs(row.difference).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "₹0.00"}
                  </td>
                  <td
                    className={`p-3 text-right font-mono tabular-nums ${
                      row.is_variance ? "text-rose-600 dark:text-rose-400 font-bold" : "text-muted-foreground"
                    }`}
                  >
                    {row.percentage_variance > 0
                      ? `+${row.percentage_variance}%`
                      : `${row.percentage_variance}%`}
                  </td>
                  <td className="p-3 text-center">
                    {row.is_variance ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-signal bg-signal-surface border border-signal-border px-2 py-0.5 rounded-full">
                        <AlertTriangle className="h-3 w-3" />
                        Discrepancy
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="h-3 w-3" />
                        Matched
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};


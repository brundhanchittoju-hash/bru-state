import React, { useEffect, useState } from "react";
import { RotateCcw, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

const FACTOR_INFO: Record<string, { label: string; desc: string }> = {
  missing_documents: {
    label: "Missing Statutory Documents",
    desc: "Absence of mandatory sanction, work order, MB, or completion certs",
  },
  amount_difference: {
    label: "Payment Chain Amount Differences",
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

export const RiskWeightsTab: React.FC = () => {
  const [weights, setWeights] = useState<Record<string, number>>({
    missing_documents: 25,
    amount_difference: 20,
    duplicate_signals: 15,
    vendor_concentration: 10,
    unusual_amount: 10,
    record_incompleteness: 10,
    date_anomalies: 10,
  });
  const [reason, setReason] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const loadWeights = async () => {
    try {
      setLoading(true);
      const res = await api.get<{ weights: Record<string, number> }>("/verification/risk-weights");
      if (res && res.weights) {
        setWeights(res.weights);
      }
    } catch {
      toast.error("Failed to load risk factor weights.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWeights();
  }, []);

  const totalSum = Object.values(weights).reduce((a, b) => a + b, 0);
  const isValidSum = totalSum === 100;

  const handleSliderChange = (key: string, val: number) => {
    setWeights((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleSaveWeights = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidSum) {
      toast.error(`Factor weights must sum to exactly 100%. Current sum: ${totalSum}%`);
      return;
    }
    if (!reason.trim() || reason.trim().length < 3) {
      toast.error("Mandatory statutory reason required to update risk weights.");
      return;
    }

    setIsSaving(true);
    try {
      await api.put("/verification/risk-weights", {
        weights,
        reason: reason.trim(),
      });
      toast.success("Risk weights updated successfully.");
      setReason("");
      loadWeights();
    } catch (err: any) {
      toast.error(err.message || "Failed to save risk weights.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset all 7 risk factor weights to Karnataka statutory defaults?")) return;
    try {
      await api.post("/verification/risk-weights/reset");
      toast.success("Risk weights reset to statutory defaults (25/20/15/10/10/10/10).");
      loadWeights();
    } catch (err: any) {
      toast.error(err.message || "Failed to reset risk weights.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h3 className="font-display text-base font-semibold text-foreground">
            Case Risk Engine Weight Calibration (7 Factor Matrix)
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Calibrate the relative weighting of each statutory anomaly signal. The sum of all 7 factor weights must equal exactly 100%.
          </p>
        </div>

        {/* Live Sum Indicator */}
        <div
          className={`px-3 py-1.5 rounded-lg text-xs font-bold border flex items-center space-x-2 tabular-nums ${
            isValidSum
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
              : "bg-destructive/10 text-destructive border-destructive/30"
          }`}
        >
          {isValidSum ? (
            <>
              <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span>Total: 100% (Statutory Valid)</span>
            </>
          ) : (
            <>
              <AlertTriangle className="h-4 w-4 text-destructive" />
              <span>Total: {totalSum}% (Must equal 100%)</span>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground text-xs">Loading risk factor weights...</div>
      ) : (
        <form onSubmit={handleSaveWeights} className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 space-y-6">
          {Object.entries(FACTOR_INFO).map(([key, meta]) => {
            const weightVal = weights[key] ?? 10;

            return (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-foreground block">
                      {meta.label}
                    </span>
                    <span className="text-[11px] text-muted-foreground">{meta.desc}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-base font-bold font-mono tabular-nums text-primary w-12 text-right">
                      {weightVal}%
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <input
                    type="range"
                    min="0"
                    max="50"
                    step="1"
                    value={weightVal}
                    onChange={(e) => handleSliderChange(key, parseInt(e.target.value, 10))}
                    className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Change Reason & Submit Bar */}
        <div className="bg-muted/40 p-4 rounded-xl border border-border space-y-3">
          <div>
            <label className="font-semibold text-xs text-foreground block mb-1">
              Statutory Justification for Weight Update <span className="text-destructive">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Cite departmental gazette notification, special audit circular, or directorate instructions justifying weight changes..."
              rows={2}
              className="w-full p-2.5 bg-background border border-input rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-destructive space-x-1"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset to Defaults</span>
            </button>

            <button
              type="submit"
              disabled={isSaving || !isValidSum || !reason.trim()}
              className="px-5 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-lg font-semibold text-xs transition-colors"
            >
              {isSaving ? "Saving Weights..." : "Save Risk Factor Weights"}
            </button>
          </div>
        </div>
      </form>
      )}
    </div>
  );
};

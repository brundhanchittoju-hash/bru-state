import React, { useState } from "react";
import { ArrowRight, CheckCircle2, AlertCircle, Search } from "lucide-react";
import { ReconciliationMatrixItem } from "@/types";

interface ReconciliationMatrixProps {
  items: ReconciliationMatrixItem[];
  onSelectBill?: (billId: string) => void;
}

export const ReconciliationMatrix: React.FC<ReconciliationMatrixProps> = ({
  items,
  onSelectBill,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const formatCurrency = (amt?: number | null) => {
    if (amt === undefined || amt === null) return "—";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amt);
  };

  const filteredItems = items.filter((item) => {
    if (filterStatus !== "all" && item.status !== filterStatus) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const bNum = (item.bill_number || "").toLowerCase();
      const vNum = (item.voucher_number || "").toLowerCase();
      const bankRef = (item.bank_reference || "").toLowerCase();
      return bNum.includes(q) || vNum.includes(q) || bankRef.includes(q);
    }
    return true;
  });

  const fullyMatchedCount = items.filter((i) => i.status === "fully_matched").length;
  const partialCount = items.filter((i) => i.status === "partially_matched").length;
  const unmatchedCount = items.filter((i) => i.status === "unmatched").length;
  const matchRate = items.length > 0 ? Math.round((fullyMatchedCount / items.length) * 100) : 100;

  return (
    <div className="bg-card border border-border rounded-xl p-6 space-y-6">
      {/* Header & Match Rate Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="font-display font-semibold text-foreground text-base">
              Payment Chain Reconciliation Matrix
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold tabular-nums bg-accent text-accent-foreground border border-primary/25">
              {matchRate}% Reconciled
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Deterministic 3-way reconciliation across Vendor Bills, Passed Vouchers, and Treasury Bank Debits.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1 bg-muted p-1 rounded-lg text-xs font-medium">
          <button
            onClick={() => setFilterStatus("all")}
            className={`px-2.5 py-1 rounded-md transition-colors tabular-nums ${
              filterStatus === "all"
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All ({items.length})
          </button>
          <button
            onClick={() => setFilterStatus("fully_matched")}
            className={`px-2.5 py-1 rounded-md transition-colors tabular-nums ${
              filterStatus === "fully_matched"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-muted-foreground hover:text-emerald-600"
            }`}
          >
            Matched ({fullyMatchedCount})
          </button>
          <button
            onClick={() => setFilterStatus("partially_matched")}
            className={`px-2.5 py-1 rounded-md transition-colors tabular-nums ${
              filterStatus === "partially_matched"
                ? "bg-amber-600 text-white shadow-sm"
                : "text-muted-foreground hover:text-signal"
            }`}
          >
            Partial ({partialCount})
          </button>
          <button
            onClick={() => setFilterStatus("unmatched")}
            className={`px-2.5 py-1 rounded-md transition-colors tabular-nums ${
              filterStatus === "unmatched"
                ? "bg-red-600 text-white shadow-sm"
                : "text-muted-foreground hover:text-red-600"
            }`}
          >
            Unmatched ({unmatchedCount})
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by Bill No, Voucher No, or Bank Ref..."
          className="w-full pl-9 pr-3 py-1.5 bg-background border border-input rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>

      {/* Reconciliation Table */}
      <div className="border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Stage 1: Vendor Bill</th>
                <th className="py-3 px-2 text-center"></th>
                <th className="py-3 px-4">Stage 2: Passed Voucher</th>
                <th className="py-3 px-2 text-center"></th>
                <th className="py-3 px-4">Stage 3: Bank Debit (UTR)</th>
                <th className="py-3 px-4">Variance / Delta</th>
                <th className="py-3 px-4 text-right">Reconciliation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-muted-foreground">
                    No payment chains match the selected filter.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, idx) => {
                  const hasBill = !!item.bill_number;
                  const hasVoucher = !!item.voucher_number;
                  const hasBank = !!item.bank_reference;

                  // Compute variance
                  let delta = 0;
                  if (item.bill_amount && item.voucher_amount) {
                    delta = Math.abs(item.bill_amount - item.voucher_amount);
                  } else if (item.voucher_amount && item.bank_amount) {
                    delta = Math.abs(item.voucher_amount - item.bank_amount);
                  }

                  return (
                    <tr
                      key={idx}
                      className="hover:bg-muted/40 transition-colors cursor-pointer"
                      onClick={() => item.bill_id && onSelectBill && onSelectBill(item.bill_id)}
                    >
                      {/* Bill */}
                      <td className="py-3 px-4">
                        {hasBill ? (
                          <div>
                            <div className="font-semibold text-foreground">
                              {item.bill_number}
                            </div>
                            <div className="text-primary font-mono text-[11px] tabular-nums">
                              {formatCurrency(item.bill_amount)}
                            </div>
                          </div>
                        ) : (
                          <span className="text-muted-foreground italic">No bill record</span>
                        )}
                      </td>

                      {/* Arrow 1 */}
                      <td className="py-3 px-2 text-center text-muted-foreground">
                        <ArrowRight className="h-3.5 w-3.5 inline" />
                      </td>

                      {/* Voucher */}
                      <td className="py-3 px-4">
                        {hasVoucher ? (
                          <div>
                            <div className="font-semibold text-foreground">
                              {item.voucher_number}
                            </div>
                            <div className="text-muted-foreground font-mono text-[11px] tabular-nums">
                              {formatCurrency(item.voucher_amount)}
                            </div>
                          </div>
                        ) : (
                          <span className="text-signal italic text-[11px]">
                            Pending Voucher Link
                          </span>
                        )}
                      </td>

                      {/* Arrow 2 */}
                      <td className="py-3 px-2 text-center text-muted-foreground">
                        <ArrowRight className="h-3.5 w-3.5 inline" />
                      </td>

                      {/* Bank Debit */}
                      <td className="py-3 px-4">
                        {hasBank ? (
                          <div>
                            <div className="font-semibold text-foreground font-mono">
                              {item.bank_reference}
                            </div>
                            <div className="text-muted-foreground font-mono text-[11px] tabular-nums">
                              {formatCurrency(item.bank_amount)}
                            </div>
                          </div>
                        ) : (
                          <span className="text-red-600 dark:text-red-400 italic text-[11px]">
                            Uncleared in Bank
                          </span>
                        )}
                      </td>

                      {/* Variance */}
                      <td className="py-3 px-4">
                        {delta > 0.01 ? (
                          <span className="px-2 py-0.5 rounded text-xs font-mono font-bold tabular-nums bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/20">
                            +{formatCurrency(delta)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground font-mono tabular-nums text-xs">₹0.00</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 text-right">
                        {item.status === "fully_matched" && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Fully Reconciled
                          </span>
                        )}
                        {item.status === "partially_matched" && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-signal-surface text-signal border border-signal/25">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Partial Match
                          </span>
                        )}
                        {item.status === "unmatched" && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/20">
                            <AlertCircle className="h-3 w-3 mr-1" />
                            Unmatched
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

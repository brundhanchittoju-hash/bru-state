import React from "react";
import { Building2, AlertTriangle, ShieldCheck } from "lucide-react";
import { VendorConcentrationItem } from "@/types";

interface VendorConcentrationCardProps {
  vendors: VendorConcentrationItem[];
  totalExpenditure: number;
}

export const VendorConcentrationCard: React.FC<VendorConcentrationCardProps> = ({
  vendors,
  totalExpenditure,
}) => {
  const formatCurrency = (amt: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(amt);
  };

  // Check if top vendor or top 3 exceed statutory vigilance thresholds
  const top1Share = vendors.length > 0 ? vendors[0].spend_share_pct : 0;
  const top3Share = vendors.slice(0, 3).reduce((sum, v) => sum + v.spend_share_pct, 0);

  const isDominantAlert = top1Share >= 40.0 || top3Share >= 70.0;

  return (
    <div className="bg-card border border-border rounded-xl p-6 space-y-5">
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center space-x-2">
          <Building2 className="h-5 w-5 text-primary" />
          <h3 className="font-display font-semibold text-foreground text-base">
            Vendor Expenditure Concentration
          </h3>
        </div>
        {isDominantAlert ? (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-signal-surface text-signal border border-signal/30">
            <AlertTriangle className="h-3.5 w-3.5 mr-1" />
            Concentration Alert (&gt;40%)
          </span>
        ) : (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20">
            <ShieldCheck className="h-3.5 w-3.5 mr-1" />
            Balanced Distribution
          </span>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        Top payees evaluated under statutory procurement vigilance rules (Karnataka Transparency in Public Procurements Act).
      </p>

      {vendors.length === 0 ? (
        <div className="text-center py-6 text-muted-foreground text-xs">
          No vendor disbursements recorded for this case.
        </div>
      ) : (
        <div className="space-y-4">
          {vendors.map((vendor, idx) => {
            const isHigh = vendor.spend_share_pct >= 40.0;

            return (
              <div key={vendor.vendor_id || idx} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2 truncate pr-2">
                    <span className="font-mono text-[11px] text-muted-foreground font-bold tabular-nums">
                      #{idx + 1}
                    </span>
                    <span className="font-semibold text-foreground truncate">
                      {vendor.vendor_name}
                    </span>
                    {vendor.is_flagged && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/20">
                        Flagged
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-3 shrink-0">
                    <span className="text-muted-foreground font-mono text-[11px] tabular-nums">
                      {vendor.payment_count} {vendor.payment_count === 1 ? "payment" : "payments"}
                    </span>
                    <span className="font-bold text-foreground font-mono tabular-nums">
                      {formatCurrency(vendor.total_spend)}
                    </span>
                    <span
                      className={`font-mono text-xs font-bold w-12 text-right tabular-nums ${
                        isHigh ? "text-red-600 dark:text-red-400" : "text-primary"
                      }`}
                    >
                      {vendor.spend_share_pct.toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Spend Share Bar */}
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all duration-500 ${
                      isHigh
                        ? "bg-red-500"
                        : vendor.spend_share_pct >= 25
                        ? "bg-amber-500"
                        : "bg-primary"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(3, vendor.spend_share_pct))}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Statutory Footer note */}
      <div className="pt-2 text-[11px] text-muted-foreground flex items-center justify-between border-t border-border">
        <span>KTPP Act Rule 14 &bull; Vendor Monopoly Guard</span>
        <span className="font-mono tabular-nums">Total Evaluated: {formatCurrency(totalExpenditure)}</span>
      </div>
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { Building2, Check, X, ArrowRight } from "lucide-react";
import { PendingVendorAlias } from "@/types";
import { api } from "@/lib/api";
import { toast } from "sonner";

export const VendorReviewTab: React.FC = () => {
  const [aliases, setAliases] = useState<PendingVendorAlias[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionId, setActionId] = useState<string | null>(null);

  const loadPendingAliases = async () => {
    try {
      setLoading(true);
      const res = await api.get<PendingVendorAlias[]>("/verification/vendors/pending");
      setAliases(res);
    } catch {
      toast.error("Failed to load pending vendor aliases.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPendingAliases();
  }, []);

  const handleConfirm = async (id: string, aliasName: string) => {
    setActionId(id);
    try {
      await api.post(`/verification/vendors/aliases/${id}/confirm`);
      toast.success(`Confirmed alias merge: '${aliasName}'`);
      loadPendingAliases();
    } catch (err: any) {
      toast.error(err.message || "Failed to confirm alias.");
    } finally {
      setActionId(null);
    }
  };

  const handleReject = async (id: string, aliasName: string) => {
    setActionId(id);
    try {
      await api.post(`/verification/vendors/aliases/${id}/reject`);
      toast.info(`Rejected alias: '${aliasName}'`);
      loadPendingAliases();
    } catch (err: any) {
      toast.error(err.message || "Failed to reject alias.");
    } finally {
      setActionId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h3 className="font-display text-base font-semibold text-foreground">
            Pending Vendor Alias Reviews ({aliases.length})
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Fuzzy matching suggestions (token sort ratio &ge; 88%) requiring human auditor confirmation before merging financial profiles.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground text-xs">Loading pending aliases...</div>
      ) : aliases.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center space-y-2">
          <Building2 className="h-8 w-8 text-muted-foreground mx-auto" />
          <h4 className="font-display text-sm font-semibold text-foreground">
            No Pending Vendor Aliases
          </h4>
          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
            All extracted vendor names have either been automatically resolved via GSTIN/PAN or previously confirmed by an auditor.
          </p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
                <tr>
                  <th className="py-3 px-4">Raw Extracted String</th>
                  <th className="py-3 px-2 text-center"></th>
                  <th className="py-3 px-4">Canonical Vendor Match</th>
                  <th className="py-3 px-4">Match Algorithm</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4 text-right">Auditor Determination</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {aliases.map((item) => (
                  <tr key={item.id} className="hover:bg-muted/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-foreground">
                      &ldquo;{item.alias_name}&rdquo;
                    </td>
                    <td className="py-3 px-2 text-center text-muted-foreground">
                      <ArrowRight className="h-3.5 w-3.5 inline" />
                    </td>
                    <td className="py-3 px-4 font-semibold text-primary">
                      {item.vendor_name}
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                      {item.match_method}
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-primary tabular-nums">
                      {item.confidence_score.toFixed(1)}%
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleConfirm(item.id, item.alias_name)}
                        disabled={actionId === item.id}
                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded text-xs font-semibold inline-flex items-center space-x-1"
                      >
                        <Check className="h-3.5 w-3.5" />
                        <span>Confirm Merge</span>
                      </button>
                      <button
                        onClick={() => handleReject(item.id, item.alias_name)}
                        disabled={actionId === item.id}
                        className="px-3 py-1 bg-muted hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50 text-foreground rounded text-xs font-semibold transition-colors inline-flex items-center space-x-1"
                      >
                        <X className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

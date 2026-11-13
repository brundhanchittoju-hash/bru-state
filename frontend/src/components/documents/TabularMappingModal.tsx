import React, { useState, useEffect } from "react";
import { CheckCircle, RefreshCw, FileSpreadsheet, ArrowRight } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ConfidenceBadge } from "@/components/documents/ConfidenceBadge";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface TabularMappingModalProps {
  isOpen: boolean;
  onClose: () => void;
  file: File | null;
  caseId: string;
  onSuccess?: () => void;
}

const CANONICAL_FIELDS: { key: string; label: string; required: boolean }[] = [
  { key: "date", label: "Transaction Date", required: true },
  { key: "reference", label: "Voucher / Reference No", required: false },
  { key: "description", label: "Particulars / Description", required: false },
  { key: "debit", label: "Debit Amount (Withdrawals)", required: false },
  { key: "credit", label: "Credit Amount (Deposits)", required: false },
  { key: "balance", label: "Closing / Net Balance", required: false },
  { key: "amount", label: "Total / Net Amount", required: false },
];

export const TabularMappingModal: React.FC<TabularMappingModalProps> = ({
  isOpen,
  onClose,
  file,
  caseId,
  onSuccess,
}) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState<number>(0);
  const [previewTransactions, setPreviewTransactions] = useState<any[]>([]);

  useEffect(() => {
    if (isOpen && file) {
      loadPreview(file);
    }
  }, [isOpen, file]);

  const loadPreview = async (selectedFile: File) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const res = await api.post<any>("/documents/tabular-preview", formData);

      setHeaders(res.headers || []);
      setMapping(res.mapping || {});
      setConfidence(res.confidence || 0);
      setPreviewTransactions(res.transactions || []);
    } catch (err: any) {
      toast.error(err.message || "Failed to parse tabular file preview.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMappingChange = (canonicalKey: string, headerValue: string) => {
    setMapping((prev) => {
      const updated = { ...prev };
      if (!headerValue) {
        delete updated[canonicalKey];
      } else {
        updated[canonicalKey] = headerValue;
      }
      return updated;
    });
  };

  const handleConfirmImport = async () => {
    if (!file || !caseId) return;

    if (!mapping.date) {
      toast.error("Please map the 'Transaction Date' column.");
      return;
    }
    if (!mapping.debit && !mapping.credit && !mapping.amount) {
      toast.error("Please map at least one financial amount column (Debit, Credit, or Total Amount).");
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Upload document into case
      const formData = new FormData();
      formData.append("file", file);
      formData.append("case_id", caseId);
      formData.append("title", file.name);
      formData.append("document_type", "Bank Statement"); // Default for tabular

      const uploadRes = await api.post<any>("/documents/upload", formData);
      const docId = uploadRes.id;

      // 2. Trigger tabular import using mapped columns
      const importRes = await api.post<any>(`/documents/${docId}/tabular-import`, {
        mapping: mapping,
      });

      toast.success(importRes.message || "Financial records imported successfully into case!");
      onSuccess?.();
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Failed to import tabular records.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between pr-6">
            <DialogTitle className="flex items-center gap-2 font-display">
              <FileSpreadsheet className="h-5 w-5 text-primary" />
              <span>Tabular Ledger & Bank Statement Column Mapping</span>
            </DialogTitle>
            {confidence > 0 && <ConfidenceBadge confidence={confidence} />}
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <RefreshCw className="h-7 w-7 text-primary animate-spin" />
            <p className="text-xs text-muted-foreground">Auto-detecting ledger column synonyms and structure...</p>
          </div>
        ) : (
          <div className="space-y-5 py-2">
            {/* Header info */}
            <div className="p-3 rounded-lg bg-muted/50 border border-border flex items-center justify-between text-xs">
              <div className="space-y-0.5">
                <p className="font-semibold text-foreground">
                  Source: <span className="font-mono text-primary">{file?.name}</span>
                </p>
                <p className="text-muted-foreground">
                  Detected {headers.length} headers across {previewTransactions.length}+ transaction rows
                </p>
              </div>
              <div className="text-right">
                <span className="text-[11px] font-mono text-muted-foreground">
                  Synonym Engine: Karnataka ZP Accounting Standards
                </span>
              </div>
            </div>

            {/* Column Mapping Selectors */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                1. Canonical Accounting Columns
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {CANONICAL_FIELDS.map((field) => {
                  const mappedHeader = mapping[field.key] || "";
                  return (
                    <div
                      key={field.key}
                      className="p-3 rounded-lg border border-border bg-card space-y-1.5 shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <label className="text-xs font-medium text-foreground">
                          {field.label} {field.required && <span className="text-rose-500">*</span>}
                        </label>
                        {mappedHeader && (
                          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                        )}
                      </div>
                      <select
                        value={mappedHeader}
                        onChange={(e) => handleMappingChange(field.key, e.target.value)}
                        className="w-full text-xs rounded-md border border-input bg-background px-2 py-1.5 text-foreground"
                      >
                        <option value="">-- Unmapped --</option>
                        {headers.map((h) => (
                          <option key={h} value={h}>
                            {h}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 5-Row Live Preview Table */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                2. Live Data Extraction Preview (First 5 Rows)
              </h4>
              <div className="rounded-lg border border-border overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted text-muted-foreground border-b border-border">
                    <tr>
                      <th className="p-2.5 font-medium">#</th>
                      <th className="p-2.5 font-medium">Date</th>
                      <th className="p-2.5 font-medium">Voucher / Ref</th>
                      <th className="p-2.5 font-medium">Description</th>
                      <th className="p-2.5 font-medium text-right">Debit (₹)</th>
                      <th className="p-2.5 font-medium text-right">Credit (₹)</th>
                      <th className="p-2.5 font-medium text-right">Balance (₹)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border font-mono text-[11px] tabular-nums">
                    {previewTransactions.slice(0, 5).map((t, idx) => (
                      <tr key={idx} className="hover:bg-muted/40">
                        <td className="p-2.5 text-muted-foreground">{t.row_number || idx + 1}</td>
                        <td className="p-2.5 text-foreground">{t.transaction_date || "-"}</td>
                        <td className="p-2.5 font-semibold text-primary">{t.voucher_no || "-"}</td>
                        <td className="p-2.5 max-w-[200px] truncate text-muted-foreground">
                          {t.description || "-"}
                        </td>
                        <td className="p-2.5 text-right text-rose-600 dark:text-rose-400">
                          {t.debit ? t.debit.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : "-"}
                        </td>
                        <td className="p-2.5 text-right text-emerald-600 dark:text-emerald-400">
                          {t.credit ? t.credit.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : "-"}
                        </td>
                        <td className="p-2.5 text-right text-foreground">
                          {t.balance ? t.balance.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmImport}
            disabled={isLoading || isSubmitting || !mapping.date}
          >
            {isSubmitting ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                Confirm Mapping & Ingest
                <ArrowRight className="h-4 w-4 ml-1.5" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

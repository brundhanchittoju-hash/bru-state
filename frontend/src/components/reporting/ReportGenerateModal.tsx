import React, { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, FileText, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { API_BASE, getAccessToken } from "@/lib/api";

interface ReportGenerateModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseNumber: string;
  caseTitle: string;
  onGenerated: () => void;
}

export const ReportGenerateModal: React.FC<ReportGenerateModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseNumber,
  caseTitle,
  onGenerated,
}) => {
  const { user } = useAuth();
  const [reportType, setReportType] = useState<"preliminary" | "interim" | "final">("preliminary");
  const [title, setTitle] = useState("");
  const [includesWatermark, setIncludesWatermark] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [checklist, setChecklist] = useState<any>(null);
  const [loadingChecklist, setLoadingChecklist] = useState(true);

  const canRemoveWatermark = ["senior_auditor", "audit_officer", "administrator"].includes(
    user?.role?.code || ""
  );

  useEffect(() => {
    if (!isOpen || !caseId) return;
    setTitle(`Statutory Financial Audit Report — ${caseTitle}`);
    setLoadingChecklist(true);

    const token = getAccessToken();
    fetch(`${API_BASE}/cases/${caseId}/reports/checklist`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        setChecklist(data);
      })
      .catch(() => {})
      .finally(() => setLoadingChecklist(false));
  }, [isOpen, caseId, caseTitle]);

  if (!isOpen) return null;

  const hasHighCriticalOpen = (checklist?.high_critical_open_count || 0) > 0;

  const handleGenerate = async () => {
    if (reportType === "final" && hasHighCriticalOpen) {
      toast.error("Cannot generate a Final report while high/critical findings remain open.");
      return;
    }

    try {
      setIsSubmitting(true);
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/cases/${caseId}/reports/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          report_type: reportType,
          title: title.trim() || undefined,
          includes_demo_watermark: includesWatermark,
          confirmed_checklist: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to generate report.");
      }

      toast.success("Statutory PDF report generated successfully with SHA-256 seal!");
      onGenerated();
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Report generation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-xl bg-card rounded-2xl shadow-2xl border border-border p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-accent text-primary border border-primary/20">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-foreground">
                Generate Statutory Audit Report
              </h3>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                Case: {caseNumber}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="h-8 w-8 p-0 rounded-full"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Pre-generation Checklist Banner */}
        {loadingChecklist ? (
          <div className="p-3 text-xs text-muted-foreground animate-pulse bg-muted/50 rounded-xl">
            Verifying case checklist and findings status...
          </div>
        ) : checklist ? (
          <div
            className={`p-3.5 rounded-xl border text-xs space-y-1.5 ${
              hasHighCriticalOpen
                ? "bg-signal-surface border-signal/30 text-signal"
                : "bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:text-emerald-200"
            }`}
          >
            <div className="flex items-center gap-2 font-semibold">
              {hasHighCriticalOpen ? (
                <AlertCircle className="h-4 w-4 text-signal" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              )}
              <span>Pre-generation Verification Checklist</span>
            </div>
            <p className="text-foreground/85 tabular-nums">
              Total findings: <b>{checklist.total_findings}</b> • High/Critical Open:{" "}
              <b>{checklist.high_critical_open_count}</b> • Unreviewed:{" "}
              <b>{checklist.unreviewed_count}</b>
            </p>
            {hasHighCriticalOpen && (
              <p className="text-signal text-[11px] font-medium">
                Note: "Final" report generation is blocked until all high/critical findings are
                resolved or closed. Preliminary and Interim reports may still be issued.
              </p>
            )}
          </div>
        ) : null}

        {/* Form Fields */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">
              Report Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full text-xs rounded-xl border border-input bg-background p-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">
              Report Type / Stage
            </label>
            <div className="grid grid-cols-3 gap-2">
              {(["preliminary", "interim", "final"] as const).map((type) => {
                const disabled = type === "final" && hasHighCriticalOpen;
                return (
                  <button
                    key={type}
                    type="button"
                    disabled={disabled}
                    onClick={() => setReportType(type)}
                    className={`py-2 px-3 text-xs font-medium rounded-xl border transition-all text-center capitalize ${
                      reportType === type
                        ? "border-primary bg-accent text-accent-foreground ring-1 ring-primary"
                        : disabled
                        ? "opacity-40 cursor-not-allowed border-border text-muted-foreground"
                        : "border-border text-foreground hover:bg-muted/50"
                    }`}
                  >
                    {type} {disabled && "(Blocked)"}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="p-3 rounded-xl border border-border bg-muted/40 flex items-start gap-3">
            <input
              type="checkbox"
              id="watermark_cb"
              checked={includesWatermark}
              disabled={!canRemoveWatermark}
              onChange={(e) => setIncludesWatermark(e.target.checked)}
              className="mt-0.5 rounded border-input text-primary focus:ring-ring"
            />
            <label htmlFor="watermark_cb" className="text-xs cursor-pointer select-none">
              <span className="font-semibold text-foreground">
                Include "DEMO DATA" diagonal watermark
              </span>
              <p className="text-muted-foreground text-[11px] mt-0.5">
                {canRemoveWatermark
                  ? "Unchecking produces an official clean publication copy (restricted to Senior Auditors & Officers)."
                  : "Watermark required for regular auditor drafts."}
              </p>
            </label>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={isSubmitting}
            className="gap-1.5"
          >
            <Sparkles className="h-4 w-4" />
            {isSubmitting ? "Generating PDF & Sealing..." : "Generate PDF Report"}
          </Button>
        </div>
      </div>
    </div>
  );
};

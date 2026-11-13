import React, { useState } from "react";
import { X, FileText, CheckCircle2, AlertTriangle, ExternalLink } from "lucide-react";
import { Finding } from "@/types";
import { apiClient } from "@/lib/api";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";

interface FindingDetailDrawerProps {
  finding: Finding | null;
  onClose: () => void;
  onStatusUpdated: (updated: Finding) => void;
  onNavigateToDocument?: (docId: string) => void;
}

export const FindingDetailDrawer: React.FC<FindingDetailDrawerProps> = ({
  finding,
  onClose,
  onStatusUpdated,
  onNavigateToDocument,
}) => {
  const [newStatus, setNewStatus] = useState<string>("");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!finding) return null;

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStatus) {
      setErrorMsg("Please select a status determination.");
      return;
    }
    if (reviewNotes.trim().length < 3) {
      setErrorMsg("Statutory justification notes (minimum 3 characters) are required.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await apiClient(`/findings/${finding.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          comments: reviewNotes.trim(),
        }),
      });
      onStatusUpdated({
        ...finding,
        status: newStatus as Finding["status"],
        review_notes: reviewNotes.trim(),
        data_changed_since_review: false,
      });
      setNewStatus("");
      setReviewNotes("");
    } catch (err: any) {
      setErrorMsg(err?.message || "Failed to update finding status.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatCurrency = (amt?: number | null) => {
    if (amt === undefined || amt === null) return "₹0.00";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(amt);
  };

  // Parse evidence
  let evidenceList: any[] = [];
  try {
    if (finding.evidence && finding.evidence.length > 0) {
      evidenceList = finding.evidence;
    } else if (finding.evidence_json) {
      evidenceList = JSON.parse(finding.evidence_json);
    }
  } catch {
    evidenceList = [];
  }

  // Parse inputs used
  let inputsUsed: Record<string, any> = {};
  try {
    if (finding.inputs_used_json) {
      inputsUsed = JSON.parse(finding.inputs_used_json);
    }
  } catch {
    inputsUsed = {};
  }

  // Parse thresholds used
  let thresholdsUsed: Record<string, any> = {};
  try {
    if (finding.thresholds_used_json) {
      thresholdsUsed = JSON.parse(finding.thresholds_used_json);
    }
  } catch {
    thresholdsUsed = {};
  }

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-sm animate-in fade-in duration-200 flex justify-end">
      <div className="w-full max-w-2xl bg-card h-full shadow-2xl flex flex-col border-l border-border animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-5 border-b border-border flex items-start justify-between bg-muted/30">
          <div className="space-y-1.5 pr-4">
            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
              <span className="font-mono text-xs font-bold text-foreground bg-muted px-2 py-0.5 rounded">
                {finding.finding_number}
              </span>
              <RiskBadge level={finding.risk_level} />
              <StatusPill status={finding.status} />
              <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-muted text-muted-foreground capitalize">
                {finding.category}
              </span>
            </div>
            <h3 className="font-display text-base font-bold text-foreground pt-1 leading-snug">
              {finding.title}
            </h3>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-foreground">
          {/* Changed Data Alert */}
          {finding.data_changed_since_review && (
            <div className="p-3.5 bg-signal-surface border border-signal/30 rounded-xl flex items-start space-x-3 text-signal">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold block">Underlying Data Modified Since Auditor Review</strong>
                <p className="mt-0.5 text-foreground/85">
                  Source documents, manual overrides, or financial records associated with this finding were updated after the previous auditor sign-off. Please review the updated calculations below.
                </p>
              </div>
            </div>
          )}

          {/* Amount at Risk Metric Card */}
          <div className="bg-muted/40 p-4 rounded-xl border border-border flex items-center justify-between">
            <div>
              <span className="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-wider block">
                Statutory Amount at Risk
              </span>
              <span className="text-2xl font-bold text-foreground font-mono tabular-nums">
                {formatCurrency(finding.amount_at_risk)}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-wider block">
                Engine Confidence
              </span>
              <span className="text-lg font-bold text-primary font-mono tabular-nums">
                {finding.confidence?.toFixed(0) || 100}%
              </span>
            </div>
          </div>

          {/* Plain Language Factual Description */}
          <div className="space-y-1.5">
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
              Observation &amp; Non-Compliance Details
            </h4>
            <p className="text-foreground/90 leading-relaxed bg-muted/30 p-3.5 rounded-xl border border-border">
              {finding.description}
            </p>
          </div>

          {/* Statutory Plain-Language Reason */}
          <div className="space-y-1.5">
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
              Statutory Basis &amp; Compliance Rule
            </h4>
            <div className="p-3.5 bg-accent/50 border border-primary/25 rounded-xl text-foreground leading-relaxed">
              {finding.reason}
            </div>
          </div>

          {/* Mathematical Calculation Formula */}
          <div className="space-y-1.5">
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
              Deterministic Mathematical Calculation
            </h4>
            <div className="p-3.5 bg-zinc-950 text-indigo-300 font-mono rounded-xl text-[11px] leading-relaxed border border-border">
              {finding.calculation}
            </div>
          </div>

          {/* Evidence Items */}
          <div className="space-y-2">
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
              Supporting Record Evidence ({evidenceList.length})
            </h4>

            {evidenceList.length === 0 ? (
              <p className="text-muted-foreground italic">No specific document references linked.</p>
            ) : (
              <div className="space-y-2">
                {evidenceList.map((ev, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-muted/30 rounded-xl border border-border flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-primary" />
                      <div>
                        <span className="font-semibold text-foreground">
                          {ev.document_number ? `Doc: ${ev.document_number}` : `Record ID: ${ev.record_id || "N/A"}`}
                        </span>
                        {ev.row && (
                          <span className="ml-2 text-[11px] text-muted-foreground font-mono tabular-nums">
                            (Row #{ev.row})
                          </span>
                        )}
                      </div>
                    </div>

                    {ev.document_id && onNavigateToDocument && (
                      <button
                        onClick={() => onNavigateToDocument(ev.document_id)}
                        className="inline-flex items-center text-primary hover:underline font-medium"
                      >
                        <span>Open Document</span>
                        <ExternalLink className="h-3 w-3 ml-1" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Parameters & Thresholds Used */}
          {(Object.keys(thresholdsUsed).length > 0 || Object.keys(inputsUsed).length > 0) && (
            <div className="space-y-2">
              <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
                Statutory Thresholds &amp; Inputs Snapshot
              </h4>
              <div className="p-3 bg-muted/30 rounded-xl border border-border font-mono text-[11px] space-y-1">
                {Object.entries(thresholdsUsed).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-muted-foreground">
                    <span>threshold.{k}:</span>
                    <span className="font-semibold text-foreground tabular-nums">{String(v)}</span>
                  </div>
                ))}
                {Object.entries(inputsUsed).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-muted-foreground">
                    <span>input.{k}:</span>
                    <span className="font-semibold text-foreground tabular-nums">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Existing Review Status History */}
          {finding.reviewed_by_name && (
            <div className="p-3.5 bg-muted/40 rounded-xl border border-border space-y-1.5">
              <div className="flex items-center space-x-1.5 text-primary font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                <span>Auditor Review on Record: {finding.status}</span>
              </div>
              <p className="text-foreground/85 italic">
                &ldquo;{finding.review_notes}&rdquo;
              </p>
              <div className="text-[11px] text-muted-foreground flex items-center justify-between pt-1">
                <span>Auditor: {finding.reviewed_by_name}</span>
                <span className="font-mono tabular-nums">{finding.reviewed_at ? new Date(finding.reviewed_at).toLocaleString() : ""}</span>
              </div>
            </div>
          )}

          {/* Auditor Review Action Form */}
          <form onSubmit={handleStatusSubmit} className="pt-4 border-t border-border space-y-3">
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-muted-foreground font-mono">
              Update Finding Review Status
            </h4>

            {errorMsg && (
              <div className="p-2.5 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg text-xs font-medium">
                {errorMsg}
              </div>
            )}

            <div className="space-y-1">
              <label className="font-medium text-foreground">
                Action / Disposition
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full p-2 bg-background border border-input rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">Select Auditor Determination...</option>
                <option value="Confirmed">Confirmed (Draft into Audit Observation / Paras)</option>
                <option value="Under Review">Under Review (Requires departmental explanation)</option>
                <option value="Dismissed">Dismissed (Valid statutory exception confirmed)</option>
                <option value="Escalated">Escalated (Referred to Directorate of Municipal Audit)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="font-medium text-foreground">
                Auditor Justification &amp; Notes <span className="text-destructive">*</span>
              </label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Enter statutory justification, verified vouchers, or grounds for dismissal/escalation..."
                rows={3}
                className="w-full p-2.5 bg-background border border-input rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !newStatus}
              className="w-full py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-lg font-semibold text-xs transition-colors flex items-center justify-center space-x-1.5"
            >
              {isSubmitting ? "Recording Audit Sign-Off..." : "Save Auditor Determination"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

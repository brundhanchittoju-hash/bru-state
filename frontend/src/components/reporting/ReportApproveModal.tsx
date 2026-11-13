import React, { useState } from "react";
import { CheckCircle2, ShieldCheck, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { API_BASE, getAccessToken } from "@/lib/api";

interface ReportApproveModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId: string | null;
  reportNumber: string;
  onApproved: () => void;
}

export const ReportApproveModal: React.FC<ReportApproveModalProps> = ({
  isOpen,
  onClose,
  reportId,
  reportNumber,
  onApproved,
}) => {
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen || !reportId) return null;

  const handleApprove = async () => {
    if (!comment.trim()) {
      toast.error("An approval review remark is required for statutory sign-off.");
      return;
    }

    try {
      setIsSubmitting(true);
      const token = getAccessToken();
      const res = await fetch(`${API_BASE}/reports/${reportId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: json_payload({ comment: comment.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to approve audit report.");
      }

      toast.success(`Report ${reportNumber} approved and digitally stamped.`);
      onApproved();
      onClose();
    } catch (err: any) {
      toast.error(err.message || "Approval failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-lg bg-card rounded-2xl shadow-2xl border border-border p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-accent text-primary border border-primary/20">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-display text-base font-semibold text-foreground">
                Statutory Report Dual Sign-off
              </h3>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                {reportNumber}
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

        <div className="p-3.5 rounded-xl bg-signal-surface border border-signal/30 text-xs text-foreground/90 leading-relaxed">
          <p className="font-semibold text-signal mb-1">Dual-Custody Certification Statement:</p>
          I hereby certify as Senior Auditor / Audit Officer that I have examined the findings,
          verified the supporting annexures, and confirm that all determinations comply with the
          Karnataka Gram Swaraj and Panchayat Raj Act & KTPP Act guidelines.
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">
            Sign-off Remarks & Scrutiny Notes <span className="text-destructive">*</span>
          </label>
          <textarea
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="e.g. Scrutinized all high-risk items; Gram Panchayat responses verified against cash book."
            className="w-full text-xs rounded-xl border border-input bg-background p-3 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isSubmitting || !comment.trim()}
            className="gap-1.5"
          >
            <CheckCircle2 className="h-4 w-4" />
            {isSubmitting ? "Digitally Signing..." : "Confirm & Sign Report"}
          </Button>
        </div>
      </div>
    </div>
  );
};

function json_payload(data: any) {
  return JSON.stringify(data);
}

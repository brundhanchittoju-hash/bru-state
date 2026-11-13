import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface FindingActionDialogsProps {
  actionType: string | null;
  findingNumber: string;
  isHighOrCritical: boolean;
  currentUserRole?: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (action: string, comment: string, targetStatus?: string) => Promise<void>;
}

export const FindingActionDialogs: React.FC<FindingActionDialogsProps> = ({
  actionType,
  findingNumber,
  isHighOrCritical,
  currentUserRole,
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [comment, setComment] = useState("");
  const [targetStatus, setTargetStatus] = useState("Confirmed");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!actionType) return null;

  const isAuditor = currentUserRole?.toLowerCase() === "auditor";
  const willTriggerMakerChecker = isAuditor && isHighOrCritical && ["confirm", "dismiss"].includes(actionType);

  const getTitle = () => {
    switch (actionType) {
      case "confirm":
        return `Confirm Finding ${findingNumber}`;
      case "dismiss":
        return `Dismiss Finding ${findingNumber}`;
      case "needs_clarification":
        return `Request Clarification for ${findingNumber}`;
      case "escalate":
        return `Escalate Finding ${findingNumber}`;
      case "approve":
        return `Maker-Checker Approval: ${findingNumber}`;
      case "reject":
        return `Reject Pending Approval for ${findingNumber}`;
      case "reopen":
        return `Reopen Finding ${findingNumber}`;
      default:
        return `Action on ${findingNumber}`;
    }
  };

  const getDescription = () => {
    if (willTriggerMakerChecker) {
      return `This is a ${isHighOrCritical ? "High/Critical" : ""} risk statutory finding. As an Auditor, your determination will transition the finding to 'Pending Approval' for dual-custody review by a Senior Auditor or Audit Officer.`;
    }
    switch (actionType) {
      case "confirm":
        return "Record your statutory determination that this anomaly is substantiated by audit evidence.";
      case "dismiss":
        return "Provide a valid statutory justification for dismissing this flagged anomaly.";
      case "needs_clarification":
        return "Specify what additional documentation or explanation is required from the auditee institution.";
      case "escalate":
        return "Route this finding to the Senior Auditor and Audit Officer priority queue for guidance.";
      case "approve":
        return "Provide senior sign-off to formally confirm or dismiss this finding. This action is cryptographically hash-chained.";
      case "reject":
        return "Provide feedback explaining why the proposed finding resolution was returned to Open status.";
      case "reopen":
        return "State the statutory basis (e.g. newly discovered vouchers, revised sanction) for reopening this finding.";
      default:
        return "Provide mandatory justification for this audit determination.";
    }
  };

  const handleSubmit = async () => {
    if (comment.trim().length < 5) {
      setError("A justification comment of at least 5 characters is mandatory.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onSubmit(actionType, comment.trim(), targetStatus);
      setComment("");
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to submit review action.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-card border border-border">
        <DialogHeader>
          <DialogTitle className="font-display text-base font-bold text-foreground">
            {getTitle()}
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground mt-1">
            {getDescription()}
          </DialogDescription>
        </DialogHeader>

        {actionType === "approve" && (
          <div className="space-y-1.5 my-2">
            <label className="text-xs font-semibold text-foreground">
              Approved Disposition:
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="radio"
                  name="approvalDisposition"
                  checked={targetStatus === "Confirmed"}
                  onChange={() => setTargetStatus("Confirmed")}
                  className="accent-primary focus:ring-ring"
                />
                <span className="font-medium text-foreground">Confirmed</span>
              </label>
              <label className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="radio"
                  name="approvalDisposition"
                  checked={targetStatus === "Dismissed"}
                  onChange={() => setTargetStatus("Dismissed")}
                  className="accent-primary focus:ring-ring"
                />
                <span className="font-medium text-foreground">Dismissed</span>
              </label>
            </div>
          </div>
        )}

        <div className="space-y-2 py-2">
          <label className="text-xs font-semibold text-foreground">
            Justification Comment <span className="text-rose-500">*</span>
          </label>
          <textarea
            value={comment}
            onChange={(e) => {
              setComment(e.target.value);
              if (error) setError(null);
            }}
            placeholder="Document detailed statutory justification (minimum 5 characters)..."
            rows={4}
            className="w-full text-xs p-2.5 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {error && <p className="text-xs text-rose-500">{error}</p>}
        </div>

        <DialogFooter className="flex items-center justify-end gap-2 pt-2 border-t border-border">
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isSubmitting || comment.trim().length < 5}
          >
            {isSubmitting ? "Recording..." : "Submit Determination"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};


import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Lock, ShieldCheck, UserCheck, ExternalLink } from "lucide-react";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";

interface FindingHeaderProps {
  finding: any;
  currentUserId?: string;
  currentUserRole?: string;
  onOpenAction: (action: string) => void;
}

export const FindingHeader: React.FC<FindingHeaderProps> = ({
  finding,
  currentUserRole,
  onOpenAction,
}) => {
  const isLocked = finding.is_case_locked;
  const isPendingApproval = finding.status === "Pending Approval";
  const isSeniorOrAbove = ["senior_auditor", "audit_officer", "administrator"].includes(
    currentUserRole?.toLowerCase() || ""
  );

  return (
    <div className="space-y-3 border-b border-border pb-4">
      {/* Statutory Banner */}
      <div className="flex items-center justify-between gap-3 bg-accent/70 border border-primary/20 px-4 py-2 rounded-xl text-xs font-medium text-accent-foreground">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary shrink-0" />
          <span>Flagged for review. Final determination rests with the auditor.</span>
        </div>
        <span className="font-mono text-[10px] bg-card px-2 py-0.5 rounded border border-border text-primary">
          KAR-SAI-RPR
        </span>
      </div>

      {/* Case Locked Alert if applicable */}
      {isLocked && (
        <div className="flex items-center gap-2 bg-signal-surface border border-signal-border px-4 py-2 rounded-xl text-xs text-signal">
          <Lock className="h-4 w-4 shrink-0" />
          <span>Case {finding.case_number} is locked (Approved/Closed). Finding determinations are read-only.</span>
        </div>
      )}

      {/* Data Changed Alert */}
      {finding.data_changed_since_review && (
        <div className="flex items-center gap-2 bg-accent border border-primary/25 px-4 py-2 rounded-xl text-xs text-accent-foreground">
          <AlertTriangle className="h-4 w-4 text-primary shrink-0" />
          <span>Data changed since last review. Re-run verification recommended to synchronize evidence.</span>
        </div>
      )}

      {/* Main Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-mono text-sm font-bold text-primary">
              {finding.finding_number}
            </span>
            <RiskBadge level={finding.risk_level} />
            <StatusPill status={finding.status} />
            <span className="text-xs px-2 py-0.5 rounded bg-muted font-mono text-muted-foreground border border-border">
              Rule: {finding.rule_code || finding.rule_id}
            </span>
          </div>
          <h1 className="font-display text-xl font-bold text-foreground mt-1">
            {finding.title}
          </h1>
          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1 flex-wrap">
            <span>
              Case:{" "}
              <Link
                to={`/cases/${finding.case_id}`}
                className="text-primary hover:underline font-mono inline-flex items-center gap-1"
              >
                {finding.case_number}
                <ExternalLink className="h-3 w-3" />
              </Link>
            </span>
            <span>•</span>
            <span>Department: {finding.department_name || "General"}</span>
            <span>•</span>
            <span>District: {finding.district || "Karnataka"}</span>
            <span>•</span>
            <span>Assigned: {finding.assigned_auditor_name || "Unassigned"}</span>
          </div>
        </div>

        {/* Action Buttons */}
        {!isLocked && (
          <div className="flex items-center gap-2 flex-wrap">
            {isPendingApproval && isSeniorOrAbove ? (
              <>
                <Button
                  size="sm"
                  variant="default"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => onOpenAction("approve")}
                >
                  <UserCheck className="h-4 w-4 mr-1.5" />
                  Approve Finding
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-rose-300 text-rose-600 hover:bg-rose-50 dark:border-rose-800 dark:text-rose-400 dark:hover:bg-rose-950/40"
                  onClick={() => onOpenAction("reject")}
                >
                  Reject & Return
                </Button>
              </>
            ) : (
              <>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => onOpenAction("confirm")}
                >
                  Confirm
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onOpenAction("dismiss")}
                >
                  Dismiss
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-signal-border text-signal hover:bg-signal-surface/50"
                  onClick={() => onOpenAction("needs_clarification")}
                >
                  Needs Clarification
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="border-primary/30 text-primary hover:bg-accent"
                  onClick={() => onOpenAction("escalate")}
                >
                  Escalate
                </Button>
                {["Confirmed", "Dismissed"].includes(finding.status) && isSeniorOrAbove && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onOpenAction("reopen")}
                  >
                    Reopen
                  </Button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

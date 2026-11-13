import React from "react";
import { Flag } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusPillProps {
  status: string;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, className }) => {
  const normalized = (status || "").toLowerCase().replace(/\s+/g, "_");

  const configs: Record<
    string,
    { label: string; dot: string; bg: string; text: string; border: string; flagged?: boolean }
  > = {
    flagged_for_review: {
      label: "Flagged for Review",
      dot: "bg-amber-600 dark:bg-amber-400",
      bg: "bg-amber-500/12 dark:bg-amber-500/15",
      text: "text-amber-900 dark:text-amber-200",
      border: "border-amber-500/40",
      flagged: true,
    },
    recommended_for_review: {
      label: "Recommended for Review",
      dot: "bg-orange-600 dark:bg-orange-400",
      bg: "bg-orange-500/12 dark:bg-orange-500/15",
      text: "text-orange-900 dark:text-orange-200",
      border: "border-orange-500/40",
      flagged: true,
    },
    under_review: {
      label: "Under Review",
      dot: "bg-sky-600 dark:bg-sky-400",
      bg: "bg-sky-500/10 dark:bg-sky-500/15",
      text: "text-sky-900 dark:text-sky-300",
      border: "border-sky-500/30",
    },
    in_progress: {
      label: "In Progress",
      dot: "bg-primary",
      bg: "bg-primary/10 dark:bg-primary/15",
      text: "text-primary dark:text-cobalt-200",
      border: "border-primary/30",
    },
    draft: {
      label: "Draft",
      dot: "bg-muted-foreground",
      bg: "bg-muted",
      text: "text-foreground/80",
      border: "border-border",
    },
    officer_review: {
      label: "Officer Review",
      dot: "bg-indigo-600 dark:bg-indigo-400",
      bg: "bg-indigo-500/10 dark:bg-indigo-500/15",
      text: "text-indigo-900 dark:text-indigo-300",
      border: "border-indigo-500/30",
    },
    completed: {
      label: "Completed",
      dot: "bg-emerald-600 dark:bg-emerald-400",
      bg: "bg-emerald-500/10 dark:bg-emerald-500/15",
      text: "text-emerald-900 dark:text-emerald-300",
      border: "border-emerald-500/30",
    },
    resolved: {
      label: "Resolved",
      dot: "bg-emerald-600 dark:bg-emerald-400",
      bg: "bg-emerald-500/10 dark:bg-emerald-500/15",
      text: "text-emerald-900 dark:text-emerald-300",
      border: "border-emerald-500/30",
    },
    dismissed: {
      label: "Dismissed with Cause",
      dot: "bg-muted-foreground",
      bg: "bg-muted/70",
      text: "text-muted-foreground",
      border: "border-border",
    },
  };

  const config = configs[normalized] || {
    label: (status || "Unknown").replace(/_/g, " "),
    dot: "bg-muted-foreground",
    bg: "bg-muted",
    text: "text-foreground/80",
    border: "border-border",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border select-none",
        config.flagged && "font-semibold tracking-tight",
        config.bg,
        config.text,
        config.border,
        className
      )}
    >
      {config.flagged ? (
        <Flag className="w-3 h-3 shrink-0" aria-hidden="true" />
      ) : (
        <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", config.dot)} aria-hidden="true" />
      )}
      {config.label}
    </span>
  );
};

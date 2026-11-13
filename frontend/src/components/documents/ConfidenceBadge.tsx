import React from "react";
import { CheckCircle2, Check, AlertTriangle } from "lucide-react";

export interface ConfidenceDetails {
  level: "high" | "medium" | "low";
  label: string;
  badgeClass: string;
  textClass: string;
  icon: React.ReactNode;
}

export function getConfidenceDetails(confidence: number): ConfidenceDetails {
  const percentage = Math.round(confidence * 100);

  if (confidence >= 0.90) {
    return {
      level: "high",
      label: `${percentage}% High Confidence`,
      badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
      textClass: "text-emerald-600 dark:text-emerald-400",
      icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
    };
  }

  if (confidence >= 0.70) {
    return {
      level: "medium",
      label: `${percentage}% Confidence`,
      badgeClass: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20",
      textClass: "text-sky-600 dark:text-sky-400",
      icon: <Check className="h-3.5 w-3.5 text-sky-500" />,
    };
  }

  return {
    level: "low",
    label: `${percentage}% Verify manually`,
    badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    textClass: "text-amber-600 dark:text-amber-400",
    icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />,
  };
}

interface ConfidenceBadgeProps {
  confidence: number;
  className?: string;
  compact?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  className = "",
  compact = false,
}) => {
  const details = getConfidenceDetails(confidence);

  if (compact) {
    return (
      <span
        title={details.label}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium border ${details.badgeClass} ${className}`}
      >
        {details.icon}
        <span>{Math.round(confidence * 100)}%</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${details.badgeClass} ${className}`}
    >
      {details.icon}
      <span>{details.label}</span>
    </span>
  );
};

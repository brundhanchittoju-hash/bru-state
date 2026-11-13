import React from "react";
import { AlertCircle, AlertTriangle, ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export type RiskLevel = "low" | "medium" | "high" | "critical";

interface RiskBadgeProps {
  level: RiskLevel | string;
  className?: string;
  showIcon?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  className,
  showIcon = true,
}) => {
  const normalized = (level || "low").toLowerCase() as RiskLevel;

  const configs: Record<
    RiskLevel,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    low: {
      label: "Low Risk",
      bg: "bg-emerald-500/10 dark:bg-emerald-500/15",
      text: "text-emerald-800 dark:text-emerald-300",
      border: "border-emerald-500/30",
      icon: <ShieldCheck className="w-3.5 h-3.5 mr-1 shrink-0" aria-hidden="true" />,
    },
    medium: {
      label: "Medium Risk",
      bg: "bg-amber-500/10 dark:bg-amber-500/15",
      text: "text-amber-800 dark:text-amber-300",
      border: "border-amber-500/35",
      icon: <AlertTriangle className="w-3.5 h-3.5 mr-1 shrink-0" aria-hidden="true" />,
    },
    high: {
      label: "High Risk",
      bg: "bg-orange-500/10 dark:bg-orange-500/15",
      text: "text-orange-800 dark:text-orange-300",
      border: "border-orange-500/35",
      icon: <AlertCircle className="w-3.5 h-3.5 mr-1 shrink-0" aria-hidden="true" />,
    },
    critical: {
      label: "Critical Risk",
      bg: "bg-rose-500/10 dark:bg-rose-500/15",
      text: "text-rose-800 dark:text-rose-300",
      border: "border-rose-500/35",
      icon: <ShieldAlert className="w-3.5 h-3.5 mr-1 shrink-0" aria-hidden="true" />,
    },
  };

  const config = configs[normalized] || configs.low;

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded-md font-medium text-[11px] border select-none transition-colors",
        config.bg,
        config.text,
        config.border,
        className
      )}
      aria-label={`Risk level: ${config.label}`}
    >
      {showIcon && config.icon}
      {config.label}
    </span>
  );
};

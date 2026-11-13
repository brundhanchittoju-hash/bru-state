import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatTone = "default" | "primary" | "signal" | "emerald" | "danger";

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  tone?: StatTone;
  className?: string;
  onClick?: () => void;
}

const TONE_ICON_MAP: Record<StatTone, string> = {
  default: "bg-accent/80 text-primary ring-primary/15 group-hover:bg-primary group-hover:text-primary-foreground",
  primary: "bg-accent/80 text-primary ring-primary/15 group-hover:bg-primary group-hover:text-primary-foreground",
  signal: "bg-signal-surface text-signal ring-signal/20 group-hover:bg-signal group-hover:text-white",
  emerald: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-emerald-500/20 group-hover:bg-emerald-600 group-hover:text-white",
  danger: "bg-rose-500/10 text-rose-700 dark:text-rose-400 ring-rose-500/20 group-hover:bg-rose-600 group-hover:text-white",
};

const TONE_BORDER_MAP: Record<StatTone, string> = {
  default: "",
  primary: "border-l-2 border-l-primary/50",
  signal: "border-l-2 border-l-signal",
  emerald: "border-l-2 border-l-emerald-500/70",
  danger: "border-l-2 border-l-rose-500/70",
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  description,
  icon,
  trend,
  tone = "default",
  className,
  onClick,
}) => {
  return (
    <Card
      onClick={onClick}
      className={cn(
        "group relative overflow-hidden transition-all",
        TONE_BORDER_MAP[tone],
        onClick && "cursor-pointer hover:border-primary/40 hover:shadow-md",
        className
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-center gap-3.5">
          {icon && (
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset transition-colors",
                TONE_ICON_MAP[tone]
              )}
            >
              {icon}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-muted-foreground truncate">
              {title}
            </p>
            <div className="mt-0.5 flex items-baseline gap-2">
              <h2 className="font-mono text-2xl font-semibold tracking-tight text-foreground tabular-nums">
                {value}
              </h2>
              {trend && (
                <span
                  className={cn(
                    "font-mono text-[11px] font-semibold tabular-nums",
                    trend.isPositive
                      ? "text-emerald-700 dark:text-emerald-400"
                      : "text-rose-700 dark:text-rose-400"
                  )}
                >
                  {trend.value}
                </span>
              )}
            </div>
            {description && (
              <p className="mt-0.5 text-[11px] text-muted-foreground truncate">
                {description}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

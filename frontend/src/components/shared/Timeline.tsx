import React from "react";
import { cn } from "@/lib/utils";

export interface TimelineItem {
  id: string;
  title: string;
  meta: string;
  detail?: string;
  icon?: React.ReactNode;
  accent?: "primary" | "signal" | "success" | "muted";
}

interface TimelineProps {
  items: TimelineItem[];
  emptyMessage?: string;
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({
  items,
  emptyMessage = "No activity recorded yet.",
  className,
}) => {
  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-xs text-muted-foreground">
        {emptyMessage}
      </p>
    );
  }

  const dotColors: Record<NonNullable<TimelineItem["accent"]>, string> = {
    primary: "bg-primary ring-primary/20",
    signal: "bg-signal ring-signal/20",
    success: "bg-emerald-600 dark:bg-emerald-400 ring-emerald-500/20",
    muted: "bg-muted-foreground ring-muted",
  };

  return (
    <ol className={cn("relative ml-2.5 space-y-4 border-l border-border pl-5", className)}>
      {items.map((item) => {
        const accent = item.accent || "primary";
        return (
          <li key={item.id} className="relative">
            <span
              aria-hidden="true"
              className={cn(
                "absolute -left-[25px] top-1.5 flex h-2.5 w-2.5 items-center justify-center rounded-full ring-4",
                dotColors[accent]
              )}
            />
            <div className="space-y-0.5">
              <p className="text-xs font-medium text-foreground capitalize leading-snug">
                {item.title}
              </p>
              <p className="font-mono text-[11px] text-muted-foreground">
                {item.meta}
              </p>
              {item.detail && (
                <p className="mt-1 rounded-lg border border-border bg-muted/40 px-2.5 py-1.5 text-[11px] text-foreground/90">
                  {item.detail}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
};


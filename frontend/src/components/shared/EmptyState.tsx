import React from "react";
import { FolderOpen, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  phaseTag?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  phaseTag,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/60 p-8 text-center animate-fade-in",
        className
      )}
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-primary ring-4 ring-accent/40 mb-4">
        {icon || <FolderOpen className="h-7 w-7 stroke-[1.6]" />}
      </div>

      <div className="flex items-center gap-2 mb-1.5">
        <h3 className="font-display text-lg font-semibold text-foreground">{title}</h3>
        {phaseTag && (
          <Badge variant="secondary" className="text-[10px] uppercase tracking-wider font-mono">
            {phaseTag}
          </Badge>
        )}
      </div>

      <p className="max-w-md text-sm text-muted-foreground mb-6 leading-relaxed">
        {description}
      </p>

      {actionLabel && onAction && (
        <Button onClick={onAction} className="gap-2">
          {actionLabel}
          <ArrowRight className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
};

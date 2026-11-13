import React from "react";
import { Clock, CheckCircle, ShieldAlert, GitCommit } from "lucide-react";

interface TimelineEvent {
  event_type: string;
  title: string;
  actor_name: string;
  actor_role?: string;
  timestamp: string;
  details?: string;
}

interface FindingTimelineTabProps {
  timeline: TimelineEvent[];
}

export const FindingTimelineTab: React.FC<FindingTimelineTabProps> = ({ timeline }) => {
  const getEventIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "finding_created":
        return <ShieldAlert className="h-4 w-4 text-signal" />;
      case "status_review":
        return <CheckCircle className="h-4 w-4 text-primary" />;
      case "review_finding":
        return <CheckCircle className="h-4 w-4 text-emerald-500" />;
      default:
        return <GitCommit className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <div className="space-y-4 text-xs">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Clock className="h-4 w-4 text-primary" />
        <span>Cryptographic activity ledger event history (SHA-256 chained).</span>
      </div>

      <div className="relative border-l-2 border-border ml-3.5 space-y-5 py-2">
        {timeline.map((evt, idx) => (
          <div key={idx} className="relative pl-6 group">
            {/* Dot / Icon */}
            <div className="absolute -left-2.5 top-0.5 bg-card rounded-full border border-border p-0.5">
              {getEventIcon(evt.event_type)}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-foreground">
                  {evt.title}
                </span>
                <span className="text-[11px] font-mono text-muted-foreground">
                  by {evt.actor_name} {evt.actor_role ? `(${evt.actor_role})` : ""}
                </span>
                {/* Absolute Time with tooltip */}
                <span
                  title={new Date(evt.timestamp).toUTCString()}
                  className="text-[10px] text-muted-foreground font-mono tabular-nums cursor-help underline decoration-dotted"
                >
                  {new Date(evt.timestamp).toLocaleString()}
                </span>
              </div>

              {evt.details && (
                <p className="text-foreground/90 leading-relaxed font-sans text-[11px] bg-muted/40 p-2.5 rounded-lg border border-border">
                  {evt.details}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

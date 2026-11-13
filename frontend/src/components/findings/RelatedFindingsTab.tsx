import React from "react";
import { Link } from "react-router-dom";
import { FileText, Bookmark, Layers } from "lucide-react";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";

interface RelatedFindingsTabProps {
  documentsUsed: any[];
  relatedFindings: any[];
  annotations: any[];
  onSelectDoc: (docId: string) => void;
}

export const RelatedFindingsTab: React.FC<RelatedFindingsTabProps> = ({
  documentsUsed,
  relatedFindings,
  annotations,
  onSelectDoc,
}) => {
  return (
    <div className="space-y-6 text-xs">
      {/* Documents Used Section */}
      <div className="space-y-2.5">
        <h4 className="font-semibold text-foreground flex items-center gap-1.5">
          <FileText className="h-4 w-4 text-primary" />
          <span>Source Documents Referenced ({documentsUsed.length})</span>
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {documentsUsed.map((doc) => (
            <div
              key={doc.id}
              onClick={() => onSelectDoc(doc.id)}
              className="p-3.5 border border-border rounded-xl bg-card hover:border-primary/50 cursor-pointer transition-colors flex items-start justify-between gap-2"
            >
              <div className="min-w-0">
                <p className="font-medium text-foreground truncate">
                  {doc.title || doc.original_filename}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono mt-1 tabular-nums">
                  <span>{doc.document_type || "Document"}</span>
                  <span>•</span>
                  <span>v{doc.current_version}</span>
                  <span>•</span>
                  <span>{doc.page_count} pages</span>
                </div>
              </div>
              <span className="text-[10px] text-primary font-medium shrink-0">View in Pane</span>
            </div>
          ))}
        </div>
      </div>

      {/* Related Findings Section */}
      <div className="space-y-2.5">
        <h4 className="font-semibold text-foreground flex items-center gap-1.5">
          <Layers className="h-4 w-4 text-primary" />
          <span>Related Findings in Case ({relatedFindings.length})</span>
        </h4>
        {relatedFindings.length === 0 ? (
          <p className="text-muted-foreground">No related findings detected for this entity or rule.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {relatedFindings.map((rf) => (
              <Link
                key={rf.id}
                to={`/findings/${rf.id}`}
                className="p-3.5 border border-border rounded-xl bg-card hover:border-primary/50 transition-colors block space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-semibold text-foreground">
                    {rf.finding_number}
                  </span>
                  <RiskBadge level={rf.risk_level} />
                </div>
                <p className="font-medium text-foreground line-clamp-1">
                  {rf.title}
                </p>
                <div className="flex items-center justify-between pt-1">
                  <StatusPill status={rf.status} />
                  <span className="font-mono text-muted-foreground tabular-nums">
                    ₹{rf.amount_at_risk.toLocaleString("en-IN")}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Attached Spatial Annotations */}
      {annotations.length > 0 && (
        <div className="space-y-2.5">
          <h4 className="font-semibold text-foreground flex items-center gap-1.5">
            <Bookmark className="h-4 w-4 text-primary" />
            <span>Attached Document Annotations ({annotations.length})</span>
          </h4>
          <div className="space-y-2">
            {annotations.map((ann) => (
              <div
                key={ann.id}
                className="p-3 bg-signal-surface border border-signal/30 rounded-xl text-xs"
              >
                <div className="flex justify-between text-[10px] text-signal font-mono tabular-nums">
                  <span>Page {ann.page}</span>
                  <span>By {ann.author}</span>
                </div>
                <p className="text-foreground mt-1">{ann.note}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

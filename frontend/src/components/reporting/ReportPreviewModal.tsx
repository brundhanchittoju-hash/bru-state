import React from "react";
import { Download, ExternalLink, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";

interface ReportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportId: string | null;
  reportNumber: string;
  versionNumber?: number;
  reportTitle?: string;
  onDownload?: () => void;
}

export const ReportPreviewModal: React.FC<ReportPreviewModalProps> = ({
  isOpen,
  onClose,
  reportId,
  reportNumber,
  versionNumber = 1,
  reportTitle,
  onDownload,
}) => {
  if (!isOpen || !reportId) return null;

  const previewUrl = `${API_BASE}/reports/${reportId}/preview?version=${versionNumber}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="relative flex flex-col w-full max-w-5xl h-[90vh] bg-card rounded-2xl shadow-2xl border border-border overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-accent text-accent-foreground border border-primary/20 tabular-nums">
                {reportNumber} • v{versionNumber}
              </span>
              <h3 className="font-display text-base font-semibold text-foreground truncate max-w-lg">
                {reportTitle || "Official Statutory Audit Report"}
              </h3>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Karnataka State Audit Department • Cryptographically Sealed Document
            </p>
          </div>

          <div className="flex items-center gap-2">
            {onDownload && (
              <Button variant="outline" size="sm" onClick={onDownload} className="text-xs gap-1.5">
                <Download className="h-3.5 w-3.5" />
                Download PDF
              </Button>
            )}
            <a
              href={previewUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:bg-muted text-foreground transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open in Tab
            </a>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0 rounded-full"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Embedded PDF Viewer */}
        <div className="flex-1 w-full bg-muted relative">
          <iframe
            src={previewUrl}
            title={reportNumber}
            className="w-full h-full border-0"
          />
        </div>
      </div>
    </div>
  );
};

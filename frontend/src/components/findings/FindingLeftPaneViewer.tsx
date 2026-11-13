import React, { useState } from "react";
import { FileText, ZoomIn, ZoomOut, RotateCw, Table as TableIcon, BookmarkPlus, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BBoxOverlay } from "@/components/documents/BBoxOverlay";

interface FindingLeftPaneViewerProps {
  documentsUsed: any[];
  evidenceList: any[];
  selectedDocId?: string;
  onSelectDoc: (docId: string) => void;
  onAddAnnotation?: () => void;
}

export const FindingLeftPaneViewer: React.FC<FindingLeftPaneViewerProps> = ({
  documentsUsed,
  evidenceList,
  selectedDocId,
  onSelectDoc,
  onAddAnnotation,
}) => {
  const [zoom, setZoom] = useState(1.0);
  const [rotation, setRotation] = useState<0 | 90 | 180 | 270>(0);
  const [activePage, setActivePage] = useState(1);

  const activeDoc = documentsUsed.find((d) => d.id === selectedDocId) || documentsUsed[0];
  const isTabular = activeDoc?.document_type?.toLowerCase().includes("ledger") ||
                    activeDoc?.original_filename?.endsWith(".csv") ||
                    activeDoc?.original_filename?.endsWith(".xlsx");

  // Evidence regions matching the active document and page
  const pageEvidence = evidenceList.filter((e) => {
    const docMatches = (e.document_id || e.doc_id) === activeDoc?.id;
    const pageMatches = (e.page || 1) === activePage;
    return docMatches && pageMatches && e.bbox;
  });

  const handleRotate = () => {
    setRotation(((rotation + 90) % 360) as 0 | 90 | 180 | 270);
  };

  return (
    <div className="flex flex-col h-full bg-muted/40 rounded-2xl border border-border overflow-hidden shadow-sm">
      {/* Top Document Selector Bar */}
      <div className="flex items-center justify-between p-3 bg-card border-b border-border gap-2 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="h-4 w-4 text-primary shrink-0" />
          <select
            value={activeDoc?.id || ""}
            onChange={(e) => onSelectDoc(e.target.value)}
            className="text-xs font-medium text-foreground bg-background border border-input rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-ring max-w-[220px] truncate"
          >
            {documentsUsed.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title || doc.original_filename} ({doc.document_type || "Document"})
              </option>
            ))}
          </select>
          <span className="text-[11px] font-mono text-muted-foreground">
            v{activeDoc?.current_version || 1}
          </span>
        </div>

        {/* Viewer Controls */}
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
            title="Zoom Out"
            className="h-7 w-7 p-0"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <span className="text-[11px] font-mono px-1 tabular-nums">{Math.round(zoom * 100)}%</span>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
            title="Zoom In"
            className="h-7 w-7 p-0"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleRotate}
            title="Rotate 90° Clockwise"
            className="h-7 w-7 p-0"
          >
            <RotateCw className="h-3.5 w-3.5" />
          </Button>
          {onAddAnnotation && (
            <Button
              size="sm"
              variant="outline"
              onClick={onAddAnnotation}
              className="h-7 text-xs px-2 ml-1 border-primary/30 text-primary"
            >
              <BookmarkPlus className="h-3.5 w-3.5 mr-1" />
              Annotate
            </Button>
          )}
        </div>
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center relative min-h-[480px]">
        {isTabular ? (
          <div className="w-full max-w-2xl bg-card rounded-xl shadow-sm border border-border p-4 space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground border-b border-border pb-2">
              <TableIcon className="h-4 w-4 text-primary" />
              <span>Tabular Source Ledger (Row Evidence)</span>
            </div>
            <div className="overflow-x-auto text-xs">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-muted text-muted-foreground">
                    <th className="p-2 border border-border">Field</th>
                    <th className="p-2 border border-border">Value in Register</th>
                    <th className="p-2 border border-border">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {evidenceList.map((ev, i) => (
                    <tr key={i} className="bg-signal-surface/40 font-medium">
                      <td className="p-2 border border-border font-mono">Row #{ev.row_number || i + 1}</td>
                      <td className="p-2 border border-border">{ev.excerpt || "Passed disbursement"}</td>
                      <td className="p-2 border border-border text-signal">Flagged Evidence</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div
            className="relative bg-card shadow-md border border-border transition-transform origin-center"
            style={{
              width: `${Math.round(595 * zoom)}px`,
              height: `${Math.round(842 * zoom)}px`,
              transform: `rotate(${rotation}deg)`,
            }}
          >
            {/* Simulated High-Res Document Sheet */}
            <div className="p-6 text-foreground space-y-4 text-xs font-sans select-none pointer-events-none opacity-85">
              <div className="font-display text-center font-bold text-sm tracking-wide border-b border-border pb-2">
                GOVERNMENT OF KARNATAKA — ZILLA PANCHAYAT
              </div>
              <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
                <span>Ref: {activeDoc?.original_filename || "Document"}</span>
                <span>Page: {activePage} of {activeDoc?.page_count || 1}</span>
              </div>
              <div className="space-y-2 pt-2">
                <p className="font-semibold">VOUCHER / PAYMENT REQUISITION</p>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Certified that the supplies/services billed herein have been inspected and pass statutory verification under Karnataka Financial Code.
                </p>
                {evidenceList.map((ev, i) => (
                  <div key={i} className="bg-signal-surface/60 p-2 rounded-lg border border-signal-border font-mono text-[11px] text-signal">
                    Highlighted Audit Evidence: {ev.excerpt || "Passed amount ₹1,25,000"}
                  </div>
                ))}
              </div>
            </div>

            {/* Bounding Box Highlights Overlay */}
            {pageEvidence.map((ev, idx) => {
              const bboxTuple: [number, number, number, number] = Array.isArray(ev.bbox)
                ? (ev.bbox as [number, number, number, number])
                : typeof ev.bbox === "string"
                ? JSON.parse(ev.bbox)
                : [0.1, 0.1, 0.5, 0.2];
              return (
                <BBoxOverlay
                  key={idx}
                  bbox={bboxTuple}
                  pageWidth={595}
                  pageHeight={842}
                  zoom={zoom}
                  rotation={rotation}
                  label={`Evidence #${idx + 1}`}
                  color="#f59e0b"
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Navigation Bar */}
      <div className="flex items-center justify-between p-2.5 bg-card border-t border-border text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <Eye className="h-3.5 w-3.5 text-primary" />
          <span>Active Evidence: {pageEvidence.length} regions</span>
        </div>
        {(activeDoc?.page_count || 1) > 1 && (
          <div className="flex items-center gap-1 font-mono">
            <Button
              size="sm"
              variant="outline"
              disabled={activePage <= 1}
              onClick={() => setActivePage((p) => p - 1)}
              className="h-6 px-2 text-[11px]"
            >
              Prev
            </Button>
            <span>
              {activePage} / {activeDoc?.page_count || 1}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={activePage >= (activeDoc?.page_count || 1)}
              onClick={() => setActivePage((p) => p + 1)}
              className="h-6 px-2 text-[11px]"
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

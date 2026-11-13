import React, { useState, useEffect, useRef } from "react";
import {
  ZoomIn,
  ZoomOut,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  Search,
  Highlighter,
  Download,
  Copy,
  Check,
  Edit2,
  Undo2,
  PlusCircle,
  FileText,
  Layers,
  MessageSquare,
  History,
  FileCode,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { API_BASE } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { ConfidenceBadge } from "@/components/documents/ConfidenceBadge";
import { BBoxOverlay } from "@/components/documents/BBoxOverlay";
import { DocumentDetail, ExtractedField } from "@/types";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface DocumentViewerProps {
  documentId: string;
  onClose?: () => void;
  onRefresh?: () => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  onClose,
  onRefresh,
}) => {
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"fields" | "text" | "annotations" | "versions" | "export">("fields");

  // Viewer controls
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [activeBBox, setActiveBBox] = useState<[number, number, number, number] | null>(null);
  const [activeFieldId, setActiveFieldId] = useState<string | null>(null);

  // Search within document
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Annotation tool
  const [isAnnotating, setIsAnnotating] = useState<boolean>(false);
  const [newAnnotationNote, setNewAnnotationNote] = useState<string>("");
  const [pendingAnnotationBbox, setPendingAnnotationBbox] = useState<string | null>(null);
  const [isAnnotationModalOpen, setIsAnnotationModalOpen] = useState<boolean>(false);

  // Field override modal
  const [overrideField, setOverrideField] = useState<ExtractedField | null>(null);
  const [overrideValue, setOverrideValue] = useState<string>("");
  const [overrideComment, setOverrideComment] = useState<string>("");
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState<boolean>(false);

  // Add manual field modal
  const [isAddFieldModalOpen, setIsAddFieldModalOpen] = useState<boolean>(false);
  const [newFieldName, setNewFieldName] = useState<string>("");
  const [newFieldValue, setNewFieldValue] = useState<string>("");
  const [newFieldComment, setNewFieldComment] = useState<string>("");

  // Reclassification modal
  const [isReclassifyModalOpen, setIsReclassifyModalOpen] = useState<boolean>(false);
  const [newDocType, setNewDocType] = useState<string>("");
  const [reclassifyComment, setReclassifyComment] = useState<string>("");

  // Copy hash helper
  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const loadDocumentDetails = async (initial = false) => {
    if (initial || !doc) setIsLoading(true);
    try {
      const data = await api.get<DocumentDetail>(`/documents/${documentId}`);
      setDoc(data);
      if (data.document_type) setNewDocType(data.document_type);
    } catch (err: any) {
      toast.error(err.message || "Failed to load document details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (documentId) {
      loadDocumentDetails(true);
    }
  }, [documentId]);

  // Page dimensions (standard A4: 595 x 842 pt scaled)
  const basePageWidth = 650;
  const basePageHeight = 880;

  const handleZoomIn = () => setZoom((prev) => Math.min(2.5, +(prev + 0.2).toFixed(1)));
  const handleZoomOut = () => setZoom((prev) => Math.max(0.5, +(prev - 0.2).toFixed(1)));
  const handleResetZoom = () => setZoom(1.0);
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  const handleCopyHash = () => {
    if (doc?.sha256_hash) {
      navigator.clipboard.writeText(doc.sha256_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
      toast.success("SHA-256 hash copied to clipboard");
    }
  };

  // Field Jump & Flash BBox
  const handleSelectField = (field: ExtractedField) => {
    setActiveFieldId(field.id);
    if (field.source_page) {
      setCurrentPage(field.source_page);
    }
    if (field.bbox) {
      try {
        const parsed = JSON.parse(field.bbox);
        if (Array.isArray(parsed) && parsed.length === 4) {
          setActiveBBox(parsed as [number, number, number, number]);
        }
      } catch {
        setActiveBBox(null);
      }
    } else {
      setActiveBBox(null);
    }
  };

  // Override Field
  const openOverrideDialog = (field: ExtractedField, e: React.MouseEvent) => {
    e.stopPropagation();
    setOverrideField(field);
    setOverrideValue(field.effective_value || field.corrected_value || field.extracted_value || "");
    setOverrideComment(field.override_comment || "");
    setIsOverrideModalOpen(true);
  };

  const handleSaveOverride = async () => {
    if (!overrideField || !overrideValue.trim()) {
      toast.error("Please enter a valid corrected value.");
      return;
    }
    if (!overrideComment.trim()) {
      toast.error("Mandatory auditor justification note is required.");
      return;
    }

    try {
      await api.post(`/documents/${documentId}/fields/${overrideField.id}/override`, {
        corrected_value: overrideValue.trim(),
        comment: overrideComment.trim(),
      });
      toast.success(`Field '${overrideField.field_name}' successfully overridden.`);
      setIsOverrideModalOpen(false);
      loadDocumentDetails();
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to override field.");
    }
  };

  // Revert Field Override
  const handleRevertOverride = async (field: ExtractedField, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.post(`/documents/${documentId}/fields/${field.id}/revert`);
      toast.success(`Field '${field.field_name}' reverted to original extracted value.`);
      loadDocumentDetails();
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to revert override.");
    }
  };

  // Add Manual Field
  const handleSaveManualField = async () => {
    if (!newFieldName.trim() || !newFieldValue.trim()) {
      toast.error("Field name and value are required.");
      return;
    }

    try {
      await api.post(`/documents/${documentId}/fields`, {
        field_name: newFieldName.trim(),
        extracted_value: newFieldValue.trim(),
        source_page: currentPage,
        comment: newFieldComment.trim() || "Manually tagged by auditor",
      });
      toast.success("Manual field tagged successfully.");
      setIsAddFieldModalOpen(false);
      setNewFieldName("");
      setNewFieldValue("");
      setNewFieldComment("");
      loadDocumentDetails();
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to add manual field.");
    }
  };

  // Document Reclassify
  const handleReclassify = async () => {
    if (!newDocType) return;
    try {
      await api.post(`/documents/${documentId}/reclassify`, {
        document_type: newDocType,
        comment: reclassifyComment.trim() || "Manual reclassification by auditor",
      });
      toast.success(`Document reclassified as ${newDocType}.`);
      setIsReclassifyModalOpen(false);
      loadDocumentDetails();
      onRefresh?.();
    } catch (err: any) {
      toast.error(err.message || "Failed to reclassify document.");
    }
  };

  // Canvas Click for Annotation
  const handleCanvasClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isAnnotating) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = +((e.clientX - rect.left) / (rect.width || 1)).toFixed(3);
    const y = +((e.clientY - rect.top) / (rect.height || 1)).toFixed(3);

    // Default note box [x, y, x + 0.15, y + 0.05]
    const bboxStr = JSON.stringify([x, y, Math.min(1.0, x + 0.15), Math.min(1.0, y + 0.05)]);
    setPendingAnnotationBbox(bboxStr);
    setIsAnnotationModalOpen(true);
  };

  const handleSaveAnnotation = async () => {
    if (!newAnnotationNote.trim()) {
      toast.error("Please enter a note comment.");
      return;
    }

    try {
      await api.post(`/documents/${documentId}/annotations`, {
        page: currentPage,
        bbox: pendingAnnotationBbox,
        note: newAnnotationNote.trim(),
      });
      toast.success("Annotation note added.");
      setIsAnnotationModalOpen(false);
      setIsAnnotating(false);
      setNewAnnotationNote("");
      setPendingAnnotationBbox(null);
      loadDocumentDetails();
    } catch (err: any) {
      toast.error(err.message || "Failed to save annotation.");
    }
  };

  const handleDeleteAnnotation = async (annId: string) => {
    try {
      await api.delete(`/documents/${documentId}/annotations/${annId}`);
      toast.success("Annotation deleted.");
      loadDocumentDetails();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete annotation.");
    }
  };

  if (isLoading || !doc) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3 bg-card border border-border rounded-2xl shadow-sm">
        <div className="h-8 w-8 rounded-full border-4 border-primary border-r-transparent animate-spin" />
        <p className="text-xs text-muted-foreground font-mono">Loading Document Pipeline & Extracted Fields...</p>
      </div>
    );
  }

  // Group fields into statutory, financial, and other
  const statutoryFields = doc.extracted_fields.filter((f) =>
    ["gstin", "pan", "ifsc_code", "bill_number", "voucher_number", "sanction_number"].includes(f.field_name)
  );
  const financialFields = doc.extracted_fields.filter((f) =>
    [
      "total_amount",
      "taxable_amount",
      "cgst_amount",
      "sgst_amount",
      "igst_amount",
      "passed_for_payment",
      "sanctioned_amount",
      "tender_amount",
    ].includes(f.field_name)
  );
  const otherFields = doc.extracted_fields.filter(
    (f) => !statutoryFields.includes(f) && !financialFields.includes(f)
  );

  const modalInputCls =
    "w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] min-h-[600px] border border-border rounded-2xl bg-card overflow-hidden shadow-sm">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-muted/40">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-primary" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-display text-sm font-semibold text-foreground truncate max-w-md">
                {doc.title || doc.original_filename}
              </h3>
              <Badge variant="outline" className="font-mono text-[10px]">
                v{doc.current_version}
              </Badge>
              {doc.document_type && (
                <Badge className="bg-accent text-accent-foreground border-primary/20 text-xs">
                  {doc.document_type}
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground flex items-center gap-2">
              <span>{doc.original_filename}</span>
              <span>•</span>
              <span className="font-mono">{(doc.file_size / 1024).toFixed(1)} KB</span>
              <span>•</span>
              <button
                onClick={handleCopyHash}
                title="Click to copy SHA-256"
                className="font-mono hover:text-primary flex items-center gap-1"
              >
                <span>SHA-256: {doc.sha256_hash.substring(0, 10)}...</span>
                {copiedHash ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
              </button>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Classification & Confidence */}
          <ConfidenceBadge confidence={doc.classification_confidence} />

          <Button data-testid="reclassify-trigger-btn" size="sm" variant="outline" onClick={() => setIsReclassifyModalOpen(true)}>
            Reclassify
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(`${API_BASE}/documents/${doc.id}/download`, "_blank")}
          >
            <Download className="h-4 w-4 mr-1.5" />
            Download
          </Button>

          {onClose && (
            <Button size="sm" variant="ghost" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>

      {/* Main Split-Pane Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Pane: Document Canvas & Controls */}
        <div className="flex-1 flex flex-col border-r border-border bg-muted/30 overflow-hidden">
          {/* Viewer Toolbar */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card text-xs">
            <div className="flex items-center gap-1">
              <Button size="icon" variant="ghost" onClick={handleZoomOut} title="Zoom Out">
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="font-mono text-[11px] px-1 text-muted-foreground tabular-nums">
                {Math.round(zoom * 100)}%
              </span>
              <Button size="icon" variant="ghost" onClick={handleZoomIn} title="Zoom In">
                <ZoomIn className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="ghost" onClick={handleResetZoom} className="text-[11px] h-7 px-2">
                Reset
              </Button>
              <div className="h-4 w-px bg-border mx-1" />
              <Button size="icon" variant="ghost" onClick={handleRotate} title="Rotate 90°">
                <RotateCw className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant={isAnnotating ? "default" : "ghost"}
                onClick={() => setIsAnnotating(!isAnnotating)}
                className={`h-7 px-2 text-[11px] ${
                  isAnnotating ? "bg-amber-600 hover:bg-amber-700 text-white" : ""
                }`}
                title="Click canvas to add note"
              >
                <Highlighter className="h-3.5 w-3.5 mr-1" />
                {isAnnotating ? "Click page to drop note" : "Add Note"}
              </Button>
            </div>

            {/* Page navigation */}
            <div className="flex items-center gap-1.5">
              <Button
                size="icon"
                variant="ghost"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-foreground font-mono text-[11px] tabular-nums">
                Page {currentPage} of {doc.page_count || 1}
              </span>
              <Button
                size="icon"
                variant="ghost"
                disabled={currentPage >= (doc.page_count || 1)}
                onClick={() => setCurrentPage((p) => Math.min(doc.page_count || 1, p + 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Extractor Mode Badge */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-muted-foreground font-medium">Mode:</span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                  doc.extractor_used === "ocr"
                    ? "bg-signal-surface text-signal border border-signal-border"
                    : "bg-accent text-accent-foreground border border-primary/20"
                }`}
              >
                {doc.extractor_used === "ocr"
                  ? "OCR: Text-layer fallback mode"
                  : "Text Layer (Word Coordinates)"}
              </span>
            </div>
          </div>

          {/* Document Canvas Container */}
          <div
            ref={containerRef}
            className="flex-1 overflow-auto p-6 flex items-center justify-center relative select-none"
          >
            <div
              onClick={handleCanvasClick}
              style={{
                width: `${basePageWidth * zoom}px`,
                height: `${basePageHeight * zoom}px`,
                transform: `rotate(${rotation}deg)`,
                transformOrigin: "center center",
              }}
              className={`relative bg-card border border-border shadow-lg rounded transition-transform duration-200 flex flex-col overflow-hidden ${
                isAnnotating ? "cursor-crosshair ring-2 ring-amber-400 ring-offset-2" : ""
              }`}
            >
              {/* High-res page thumbnail / image display */}
              <img
                src={`${API_BASE}/documents/${doc.id}/pages/${currentPage}/thumbnail`}
                alt={`Page ${currentPage}`}
                className="w-full h-full object-contain pointer-events-none"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = "none";
                }}
              />

              {/* Render Active Field Bounding Box Overlay */}
              {activeBBox && (
                <BBoxOverlay
                  bbox={activeBBox}
                  pageWidth={basePageWidth}
                  pageHeight={basePageHeight}
                  zoom={zoom}
                  rotation={rotation}
                  isActive={true}
                  color="#4338CA"
                />
              )}

              {/* Render Page Annotations */}
              {doc.annotations
                .filter((a) => a.page === currentPage && a.bbox)
                .map((a) => {
                  try {
                    const parsed = JSON.parse(a.bbox!);
                    return (
                      <BBoxOverlay
                        key={a.id}
                        bbox={parsed as [number, number, number, number]}
                        pageWidth={basePageWidth}
                        pageHeight={basePageHeight}
                        zoom={zoom}
                        rotation={rotation}
                        label={a.note}
                        isActive={false}
                        color="#d97706"
                      />
                    );
                  } catch {
                    return null;
                  }
                })}
            </div>
          </div>
        </div>

        {/* Right Pane: Extracted Data & Auditor Inspection */}
        <div className="w-[440px] flex flex-col bg-card overflow-hidden">
          {/* Sub-tabs header */}
          <div className="flex border-b border-border bg-muted/30 px-2 pt-1">
            <button
              onClick={() => setActiveTab("fields")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "fields"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Fields ({doc.extracted_fields.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("text")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "text"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileCode className="h-3.5 w-3.5" />
              <span>Raw Text</span>
            </button>

            <button
              onClick={() => setActiveTab("annotations")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "annotations"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Notes ({doc.annotations.length})</span>
            </button>

            <button
              onClick={() => setActiveTab("versions")}
              className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === "versions"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <History className="h-3.5 w-3.5" />
              <span>Versions ({doc.versions.length})</span>
            </button>
          </div>

          {/* Tab 1: Extracted Fields Panel */}
          {activeTab === "fields" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Extracted Statutory Fields
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={() => setIsAddFieldModalOpen(true)}
                >
                  <PlusCircle className="h-3.5 w-3.5 mr-1" />
                  Add Missing Field
                </Button>
              </div>

              {/* Statutory Group */}
              {statutoryFields.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-[11px] font-medium text-muted-foreground">
                    Statutory Identifiers
                  </h5>
                  <div className="space-y-2">
                    {statutoryFields.map((field) => renderFieldCard(field))}
                  </div>
                </div>
              )}

              {/* Financial Amounts Group */}
              {financialFields.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-[11px] font-medium text-muted-foreground">
                    Financial Amounts & Passed Bills
                  </h5>
                  <div className="space-y-2">
                    {financialFields.map((field) => renderFieldCard(field))}
                  </div>
                </div>
              )}

              {/* Other Fields */}
              {otherFields.length > 0 && (
                <div className="space-y-2">
                  <h5 className="text-[11px] font-medium text-muted-foreground">
                    Dates & Vendor Metadata
                  </h5>
                  <div className="space-y-2">
                    {otherFields.map((field) => renderFieldCard(field))}
                  </div>
                </div>
              )}

              {doc.extracted_fields.length === 0 && (
                <div className="text-center py-12 text-muted-foreground text-xs">
                  No statutory fields extracted. Click "Add Missing Field" to tag values manually.
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Raw Document Text */}
          {activeTab === "text" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              <div className="relative">
                <Search className="h-3.5 w-3.5 absolute left-2.5 top-2.5 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search extracted document text..."
                  className="w-full text-xs pl-8 pr-3 py-1.5 rounded-lg border border-input bg-background text-foreground"
                />
              </div>

              <div className="p-3 rounded-lg bg-muted/40 border border-border font-mono text-[11px] text-foreground whitespace-pre-wrap leading-relaxed select-text">
                {doc.raw_text ||
                  doc.extracted_fields.map((f) => `${f.field_name}: ${f.extracted_value}`).join("\n") ||
                  "No raw text stream available for this document."}
              </div>
            </div>
          )}

          {/* Tab 3: Annotations Panel */}
          {activeTab === "annotations" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground">
                  Auditor Page Notes ({doc.annotations.length})
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsAnnotating(true)}
                  className="h-7 text-xs"
                >
                  <Highlighter className="h-3.5 w-3.5 mr-1" />
                  Drop Note
                </Button>
              </div>

              {doc.annotations.map((ann) => (
                <div
                  key={ann.id}
                  className="p-3 rounded-lg border border-signal-border bg-signal-surface/60 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-signal">
                      Page {ann.page}
                    </span>
                    <span className="text-muted-foreground font-mono">{new Date(ann.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-foreground font-medium">{ann.note}</p>
                  <div className="flex items-center justify-between pt-1 border-t border-signal-border/40 text-[11px]">
                    <span className="text-muted-foreground">By: {ann.created_by_name || "Auditor"}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteAnnotation(ann.id)}
                      className="h-6 text-rose-600 dark:text-rose-400 hover:text-rose-700 px-2"
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              ))}

              {doc.annotations.length === 0 && (
                <div className="text-center py-12 text-muted-foreground text-xs">
                  No notes added. Click "Drop Note" and click on the document canvas to leave audit notes.
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Version History */}
          {activeTab === "versions" && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              <h5 className="text-xs font-semibold text-foreground">
                Document Version History
              </h5>
              {doc.versions.map((ver) => (
                <div
                  key={ver.id}
                  className="p-3 rounded-lg border border-border bg-muted/30 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-primary font-mono">
                      Version {ver.version_number}
                    </span>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {new Date(ver.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-[11px] font-mono text-muted-foreground truncate">
                    SHA-256: {ver.sha256_hash}
                  </p>
                  {ver.change_summary && (
                    <p className="text-foreground/90 italic">{ver.change_summary}</p>
                  )}
                  <div className="pt-1 flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Uploader: {ver.created_by_name || "Auditor"}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        window.open(
                          `${API_BASE}/documents/${doc.id}/download?version=${ver.version_number}`,
                          "_blank"
                        )
                      }
                      className="h-6 px-2 text-primary"
                    >
                      <Download className="h-3 w-3 mr-1" /> Download v{ver.version_number}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Override Field Modal */}
      <Dialog open={isOverrideModalOpen} onOpenChange={setIsOverrideModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-display">
              <Edit2 className="h-4 w-4 text-primary" />
              <span>Manual Field Override (Human-in-the-Loop)</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="p-2.5 rounded-lg bg-muted/50 border border-border text-muted-foreground">
              <span className="font-semibold text-foreground">Field: </span>
              <span className="font-mono text-primary">{overrideField?.field_name}</span>
              <br />
              <span className="font-semibold text-foreground">Original Extracted: </span>
              <span className="font-mono">{overrideField?.extracted_value || "[None]"}</span>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                Auditor Corrected Value *
              </label>
              <input
                data-testid="override-value-input"
                type="text"
                value={overrideValue}
                onChange={(e) => setOverrideValue(e.target.value)}
                className={`${modalInputCls} font-medium`}
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                Mandatory Auditor Justification / Reason *
              </label>
              <textarea
                data-testid="override-reason-input"
                rows={3}
                value={overrideComment}
                onChange={(e) => setOverrideComment(e.target.value)}
                placeholder="e.g. Verified with physical invoice seal; OCR misread numeral 0 as O."
                className={modalInputCls}
              />
              <p className="text-[11px] text-muted-foreground">
                This modification is permanently recorded in the cryptographic audit trail.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsOverrideModalOpen(false)}>
              Cancel
            </Button>
            <Button data-testid="save-override-btn" onClick={handleSaveOverride}>
              Save Verified Override
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Missing Field Modal */}
      <Dialog open={isAddFieldModalOpen} onOpenChange={setIsAddFieldModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-display">
              <PlusCircle className="h-4 w-4 text-primary" />
              <span>Tag Missing Statutory Field</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-foreground">Field Name *</label>
              <input
                type="text"
                value={newFieldName}
                onChange={(e) => setNewFieldName(e.target.value)}
                placeholder="e.g. pan, sanction_number, work_order_date"
                className={modalInputCls}
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">Field Value *</label>
              <input
                type="text"
                value={newFieldValue}
                onChange={(e) => setNewFieldValue(e.target.value)}
                placeholder="e.g. AAACB1234F"
                className={`${modalInputCls} font-mono`}
              />
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">Auditor Comment</label>
              <input
                type="text"
                value={newFieldComment}
                onChange={(e) => setNewFieldComment(e.target.value)}
                placeholder="Identified from header stamp"
                className={modalInputCls}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsAddFieldModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveManualField}>
              Add Field
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reclassify Modal */}
      <Dialog open={isReclassifyModalOpen} onOpenChange={setIsReclassifyModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-display">Reclassify Document</DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                New Document Classification *
              </label>
              <select
                value={newDocType}
                onChange={(e) => setNewDocType(e.target.value)}
                className={modalInputCls}
              >
                <option value="Bill">Bill / Tax Invoice</option>
                <option value="Voucher">Payment Voucher</option>
                <option value="Work Order">Work Order</option>
                <option value="Sanction Order">Sanction Order</option>
                <option value="Tender">Tender Notice (IFT)</option>
                <option value="Measurement Book">Measurement Book</option>
                <option value="Completion Certificate">Completion Certificate</option>
                <option value="Utilization Certificate">Utilization Certificate</option>
                <option value="Cash Book">Cash Book</option>
                <option value="Ledger">General Ledger</option>
                <option value="Bank Statement">Bank Statement</option>
                <option value="Supporting Document">Supporting Document</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-foreground">
                Reason for Reclassification *
              </label>
              <input
                type="text"
                value={reclassifyComment}
                onChange={(e) => setReclassifyComment(e.target.value)}
                placeholder="e.g. Corrected document header from voucher to tax invoice"
                className={modalInputCls}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsReclassifyModalOpen(false)}>
              Cancel
            </Button>
            <Button data-testid="confirm-reclassification-btn" onClick={handleReclassify}>
              Confirm Reclassification
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Drop Annotation Note Modal */}
      <Dialog open={isAnnotationModalOpen} onOpenChange={setIsAnnotationModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 font-display">
              <MessageSquare className="h-4 w-4 text-signal" />
              <span>Add Auditor Page Annotation Note</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-3 py-2 text-xs">
            <p className="text-muted-foreground">
              Attaching note on <span className="font-semibold text-foreground">Page {currentPage}</span>.
            </p>
            <div className="space-y-1">
              <label className="font-semibold text-foreground">Audit Observation *</label>
              <textarea
                rows={3}
                value={newAnnotationNote}
                onChange={(e) => setNewAnnotationNote(e.target.value)}
                placeholder="e.g. Work completion date does not match sanction order clause 4."
                className={modalInputCls}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setIsAnnotationModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveAnnotation} className="bg-amber-600 hover:bg-amber-700 text-white">
              Save Annotation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );

  function renderFieldCard(field: ExtractedField) {
    const isSelected = activeFieldId === field.id;
    const isOverridden = field.is_overridden && field.corrected_value !== null;
    const effectiveVal = field.effective_value || field.corrected_value || field.extracted_value || "";

    return (
      <div
        key={field.id}
        onClick={() => handleSelectField(field)}
        className={`p-3 rounded-xl border transition-all cursor-pointer text-xs space-y-1.5 ${
          isSelected
            ? "border-primary bg-accent/60 shadow-sm"
            : "border-border bg-muted/30 hover:border-primary/40"
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="font-semibold font-mono text-foreground">
              {field.field_name}
            </span>
            {isOverridden && (
              <Badge className="bg-accent text-accent-foreground border-primary/20 text-[10px] px-1.5 py-0">
                Overridden
              </Badge>
            )}
            {field.validation_status === "valid" && (
              <span className="flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400 text-[10px] font-medium">
                <CheckCircle2 className="h-3 w-3" />
                <span>Valid</span>
              </span>
            )}
            {field.validation_status === "invalid" && (
              <span
                title={field.validation_message || "Invalid format"}
                className="flex items-center gap-0.5 text-rose-600 dark:text-rose-400 text-[10px] font-medium"
              >
                <XCircle className="h-3 w-3" />
                <span>Invalid</span>
              </span>
            )}
          </div>
          <ConfidenceBadge confidence={field.confidence} compact />
        </div>

        <div className="flex items-baseline justify-between pt-0.5">
          <span className="font-mono text-xs font-bold text-foreground truncate max-w-[240px]">
            {effectiveVal}
          </span>
          <div className="flex items-center gap-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => openOverrideDialog(field, e)}
              className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
            >
              <Edit2 className="h-3 w-3 mr-1" />
              Edit
            </Button>
            {isOverridden && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => handleRevertOverride(field, e)}
                className="h-6 px-1.5 text-[11px] text-primary hover:text-primary"
                title="Revert to original extracted value"
              >
                <Undo2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>

        {isOverridden && field.override_comment && (
          <p className="text-[11px] text-primary/90 italic pt-0.5 border-t border-border">
            Justification: {field.override_comment}
          </p>
        )}
      </div>
    );
  }
};

import React, { useState, useRef } from "react";
import { Upload, FileText, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { api, ApiError } from "@/lib/api";
import { AuditCase } from "@/types";
import { toast } from "sonner";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId?: string;
  cases?: AuditCase[];
  onUploadSuccess?: (doc: any) => void;
  onOpenTabularMapping?: (file: File, caseId: string) => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  caseId: initialCaseId,
  cases = [],
  onUploadSuccess,
  onOpenTabularMapping,
}) => {
  const [selectedCaseId, setSelectedCaseId] = useState<string>(initialCaseId || "");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>("");
  const [docType, setDocType] = useState<string>("auto");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  
  // Duplicate hash resolution state
  const [duplicateWarning, setDuplicateWarning] = useState<any | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync caseId when prop changes
  React.useEffect(() => {
    if (initialCaseId) {
      setSelectedCaseId(initialCaseId);
    } else if (cases.length > 0 && !selectedCaseId) {
      setSelectedCaseId(cases[0].id);
    }
  }, [initialCaseId, cases]);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      selectFile(e.dataTransfer.files[0]);
    }
  };

  const selectFile = (selected: File) => {
    setFile(selected);
    if (!title) {
      setTitle(selected.name.replace(/\.[^/.]+$/, ""));
    }
    setDuplicateWarning(null);
  };

  const pollJobStatus = async (jobId: string, docData: any) => {
    setStatusMessage("Extracting text and identifying statutory fields...");
    setUploadProgress(45);

    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const job = await api.get<any>(`/jobs/${jobId}`);
        if (job.status === "completed") {
          clearInterval(interval);
          setUploadProgress(100);
          setStatusMessage("Extraction completed successfully!");
          toast.success("Document uploaded and extracted successfully!");
          setTimeout(() => {
            onUploadSuccess?.(docData);
            handleClose();
          }, 800);
        } else if (job.status === "failed") {
          clearInterval(interval);
          setIsUploading(false);
          setStatusMessage("Extraction pipeline encountered an issue; manual review needed.");
          toast.warning("Extraction partially completed. Flagged for manual auditor review.");
          onUploadSuccess?.(docData);
          handleClose();
        } else {
          setUploadProgress((prev) => Math.min(95, prev + 10));
        }
      } catch {
        if (attempts > 15) {
          clearInterval(interval);
          setIsUploading(false);
          onUploadSuccess?.(docData);
          handleClose();
        }
      }
    }, 1000);
  };

  const handleUpload = async (asNewVersionOf?: string) => {
    if (!file) {
      toast.error("Please select a file to upload.");
      return;
    }
    const targetCaseId = selectedCaseId || initialCaseId;
    if (!targetCaseId) {
      toast.error("Please select an Audit Case.");
      return;
    }

    // Check if tabular file and offer column mapping
    const isTabular = file.name.endsWith(".csv") || file.name.endsWith(".xlsx") || file.name.endsWith(".xls");
    if (isTabular && onOpenTabularMapping && !asNewVersionOf) {
      onOpenTabularMapping(file, targetCaseId);
      handleClose();
      return;
    }

    setIsUploading(true);
    setUploadProgress(20);
    setStatusMessage("Calculating SHA-256 and uploading to secure storage...");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("case_id", targetCaseId);
      if (title) formData.append("title", title);
      if (docType && docType !== "auto") formData.append("document_type", docType);
      if (asNewVersionOf) formData.append("as_new_version_of", asNewVersionOf);

      const res = await api.post<any>("/documents/upload", formData);

      if (res.job_id) {
        pollJobStatus(res.job_id, res);
      } else {
        setUploadProgress(100);
        toast.success("Document uploaded successfully!");
        onUploadSuccess?.(res);
        handleClose();
      }
    } catch (err: any) {
      setIsUploading(false);
      if (err instanceof ApiError && err.status === 409 && err.data?.code === "DUPLICATE_CHECKSUM") {
        setDuplicateWarning(err.data);
      } else {
        toast.error(err.message || "Failed to upload document.");
      }
    }
  };

  const handleClose = () => {
    setFile(null);
    setTitle("");
    setDocType("auto");
    setDuplicateWarning(null);
    setIsUploading(false);
    setUploadProgress(0);
    setStatusMessage("");
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-display">
            <Upload className="h-5 w-5 text-primary" />
            <span>Upload Audit Evidence Document</span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Target Case selection (if not pre-selected) */}
          {!initialCaseId && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground">
                Target Audit Case *
              </label>
              <select
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                disabled={isUploading}
                className="w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
                <option value="">-- Select Audit Case --</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.case_number} - {c.title} ({c.district || "Karnataka"})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Duplicate Warning Prompt */}
          {duplicateWarning && (
            <div className="rounded-lg border border-signal-border bg-signal-surface p-3.5 space-y-2 text-xs">
              <div className="flex items-center gap-2 font-semibold text-signal">
                <AlertCircle className="h-4 w-4" />
                <span>Duplicate File Detected</span>
              </div>
              <p className="text-muted-foreground">
                This exact file (matching SHA-256 checksum) was already uploaded as{" "}
                <span className="font-semibold text-foreground">
                  "{duplicateWarning.existing_filename}"
                </span>
                .
              </p>
              <div className="flex items-center gap-2 pt-1">
                <Button
                  size="sm"
                  variant="default"
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                  onClick={() => handleUpload(duplicateWarning.existing_document_id)}
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Upload as New Version (v2+)
                </Button>
                <Button size="sm" variant="outline" onClick={() => setDuplicateWarning(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              file
                ? "border-primary/50 bg-accent/60"
                : "border-border hover:border-primary hover:bg-muted/50"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => e.target.files?.[0] && selectFile(e.target.files[0])}
              accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx,.xls"
              className="hidden"
            />
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                <div className="text-left">
                  <p className="text-sm font-semibold text-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB • Click or drag to replace
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">
                  Drag and drop document here, or <span className="text-primary underline">browse</span>
                </p>
                <p className="text-[11px] text-muted-foreground">
                  Supported formats: PDF, Scanned Images (PNG, JPG), Tabular (CSV, XLSX) • Up to 50 MB
                </p>
              </div>
            )}
          </div>

          {/* Document Title & Class Selector */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-foreground">
                Document Label / Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Tax Invoice #INV-4912"
                disabled={isUploading}
                className="w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-foreground">
                Document Class
              </label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                disabled={isUploading}
                className="w-full text-xs rounded-lg border border-input bg-background px-3 py-2 text-foreground"
              >
                <option value="auto">Auto-detect with 13-class AI Classifier</option>
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
          </div>

          {/* Progress and status message */}
          {isUploading && (
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-foreground">{statusMessage}</span>
                <span className="font-mono text-primary tabular-nums">{uploadProgress}%</span>
              </div>
              <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                <div
                  style={{ width: `${uploadProgress}%` }}
                  className="h-full bg-primary rounded-full transition-all duration-300"
                />
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            onClick={() => handleUpload()}
            disabled={!file || isUploading || (!selectedCaseId && !initialCaseId)}
          >
            {isUploading ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload & Extract
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

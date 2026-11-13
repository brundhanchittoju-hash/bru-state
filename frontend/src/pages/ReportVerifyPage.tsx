import React, { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  FileCheck2,
  Lock,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { toast } from "sonner";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { API_BASE } from "@/lib/api";

interface VerificationMetadata {
  valid: boolean;
  report_number: string;
  version_number: number;
  status: string;
  report_title: string;
  case_number: string;
  case_title: string;
  department: string;
  district: string;
  financial_year: string;
  generated_at: string | null;
  approved_at: string | null;
  approver_name: string | null;
  pdf_sha256: string;
  is_demo_data: boolean;
  page_count: number;
}

export const ReportVerifyPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const [searchParams] = useSearchParams();
  const versionParam = searchParams.get("v");

  const [metadata, setMetadata] = useState<VerificationMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // File integrity check state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isVerifyingFile, setIsVerifyingFile] = useState(false);
  const [verificationResult, setVerificationResult] = useState<{
    match: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    if (!reportId) return;
    setIsLoading(true);
    setNotFound(false);

    const q = versionParam ? `?v=${versionParam}` : "";
    fetch(`${API_BASE}/verify/${reportId}${q}`)
      .then(async (res) => {
        if (!res.ok) {
          throw new Error("Report not found");
        }
        return res.json();
      })
      .then((data) => {
        setMetadata(data);
      })
      .catch(() => {
        setNotFound(true);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [reportId, versionParam]);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (f.name.toLowerCase().endsWith(".pdf")) {
        setSelectedFile(f);
        setVerificationResult(null);
      } else {
        toast.error("Please drop a valid PDF document.");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setVerificationResult(null);
    }
  };

  const verifyFileIntegrity = async () => {
    if (!selectedFile || !reportId) return;

    try {
      setIsVerifyingFile(true);
      const formData = new FormData();
      formData.append("file", selectedFile);

      const q = versionParam ? `?v=${versionParam}` : "";
      const res = await fetch(`${API_BASE}/verify/${reportId}/file${q}`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Integrity verification failed.");
      }

      setVerificationResult({
        match: data.match,
        message: data.message,
      });
    } catch (err: any) {
      toast.error(err.message || "File verification failed.");
    } finally {
      setIsVerifyingFile(false);
    }
  };

  const copyHash = () => {
    if (metadata?.pdf_sha256) {
      navigator.clipboard.writeText(metadata.pdf_sha256);
      toast.success("SHA-256 seal copied to clipboard!");
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top Bar */}
      <header className="border-b border-border bg-card/90 backdrop-blur-md px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-primary text-primary-foreground flex items-center justify-center font-bold font-mono text-sm">
              KA
            </div>
            <div>
              <h1 className="font-display text-sm font-bold tracking-tight text-foreground">
                GOVERNMENT OF KARNATAKA
              </h1>
              <p className="text-xs text-primary font-medium">
                Karnataka State Audit Department • Public Verification Portal
              </p>
            </div>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-muted text-muted-foreground border border-border">
            Zero-Knowledge Verifier
          </span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-6 md:p-8 space-y-8">
        {isLoading ? (
          <div className="p-12 text-center space-y-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-r-transparent mx-auto" />
            <p className="text-xs font-mono text-muted-foreground">
              Querying cryptographic audit registry...
            </p>
          </div>
        ) : notFound || !metadata ? (
          <div className="p-10 rounded-2xl bg-card border border-border text-center space-y-4 max-w-lg mx-auto">
            <div className="h-12 w-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h2 className="font-display text-base font-bold text-foreground">
              Invalid or Unregistered Audit Report
            </h2>
            <p className="text-xs text-muted-foreground leading-relaxed">
              No official audit report matching identifier <code className="font-mono text-foreground font-semibold">{reportId}</code> was found in the state audit registry.
            </p>
            <p className="text-[11px] text-muted-foreground">
              Please ensure the QR code was scanned properly or contact the Karnataka State Audit Department.
            </p>
          </div>
        ) : (
          <>
            {/* Seal Card */}
            <div className="relative overflow-hidden rounded-2xl bg-card border border-border p-6 md:p-8 space-y-6">
              {metadata.is_demo_data && (
                <div className="absolute top-4 right-4 rotate-12 bg-signal-surface text-signal font-bold font-mono text-[10px] px-2.5 py-0.5 rounded border border-signal/40 select-none">
                  DEMO DATA
                </div>
              )}

              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-2xl bg-accent text-primary flex items-center justify-center border border-primary/25">
                  <ShieldCheck className="h-7 w-7" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="font-display text-lg font-bold text-foreground font-mono">
                      {metadata.report_number}
                    </h2>
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-foreground tabular-nums">
                      v{metadata.version_number}.0
                    </span>
                    <StatusPill status={metadata.status} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {metadata.report_title}
                  </p>
                </div>
              </div>

              {/* Particulars Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-xl bg-muted/40 border border-border text-xs">
                <div>
                  <span className="text-muted-foreground block text-[11px]">Audit Case ID</span>
                  <span className="font-mono font-medium text-foreground">
                    {metadata.case_number}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Department</span>
                  <span className="font-medium text-foreground truncate block">
                    {metadata.department}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">District / FY</span>
                  <span className="font-medium text-foreground font-mono tabular-nums">
                    {metadata.district} • {metadata.financial_year}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block text-[11px]">Dual Sign-off</span>
                  <span className="font-medium text-foreground">
                    {metadata.approver_name || "Pending Senior Officer"}
                  </span>
                </div>
              </div>

              {/* SHA-256 Box */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-foreground flex items-center gap-1.5">
                    <Lock className="h-3.5 w-3.5 text-primary" />
                    Cryptographic SHA-256 Hash Seal
                  </span>
                  <button
                    onClick={copyHash}
                    className="text-[11px] text-primary hover:underline flex items-center gap-1"
                  >
                    <Copy className="h-3 w-3" />
                    Copy Seal
                  </button>
                </div>
                <div className="p-3 rounded-xl bg-muted/60 font-mono text-[11px] text-foreground break-all select-all border border-border">
                  {metadata.pdf_sha256}
                </div>
              </div>

              {/* Zero Knowledge Notice */}
              <div className="p-3 rounded-xl bg-accent/50 border border-primary/20 text-[11px] text-foreground/90 leading-relaxed">
                <span className="font-semibold text-primary block mb-0.5">Zero-Knowledge Guarantee:</span>
                This public register confirms official document existence and cryptographic validity.
                Individual questioned amounts, supplier names, and finding texts are protected under
                statutory audit rules and are accessible only to authorized audit personnel.
              </div>
            </div>

            {/* Document Integrity Verifier Widget */}
            <div className="rounded-2xl bg-card border border-border p-6 md:p-8 space-y-5">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-muted text-foreground flex items-center justify-center">
                  <FileCheck2 className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-display text-base font-bold text-foreground">
                    Verify Document Authenticity
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Upload your digital copy of this report to prove it has not been modified or tampered with.
                  </p>
                </div>
              </div>

              {/* Dropzone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                className="border-2 border-dashed border-border hover:border-primary rounded-2xl p-6 text-center cursor-pointer transition-colors bg-muted/30"
              >
                <input
                  type="file"
                  id="pdf_upload_input"
                  accept=".pdf"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <label htmlFor="pdf_upload_input" className="cursor-pointer space-y-2 block">
                  <UploadCloud className="h-8 w-8 mx-auto text-muted-foreground" />
                  <p className="text-xs font-medium text-foreground">
                    {selectedFile ? (
                      <span className="text-primary font-semibold font-mono tabular-nums">
                        {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </span>
                    ) : (
                      <>
                        <span className="text-primary">Click to upload</span> or drag and drop your PDF report here
                      </>
                    )}
                  </p>
                  <p className="text-[11px] text-muted-foreground">PDF files up to 25 MB</p>
                </label>
              </div>

              {selectedFile && (
                <div className="flex justify-end">
                  <Button
                    onClick={verifyFileIntegrity}
                    disabled={isVerifyingFile}
                    className="gap-2 text-xs"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {isVerifyingFile ? "Computing Checksum..." : "Verify Cryptographic Match"}
                  </Button>
                </div>
              )}

              {/* Verification Result Banner */}
              {verificationResult && (
                <div
                  className={`p-4 rounded-xl border text-xs flex items-start gap-3 animate-in fade-in duration-200 ${
                    verificationResult.match
                      ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200"
                      : "bg-destructive/10 border-destructive/30 text-destructive"
                  }`}
                >
                  {verificationResult.match ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1">
                    <p className="font-semibold text-sm">
                      {verificationResult.match
                        ? "MATCH CONFIRMED: Document is Authentic"
                        : "TAMPER WARNING: Integrity Mismatch"}
                    </p>
                    <p className="leading-relaxed">{verificationResult.message}</p>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-[11px] text-muted-foreground">
        Karnataka State Audit Department • Government of Karnataka • Powered by SHA-256 Hash Chaining
      </footer>
    </div>
  );
};

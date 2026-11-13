import React, { useEffect, useState } from "react";
import { ColumnDef } from "@tanstack/react-table";
import { Upload, Download, Eye, RefreshCw, Copy, Check } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { FilterBar } from "@/components/shared/FilterBar";
import { DataTable } from "@/components/shared/DataTable";
import { StatusPill } from "@/components/shared/StatusPill";
import { ConfidenceBadge } from "@/components/documents/ConfidenceBadge";
import { DocumentUploadModal } from "@/components/documents/DocumentUploadModal";
import { TabularMappingModal } from "@/components/documents/TabularMappingModal";
import { DocumentViewer } from "@/components/documents/DocumentViewer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api, API_BASE } from "@/lib/api";
import { DocumentItem, AuditCase } from "@/types";
import { toast } from "sonner";

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [cases, setCases] = useState<AuditCase[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Modals
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isTabularModalOpen, setIsTabularModalOpen] = useState<boolean>(false);
  const [tabularFile, setTabularFile] = useState<File | null>(null);
  const [tabularCaseId, setTabularCaseId] = useState<string>("");

  // Active Document Viewer
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // Copy helper
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      let url = "/documents?";
      const params = new URLSearchParams();
      if (searchQuery) params.append("search", searchQuery);
      if (typeFilter) params.append("document_type", typeFilter);
      if (statusFilter) params.append("status", statusFilter);

      const [docsRes, casesRes] = await Promise.all([
        api.get<DocumentItem[]>(url + params.toString()),
        api.get<AuditCase[]>("/cases"),
      ]);

      setDocuments(docsRes);
      setCases(casesRes);
    } catch {
      toast.error("Failed to load documents repository.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [searchQuery, typeFilter, statusFilter]);

  // Polling if any document is in "processing" or "uploaded" status
  useEffect(() => {
    const hasPending = documents.some((d) => d.status === "processing" || d.status === "uploaded");
    if (!hasPending) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.get<DocumentItem[]>("/documents");
        setDocuments(res);
      } catch {
        // Silent poll error
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [documents]);

  const handleCopyHash = (hash: string, id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    toast.success("SHA-256 hash copied");
  };

  const handleOpenTabularMapping = (file: File, caseId: string) => {
    setTabularFile(file);
    setTabularCaseId(caseId);
    setIsTabularModalOpen(true);
  };

  const columns: ColumnDef<DocumentItem>[] = [
    {
      accessorKey: "title",
      header: "Document Title & Filename",
      cell: ({ row }) => (
        <div className="space-y-0.5 max-w-sm">
          <p className="font-semibold text-xs text-foreground truncate">
            {row.getValue("title") || row.original.original_filename}
          </p>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
            <span className="truncate">{row.original.original_filename}</span>
            <span>•</span>
            <span className="bg-muted px-1.5 py-0.2 rounded text-[10px]">
              v{row.original.current_version}
            </span>
          </div>
        </div>
      ),
    },
    {
      accessorKey: "document_type",
      header: "Classification",
      cell: ({ row }) => (
        <div className="space-y-1">
          <Badge
            variant="outline"
            className="text-[11px] bg-accent text-accent-foreground border-primary/20"
          >
            {row.getValue("document_type") || "Unknown"}
          </Badge>
          <div>
            <ConfidenceBadge confidence={row.original.classification_confidence} compact />
          </div>
        </div>
      ),
    },
    {
      accessorKey: "sha256_hash",
      header: "SHA-256 Checksum",
      cell: ({ row }) => {
        const hash = row.getValue("sha256_hash") as string;
        const isCopied = copiedId === row.original.id;
        return (
          <button
            onClick={(e) => handleCopyHash(hash, row.original.id, e)}
            className="flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground hover:text-primary group"
            title="Click to copy SHA-256"
          >
            <span>{hash.substring(0, 12)}...</span>
            {isCopied ? (
              <Check className="h-3 w-3 text-emerald-500" />
            ) : (
              <Copy className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            )}
          </button>
        );
      },
    },
    {
      accessorKey: "file_size",
      header: "Size & Pages",
      cell: ({ row }) => (
        <div className="text-[11px] text-muted-foreground font-mono tabular-nums">
          <p>{(row.original.file_size / 1024).toFixed(1)} KB</p>
          <p className="opacity-75">{row.original.page_count || 1} pages</p>
        </div>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => <StatusPill status={row.getValue("status")} />,
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedDocId(row.original.id);
            }}
            className="h-7 px-2 text-xs text-primary hover:text-primary"
          >
            <Eye className="h-3.5 w-3.5 mr-1" />
            Inspect
          </Button>
          <Button
            size="icon"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              window.open(`${API_BASE}/documents/${row.original.id}/download`, "_blank");
            }}
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            title="Download document"
          >
            <Download className="h-3.5 w-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  const selectCls =
    "h-9 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="space-y-5">
      <PageHeader
        title="Document Ingestion & Repository"
        description="Centralized statutory evidence archive with cryptographic SHA-256 hashing, 13-class bilingual classification, and dual-mode coordinate extraction."
      >
        <Button onClick={() => setIsUploadModalOpen(true)}>
          <Upload className="h-4 w-4 mr-1.5" />
          Upload Document
        </Button>
      </PageHeader>

      {/* Show Document Viewer if active */}
      {selectedDocId ? (
        <DocumentViewer
          documentId={selectedDocId}
          onClose={() => setSelectedDocId(null)}
          onRefresh={loadDocuments}
        />
      ) : (
        <>
          <FilterBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            placeholder="Search by title, original filename, or checksum..."
            onReset={
              searchQuery || typeFilter || statusFilter
                ? () => {
                    setSearchQuery("");
                    setTypeFilter("");
                    setStatusFilter("");
                  }
                : undefined
            }
          >
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className={selectCls}
              aria-label="Filter by document class"
            >
              <option value="">All Document Classes</option>
              <option value="Bill">Bill / Tax Invoice</option>
              <option value="Voucher">Payment Voucher</option>
              <option value="Work Order">Work Order</option>
              <option value="Sanction Order">Sanction Order</option>
              <option value="Tender">Tender Notice</option>
              <option value="Measurement Book">Measurement Book</option>
              <option value="Completion Certificate">Completion Certificate</option>
              <option value="Utilization Certificate">Utilization Certificate</option>
              <option value="Cash Book">Cash Book</option>
              <option value="Ledger">General Ledger</option>
              <option value="Bank Statement">Bank Statement</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className={selectCls}
              aria-label="Filter by status"
            >
              <option value="">All Statuses</option>
              <option value="processed">Processed</option>
              <option value="processing">Processing</option>
              <option value="uploaded">Uploaded</option>
              <option value="failed">Failed</option>
            </select>

            <Button size="icon" variant="outline" onClick={loadDocuments} className="h-9 w-9" title="Refresh">
              <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </FilterBar>

          {/* DataTable */}
          <DataTable
            columns={columns}
            data={documents}
            isLoading={isLoading}
            emptyMessage="No documents found in repository."
            onRowClick={(doc: DocumentItem) => setSelectedDocId(doc.id)}
          />
        </>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        cases={cases}
        onUploadSuccess={() => {
          loadDocuments();
        }}
        onOpenTabularMapping={handleOpenTabularMapping}
      />

      {/* Tabular Mapping Modal */}
      <TabularMappingModal
        isOpen={isTabularModalOpen}
        onClose={() => {
          setIsTabularModalOpen(false);
          setTabularFile(null);
        }}
        file={tabularFile}
        caseId={tabularCaseId}
        onSuccess={() => {
          loadDocuments();
        }}
      />
    </div>
  );
};

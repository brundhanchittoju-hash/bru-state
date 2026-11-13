import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ColumnDef } from "@tanstack/react-table";
import { Building, ExternalLink, ShieldAlert, CheckCircle2 } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { FilterBar } from "@/components/shared/FilterBar";
import { DataTable } from "@/components/shared/DataTable";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface VendorListItem {
  id: string;
  canonical_name: string;
  pan?: string;
  gstin?: string;
  state?: string;
  risk_level: string;
  total_spend: number;
  findings_count: number;
  records_count: number;
}

export const VendorsPage: React.FC = () => {
  const navigate = useNavigate();
  const [vendors, setVendors] = useState<VendorListItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [riskFilter, setRiskFilter] = useState<string>("");

  const loadVendors = async () => {
    setIsLoading(true);
    try {
      const q = new URLSearchParams();
      if (searchQuery) q.append("search", searchQuery);
      if (riskFilter) q.append("risk_level", riskFilter);

      const res = await api.get<VendorListItem[]>(`/vendors?${q.toString()}`);
      setVendors(res);
    } catch {
      toast.error("Failed to load vendors list.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadVendors();
  }, [searchQuery, riskFilter]);

  const columns: ColumnDef<VendorListItem>[] = [
    {
      accessorKey: "canonical_name",
      header: "Vendor Legal / Canonical Name",
      cell: ({ row }) => (
        <div
          onClick={() => navigate(`/vendors/${row.original.id}`)}
          className="cursor-pointer group flex items-center gap-2"
        >
          <Building className="h-4 w-4 text-muted-foreground group-hover:text-primary" />
          <span className="font-semibold text-foreground group-hover:text-primary transition-colors">
            {row.original.canonical_name}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "pan",
      header: "PAN",
      cell: ({ row }) => (
        <span className="font-mono text-xs font-medium text-foreground/85">
          {row.original.pan || "N/A"}
        </span>
      ),
    },
    {
      accessorKey: "gstin",
      header: "GSTIN",
      cell: ({ row }) => (
        <span className="font-mono text-xs font-medium text-foreground/85">
          {row.original.gstin || "N/A"}
        </span>
      ),
    },
    {
      accessorKey: "risk_level",
      header: "Risk Status",
      cell: ({ row }) => {
        const isHigh = row.original.risk_level.toLowerCase() === "high";
        return isHigh ? (
          <Badge variant="destructive" className="gap-1 text-[10px]">
            <ShieldAlert className="h-3 w-3" />
            <span>Flagged</span>
          </Badge>
        ) : (
          <Badge variant="secondary" className="gap-1 text-[10px]">
            <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
            <span>Standard</span>
          </Badge>
        );
      },
    },
    {
      accessorKey: "total_spend",
      header: "Total Spend (₹)",
      cell: ({ row }) => (
        <span className="font-mono font-medium tabular-nums">
          ₹{row.original.total_spend.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      accessorKey: "findings_count",
      header: "Linked Findings",
      cell: ({ row }) => {
        const cnt = row.original.findings_count;
        return (
          <span className={`font-mono font-semibold tabular-nums ${cnt > 0 ? "text-rose-600 dark:text-rose-400" : "text-muted-foreground"}`}>
            {cnt}
          </span>
        );
      },
    },
    {
      id: "actions",
      header: "Dossier",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/vendors/${row.original.id}`)}
          className="h-7 px-2 text-xs gap-1"
        >
          <span>View</span>
          <ExternalLink className="h-3 w-3 text-muted-foreground" />
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendors & Contractors Intelligence"
        description="Resolved vendor entities, tax identification validity, historical expenditure records, and linked audit findings."
        badge={
          <Badge variant="outline" className="text-xs border-primary/30 text-primary font-mono tabular-nums">
            {vendors.length} Resolved Vendors
          </Badge>
        }
      />

      {/* Filter and Search Bar */}
      <FilterBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        placeholder="Filter vendors by legal name, PAN, or GSTIN..."
        onReset={
          searchQuery || riskFilter
            ? () => {
                setSearchQuery("");
                setRiskFilter("");
              }
            : undefined
        }
      >
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="h-9 rounded-lg border border-input bg-card px-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label="Filter by risk profile"
        >
          <option value="">All Risk Profiles</option>
          <option value="high">Flagged Only</option>
          <option value="low">Standard Only</option>
        </select>
      </FilterBar>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={vendors}
        isLoading={isLoading}
        onRowClick={(row) => navigate(`/vendors/${row.id}`)}
      />
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Search,
  Briefcase,
  Building,
  FileText,
  AlertTriangle,
  FileCheck2,
  ExternalLink,
  Info,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface SearchItem {
  id: string;
  entity_type: string;
  title: string;
  subtitle?: string;
  badge?: string;
  link: string;
}

interface SearchResponse {
  query: string;
  basic_search_mode: boolean;
  total_results: number;
  results: Record<string, SearchItem[]>;
}

export const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryParam = searchParams.get("q") || "";

  const [inputVal, setInputVal] = useState<string>(queryParam);
  const [resultsData, setResultsData] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("all");

  const performSearch = async (term: string) => {
    if (!term || term.trim().length < 2) {
      setResultsData(null);
      return;
    }
    setIsLoading(true);
    try {
      const res = await api.get<SearchResponse>(`/search?q=${encodeURIComponent(term.trim())}&limit_per_entity=10`);
      setResultsData(res);
    } catch {
      toast.error("Failed to execute search query.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (queryParam) {
      setInputVal(queryParam);
      performSearch(queryParam);
    }
  }, [queryParam]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim() || inputVal.trim().length < 2) {
      toast.error("Please enter at least 2 characters to search.");
      return;
    }
    setSearchParams({ q: inputVal.trim() });
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case "cases":
        return <Briefcase className="h-4 w-4 text-primary" />;
      case "vendors":
        return <Building className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />;
      case "departments":
        return <Building className="h-4 w-4 text-sky-600 dark:text-sky-400" />;
      case "findings":
        return <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />;
      case "vouchers":
      case "bills":
        return <FileText className="h-4 w-4 text-signal" />;
      case "reports":
        return <FileCheck2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />;
      default:
        return <Search className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const renderGroup = (entityKey: string, title: string, items: SearchItem[]) => {
    if (!items || items.length === 0) return null;
    return (
      <div key={entityKey} className="space-y-2.5">
        <div className="flex items-center justify-between border-b border-border pb-1.5">
          <div className="flex items-center gap-2">
            {getEntityIcon(entityKey)}
            <h3 className="font-display text-sm font-semibold text-foreground">{title}</h3>
          </div>
          <Badge variant="secondary" className="text-xs font-mono tabular-nums">
            {items.length} {items.length === 1 ? "match" : "matches"}
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => navigate(item.link)}
              className="p-3.5 rounded-xl border border-border bg-card hover:border-primary/50 cursor-pointer transition-colors flex items-start justify-between text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-semibold text-foreground">{item.title}</span>
                  {item.badge && (
                    <Badge variant="outline" className="text-[10px]">
                      {item.badge}
                    </Badge>
                  )}
                </div>
                {item.subtitle && <p className="text-muted-foreground text-[11px]">{item.subtitle}</p>}
              </div>
              <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Universal Audit Search"
        description="Search across audit cases, resolved vendors, departments, financial vouchers, extracted bills, findings, and reports."
        badge={
          <Badge variant="outline" className="text-xs border-primary/30 text-primary font-mono">
            7 Indexed Domains
          </Badge>
        }
      />

      {/* Search Input Bar */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Search by case code, vendor name, PAN, voucher ID, rule description..."
            className="w-full h-11 pl-10 pr-4 rounded-xl border border-input bg-card text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <Button type="submit" disabled={isLoading} className="h-11 px-6">
          {isLoading ? "Searching..." : "Search"}
        </Button>
      </form>

      {/* Basic Search Mode Fallback Indicator */}
      {resultsData?.basic_search_mode && (
        <div className="flex items-center gap-3 p-3 rounded-xl border border-primary/25 bg-accent/50 text-foreground text-xs">
          <Info className="h-4 w-4 shrink-0 text-primary" />
          <div className="flex-1">
            <span className="font-semibold">Basic Search Mode Active:</span> SQL pattern matching fallback active.
            Results are queried across all 7 statutory entities.
          </div>
        </div>
      )}

      {/* Tabs */}
      {resultsData && (
        <div className="flex items-center gap-1.5 border-b border-border pb-2 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveTab("all")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-colors tabular-nums ${
              activeTab === "all"
                ? "bg-accent text-accent-foreground font-semibold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All Results ({resultsData.total_results})
          </button>
          {Object.entries(resultsData.results).map(([k, items]) => {
            if (items.length === 0) return null;
            return (
              <button
                key={k}
                onClick={() => setActiveTab(k)}
                className={`px-3 py-1.5 rounded-lg font-medium capitalize transition-colors tabular-nums ${
                  activeTab === k
                    ? "bg-accent text-accent-foreground font-semibold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {k} ({items.length})
              </button>
            );
          })}
        </div>
      )}

      {/* Results Content */}
      {isLoading ? (
        <div className="py-20 text-center text-sm text-muted-foreground">Searching records...</div>
      ) : !resultsData ? (
        <div className="py-20 text-center text-sm text-muted-foreground">Enter a search term above or press Ctrl+K anywhere.</div>
      ) : resultsData.total_results === 0 ? (
        <div className="py-16 text-center text-sm text-muted-foreground space-y-2">
          <p className="font-medium text-foreground">No matching records found for "{resultsData.query}".</p>
          <p className="text-xs text-muted-foreground">Try searching with a broader term, PAN prefix, or case number.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {(activeTab === "all" || activeTab === "cases") &&
            renderGroup("cases", "Audit Cases", resultsData.results.cases)}
          {(activeTab === "all" || activeTab === "findings") &&
            renderGroup("findings", "Flagged Findings", resultsData.results.findings)}
          {(activeTab === "all" || activeTab === "vendors") &&
            renderGroup("vendors", "Vendors & Contractors", resultsData.results.vendors)}
          {(activeTab === "all" || activeTab === "vouchers") &&
            renderGroup("vouchers", "Payment Vouchers", resultsData.results.vouchers)}
          {(activeTab === "all" || activeTab === "bills") &&
            renderGroup("bills", "Invoices & Bills", resultsData.results.bills)}
          {(activeTab === "all" || activeTab === "departments") &&
            renderGroup("departments", "Departments & Panchayats", resultsData.results.departments)}
          {(activeTab === "all" || activeTab === "reports") &&
            renderGroup("reports", "Reports & Paras", resultsData.results.reports)}
        </div>
      )}
    </div>
  );
};

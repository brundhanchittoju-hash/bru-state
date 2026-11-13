import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Building,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  CreditCard,
  Layers,
  ExternalLink,
} from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import { RiskBadge } from "@/components/shared/RiskBadge";
import { StatusPill } from "@/components/shared/StatusPill";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "sonner";

interface VendorAlias {
  id: string;
  raw_name: string;
  confidence_score: number;
  source: string;
}

interface VendorDossier {
  id: string;
  canonical_name: string;
  pan?: string;
  is_pan_valid: boolean;
  gstin?: string;
  is_gstin_valid: boolean;
  state?: string;
  risk_level: string;
  bank_account_number?: string;
  ifsc_code?: string;
  aliases: VendorAlias[];
  total_spend: number;
  total_records: number;
  total_findings: number;
  findings: Array<{
    id: string;
    finding_number: string;
    title: string;
    case_number?: string;
    rule_code?: string;
    severity: string;
    risk_score: number;
    amount: number;
    status: string;
    created_at: string;
  }>;
  recent_transactions: Array<{
    id: string;
    record_type: string;
    record_number: string;
    record_date?: string;
    amount: number;
    description?: string;
    case_id: string;
  }>;
}

export const VendorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [dossier, setDossier] = useState<VendorDossier | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadDossier() {
      if (!id) return;
      setIsLoading(true);
      try {
        const res = await api.get<VendorDossier>(`/vendors/${id}`);
        setDossier(res);
      } catch {
        toast.error("Failed to load vendor dossier.");
      } finally {
        setIsLoading(false);
      }
    }
    loadDossier();
  }, [id]);

  if (isLoading) {
    return <div className="py-20 text-center text-sm text-muted-foreground">Loading vendor dossier...</div>;
  }

  if (!dossier) {
    return <div className="py-20 text-center text-sm text-muted-foreground">Vendor record not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/vendors")} className="gap-1.5 text-xs">
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>All Vendors</span>
        </Button>
      </div>

      <div className="p-5 rounded-xl border border-border bg-card space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5 flex-wrap">
              <Building className="h-5 w-5 text-primary" />
              <h2 className="font-display text-xl font-bold text-foreground">{dossier.canonical_name}</h2>
              {dossier.risk_level === "high" ? (
                <Badge variant="destructive" className="gap-1 text-xs">
                  <AlertTriangle className="h-3 w-3" />
                  <span>Flagged Vendor</span>
                </Badge>
              ) : (
                <Badge variant="secondary" className="gap-1 text-xs">
                  <CheckCircle2 className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
                  <span>Verified Standard</span>
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              State: <span className="font-medium text-foreground">{dossier.state || "Karnataka"}</span> • Bank IFSC:{" "}
              <span className="font-mono text-foreground">{dossier.ifsc_code || "N/A"}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* PAN Validity Pill */}
            <div className="px-3 py-1.5 rounded-xl border border-border bg-muted/40 flex items-center gap-2 text-xs">
              <span className="font-semibold text-muted-foreground">PAN:</span>
              <span className="font-mono font-bold text-foreground">{dossier.pan || "N/A"}</span>
              {dossier.is_pan_valid ? (
                <Badge variant="success" className="text-[10px] gap-0.5">
                  <CheckCircle2 className="h-2.5 w-2.5" /> Valid
                </Badge>
              ) : (
                <Badge variant="destructive" className="text-[10px] gap-0.5">
                  <XCircle className="h-2.5 w-2.5" /> Invalid
                </Badge>
              )}
            </div>

            {/* GSTIN Validity Pill */}
            <div className="px-3 py-1.5 rounded-xl border border-border bg-muted/40 flex items-center gap-2 text-xs">
              <span className="font-semibold text-muted-foreground">GSTIN:</span>
              <span className="font-mono font-bold text-foreground">{dossier.gstin || "N/A"}</span>
              {dossier.is_gstin_valid ? (
                <Badge variant="success" className="text-[10px] gap-0.5">
                  <CheckCircle2 className="h-2.5 w-2.5" /> Valid
                </Badge>
              ) : (
                <Badge variant="destructive" className="text-[10px] gap-0.5">
                  <XCircle className="h-2.5 w-2.5" /> Invalid
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Total Audited Spend"
          value={`₹${dossier.total_spend.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
          description="Cumulative across all local bodies"
          icon={<CreditCard className="h-4 w-4 text-primary" />}
          tone="primary"
        />
        <StatCard
          title="Financial Transactions"
          value={String(dossier.total_records)}
          description="Vouchers & ledger entries matched"
          icon={<FileText className="h-4 w-4 text-primary" />}
          tone="primary"
        />
        <StatCard
          title="Linked Audit Findings"
          value={String(dossier.total_findings)}
          description="Flagged across verification rules"
          icon={<AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />}
          tone="danger"
        />
      </div>

      {/* Aliases & Disambiguation */}
      <div className="p-4 rounded-xl border border-border bg-card space-y-3">
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <Layers className="h-4 w-4 text-primary" />
          <h3 className="font-display text-sm font-semibold text-foreground">
            Resolved Entity Aliases & Ingested Variations
          </h3>
        </div>

        <div className="flex flex-wrap gap-2">
          {(!dossier.aliases || dossier.aliases.length === 0) ? (
            <span className="text-xs text-muted-foreground">No alias variants detected for this vendor.</span>
          ) : (
            dossier.aliases.map((a) => (
              <Badge key={a.id} variant="secondary" className="text-xs gap-1.5 py-1 px-2.5">
                <span>{a.raw_name}</span>
                <span className="text-[10px] opacity-70 font-mono tabular-nums">({Math.round(a.confidence_score * 100)}%)</span>
              </Badge>
            ))
          )}
        </div>
      </div>

      {/* Linked Findings Table */}
      <div className="p-4 rounded-xl border border-border bg-card space-y-3">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h3 className="font-display text-sm font-semibold text-foreground">
            Audit Findings Associated with Vendor ({(dossier.findings || []).length})
          </h3>
        </div>

        {(!dossier.findings || dossier.findings.length === 0) ? (
          <p className="text-xs text-muted-foreground py-4 text-center">No audit findings flagged for this vendor.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-semibold">Finding ID</th>
                  <th className="px-3 py-2 font-semibold">Case</th>
                  <th className="px-3 py-2 font-semibold">Title</th>
                  <th className="px-3 py-2 font-semibold">Risk</th>
                  <th className="px-3 py-2 font-semibold">Flagged Amount</th>
                  <th className="px-3 py-2 font-semibold">Status</th>
                  <th className="px-3 py-2 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {dossier.findings.map((f) => (
                  <tr key={f.id} className="hover:bg-muted/40 transition-colors">
                    <td className="px-3 py-2 font-mono font-semibold text-primary">
                      {f.finding_number}
                    </td>
                    <td className="px-3 py-2 font-mono text-muted-foreground">{f.case_number || "N/A"}</td>
                    <td className="px-3 py-2 font-medium text-foreground">{f.title}</td>
                    <td className="px-3 py-2">
                      <RiskBadge level={f.severity} />
                      <span className="font-mono text-[10px] text-muted-foreground font-bold ml-1 tabular-nums">({f.risk_score.toFixed(0)})</span>
                    </td>
                    <td className="px-3 py-2 font-mono tabular-nums text-foreground">
                      ₹{f.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-3 py-2">
                      <StatusPill status={f.status} />
                    </td>
                    <td className="px-3 py-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/findings/${f.id}`)}
                        className="h-6 px-2 text-[11px] gap-1"
                      >
                        <span>Evidence</span>
                        <ExternalLink className="h-2.5 w-2.5 text-muted-foreground" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Recent Transactions Table */}
      <div className="p-4 rounded-xl border border-border bg-card space-y-3">
        <h3 className="font-display text-sm font-semibold text-foreground border-b border-border pb-2">
          Recent Payment Transactions ({dossier.recent_transactions.length})
        </h3>

        {dossier.recent_transactions.length === 0 ? (
          <p className="text-xs text-muted-foreground py-4 text-center">No payment transactions recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-semibold">Voucher / Doc #</th>
                  <th className="px-3 py-2 font-semibold">Date</th>
                  <th className="px-3 py-2 font-semibold">Amount</th>
                  <th className="px-3 py-2 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {dossier.recent_transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-muted/40 transition-colors">
                    <td className="px-3 py-2 font-mono font-medium text-foreground">
                      {t.record_number}
                    </td>
                    <td className="px-3 py-2 font-mono text-muted-foreground tabular-nums">{t.record_date || "N/A"}</td>
                    <td className="px-3 py-2 font-mono font-medium tabular-nums text-foreground">
                      ₹{t.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{t.description || "N/A"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { FindingHeader } from "@/components/findings/FindingHeader";
import { FindingActionDialogs } from "@/components/findings/FindingActionDialogs";
import { FindingLeftPaneViewer } from "@/components/findings/FindingLeftPaneViewer";
import { ExtractedValuesTab } from "@/components/findings/ExtractedValuesTab";
import { ComparisonTab } from "@/components/findings/ComparisonTab";
import { CalculationReasonTab } from "@/components/findings/CalculationReasonTab";
import { ReviewerNotesTab } from "@/components/findings/ReviewerNotesTab";
import { FindingTimelineTab } from "@/components/findings/FindingTimelineTab";
import { RelatedFindingsTab } from "@/components/findings/RelatedFindingsTab";

export const FindingEvidencePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [finding, setFinding] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<
    "extracted" | "comparison" | "calculation" | "notes" | "timeline" | "related"
  >("extracted");
  const [selectedDocId, setSelectedDocId] = useState<string | undefined>(undefined);
  const [activeAction, setActiveAction] = useState<string | null>(null);

  const fetchFindingDetail = async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await api.get<any>(`/findings/${id}`);
      setFinding(data);
      if (data.documents_used?.length > 0) {
        setSelectedDocId(data.documents_used[0].id);
      }
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to load finding evidence.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFindingDetail();
  }, [id]);

  const handleReviewAction = async (action: string, comment: string, targetStatus?: string) => {
    if (!id) return;
    try {
      const res = await api.post<any>(`/findings/${id}/review`, {
        action,
        comment,
        target_status: targetStatus,
      });
      toast.success(res.message || "Review action recorded.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Review action failed.");
      throw err;
    }
  };

  const handleOverrideField = async (fieldId: string, correctedValue: string, reason: string) => {
    try {
      await api.patch(`/documents/fields/${fieldId}/override`, {
        override_value: correctedValue,
        override_reason: reason,
      });
      toast.success("Field override recorded in hash-chained audit trail.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Field override failed.");
      throw err;
    }
  };

  const handleAddNote = async (content: string, parentId?: string) => {
    if (!id) return;
    try {
      await api.post(`/findings/${id}/notes`, { content, parent_id: parentId });
      toast.success("Reviewer note added.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to add note.");
    }
  };

  const handleEditNote = async (noteId: string, content: string) => {
    if (!id) return;
    try {
      await api.patch(`/findings/${id}/notes/${noteId}`, { content });
      toast.success("Note updated.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to update note.");
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!id) return;
    try {
      await api.delete(`/findings/${id}/notes/${noteId}`);
      toast.success("Note deleted.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Failed to delete note.");
    }
  };

  const handleTriggerReVerify = async () => {
    if (!finding?.case_id) return;
    try {
      await api.post(`/cases/${finding.case_id}/verify`);
      toast.success("Verification re-run complete. Evidence refreshed.");
      await fetchFindingDetail();
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || "Verification run failed.");
    }
  };

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-10 w-1/3" />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <Skeleton className="lg:col-span-6 h-[600px] rounded-xl" />
          <Skeleton className="lg:col-span-6 h-[600px] rounded-xl" />
        </div>
      </div>
    );
  }

  if (!finding) {
    return (
      <div className="p-8 text-center space-y-3">
        <p className="text-muted-foreground">Finding not found or has been removed.</p>
        <Button onClick={() => navigate("/findings")} variant="outline">
          Return to Findings
        </Button>
      </div>
    );
  }

  const isHighOrCritical = ["high", "critical"].includes(finding.risk_level?.toLowerCase());

  return (
    <div className="space-y-4 print:p-0">
      {/* Back & Print Bar (Hidden during print) */}
      <div className="flex items-center justify-between gap-2 print:hidden">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/findings")}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          Back to Findings Register
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrint}
          className="text-xs"
        >
          <Printer className="h-3.5 w-3.5 mr-1.5" />
          Print Audit Dossier
        </Button>
      </div>

      {/* Header Banner */}
      <FindingHeader
        finding={finding}
        currentUserId={user?.id}
        currentUserRole={user?.role?.code}
        onOpenAction={(action) => setActiveAction(action)}
      />

      {/* Main Split-Pane Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Pane: Interactive Document & Evidence Viewer (6 cols) */}
        <div className="lg:col-span-6 min-h-[600px]">
          <FindingLeftPaneViewer
            documentsUsed={finding.documents_used || []}
            evidenceList={finding.evidence || []}
            selectedDocId={selectedDocId}
            onSelectDoc={(docId) => setSelectedDocId(docId)}
          />
        </div>

        {/* Right Pane: Multi-Tab Evidence Dossier (6 cols) */}
        <div className="lg:col-span-6">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as any)}>
            <TabsList className="w-full justify-start overflow-x-auto h-auto flex-wrap gap-1 p-1">
              {[
                { id: "extracted", label: "Extracted Values" },
                { id: "comparison", label: "Comparison" },
                { id: "calculation", label: "Calculation & Reason" },
                { id: "notes", label: `Notes (${finding.notes?.length || 0})` },
                { id: "timeline", label: "Timeline" },
                { id: "related", label: `Documents & Related (${finding.related_findings?.length || 0})` },
              ].map((tab) => (
                <TabsTrigger key={tab.id} value={tab.id}>
                  {tab.label}
                </TabsTrigger>
              ))}
            </TabsList>

            <div className="mt-3 bg-card rounded-2xl border border-border p-4 min-h-[480px] shadow-sm">
              <TabsContent value="extracted" className="mt-0">
                <ExtractedValuesTab
                  extractedValues={finding.extracted_values || []}
                  onOverrideField={handleOverrideField}
                  onTriggerReVerify={handleTriggerReVerify}
                  isLocked={finding.is_case_locked}
                />
              </TabsContent>

              <TabsContent value="comparison" className="mt-0">
                <ComparisonTab comparisonData={finding.comparison_data || []} />
              </TabsContent>

              <TabsContent value="calculation" className="mt-0">
                <CalculationReasonTab finding={finding} />
              </TabsContent>

              <TabsContent value="notes" className="mt-0">
                <ReviewerNotesTab
                  notes={finding.notes || []}
                  currentUserId={user?.id}
                  onAddNote={handleAddNote}
                  onEditNote={handleEditNote}
                  onDeleteNote={handleDeleteNote}
                  isLocked={finding.is_case_locked}
                />
              </TabsContent>

              <TabsContent value="timeline" className="mt-0">
                <FindingTimelineTab timeline={finding.timeline || []} />
              </TabsContent>

              <TabsContent value="related" className="mt-0">
                <RelatedFindingsTab
                  documentsUsed={finding.documents_used || []}
                  relatedFindings={finding.related_findings || []}
                  annotations={finding.annotations || []}
                  onSelectDoc={(docId) => setSelectedDocId(docId)}
                />
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>

      {/* Review Action Modals */}
      <FindingActionDialogs
        actionType={activeAction}
        findingNumber={finding.finding_number}
        isHighOrCritical={isHighOrCritical}
        currentUserRole={user?.role?.code}
        isOpen={!!activeAction}
        onClose={() => setActiveAction(null)}
        onSubmit={handleReviewAction}
      />
    </div>
  );
};

import React, { useState } from "react";
import { Edit3, CheckCircle2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfidenceBadge } from "@/components/documents/ConfidenceBadge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ExtractedValuesTabProps {
  extractedValues: any[];
  onOverrideField: (fieldId: string, correctedValue: string, reason: string) => Promise<void>;
  onTriggerReVerify?: () => void;
  isLocked?: boolean;
}

export const ExtractedValuesTab: React.FC<ExtractedValuesTabProps> = ({
  extractedValues,
  onOverrideField,
  onTriggerReVerify,
  isLocked = false,
}) => {
  const [selectedField, setSelectedField] = useState<any | null>(null);
  const [correctedValue, setCorrectedValue] = useState("");
  const [overrideReason, setOverrideReason] = useState("");
  const [hasOverridden, setHasOverridden] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpenModal = (f: any) => {
    setSelectedField(f);
    setCorrectedValue(f.effective_value || f.original_value || "");
    setOverrideReason("");
    setError(null);
  };

  const handleSubmitOverride = async () => {
    if (!overrideReason.trim()) {
      setError("A statutory justification reason is required for manual field corrections.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onOverrideField(selectedField.id, correctedValue.trim(), overrideReason.trim());
      setHasOverridden(true);
      setSelectedField(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to submit field correction.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Post-override Banner */}
      {(hasOverridden || extractedValues.some((f) => f.is_overridden)) && (
        <div className="flex items-center justify-between p-3 bg-accent/70 border border-primary/20 rounded-xl text-xs text-accent-foreground">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            <span>Field correction saved to cryptographic audit trail. Re-run verification to refresh this finding.</span>
          </div>
          {onTriggerReVerify && (
            <Button size="sm" onClick={onTriggerReVerify} className="h-7 text-xs">
              <RefreshCw className="h-3.5 w-3.5 mr-1" />
              Re-run Verification
            </Button>
          )}
        </div>
      )}

      {/* Fields Table */}
      <div className="overflow-x-auto border border-border rounded-xl">
        <table className="w-full text-xs text-left">
          <thead className="bg-muted text-muted-foreground font-semibold border-b border-border">
            <tr>
              <th className="p-3">Field Name</th>
              <th className="p-3">Effective Value</th>
              <th className="p-3">Original Extracted</th>
              <th className="p-3">Confidence</th>
              <th className="p-3">Extractor</th>
              {!isLocked && <th className="p-3 text-right">Action</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {extractedValues.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-4 text-center text-muted-foreground">
                  No extracted fields directly referenced in this finding.
                </td>
              </tr>
            ) : (
              extractedValues.map((field) => (
                <tr key={field.id} className="hover:bg-muted/40">
                  <td className="p-3 font-mono font-medium text-foreground">
                    {field.field_name}
                  </td>
                  <td className="p-3">
                    <span className="font-semibold text-foreground font-mono">
                      {field.effective_value || "—"}
                    </span>
                    {field.is_overridden && (
                      <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-signal-surface text-signal border border-signal-border font-medium">
                        Auditor Corrected
                      </span>
                    )}
                  </td>
                  <td className="p-3 text-muted-foreground font-mono">
                    {field.original_value || "—"}
                  </td>
                  <td className="p-3">
                    <ConfidenceBadge confidence={field.confidence || 0.9} />
                  </td>
                  <td className="p-3">
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
                      {field.extractor || "text_layer"}
                    </span>
                  </td>
                  {!isLocked && (
                    <td className="p-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleOpenModal(field)}
                        className="h-7 px-2 text-xs text-primary hover:text-primary"
                      >
                        <Edit3 className="h-3.5 w-3.5 mr-1" />
                        Correct
                      </Button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Override Modal */}
      {selectedField && (
        <Dialog open={!!selectedField} onOpenChange={() => setSelectedField(null)}>
          <DialogContent className="max-w-sm bg-card border border-border">
            <DialogHeader>
              <DialogTitle className="font-display text-sm font-bold">
                Correct Value: {selectedField.field_name}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 py-2 text-xs">
              <div>
                <label className="font-medium text-muted-foreground">
                  Original Extracted Value:
                </label>
                <div className="p-2 bg-muted rounded-lg font-mono mt-1 text-foreground">
                  {selectedField.original_value || "None"}
                </div>
              </div>
              <div>
                <label className="font-medium text-foreground">
                  Corrected Value <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={correctedValue}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                  className="w-full mt-1 p-2 border border-input rounded-lg bg-background text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label className="font-medium text-foreground">
                  Statutory Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Mandatory reason for auditor override (e.g. verified with ink signature)..."
                  rows={3}
                  className="w-full mt-1 p-2 border border-input rounded-lg text-xs bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              {error && <p className="text-rose-500 text-xs">{error}</p>}
            </div>
            <DialogFooter>
              <Button size="sm" variant="outline" onClick={() => setSelectedField(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitOverride}
                disabled={isSubmitting || !overrideReason.trim()}
              >
                {isSubmitting ? "Saving..." : "Save Correction"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

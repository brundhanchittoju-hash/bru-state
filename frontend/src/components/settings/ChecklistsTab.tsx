import React, { useEffect, useState } from "react";
import { Plus, Trash2, X, FileText } from "lucide-react";
import { MandatoryChecklistItem } from "@/types";
import { api } from "@/lib/api";
import { toast } from "sonner";

const SCHEMES = ["MGNREGA", "PMAY-G", "15th Finance Commission", "Jal Jeevan Mission", "General Statutory"];

export const ChecklistsTab: React.FC = () => {
  const [items, setItems] = useState<MandatoryChecklistItem[]>([]);
  const [selectedScheme, setSelectedScheme] = useState<string>("MGNREGA");
  const [loading, setLoading] = useState<boolean>(true);

  // Add dialog
  const [isAddOpen, setIsAddOpen] = useState<boolean>(false);
  const [newDocType, setNewDocType] = useState<string>("");
  const [newDesc, setNewDesc] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const loadChecklists = async () => {
    try {
      setLoading(true);
      const res = await api.get<MandatoryChecklistItem[]>("/verification/checklists");
      setItems(res);
    } catch {
      toast.error("Failed to load mandatory document checklists.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChecklists();
  }, []);

  const schemeItems = items.filter((i) => i.scheme_name.toLowerCase() === selectedScheme.toLowerCase());

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDocType.trim()) return;

    setIsSubmitting(true);
    try {
      await api.post("/verification/checklists", {
        scheme_name: selectedScheme,
        document_type: newDocType.trim(),
        is_mandatory: true,
        description: newDesc.trim() || undefined,
      });
      toast.success(`Added ${newDocType} to ${selectedScheme} checklist.`);
      setIsAddOpen(false);
      setNewDocType("");
      setNewDesc("");
      loadChecklists();
    } catch (err: any) {
      toast.error(err.message || "Failed to add checklist item.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteItem = async (id: string, docType: string) => {
    if (!confirm(`Remove mandatory requirement for '${docType}' in scheme '${selectedScheme}'?`)) return;
    try {
      await api.delete(`/verification/checklists/${id}`);
      toast.success("Document requirement removed.");
      loadChecklists();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete checklist item.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h3 className="font-display text-base font-semibold text-foreground">
            Mandatory Statutory Document Checklists
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Rules engine evaluates Rule R-008 against these scheme-specific document requirements.
          </p>
        </div>

        <button
          onClick={() => setIsAddOpen(true)}
          className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          <span>Add Requirement</span>
        </button>
      </div>

      {/* Scheme Selection Tabs */}
      <div className="flex flex-wrap gap-2 text-xs">
        {SCHEMES.map((scheme) => (
          <button
            key={scheme}
            onClick={() => setSelectedScheme(scheme)}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-colors ${
              selectedScheme === scheme
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            {scheme}
          </button>
        ))}
      </div>

      {/* Checklist Items Table */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Mandatory Document Type</th>
                <th className="py-3 px-4">Statutory Description / Justification</th>
                <th className="py-3 px-4">Enforcement Level</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {loading ? (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-muted-foreground">
                    Loading statutory checklists...
                  </td>
                </tr>
              ) : schemeItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-muted-foreground">
                    No mandatory document requirements configured for {selectedScheme}.
                  </td>
                </tr>
              ) : (
                schemeItems.map((item) => (
                  <tr key={item.id} className="hover:bg-muted/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-foreground flex items-center space-x-2">
                      <FileText className="h-4 w-4 text-primary shrink-0" />
                      <span>{item.document_type}</span>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {item.description || "Required for statutory scheme compliance."}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-destructive/10 text-destructive border border-destructive/20">
                        Mandatory
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDeleteItem(item.id, item.document_type)}
                        className="text-muted-foreground hover:text-destructive p-1 rounded"
                        title="Delete requirement"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Dialog */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h4 className="font-display font-semibold text-foreground text-base">
                Add Mandatory Requirement for {selectedScheme}
              </h4>
              <button
                onClick={() => setIsAddOpen(false)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleAddItem} className="p-5 space-y-4 text-xs">
              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  Document Type / Category <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={newDocType}
                  onChange={(e) => setNewDocType(e.target.value)}
                  placeholder="e.g. Sanction Order, Work Order, Measurement Book"
                  className="w-full p-2 bg-background border border-input rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-foreground">
                  Statutory Description
                </label>
                <textarea
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Reference government order or rule number requiring this document..."
                  rows={2}
                  className="w-full p-2 bg-background border border-input rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="pt-3 border-t border-border flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="px-3 py-1.5 bg-muted text-foreground rounded-lg font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !newDocType.trim()}
                  className="px-4 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-lg font-semibold"
                >
                  {isSubmitting ? "Adding..." : "Add to Checklist"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

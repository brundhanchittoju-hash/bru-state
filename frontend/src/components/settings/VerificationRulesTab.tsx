import React, { useEffect, useState } from "react";
import { RotateCcw, X } from "lucide-react";
import { VerificationRuleConfig } from "@/types";
import { api } from "@/lib/api";
import { toast } from "sonner";

export const VerificationRulesTab: React.FC = () => {
  const [rules, setRules] = useState<VerificationRuleConfig[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [editRule, setEditRule] = useState<VerificationRuleConfig | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [isEnabledVal, setIsEnabledVal] = useState<boolean>(true);
  const [changeReason, setChangeReason] = useState<string>("");
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const loadRules = async () => {
    try {
      setLoading(true);
      const res = await api.get<VerificationRuleConfig[]>("/verification/rules");
      setRules(res);
    } catch {
      toast.error("Failed to load verification rules.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const openEditModal = (rule: VerificationRuleConfig) => {
    setEditRule(rule);
    setParamValues({ ...rule.parameters });
    setIsEnabledVal(rule.is_enabled);
    setChangeReason("");
  };

  const handleSaveParams = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editRule) return;
    if (!changeReason.trim() || changeReason.trim().length < 3) {
      toast.error("Mandatory statutory reason required to modify rule parameters.");
      return;
    }

    setIsSaving(true);
    try {
      await api.put(`/verification/rules/${editRule.rule_code}`, {
        is_enabled: isEnabledVal,
        parameters: paramValues,
        reason: changeReason.trim(),
      });
      toast.success(`Rule ${editRule.rule_code} updated successfully.`);
      setEditRule(null);
      loadRules();
    } catch (err: any) {
      toast.error(err.message || "Failed to update rule parameters.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetRule = async (ruleCode: string) => {
    if (!confirm(`Reset rule ${ruleCode} to Karnataka statutory defaults?`)) return;
    try {
      await api.post(`/verification/rules/${ruleCode}/reset`);
      toast.success(`Rule ${ruleCode} reset to statutory defaults.`);
      if (editRule?.rule_code === ruleCode) setEditRule(null);
      loadRules();
    } catch (err: any) {
      toast.error(err.message || "Failed to reset rule.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <h3 className="font-display text-base font-semibold text-foreground">
            Statutory Verification Rules (16 Rules Engine)
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Configure thresholds, enable/disable checks, and review statutory legal citations.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground text-xs">Loading verification rules...</div>
      ) : (
        <div className="border border-border rounded-xl overflow-hidden bg-card">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
                <tr>
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Rule Name</th>
                  <th className="py-3 px-3">Category</th>
                  <th className="py-3 px-3">Severity</th>
                  <th className="py-3 px-4">Parameters</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/70">
                {rules.map((rule) => {
                  const paramKeys = Object.keys(rule.parameters || {});
                  return (
                    <tr key={rule.rule_code} className="hover:bg-muted/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-foreground">
                        {rule.rule_code}
                      </td>
                      <td className="py-3 px-4 font-medium text-foreground max-w-xs">
                        <div>{rule.name}</div>
                        {rule.statutory_basis && (
                          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                            {rule.statutory_basis}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3 capitalize text-muted-foreground">
                        {rule.category}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            rule.default_severity === "critical"
                              ? "bg-red-500/10 text-red-700 dark:text-red-300 border border-red-500/20"
                              : rule.default_severity === "high"
                              ? "bg-orange-500/10 text-orange-700 dark:text-orange-300 border border-orange-500/20"
                              : "bg-signal-surface text-signal border border-signal/25"
                          }`}
                        >
                          {rule.default_severity}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                        {paramKeys.length === 0 ? (
                          <span className="text-muted-foreground italic">None</span>
                        ) : (
                          paramKeys.map((k) => `${k}: ${rule.parameters[k]}`).join(", ")
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                            rule.is_enabled
                              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {rule.is_enabled ? "Enabled" : "Disabled"}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          onClick={() => openEditModal(rule)}
                          className="px-2.5 py-1 bg-muted hover:bg-muted/80 rounded text-xs font-semibold text-foreground transition-colors"
                        >
                          Configure
                        </button>
                        <button
                          onClick={() => handleResetRule(rule.rule_code)}
                          title="Reset to statutory default parameters"
                          className="p-1 text-muted-foreground hover:text-foreground rounded"
                        >
                          <RotateCcw className="h-3.5 w-3.5 inline" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Parameters Modal */}
      {editRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-lg w-full overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <div>
                <span className="font-mono text-xs font-bold text-primary uppercase">
                  {editRule.rule_code}
                </span>
                <h4 className="font-display font-semibold text-foreground text-base">
                  Configure Rule Parameters
                </h4>
              </div>
              <button
                onClick={() => setEditRule(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveParams} className="p-5 space-y-4 text-xs">
              {/* Enabled toggle */}
              <div className="flex items-center justify-between p-3 bg-muted/40 rounded-lg border border-border">
                <div>
                  <span className="font-semibold text-foreground block">
                    Statutory Rule Execution
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    If disabled, this rule is skipped during case verification runs.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={isEnabledVal}
                  onChange={(e) => setIsEnabledVal(e.target.checked)}
                  className="h-4 w-4 rounded text-primary focus:ring-ring"
                />
              </div>

              {/* Dynamic Parameter Fields */}
              {Object.keys(editRule.default_parameters || {}).length === 0 ? (
                <p className="text-muted-foreground italic">This statutory rule does not require configurable parameters.</p>
              ) : (
                <div className="space-y-3">
                  <h5 className="font-semibold text-foreground">
                    Threshold &amp; Tolerance Parameters
                  </h5>
                  {Object.entries(editRule.default_parameters).map(([key, defVal]) => (
                    <div key={key} className="space-y-1">
                      <div className="flex justify-between">
                        <label className="font-medium text-foreground font-mono">
                          {key}
                        </label>
                        <span className="text-[11px] text-muted-foreground font-mono">
                          default: {String(defVal)}
                        </span>
                      </div>
                      <input
                        type={typeof defVal === "number" ? "number" : "text"}
                        step="any"
                        value={paramValues[key] ?? defVal}
                        onChange={(e) =>
                          setParamValues({
                            ...paramValues,
                            [key]: typeof defVal === "number" ? parseFloat(e.target.value) : e.target.value,
                          })
                        }
                        className="w-full p-2 bg-background border border-input rounded-lg text-xs font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                    </div>
                  ))}
                </div>
              )}

              {/* Mandatory Reason Input */}
              <div className="space-y-1 pt-2 border-t border-border">
                <label className="font-semibold text-foreground">
                  Reason for Parameter Change <span className="text-destructive">*</span>
                </label>
                <textarea
                  value={changeReason}
                  onChange={(e) => setChangeReason(e.target.value)}
                  placeholder="Audit circular, government order, or departmental authorization justifying threshold change..."
                  rows={2}
                  className="w-full p-2 bg-background border border-input rounded-lg text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="pt-3 border-t border-border flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => handleResetRule(editRule.rule_code)}
                  className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-destructive space-x-1"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Reset to Statutory Default</span>
                </button>

                <div className="flex space-x-2">
                  <button
                    type="button"
                    onClick={() => setEditRule(null)}
                    className="px-3 py-1.5 bg-muted text-foreground rounded-lg font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSaving || !changeReason.trim()}
                    className="px-4 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-lg font-semibold transition-colors"
                  >
                    {isSaving ? "Saving..." : "Save Configuration"}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

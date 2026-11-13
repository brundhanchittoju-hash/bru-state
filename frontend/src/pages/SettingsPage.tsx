import React, { useEffect, useState } from "react";
import {
  Calendar,
  Globe,
  Sliders,
  Sun,
  Moon,
  Plus,
  Save,
  Check,
  CheckSquare,
  Building2,
  ShieldCheck,
} from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";
import { Holiday, SystemSetting } from "@/types";
import { formatDate } from "@/lib/formatters";
import { toast } from "sonner";
import { VerificationRulesTab } from "@/components/settings/VerificationRulesTab";
import { RiskWeightsTab } from "@/components/settings/RiskWeightsTab";
import { ChecklistsTab } from "@/components/settings/ChecklistsTab";
import { VendorReviewTab } from "@/components/settings/VendorReviewTab";

export const SettingsPage: React.FC = () => {
  const { hasRole } = useAuth();
  const { theme, setTheme } = useTheme();
  const isAdmin = hasRole(["administrator"]);

  const [activeTab, setActiveTab] = useState<
    "governance" | "rules" | "risk_weights" | "checklists" | "vendors" | "holidays" | "localization" | "theme"
  >("governance");
  const [holidays, setHolidays] = useState<Holiday[]>([]);

  // Local body terms state
  const [localTerms, setLocalTerms] = useState({
    state: "Karnataka",
    tier1: "Zilla Panchayat",
    tier2: "Taluk Panchayat",
    tier3: "Taluk",
    tier4: "Gram Panchayat",
  });
  const [isSavingTerms, setIsSavingTerms] = useState(false);

  // Holiday Add Modal
  const [addHolidayOpen, setAddHolidayOpen] = useState(false);
  const [newHoliday, setNewHoliday] = useState({
    holiday_date: "",
    name: "",
    state: "Karnataka",
    description: "",
  });

  const loadSettingsAndHolidays = async () => {
    try {
      const [settingsRes, holidaysRes] = await Promise.all([
        api.get<SystemSetting[]>("/settings"),
        api.get<Holiday[]>("/settings/holidays"),
      ]);
      setHolidays(holidaysRes);

      const termsSetting = settingsRes.find((s) => s.key === "local_body_terms");
      if (termsSetting) {
        try {
          const parsed = JSON.parse(termsSetting.value_json);
          setLocalTerms(parsed);
        } catch {}
      }
    } catch {
      toast.error("Failed to load settings.");
    }
  };

  useEffect(() => {
    loadSettingsAndHolidays();
  }, []);

  const handleSaveTerms = async () => {
    setIsSavingTerms(true);
    try {
      await api.put("/settings/local_body_terms", {
        value_json: JSON.stringify(localTerms),
      });
      toast.success("Governance local body terminology updated successfully.");
      loadSettingsAndHolidays();
    } catch (err: any) {
      toast.error(err.message || "Failed to update terms.");
    } finally {
      setIsSavingTerms(false);
    }
  };

  const handleAddHoliday = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/settings/holidays", newHoliday);
      toast.success(`Holiday ${newHoliday.name} registered.`);
      setAddHolidayOpen(false);
      setNewHoliday({ holiday_date: "", name: "", state: "Karnataka", description: "" });
      loadSettingsAndHolidays();
    } catch (err: any) {
      toast.error(err.message || "Failed to add holiday.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Settings & Governance"
        description="Configure state governance terms, public holiday calendars, financial localization, and appearance."
      />

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-border gap-5 overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab("governance")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "governance"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sliders className="h-4 w-4" />
          Local Body Hierarchy
        </button>

        <button
          onClick={() => setActiveTab("rules")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "rules"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sliders className="h-4 w-4" />
          Verification Rules
        </button>

        <button
          onClick={() => setActiveTab("risk_weights")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "risk_weights"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          Risk Weights (100% Guard)
        </button>

        <button
          onClick={() => setActiveTab("checklists")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "checklists"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <CheckSquare className="h-4 w-4" />
          Mandatory Checklists
        </button>

        <button
          onClick={() => setActiveTab("vendors")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "vendors"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="h-4 w-4" />
          Pending Vendor Reviews
        </button>

        <button
          onClick={() => setActiveTab("holidays")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "holidays"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Calendar className="h-4 w-4" />
          Karnataka Public Holidays
        </button>

        <button
          onClick={() => setActiveTab("localization")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "localization"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Globe className="h-4 w-4" />
          Currency & Locale
        </button>

        <button
          onClick={() => setActiveTab("theme")}
          className={`pb-3 whitespace-nowrap transition-colors flex items-center gap-2 border-b-2 ${
            activeTab === "theme"
              ? "border-primary text-primary font-semibold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
          Display Theme
        </button>
      </div>

      {/* Tab 1: Local Body Terms */}
      {activeTab === "governance" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">State Panchayati Raj Terminology</CardTitle>
            <CardDescription>
              Drive institutional local body designations from centralized settings. Allows
              retargeting to other states without code rewrites.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 max-w-xl">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold">State Name</label>
              <Input
                value={localTerms.state}
                onChange={(e) => setLocalTerms({ ...localTerms, state: e.target.value })}
                disabled={!isAdmin}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">District Body (Tier 1)</label>
                <Input
                  value={localTerms.tier1}
                  onChange={(e) => setLocalTerms({ ...localTerms, tier1: e.target.value })}
                  disabled={!isAdmin}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Block / Taluk Body (Tier 2)</label>
                <Input
                  value={localTerms.tier2}
                  onChange={(e) => setLocalTerms({ ...localTerms, tier2: e.target.value })}
                  disabled={!isAdmin}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Administrative Sub-division (Tier 3)</label>
                <Input
                  value={localTerms.tier3}
                  onChange={(e) => setLocalTerms({ ...localTerms, tier3: e.target.value })}
                  disabled={!isAdmin}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold">Village Panchayat (Tier 4)</label>
                <Input
                  value={localTerms.tier4}
                  onChange={(e) => setLocalTerms({ ...localTerms, tier4: e.target.value })}
                  disabled={!isAdmin}
                />
              </div>
            </div>

            {isAdmin && (
              <div className="pt-2">
                <Button onClick={handleSaveTerms} disabled={isSavingTerms} className="gap-2">
                  <Save className="h-4 w-4" />
                  {isSavingTerms ? "Saving..." : "Save Governance Settings"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab: Statutory Verification Rules */}
      {activeTab === "rules" && <VerificationRulesTab />}

      {/* Tab: Risk Weights */}
      {activeTab === "risk_weights" && <RiskWeightsTab />}

      {/* Tab: Mandatory Checklists */}
      {activeTab === "checklists" && <ChecklistsTab />}

      {/* Tab: Pending Vendor Aliases */}
      {activeTab === "vendors" && <VendorReviewTab />}

      {/* Tab: Holidays */}
      {activeTab === "holidays" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg">Karnataka Public Holiday Calendar</CardTitle>
              <CardDescription>
                Holidays used in financial verification rules to flag transactions disbursed on non-working days.
              </CardDescription>
            </div>
            {isAdmin && (
              <Button onClick={() => setAddHolidayOpen(true)} size="sm" className="gap-1.5">
                <Plus className="h-4 w-4" />
                Add Holiday
              </Button>
            )}
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border rounded-xl border border-border overflow-hidden">
              {holidays.map((h) => (
                <div
                  key={h.id}
                  className="flex items-center justify-between p-4 bg-card text-sm"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-xs font-bold bg-muted px-2.5 py-1 rounded text-foreground tabular-nums">
                      {formatDate(h.holiday_date)}
                    </span>
                    <div>
                      <p className="font-semibold text-foreground">{h.name}</p>
                      {h.description && (
                        <p className="text-xs text-muted-foreground">{h.description}</p>
                      )}
                    </div>
                  </div>
                  <Badge variant="outline" className="text-xs font-mono">
                    {h.state}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tab 3: Localization */}
      {activeTab === "localization" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Financial Currency & Locale Settings</CardTitle>
            <CardDescription>
              Standardized formatting standards compliant with Indian government accounting norms.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 max-w-xl text-sm">
            <div className="p-4 rounded-xl border border-border bg-muted/40 space-y-3 font-mono text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Currency Code:</span>
                <span className="font-bold text-foreground">INR (₹)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Locale Specifier:</span>
                <span className="font-bold text-foreground">en-IN</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Number Grouping:</span>
                <span className="font-bold text-foreground">Lakh & Crore (₹ 1,23,456.00)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Financial Year Format:</span>
                <span className="font-bold text-foreground">April to March (e.g. 2024-25)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Regional Language Hooks:</span>
                <span className="text-primary font-semibold">Kannada (kn-IN) i18n ready</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tab 4: Display Theme */}
      {activeTab === "theme" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Interface Theme</CardTitle>
            <CardDescription>Select between Workspace Canvas Light and Dark modes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 max-w-md">
              <button
                type="button"
                onClick={() => setTheme("light")}
                className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all ${
                  theme === "light"
                    ? "border-primary bg-accent text-accent-foreground"
                    : "border-border hover:border-primary/40 text-muted-foreground"
                }`}
              >
                <Sun className="h-8 w-8 text-signal mb-2" />
                <span className="text-sm font-semibold">Canvas Light</span>
                <span className="text-xs text-muted-foreground mt-1">Soft slate surface</span>
                {theme === "light" && <Check className="h-4 w-4 text-primary mt-2" />}
              </button>

              <button
                type="button"
                onClick={() => setTheme("dark")}
                className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all ${
                  theme === "dark"
                    ? "border-primary bg-accent text-accent-foreground"
                    : "border-border hover:border-primary/40 text-muted-foreground"
                }`}
              >
                <Moon className="h-8 w-8 text-primary mb-2" />
                <span className="text-sm font-semibold">Graphite Dark</span>
                <span className="text-xs text-muted-foreground mt-1">High-contrast audit view</span>
                {theme === "dark" && <Check className="h-4 w-4 text-primary mt-2" />}
              </button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Holiday Dialog */}
      <Dialog open={addHolidayOpen} onOpenChange={setAddHolidayOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Register State Public Holiday</DialogTitle>
            <DialogDescription>
              Add a public holiday to the Karnataka audit compliance calendar.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleAddHoliday} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Holiday Date</label>
              <Input
                type="date"
                value={newHoliday.holiday_date}
                onChange={(e) => setNewHoliday({ ...newHoliday, holiday_date: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Holiday Name</label>
              <Input
                placeholder="e.g. Basava Jayanti"
                value={newHoliday.name}
                onChange={(e) => setNewHoliday({ ...newHoliday, name: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">State</label>
              <Input
                value={newHoliday.state}
                onChange={(e) => setNewHoliday({ ...newHoliday, state: e.target.value })}
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold">Description / Purpose</label>
              <Input
                placeholder="State holiday for public offices and banks"
                value={newHoliday.description}
                onChange={(e) => setNewHoliday({ ...newHoliday, description: e.target.value })}
              />
            </div>

            <DialogFooter className="pt-2">
              <Button type="button" variant="outline" onClick={() => setAddHolidayOpen(false)}>
                Cancel
              </Button>
              <Button type="submit">Add to Calendar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

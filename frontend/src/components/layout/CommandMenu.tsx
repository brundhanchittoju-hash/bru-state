import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import {
  Briefcase,
  FileCheck2,
  LayoutDashboard,
  Moon,
  Search,
  Settings,
  Sun,
  Users,
  Building,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { api } from "@/lib/api";

interface CommandMenuProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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

export const CommandMenu: React.FC<CommandMenuProps> = ({ open, onOpenChange }) => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [query, setQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, onOpenChange]);

  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }

    const handler = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await api.get<SearchResponse>(`/search?q=${encodeURIComponent(query.trim())}&limit_per_entity=3`);
        setSearchResults(res);
      } catch {
        setSearchResults(null);
      } finally {
        setIsSearching(false);
      }
    }, 200);

    return () => clearTimeout(handler);
  }, [query]);

  if (!open) return null;

  const handleSelect = (path: string) => {
    onOpenChange(false);
    navigate(path);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-graphite-950/50 dark:bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
        <Command className="w-full">
          <div className="flex items-center border-b border-border px-4">
            <Search className="mr-3 h-4 w-4 shrink-0 text-primary" />
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder="Search cases, vendors, findings, vouchers, or type a command..."
              className="flex h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground text-foreground"
              autoFocus
            />
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="font-mono text-[10px] text-muted-foreground hover:text-foreground rounded-md border border-border bg-muted px-1.5 py-0.5"
            >
              ESC
            </button>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2 text-sm">
            {isSearching && (
              <div className="p-3 text-center text-xs text-muted-foreground font-mono">
                Searching workspace records...
              </div>
            )}

            {/* Dynamic Live Search Results */}
            {searchResults && searchResults.total_results > 0 && (
              <>
                {searchResults.results.cases?.length > 0 && (
                  <Command.Group heading="Audit Cases" className="text-[11px] font-semibold text-muted-foreground px-2 py-1">
                    {searchResults.results.cases.map((c) => (
                      <Command.Item
                        key={c.id}
                        onSelect={() => handleSelect(c.link)}
                        className="flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Briefcase className="h-4 w-4 text-primary shrink-0" />
                          <span className="truncate">{c.title}</span>
                        </div>
                        {c.badge && <span className="font-mono text-[10px] text-muted-foreground ml-2">{c.badge}</span>}
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {searchResults.results.findings?.length > 0 && (
                  <Command.Group heading="Flagged Findings" className="text-[11px] font-semibold text-muted-foreground px-2 py-1">
                    {searchResults.results.findings.map((f) => (
                      <Command.Item
                        key={f.id}
                        onSelect={() => handleSelect(f.link)}
                        className="flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
                          <span className="truncate">{f.title}</span>
                        </div>
                        {f.badge && <span className="font-mono text-[10px] text-muted-foreground ml-2">{f.badge}</span>}
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {searchResults.results.vendors?.length > 0 && (
                  <Command.Group heading="Vendors" className="text-[11px] font-semibold text-muted-foreground px-2 py-1">
                    {searchResults.results.vendors.map((v) => (
                      <Command.Item
                        key={v.id}
                        onSelect={() => handleSelect(v.link)}
                        className="flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Building className="h-4 w-4 text-signal shrink-0" />
                          <span className="truncate">{v.title}</span>
                        </div>
                        {v.subtitle && <span className="font-mono text-[10px] text-muted-foreground ml-2">{v.subtitle}</span>}
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                <Command.Item
                  onSelect={() => handleSelect(`/search?q=${encodeURIComponent(query)}`)}
                  className="flex cursor-pointer items-center justify-center gap-2 rounded-xl p-2 text-xs text-primary font-semibold border-t border-border mt-1 hover:bg-muted"
                >
                  <Search className="h-3.5 w-3.5" />
                  <span>View all {searchResults.total_results} matching results on Universal Search</span>
                </Command.Item>
              </>
            )}

            {/* Static Navigation */}
            <Command.Group heading="Navigation" className="text-[11px] font-semibold text-muted-foreground px-2 py-1.5">
              <Command.Item
                onSelect={() => handleSelect("/dashboard")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <LayoutDashboard className="h-4 w-4 text-primary" />
                <span>Dashboard Overview</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelect("/cases")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <Briefcase className="h-4 w-4 text-primary" />
                <span>Audit Cases</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelect("/findings")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <AlertTriangle className="h-4 w-4 text-primary" />
                <span>Audit Findings</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelect("/analytics")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <FileCheck2 className="h-4 w-4 text-primary" />
                <span>Analytics &amp; Trend Intelligence</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelect("/vendors")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <Building className="h-4 w-4 text-primary" />
                <span>Vendors &amp; Contractors</span>
              </Command.Item>

              <Command.Item
                onSelect={() => handleSelect("/search")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <Search className="h-4 w-4 text-primary" />
                <span>Universal Search Page</span>
              </Command.Item>

              {hasRole(["administrator"]) && (
                <Command.Item
                  onSelect={() => handleSelect("/users")}
                  className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
                >
                  <Users className="h-4 w-4 text-primary" />
                  <span>User Administration</span>
                </Command.Item>
              )}

              <Command.Item
                onSelect={() => handleSelect("/settings")}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                <Settings className="h-4 w-4 text-primary" />
                <span>System Configuration &amp; Holidays</span>
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Preferences" className="text-[11px] font-semibold text-muted-foreground px-2 py-1.5 mt-1">
              <Command.Item
                onSelect={() => {
                  toggleTheme();
                  onOpenChange(false);
                }}
                className="flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm text-foreground hover:bg-muted"
              >
                {theme === "dark" ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-foreground/80" />}
                <span>Toggle {theme === "dark" ? "Light" : "Dark"} Mode</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
};

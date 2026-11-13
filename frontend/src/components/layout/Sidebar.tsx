import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  BadgePercent,
  AlertTriangle,
  FileCheck2,
  BarChart3,
  Users,
  Settings,
  ShieldCheck,
  Building,
  Search,
  Pin,
  PinOff,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { RoleCode } from "@/types";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles?: RoleCode[];
}

const navItems: NavItem[] = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Audit Cases", href: "/cases", icon: Briefcase },
  { name: "Findings", href: "/findings", icon: AlertTriangle },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Vendors", href: "/vendors", icon: Building },
  { name: "Documents", href: "/documents", icon: FileText },
  { name: "Financial Verification", href: "/verification", icon: BadgePercent },
  { name: "Universal Search", href: "/search", icon: Search },
  { name: "Reports", href: "/reports", icon: FileCheck2 },
  { name: "Users", href: "/users", icon: Users, roles: ["administrator"] },
  { name: "Settings", href: "/settings", icon: Settings },
];

export const Sidebar: React.FC = () => {
  const [pinned, setPinned] = useState(false);
  const { user } = useAuth();
  const userRole = (user?.role?.code || "auditor") as RoleCode;

  const accessibleItems = navItems.filter((item) => {
    if (!item.roles) return true;
    return item.roles.includes(userRole);
  });

  return (
    <aside
      aria-label="Workspace navigation rail"
      className={cn(
        "group/rail fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border bg-card/95 backdrop-blur-md text-foreground transition-[width,box-shadow] duration-200 ease-out overflow-hidden",
        pinned
          ? "w-60 shadow-xl"
          : "w-16 hover:w-60 focus-within:w-60 hover:shadow-xl focus-within:shadow-xl"
      )}
    >
      {/* Brand Header */}
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-border px-3">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div
            className={cn(
              "flex flex-col whitespace-nowrap transition-opacity duration-150",
              pinned
                ? "opacity-100"
                : "opacity-0 group-hover/rail:opacity-100 group-focus-within/rail:opacity-100"
            )}
          >
            <span className="font-display text-sm font-bold tracking-tight text-foreground leading-none">
              State Audit AI
            </span>
            <span className="font-mono text-[10px] text-muted-foreground mt-1">
              Karnataka SAC
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setPinned(!pinned)}
          aria-label={pinned ? "Collapse sidebar" : "Expand sidebar"}
          title={pinned ? "Unpin navigation rail" : "Pin navigation rail open"}
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-opacity",
            pinned
              ? "opacity-100"
              : "opacity-0 group-hover/rail:opacity-100 group-focus-within/rail:opacity-100"
          )}
        >
          {pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-1 px-2.5 py-3 overflow-y-auto overflow-x-hidden" aria-label="Primary audit navigation">
        {accessibleItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors whitespace-nowrap",
                  isActive
                    ? "bg-primary/12 text-primary font-semibold"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )
              }
              title={item.name}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn(
                      "h-5 w-5 shrink-0 transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                  <span
                    className={cn(
                      "truncate transition-opacity duration-150",
                      pinned
                        ? "opacity-100"
                        : "opacity-0 group-hover/rail:opacity-100 group-focus-within/rail:opacity-100"
                    )}
                  >
                    {item.name}
                  </span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="border-t border-border p-3 shrink-0">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted font-mono text-[11px] font-bold text-foreground">
            FY25
          </div>
          <div
            className={cn(
              "min-w-0 whitespace-nowrap transition-opacity duration-150",
              pinned
                ? "opacity-100"
                : "opacity-0 group-hover/rail:opacity-100 group-focus-within/rail:opacity-100"
            )}
          >
            <p className="text-xs font-semibold text-foreground truncate">
              {user?.department?.name || "Karnataka Audit Office"}
            </p>
            <p className="font-mono text-[10px] text-muted-foreground">
              FY 2024-25 • Workspace
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

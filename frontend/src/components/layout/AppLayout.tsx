import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { CommandMenu } from "@/components/layout/CommandMenu";

export const AppLayout: React.FC = () => {
  const [commandOpen, setCommandOpen] = useState(false);

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-background text-foreground">
      {/* Slim icon rail with fixed 64px spacer so hover-expand overlays cleanly without layout shift */}
      <div className="w-16 shrink-0" aria-hidden="true" />
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Topbar onOpenCommand={() => setCommandOpen(true)} />
        <main className="flex-1 overflow-y-auto p-5 md:p-6 lg:p-7">
          <div className="mx-auto max-w-[1600px]">
            <Outlet />
          </div>
        </main>
      </div>

      <CommandMenu open={commandOpen} onOpenChange={setCommandOpen} />
    </div>
  );
};

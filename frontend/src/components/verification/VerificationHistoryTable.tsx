import React, { useState } from "react";
import { History, Eye, X } from "lucide-react";
import { RuleRunItem } from "@/types";

interface VerificationHistoryTableProps {
  runs: RuleRunItem[];
}

export const VerificationHistoryTable: React.FC<VerificationHistoryTableProps> = ({ runs }) => {
  const [selectedSnapshot, setSelectedSnapshot] = useState<Record<string, any> | null>(null);

  return (
    <div className="bg-card border border-border rounded-xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center space-x-2">
          <History className="h-5 w-5 text-primary" />
          <h3 className="font-display font-semibold text-foreground text-base">
            Verification Run History &amp; Audit Snapshots
          </h3>
        </div>
        <span className="text-xs text-muted-foreground font-mono tabular-nums">
          {runs.length} {runs.length === 1 ? "run" : "runs"} recorded
        </span>
      </div>

      <div className="border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase tracking-wider font-semibold text-[11px]">
              <tr>
                <th className="py-3 px-4">Executed At</th>
                <th className="py-3 px-4">Triggered By</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Records Evaluated</th>
                <th className="py-3 px-4">Findings Result</th>
                <th className="py-3 px-4 text-right">Snapshot</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/70">
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted-foreground">
                    No verification executions logged for this case yet.
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.id} className="hover:bg-muted/40 transition-colors">
                    <td className="py-3 px-4 font-mono tabular-nums text-foreground">
                      {new Date(run.run_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-foreground font-medium">
                      {run.triggered_by_name || "System"}
                    </td>
                    <td className="py-3 px-4 font-mono tabular-nums text-muted-foreground">
                      {run.duration_ms} ms
                    </td>
                    <td className="py-3 px-4 font-mono tabular-nums font-medium text-foreground">
                      {run.items_evaluated} records
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-accent text-accent-foreground border border-primary/20 tabular-nums">
                        {run.findings_count} findings
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedSnapshot(run.thresholds_snapshot)}
                        className="inline-flex items-center text-primary hover:underline font-medium text-xs space-x-1"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Thresholds</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Snapshot Modal */}
      {selectedSnapshot && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-lg w-full overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h4 className="font-display font-semibold text-foreground text-base">
                Execution Thresholds Snapshot
              </h4>
              <button
                onClick={() => setSelectedSnapshot(null)}
                className="text-muted-foreground hover:text-foreground p-1 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 max-h-[60vh] overflow-y-auto">
              <pre className="bg-zinc-950 text-indigo-300 border border-border p-4 rounded-lg font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(selectedSnapshot, null, 2)}
              </pre>
            </div>
            <div className="p-4 bg-muted/30 border-t border-border flex justify-end">
              <button
                onClick={() => setSelectedSnapshot(null)}
                className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-lg text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

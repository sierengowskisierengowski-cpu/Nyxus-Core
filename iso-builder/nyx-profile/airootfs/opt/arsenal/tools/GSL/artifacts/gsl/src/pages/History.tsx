import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, Download, Flag, Trash2, ChevronDown, ChevronRight, History as HistoryIcon } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Run {
  id: number;
  toolId: string;
  toolName: string;
  command: string;
  status: string;
  output?: string;
  startedAt: string;
  endedAt?: string;
  isFlagged: boolean;
  flagNote?: string;
  severity?: string;
}

const STATUS_CFG: Record<string, { color: string; bg: string; border: string }> = {
  completed: { color: "#4ade80", bg: "rgba(74,222,128,0.07)",  border: "rgba(74,222,128,0.2)" },
  running:   { color: "#60a5fa", bg: "rgba(96,165,250,0.07)",  border: "rgba(96,165,250,0.2)" },
  error:     { color: "#ff2d55", bg: "rgba(255,45,85,0.07)", border: "rgba(255,45,85,0.2)" },
  killed:    { color: "#fbbf24", bg: "rgba(251,191,36,0.07)",  border: "rgba(251,191,36,0.2)" },
  pending:   { color: "#94a3b8", bg: "rgba(148,163,184,0.06)", border: "rgba(148,163,184,0.15)" },
};

function timeAgo(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function duration(start: string, end?: string) {
  if (!end) return null;
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

export default function History() {
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const qc = useQueryClient();

  const { data: runs = [], isLoading } = useQuery<Run[]>({
    queryKey: ["runs"],
    queryFn: () => apiFetch<Run[]>("/api/runs?limit=100"),
    refetchInterval: 5000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/runs/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });

  const flagMutation = useMutation({
    mutationFn: ({ id, flagged }: { id: number; flagged: boolean }) =>
      apiFetch(`/api/runs/${id}/flag`, { method: "POST", body: JSON.stringify({ flagged }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });

  const filtered = runs.filter(
    (r) =>
      r.toolName.toLowerCase().includes(search.toLowerCase()) ||
      r.command.toLowerCase().includes(search.toLowerCase())
  );

  const handleExport = () => {
    const rows = [
      ["ID", "Tool", "Command", "Status", "Started", "Ended", "Duration", "Flagged"].join(","),
      ...filtered.map((r) => [
        r.id, r.toolName,
        `"${r.command.replace(/"/g, '""')}"`,
        r.status, r.startedAt, r.endedAt ?? "",
        duration(r.startedAt, r.endedAt) ?? "",
        r.isFlagged ? "yes" : "no",
      ].join(",")),
    ].join("\n");
    const blob = new Blob([rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gsl-history-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <div className="p-5 max-w-6xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-1">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div
              className="w-8 h-8 rounded flex items-center justify-center"
              style={{ background: "rgba(96,165,250,0.1)", border: "1px solid rgba(96,165,250,0.2)" }}
            >
              <HistoryIcon className="h-4 w-4" style={{ color: "#60a5fa" }} />
            </div>
            <h2 className="text-xl font-bold tracking-tight">Run History</h2>
          </div>
          <p className="text-[11px] font-mono pl-0.5" style={{ color: "hsl(232 10% 38%)" }}>
            Every command executed on GowskiNet — with full output
          </p>
        </div>
        <Button
          variant="outline" size="sm"
          onClick={handleExport}
          className="h-8 text-xs gap-2 font-mono"
          style={{ borderColor: "hsl(232 18% 16%)" }}
        >
          <Download className="h-3.5 w-3.5" /> Export CSV
        </Button>
      </div>

      {/* Search bar */}
      <div
        className="flex items-center gap-3 px-3 py-2 rounded-sm"
        style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
      >
        <Search className="h-4 w-4 flex-shrink-0" style={{ color: "hsl(232 10% 38%)" }} />
        <Input
          placeholder="Search tools, commands..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border-0 bg-transparent focus-visible:ring-0 text-sm h-auto p-0 placeholder:text-muted-foreground/40"
        />
        <span className="text-[11px] font-mono flex-shrink-0" style={{ color: "hsl(232 10% 35%)" }}>
          {filtered.length} runs
        </span>
      </div>

      {/* Table */}
      <div
        className="rounded-sm overflow-hidden"
        style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
      >
        {/* Header row */}
        <div
          className="grid text-[10px] font-mono uppercase tracking-wider px-4 py-2.5 gap-4"
          style={{
            gridTemplateColumns: "28px 1fr minmax(0,1.5fr) 90px 90px 70px 70px",
            color: "hsl(232 10% 35%)",
            borderBottom: "1px solid hsl(232 18% 10%)",
            background: "hsl(235 28% 5%)",
            letterSpacing: "0.1em",
          }}
        >
          <span />
          <span>Tool</span>
          <span>Command</span>
          <span>Status</span>
          <span>When</span>
          <span>Duration</span>
          <span className="text-right">Actions</span>
        </div>

        {isLoading ? (
          <div className="p-6 space-y-2">
            {[...Array(5)].map((_, i) => <div key={i} className="shimmer h-10 rounded-sm" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center">
            <HistoryIcon className="h-10 w-10 mx-auto mb-3" style={{ color: "hsl(232 10% 20%)" }} />
            <p className="text-sm font-medium" style={{ color: "hsl(232 10% 45%)" }}>
              {runs.length === 0 ? "No runs yet. Execute a tool to see history here." : "No matching runs."}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[hsl(232_18%_9%)]">
            {filtered.map((run) => {
              const sc = STATUS_CFG[run.status] ?? STATUS_CFG["pending"];
              const isExpanded = expandedId === run.id;
              const dur = duration(run.startedAt, run.endedAt);
              return (
                <div key={run.id}>
                  <div
                    className="grid items-center px-4 py-2.5 gap-4 cursor-pointer hover:bg-white/[0.015] transition-colors"
                    style={{ gridTemplateColumns: "28px 1fr minmax(0,1.5fr) 90px 90px 70px 70px" }}
                    onClick={() => setExpandedId(isExpanded ? null : run.id)}
                  >
                    {/* Expand */}
                    <div className="flex items-center justify-center">
                      {isExpanded
                        ? <ChevronDown className="h-3.5 w-3.5" style={{ color: "hsl(232 10% 40%)" }} />
                        : <ChevronRight className="h-3.5 w-3.5" style={{ color: "hsl(232 10% 30%)" }} />}
                    </div>

                    {/* Tool */}
                    <div className="flex items-center gap-2 min-w-0">
                      {run.isFlagged && (
                        <Flag className="h-3 w-3 flex-shrink-0" style={{ color: "#ff2d55" }} />
                      )}
                      <span className="text-sm font-medium truncate" style={{ color: "hsl(220 20% 88%)" }}>
                        {run.toolName}
                      </span>
                    </div>

                    {/* Command */}
                    <div className="min-w-0">
                      <code
                        className="text-[11px] font-mono truncate block px-2 py-1 rounded-sm"
                        style={{
                          background: "#020204",
                          border: "1px solid hsl(232 18% 11%)",
                          color: "hsl(263 55% 65%)",
                        }}
                      >
                        {run.command}
                      </code>
                    </div>

                    {/* Status */}
                    <div>
                      <span
                        className="text-[9px] font-mono px-2 py-0.5 rounded-sm border uppercase font-semibold"
                        style={{ color: sc.color, background: sc.bg, borderColor: sc.border }}
                      >
                        {run.status}
                      </span>
                    </div>

                    {/* When */}
                    <div className="text-[11px] font-mono" style={{ color: "hsl(232 10% 38%)" }}>
                      {timeAgo(run.startedAt)}
                    </div>

                    {/* Duration */}
                    <div className="text-[11px] font-mono" style={{ color: "hsl(232 10% 32%)" }}>
                      {dur ?? "—"}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="h-6 w-6 flex items-center justify-center rounded-sm transition-colors"
                        style={{ color: run.isFlagged ? "#ff2d55" : "hsl(232 10% 30%)" }}
                        title={run.isFlagged ? "Unflag" : "Flag as Finding"}
                        onClick={() => flagMutation.mutate({ id: run.id, flagged: !run.isFlagged })}
                        onMouseEnter={(e) => (e.currentTarget.style.color = "#ff2d55")}
                        onMouseLeave={(e) => (e.currentTarget.style.color = run.isFlagged ? "#ff2d55" : "hsl(232 10% 30%)")}
                      >
                        <Flag className="h-3 w-3" />
                      </button>
                      <button
                        className="h-6 w-6 flex items-center justify-center rounded-sm transition-colors"
                        style={{ color: "hsl(232 10% 30%)" }}
                        title="Delete"
                        onClick={() => deleteMutation.mutate(run.id)}
                        onMouseEnter={(e) => (e.currentTarget.style.color = "#ff2d55")}
                        onMouseLeave={(e) => (e.currentTarget.style.color = "hsl(232 10% 30%)")}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded output */}
                  {isExpanded && run.output && (
                    <div
                      style={{
                        background: "#030305",
                        borderTop: "1px solid hsl(232 18% 10%)",
                        borderBottom: "1px solid hsl(232 18% 10%)",
                      }}
                    >
                      <div
                        className="px-4 py-1.5 flex items-center gap-2 text-[9px] font-mono uppercase tracking-wider"
                        style={{ color: "hsl(232 10% 30%)", borderBottom: "1px solid hsl(232 18% 9%)" }}
                      >
                        <span>Output · run #{run.id} · {new Date(run.startedAt).toLocaleString()}</span>
                        {dur && <span style={{ color: "hsl(263 55% 55%)" }}>· {dur}</span>}
                      </div>
                      <div
                        className="px-10 py-3 font-mono text-[11px] whitespace-pre-wrap max-h-56 overflow-y-auto leading-relaxed"
                        style={{ color: "#b8c4d8", fontFamily: "'JetBrains Mono', monospace" }}
                      >
                        {run.output}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

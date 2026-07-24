import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ShieldAlert, Flag, ChevronDown, ChevronRight, Download, AlertTriangle, AlertCircle, Info, Trash2, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

const SEVERITIES = ["critical", "high", "medium", "low", "info"];

const SEV: Record<string, { label: string; icon: React.ElementType; color: string; bg: string; border: string; glow: string }> = {
  critical: { label: "Critical", icon: AlertTriangle, color: "#f87171", bg: "rgba(248,113,113,0.06)", border: "rgba(248,113,113,0.2)", glow: "rgba(248,113,113,0.08)" },
  high:     { label: "High",     icon: AlertCircle,  color: "#fb923c", bg: "rgba(249,115,22,0.06)",  border: "rgba(249,115,22,0.2)",  glow: "rgba(249,115,22,0.08)" },
  medium:   { label: "Medium",   icon: AlertCircle,  color: "#fbbf24", bg: "rgba(251,191,36,0.06)",  border: "rgba(251,191,36,0.2)",  glow: "rgba(251,191,36,0.08)" },
  low:      { label: "Low",      icon: Info,         color: "#60a5fa", bg: "rgba(96,165,250,0.06)",  border: "rgba(96,165,250,0.2)",  glow: "rgba(96,165,250,0.08)" },
  info:     { label: "Info",     icon: Info,         color: "#94a3b8", bg: "rgba(148,163,184,0.04)", border: "rgba(148,163,184,0.15)", glow: "transparent" },
  unset:    { label: "Unset",    icon: Flag,         color: "#64748b", bg: "rgba(100,116,139,0.04)", border: "rgba(100,116,139,0.15)", glow: "transparent" },
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

export default function Findings() {
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const qc = useQueryClient();

  const { data: allRuns = [], isLoading } = useQuery<Run[]>({
    queryKey: ["runs"],
    queryFn: () => apiFetch<Run[]>("/api/runs?limit=500"),
    refetchInterval: 10000,
  });

  const findings = allRuns.filter((r) => r.isFlagged);

  const updateFlag = useMutation({
    mutationFn: ({ id, severity, flagNote }: { id: number; severity?: string; flagNote?: string }) =>
      apiFetch(`/api/runs/${id}/flag`, {
        method: "POST",
        body: JSON.stringify({ flagged: true, severity, flagNote }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });

  const removeFinding = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/api/runs/${id}/flag`, { method: "POST", body: JSON.stringify({ flagged: false }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });

  const grouped = SEVERITIES.reduce<Record<string, Run[]>>((acc, sev) => {
    acc[sev] = findings.filter((r) => r.severity === sev);
    return acc;
  }, {});
  grouped["unset"] = findings.filter((r) => !r.severity || !SEVERITIES.includes(r.severity));

  const exportFindings = () => {
    const rows = [
      ["ID", "Tool", "Command", "Severity", "Date", "Note", "Output Preview"].join(","),
      ...findings.map((r) =>
        [r.id, r.toolName, `"${r.command.replace(/"/g, '""')}"`, r.severity || "unset",
          r.startedAt, `"${(r.flagNote || "").replace(/"/g, '""')}"`,
          `"${(r.output || "").slice(0, 200).replace(/"/g, '""').replace(/\n/g, " ")}"`
        ].join(",")
      ),
    ].join("\n");
    const blob = new Blob([rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `gsl-findings-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  if (isLoading) {
    return (
      <div className="p-5 space-y-3">
        {[...Array(4)].map((_, i) => <div key={i} className="shimmer h-20 rounded-sm" />)}
      </div>
    );
  }

  return (
    <div className="p-5 max-w-5xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 pt-1">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div
              className="w-8 h-8 rounded flex items-center justify-center"
              style={{ background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)" }}
            >
              <ShieldAlert className="h-4 w-4" style={{ color: "#f87171" }} />
            </div>
            <h2 className="text-xl font-bold tracking-tight">Findings Tracker</h2>
          </div>
          <p className="text-[11px] font-mono pl-0.5" style={{ color: "hsl(232 10% 38%)" }}>
            Flagged security observations organized by severity
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Severity counters */}
          <div className="flex items-center gap-1.5">
            {[...SEVERITIES, "unset"].map((sev) => {
              const count = grouped[sev]?.length ?? 0;
              if (count === 0) return null;
              const s = SEV[sev];
              return (
                <span
                  key={sev}
                  className="text-[10px] font-mono px-2 py-1 rounded-sm border font-bold uppercase"
                  style={{ color: s.color, background: s.bg, borderColor: s.border }}
                >
                  {count}
                </span>
              );
            })}
          </div>
          {findings.length > 0 && (
            <Button variant="outline" size="sm" onClick={exportFindings} className="h-8 text-xs gap-2 font-mono" style={{ borderColor: "hsl(232 18% 16%)" }}>
              <Download className="h-3.5 w-3.5" /> Export
            </Button>
          )}
        </div>
      </div>

      {/* Empty state */}
      {findings.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-24 rounded-sm"
          style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
        >
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
            style={{ background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.2)" }}
          >
            <Shield className="h-8 w-8" style={{ color: "#4ade80" }} />
          </div>
          <h3 className="text-lg font-semibold mb-1" style={{ color: "#4ade80" }}>No Findings</h3>
          <p className="text-sm text-center max-w-sm" style={{ color: "hsl(232 10% 40%)" }}>
            No runs have been flagged yet. Use the flag button in History or Tools to mark interesting results.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {[...SEVERITIES, "unset"].map((sev) => {
            const sevRuns = grouped[sev] ?? [];
            if (sevRuns.length === 0) return null;
            const s = SEV[sev];
            const Icon = s.icon;

            return (
              <div key={sev}>
                {/* Severity header */}
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="flex items-center gap-2 px-3 py-1 rounded-sm"
                    style={{ background: s.bg, border: `1px solid ${s.border}` }}
                  >
                    <Icon className="h-3.5 w-3.5" style={{ color: s.color }} />
                    <span className="font-bold uppercase tracking-wider text-[11px] font-mono" style={{ color: s.color }}>
                      {s.label}
                    </span>
                    <span className="font-mono text-[10px]" style={{ color: `${s.color}80` }}>
                      {sevRuns.length}
                    </span>
                  </div>
                  <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${s.border}, transparent)` }} />
                </div>

                <div className="space-y-2">
                  {sevRuns.map((run) => (
                    <div
                      key={run.id}
                      className="rounded-sm overflow-hidden"
                      style={{
                        background: "hsl(235 28% 6%)",
                        border: `1px solid hsl(232 18% 12%)`,
                        boxShadow: `0 0 20px ${s.glow}`,
                      }}
                    >
                      {/* Card header */}
                      <div
                        className="flex items-start justify-between gap-3 px-4 py-3 cursor-pointer hover:bg-white/[0.01] transition-colors"
                        style={{ borderLeft: `3px solid ${s.color}` }}
                        onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                      >
                        <div className="flex items-start gap-3 min-w-0 flex-1">
                          <div className="mt-0.5 flex-shrink-0">
                            {expandedId === run.id
                              ? <ChevronDown className="h-4 w-4" style={{ color: "hsl(232 10% 40%)" }} />
                              : <ChevronRight className="h-4 w-4" style={{ color: "hsl(232 10% 30%)" }} />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="font-semibold text-sm" style={{ color: "hsl(220 20% 90%)" }}>{run.toolName}</span>
                              <span className="text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                                {timeAgo(run.startedAt)}
                              </span>
                            </div>
                            <code
                              className="text-[11px] font-mono px-2 py-0.5 rounded-sm block truncate"
                              style={{ background: "#030305", border: "1px solid hsl(232 18% 11%)", color: "hsl(263 55% 62%)" }}
                            >
                              $ {run.command}
                            </code>
                            {run.flagNote && (
                              <p className="text-xs mt-1.5 italic" style={{ color: "hsl(232 10% 42%)" }}>
                                "{run.flagNote}"
                              </p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
                          <Select
                            value={run.severity || "unset"}
                            onValueChange={(v) =>
                              updateFlag.mutate({ id: run.id, severity: v === "unset" ? undefined : v, flagNote: run.flagNote })
                            }
                          >
                            <SelectTrigger
                              className="h-7 w-24 text-[10px] font-mono uppercase border"
                              style={{ color: s.color, borderColor: s.border, background: s.bg }}
                            >
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {[...SEVERITIES, "unset"].map((sv) => (
                                <SelectItem key={sv} value={sv} className="text-xs font-mono uppercase">
                                  {SEV[sv]?.label ?? sv}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <button
                            className="h-7 w-7 flex items-center justify-center rounded-sm transition-colors"
                            style={{ color: "hsl(232 10% 30%)" }}
                            title="Remove finding"
                            onClick={() => removeFinding.mutate(run.id)}
                            onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
                            onMouseLeave={(e) => (e.currentTarget.style.color = "hsl(232 10% 30%)")}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Expanded output */}
                      {expandedId === run.id && run.output && (
                        <div style={{ borderTop: `1px solid hsl(232 18% 10%)` }}>
                          <div
                            className="px-4 py-1.5 text-[9px] font-mono uppercase tracking-wider"
                            style={{ color: "hsl(232 10% 28%)", borderBottom: "1px solid hsl(232 18% 9%)", background: "#030305" }}
                          >
                            Last output · {new Date(run.startedAt).toLocaleString()}
                          </div>
                          <div
                            className="px-6 py-3 font-mono text-[11px] whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed"
                            style={{ background: "#030305", color: "#b8c4d8", fontFamily: "'JetBrains Mono', monospace" }}
                          >
                            {run.output}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

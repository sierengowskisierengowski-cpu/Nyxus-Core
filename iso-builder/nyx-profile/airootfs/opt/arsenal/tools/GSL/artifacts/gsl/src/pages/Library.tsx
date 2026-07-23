import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen, Search, Copy, ChevronDown, ChevronRight,
  Terminal, CheckCircle2, XOctagon, Clock, Hash,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";

interface LibraryCommand {
  command: string;
  runCount: number;
  successCount: number;
  lastRun: string;
  lastStatus: string;
  lastOutput: string;
}

interface LibraryTool {
  toolId: string;
  toolName: string;
  difficulty: string;
  runCount: number;
  lastRun: string;
  commands: LibraryCommand[];
}

interface LibraryCategory {
  category: string;
  totalRuns: number;
  tools: LibraryTool[];
}

const CATEGORY_COLOR: Record<string, string> = {
  "Network Scanning":           "#3b82f6",
  "WiFi Security":              "#f59e0b",
  "Web Application Testing":    "#10b981",
  "Password & Hash Testing":    "#f97316",
  "Exploitation Framework":     "#ef4444",
  "Honeypot Testing":           "#ec4899",
  "Packet Analysis":            "#06b6d4",
  "Bluetooth & RF":             "#8b5cf6",
  "Stress Testing":             "#14b8a6",
  "Forensics & Analysis":       "#a855f7",
  "OSINT":                      "#6366f1",
  "Vulnerability Scanning":     "#f43f5e",
  "Cryptography":               "#84cc16",
  "Steganography":              "#d946ef",
  "Reverse Engineering":        "#fb923c",
  "Docker & Container Security":"#22d3ee",
  "Social Engineering":         "#ff2d55",
  "IoT & Hardware":             "#4ade80",
  "GowskiNet Specific":         "#9b7fef",
  "CTF & Practice":             "#34d399",
};

function HighlightedCommand({ cmd }: { cmd: string }) {
  const tokens = cmd.split(/(\s+)/);
  return (
    <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "0.7rem", lineHeight: 1.6 }}>
      {tokens.map((token, i) => {
        if (/^\s+$/.test(token)) return <span key={i}>{token}</span>;
        if (i === 0) return <span key={i} style={{ color: "#4ade80", fontWeight: 600 }}>{token}</span>;
        if (token.startsWith("--")) return <span key={i} style={{ color: "#fde047" }}>{token}</span>;
        if (token.startsWith("-") && token.length > 1 && !token.match(/^\d/)) return <span key={i} style={{ color: "#fbbf24" }}>{token}</span>;
        if (token.match(/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d+)?$/)) return <span key={i} style={{ color: "#67e8f9" }}>{token}</span>;
        if (token.match(/^(http|https|ftp):\/\//)) return <span key={i} style={{ color: "#60a5fa" }}>{token}</span>;
        if (token.match(/^\d+$/) && parseInt(token) > 0) return <span key={i} style={{ color: "#fb923c" }}>{token}</span>;
        if (token.startsWith("/") || token.match(/\.(txt|lst|xml|pcap|pcapng|cap|csv|json)$/)) return <span key={i} style={{ color: "#7d3dff" }}>{token}</span>;
        if (token.startsWith("192.168")) return <span key={i} style={{ color: "#67e8f9" }}>{token}</span>;
        return <span key={i} style={{ color: "#b8c4d8" }}>{token}</span>;
      })}
    </code>
  );
}

function timeAgo(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const DIFF_STYLE: Record<string, { color: string; border: string; bg: string }> = {
  beginner:     { color: "#4ade80", border: "rgba(74,222,128,0.2)",  bg: "rgba(74,222,128,0.06)"  },
  intermediate: { color: "#fbbf24", border: "rgba(251,191,36,0.2)",  bg: "rgba(251,191,36,0.06)"  },
  advanced:     { color: "#fb923c", border: "rgba(249,115,22,0.2)",  bg: "rgba(249,115,22,0.06)"  },
};

export default function Library() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [expandedCmd, setExpandedCmd] = useState<string | null>(null);
  const { toast } = useToast();

  const { data: library = [], isLoading } = useQuery<LibraryCategory[]>({
    queryKey: ["library"],
    queryFn: () => apiFetch<LibraryCategory[]>("/api/runs/library"),
    refetchInterval: 15000,
  });

  const totalRuns = library.reduce((s, c) => s + c.totalRuns, 0);
  const totalCommands = library.reduce((s, c) => s + c.tools.reduce((ts, t) => ts + t.commands.length, 0), 0);
  const categories = useMemo(() => ["All", ...library.map((c) => c.category)], [library]);

  const filtered = useMemo(() => {
    let cats = selectedCategory === "All" ? library : library.filter((c) => c.category === selectedCategory);
    if (search.trim()) {
      const q = search.toLowerCase();
      cats = cats
        .map((cat) => ({
          ...cat,
          tools: cat.tools
            .map((tool) => ({
              ...tool,
              commands: tool.commands.filter(
                (cmd) => cmd.command.toLowerCase().includes(q) || tool.toolName.toLowerCase().includes(q)
              ),
            }))
            .filter((t) => t.commands.length > 0),
        }))
        .filter((c) => c.tools.length > 0);
    }
    return cats;
  }, [library, selectedCategory, search]);

  const copyCmd = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    toast({ title: "Command copied to clipboard" });
  };

  return (
    <div className="flex h-[calc(100vh-40px)] overflow-hidden">
      {/* Category sidebar */}
      <div
        className="w-[200px] flex-col hidden lg:flex flex-shrink-0 overflow-y-auto"
        style={{ background: "hsl(237 38% 3.5%)", borderRight: "1px solid hsl(232 18% 10%)" }}
      >
        <div className="p-3 pb-2" style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}>
          <div className="text-[10px] uppercase tracking-wider font-mono font-bold mb-0.5" style={{ color: "hsl(232 10% 35%)", letterSpacing: "0.12em" }}>
            Categories
          </div>
          <div className="text-[9px] font-mono" style={{ color: "hsl(232 10% 28%)" }}>
            {totalRuns} runs · {totalCommands} cmds
          </div>
        </div>
        <div className="p-2 space-y-0.5 flex-1">
          {categories.map((cat) => {
            const catData = library.find((c) => c.category === cat);
            const count = cat === "All" ? totalRuns : (catData?.totalRuns ?? 0);
            const isActive = selectedCategory === cat;
            const catColor = cat === "All" ? "hsl(263 55% 62%)" : (CATEGORY_COLOR[cat] ?? "#9b7fef");
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className="w-full text-left px-2.5 py-1.5 rounded-sm text-[11px] flex items-center justify-between transition-all"
                style={{
                  color: isActive ? "hsl(220 20% 92%)" : "hsl(232 10% 40%)",
                  background: isActive ? `${catColor}10` : "transparent",
                  borderLeft: isActive ? `2px solid ${catColor}` : "2px solid transparent",
                  paddingLeft: isActive ? "8px" : "10px",
                  fontWeight: isActive ? 600 : 400,
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLButtonElement).style.color = "hsl(220 20% 80%)";
                    (e.currentTarget as HTMLButtonElement).style.background = "hsl(235 28% 7%)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLButtonElement).style.color = "hsl(232 10% 40%)";
                    (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                  }
                }}
              >
                <span className="truncate">{cat}</span>
                {count > 0 && (
                  <span className="text-[9px] font-mono ml-1 flex-shrink-0" style={{ color: isActive ? catColor : "hsl(232 10% 28%)" }}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div
          className="px-5 py-3.5 flex-shrink-0"
          style={{ borderBottom: "1px solid hsl(232 18% 11%)" }}
        >
          <div className="flex items-center gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <BookOpen className="h-4 w-4" style={{ color: "#4ade80" }} />
                <h2 className="text-base font-bold">Command Library</h2>
              </div>
              <p className="text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                Every command you've executed — study real syntax and real output
              </p>
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <div className="relative">
                <Search className="absolute left-2.5 top-2 h-3.5 w-3.5" style={{ color: "hsl(232 10% 35%)" }} />
                <Input
                  placeholder="Search commands..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 h-8 text-xs w-52 bg-background border-border/60 rounded-sm"
                  style={{ borderColor: "hsl(232 18% 13%)" }}
                />
              </div>
              <div className="lg:hidden">
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="h-8 text-xs rounded-sm px-2"
                  style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 13%)", color: "hsl(220 20% 85%)" }}
                >
                  {categories.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-5 space-y-3">
              {[...Array(3)].map((_, i) => <div key={i} className="shimmer h-24 rounded-sm" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div
                className="w-16 h-16 rounded-sm flex items-center justify-center mb-4"
                style={{ background: "rgba(74,222,128,0.07)", border: "1px solid rgba(74,222,128,0.15)" }}
              >
                <Terminal className="h-8 w-8" style={{ color: "rgba(74,222,128,0.4)" }} />
              </div>
              <h3 className="font-semibold text-sm mb-1" style={{ color: "hsl(220 20% 70%)" }}>No commands yet</h3>
              <p className="text-xs max-w-xs" style={{ color: "hsl(232 10% 38%)" }}>
                {search
                  ? `No commands match "${search}"`
                  : "Execute tools from the Tools page — every command you run will appear here for study."}
              </p>
            </div>
          ) : (
            <div className="p-5 space-y-7">
              {filtered.map((cat) => {
                const catColor = CATEGORY_COLOR[cat.category] ?? "#9b7fef";
                return (
                  <div key={cat.category}>
                    {/* Category header */}
                    <div className="flex items-center gap-3 mb-3">
                      <div
                        className="flex items-center gap-2 px-2.5 py-1 rounded-sm"
                        style={{
                          background: `${catColor}0d`,
                          border: `1px solid ${catColor}25`,
                        }}
                      >
                        <div className="w-1.5 h-1.5 rounded-full" style={{ background: catColor }} />
                        <span
                          className="text-[10px] font-mono font-bold uppercase tracking-wider"
                          style={{ color: catColor }}
                        >
                          {cat.category}
                        </span>
                        <span className="text-[9px] font-mono" style={{ color: `${catColor}70` }}>
                          {cat.totalRuns} runs
                        </span>
                      </div>
                      <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${catColor}20, transparent)` }} />
                    </div>

                    <div className="space-y-2">
                      {cat.tools.map((tool) => {
                        const ds = DIFF_STYLE[tool.difficulty?.toLowerCase()] ?? DIFF_STYLE.beginner;
                        return (
                          <div
                            key={tool.toolId}
                            className="rounded-sm overflow-hidden"
                            style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
                          >
                            {/* Tool header */}
                            <div
                              className="flex items-center gap-3 px-4 py-2.5"
                              style={{
                                borderBottom: "1px solid hsl(232 18% 10%)",
                                background: "hsl(235 28% 5.5%)",
                                borderLeft: `3px solid ${catColor}`,
                              }}
                            >
                              <Terminal className="h-3.5 w-3.5 flex-shrink-0" style={{ color: `${catColor}80` }} />
                              <span className="font-semibold text-sm" style={{ color: "hsl(220 20% 90%)" }}>{tool.toolName}</span>
                              {tool.difficulty && (
                                <span
                                  className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded-sm border font-bold"
                                  style={{ color: ds.color, background: ds.bg, borderColor: ds.border }}
                                >
                                  {tool.difficulty}
                                </span>
                              )}
                              <div className="ml-auto flex items-center gap-3 text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                                <span className="flex items-center gap-1">
                                  <Hash className="h-2.5 w-2.5" />
                                  {tool.runCount} run{tool.runCount !== 1 ? "s" : ""}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Clock className="h-2.5 w-2.5" />
                                  {timeAgo(tool.lastRun)}
                                </span>
                              </div>
                            </div>

                            {/* Commands */}
                            <div className="divide-y divide-[hsl(232_18%_9%)]">
                              {tool.commands.map((cmdEntry, ci) => {
                                const key = `${tool.toolId}-${ci}`;
                                const isExpanded = expandedCmd === key;
                                return (
                                  <div key={ci}>
                                    <div
                                      className="px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.01] transition-colors cursor-pointer"
                                      onClick={() => setExpandedCmd(isExpanded ? null : key)}
                                    >
                                      {/* Expand */}
                                      <div className="flex-shrink-0" style={{ color: "hsl(232 10% 30%)" }}>
                                        {isExpanded
                                          ? <ChevronDown className="h-3.5 w-3.5" />
                                          : <ChevronRight className="h-3.5 w-3.5" />}
                                      </div>

                                      {/* Command */}
                                      <div className="flex-1 min-w-0">
                                        <div
                                          className="px-3 py-1.5 rounded-sm flex items-start gap-2"
                                          style={{ background: "#020204", border: "1px solid hsl(232 18% 11%)" }}
                                        >
                                          <span
                                            className="flex-shrink-0 select-none"
                                            style={{ color: `${catColor}50`, fontFamily: "'JetBrains Mono', monospace", fontSize: "0.7rem", paddingTop: "1px" }}
                                          >
                                            $
                                          </span>
                                          <HighlightedCommand cmd={cmdEntry.command} />
                                        </div>
                                      </div>

                                      {/* Meta */}
                                      <div className="flex items-center gap-3 flex-shrink-0">
                                        <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono" style={{ color: "hsl(232 10% 32%)" }}>
                                          {cmdEntry.lastStatus === "completed"
                                            ? <CheckCircle2 className="h-2.5 w-2.5" style={{ color: "#4ade80" }} />
                                            : <XOctagon className="h-2.5 w-2.5" style={{ color: "#ff2d55" }} />}
                                          <span>×{cmdEntry.runCount}</span>
                                          <span style={{ color: "hsl(232 10% 22%)" }}>·</span>
                                          <span>{timeAgo(cmdEntry.lastRun)}</span>
                                        </div>
                                        <button
                                          className="h-6 w-6 flex items-center justify-center rounded-sm transition-colors"
                                          style={{ color: "hsl(232 10% 28%)" }}
                                          title="Copy command"
                                          onClick={(e) => { e.stopPropagation(); copyCmd(cmdEntry.command); }}
                                          onMouseEnter={(e) => (e.currentTarget.style.color = catColor)}
                                          onMouseLeave={(e) => (e.currentTarget.style.color = "hsl(232 10% 28%)")}
                                        >
                                          <Copy className="h-3 w-3" />
                                        </button>
                                      </div>
                                    </div>

                                    {/* Expanded output */}
                                    {isExpanded && (
                                      <div style={{ borderTop: "1px solid hsl(232 18% 9%)" }}>
                                        {cmdEntry.lastOutput ? (
                                          <>
                                            <div
                                              className="px-4 py-1 flex items-center gap-2 text-[9px] font-mono uppercase tracking-wider"
                                              style={{
                                                color: "hsl(232 10% 28%)",
                                                borderBottom: "1px solid hsl(232 18% 8%)",
                                                background: "#020204",
                                              }}
                                            >
                                              <span>Last output</span>
                                              <span style={{ color: `${catColor}50` }}>·</span>
                                              <span>{timeAgo(cmdEntry.lastRun)}</span>
                                            </div>
                                            <div
                                              className="px-6 py-3 font-mono text-[11px] whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed"
                                              style={{ background: "#030305", color: "#b8c4d8", fontFamily: "'JetBrains Mono', monospace" }}
                                            >
                                              {cmdEntry.lastOutput}
                                            </div>
                                          </>
                                        ) : (
                                          <div
                                            className="px-6 py-3 text-[11px] font-mono italic"
                                            style={{ background: "#030305", color: "hsl(232 10% 28%)" }}
                                          >
                                            No output recorded for this run.
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

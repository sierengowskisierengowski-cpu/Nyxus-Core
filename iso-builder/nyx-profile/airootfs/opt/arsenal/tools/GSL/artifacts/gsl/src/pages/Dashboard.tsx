import { useQuery } from "@tanstack/react-query";
import {
  Activity, ShieldAlert, Star, Terminal as TerminalIcon,
  Network, RefreshCw, Clock, Cpu, MemoryStick, HardDrive,
  ArrowDownToLine, ArrowUpFromLine, Timer, ChevronRight, Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { apiFetch } from "@/lib/api";

interface DashboardSummary {
  totalTools: number;
  totalRuns: number;
  totalCategories: number;
  favoriteCount: number;
  findingsCount: number;
  recentActivity: string;
}

interface NetworkDevice {
  ip: string;
  hostname?: string;
  mac?: string;
  vendor?: string;
  status: string;
}

interface Run {
  id: number;
  toolId: string;
  toolName: string;
  command: string;
  status: string;
  startedAt: string;
  endedAt?: string;
  isFlagged: boolean;
  severity?: string;
}

interface SystemStats {
  cpu: { percent: number; load1: number; load5: number; load15: number; count: number };
  memory: { percent: number; used: string; total: string; available: string };
  disk: { percent: number; used: string; total: string; free: string };
  network: { rx_rate: string; tx_rate: string; bytes_recv_total: string; bytes_sent_total: string };
  uptime: string;
}

function RingGauge({ percent, color, label, value, sub }: {
  percent: number; color: string; label: string; value: string; sub: string;
}) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const offset = circ - (Math.min(100, Math.max(0, percent)) / 100) * circ;
  const danger = percent > 85;
  const warn = percent > 65;
  const finalColor = danger ? "#f87171" : warn ? "#fbbf24" : color;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-16 h-16">
        <svg className="w-full h-full" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r={r} fill="none" stroke="hsl(232 18% 12%)" strokeWidth="5" />
          <circle
            cx="36" cy="36" r={r}
            fill="none"
            stroke={finalColor}
            strokeWidth="5"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="ring-progress"
            style={{ filter: `drop-shadow(0 0 4px ${finalColor}60)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[11px] font-mono font-bold tabular-nums" style={{ color: finalColor }}>
            {percent}%
          </span>
        </div>
      </div>
      <div className="text-center">
        <div className="text-[10px] font-mono font-semibold uppercase tracking-wider" style={{ color: "hsl(232 10% 50%)" }}>{label}</div>
        <div className="text-[9px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>{sub}</div>
      </div>
    </div>
  );
}

function StatCard({
  label, value, sub, icon: Icon, color = "#9b7fef", onClick,
}: {
  label: string; value: string | number; sub?: string;
  icon: React.ElementType; color?: string; onClick?: () => void;
}) {
  return (
    <div
      className="relative overflow-hidden rounded-sm cursor-default transition-all duration-200"
      style={{
        background: "hsl(235 28% 6%)",
        border: `1px solid hsl(232 18% 12%)`,
        cursor: onClick ? "pointer" : "default",
      }}
      onClick={onClick}
      onMouseEnter={(e) => {
        if (onClick) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.borderColor = `${color}35`;
          el.style.boxShadow = `0 0 16px ${color}08`;
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          const el = e.currentTarget as HTMLDivElement;
          el.style.borderColor = "hsl(232 18% 12%)";
          el.style.boxShadow = "";
        }
      }}
    >
      {/* Top accent line */}
      <div className="h-px w-full" style={{ background: `linear-gradient(90deg, transparent, ${color}40, transparent)` }} />

      <div className="px-4 pt-4 pb-4">
        <div className="flex items-start justify-between mb-3">
          <span
            className="text-[10px] font-mono uppercase tracking-widest font-semibold"
            style={{ color: "hsl(232 10% 40%)", letterSpacing: "0.12em" }}
          >
            {label}
          </span>
          <div
            className="w-7 h-7 rounded flex items-center justify-center"
            style={{ background: `${color}12`, border: `1px solid ${color}20` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color }} />
          </div>
        </div>
        <div className="text-3xl font-bold font-mono tabular-nums stat-number" style={{ color: "hsl(220 20% 95%)" }}>
          {value}
        </div>
        {sub && (
          <p className="text-[11px] mt-1 font-mono" style={{ color: "hsl(232 10% 38%)" }}>{sub}</p>
        )}
      </div>

      {/* Bottom glow */}
      <div
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${color}20, transparent)` }}
      />
    </div>
  );
}

const STATUS_DOT: Record<string, { color: string; label: string }> = {
  completed: { color: "#4ade80", label: "completed" },
  running:   { color: "#60a5fa", label: "running" },
  error:     { color: "#f87171", label: "error" },
  killed:    { color: "#fbbf24", label: "killed" },
  pending:   { color: "#94a3b8", label: "pending" },
};

export default function Dashboard() {
  const [, setLocation] = useLocation();

  const { data: summary, isLoading: loadingSummary } = useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiFetch<DashboardSummary>("/api/dashboard/summary"),
    refetchInterval: 15000,
  });

  const { data: devices = [], isLoading: loadingDevices, refetch: refetchDevices } = useQuery<NetworkDevice[]>({
    queryKey: ["devices"],
    queryFn: () => apiFetch<NetworkDevice[]>("/api/dashboard/devices"),
    refetchInterval: 60000,
    staleTime: 30000,
  });

  const { data: recentRuns = [] } = useQuery<Run[]>({
    queryKey: ["recent-runs"],
    queryFn: () => apiFetch<Run[]>("/api/dashboard/recent-runs"),
    refetchInterval: 10000,
  });

  const { data: sysStats, isLoading: loadingSys } = useQuery<SystemStats>({
    queryKey: ["system-stats"],
    queryFn: () => apiFetch<SystemStats>("/api/dashboard/system-stats"),
    refetchInterval: 8000,
  });

  return (
    <div className="p-5 space-y-5 max-w-7xl mx-auto">
      {/* Hero Header */}
      <div
        className="relative rounded-sm overflow-hidden"
        style={{
          background: "linear-gradient(135deg, hsl(235 28% 6%) 0%, hsl(237 35% 5%) 100%)",
          border: "1px solid hsl(232 18% 12%)",
          padding: "20px 24px",
        }}
      >
        {/* Background glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "radial-gradient(ellipse 60% 80% at 80% 50%, hsl(263 55% 62% / 0.04) 0%, transparent 70%)",
          }}
        />
        {/* Top accent line */}
        <div className="absolute top-0 left-0 right-0 h-px" style={{ background: "linear-gradient(90deg, transparent, hsl(263 55% 62% / 0.4), transparent)" }} />

        <div className="relative flex items-center justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div
                className="w-9 h-9 rounded flex items-center justify-center"
                style={{
                  background: "hsl(263 55% 62% / 0.12)",
                  border: "1px solid hsl(263 55% 62% / 0.25)",
                  boxShadow: "0 0 16px hsl(263 55% 62% / 0.1)",
                }}
              >
                <Zap className="h-4.5 w-4.5" style={{ color: "hsl(263 55% 72%)" }} />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight" style={{ color: "hsl(220 20% 95%)" }}>
                  System Overview
                </h1>
                <p className="text-[11px] font-mono mt-0.5" style={{ color: "hsl(232 10% 38%)" }}>
                  GowskiNet Security Lab · nyx-cosmic · 192.168.0.172
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {sysStats && (
              <div className="text-[10px] font-mono px-2.5 py-1.5 rounded-sm" style={{ background: "hsl(235 22% 8%)", border: "1px solid hsl(232 18% 13%)", color: "hsl(232 10% 45%)" }}>
                <span style={{ color: "hsl(263 55% 65%)" }}>uptime</span> {sysStats.uptime}
              </div>
            )}
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-sm text-[11px] font-mono font-semibold"
              style={{
                background: "hsl(142 76% 56% / 0.06)",
                border: "1px solid hsl(142 76% 56% / 0.2)",
                color: "#4ade80",
                boxShadow: "0 0 12px hsl(142 76% 56% / 0.05)",
              }}
            >
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 pulse-dot" />
              SECURE
            </div>
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Active Tools" value={loadingSummary ? "—" : summary?.totalTools ?? 0}
          sub={`${summary?.totalCategories ?? 0} categories`}
          icon={Activity} color="#9b7fef"
        />
        <StatCard
          label="Total Runs" value={loadingSummary ? "—" : summary?.totalRuns ?? 0}
          sub="All time executions"
          icon={TerminalIcon} color="#60a5fa"
          onClick={() => setLocation("/history")}
        />
        <StatCard
          label="Findings" value={loadingSummary ? "—" : summary?.findingsCount ?? 0}
          sub="Flagged for review"
          icon={ShieldAlert} color="#f87171"
          onClick={() => setLocation("/findings")}
        />
        <StatCard
          label="Favorites" value={loadingSummary ? "—" : summary?.favoriteCount ?? 0}
          sub="Pinned tools"
          icon={Star} color="#fbbf24"
        />
      </div>

      {/* System Monitor */}
      <div
        className="rounded-sm overflow-hidden"
        style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
      >
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}
        >
          <div className="flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5" style={{ color: "hsl(263 55% 62%)" }} />
            <span className="text-[11px] font-mono uppercase tracking-wider font-semibold" style={{ color: "hsl(232 10% 45%)" }}>
              System Monitor
            </span>
            <span className="text-[10px] font-mono" style={{ color: "hsl(232 10% 30%)" }}>· nyx-cosmic</span>
          </div>
          {sysStats && (
            <div className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
              <Timer className="h-3 w-3" /> up {sysStats.uptime}
            </div>
          )}
        </div>

        <div className="px-6 py-5">
          {loadingSys || !sysStats ? (
            <div className="flex items-center justify-center py-8 gap-3">
              <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground animate-pulse">Reading system metrics...</span>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 items-start">
              <RingGauge percent={sysStats.cpu.percent} color="#9b7fef" label="CPU" value={`${sysStats.cpu.percent}%`} sub={`${sysStats.cpu.count} cores`} />
              <RingGauge percent={sysStats.memory.percent} color="#60a5fa" label="Memory" value={sysStats.memory.used} sub={`of ${sysStats.memory.total}`} />
              <RingGauge percent={sysStats.disk.percent} color="#22d3ee" label="Disk" value={sysStats.disk.used} sub={`${sysStats.disk.free} free`} />

              {/* Network (no ring, just rates) */}
              <div className="flex flex-col items-center gap-2">
                <div
                  className="w-16 h-16 rounded flex flex-col items-center justify-center"
                  style={{ background: "hsl(235 22% 9%)", border: "1px solid hsl(232 18% 13%)" }}
                >
                  <Network className="h-5 w-5 mb-1" style={{ color: "#34d399" }} />
                  <div className="text-[8px] font-mono font-bold uppercase tracking-widest" style={{ color: "#34d399" }}>NET</div>
                </div>
                <div className="text-center space-y-1">
                  <div className="flex items-center justify-center gap-1 text-[10px] font-mono" style={{ color: "#4ade80" }}>
                    <ArrowDownToLine className="h-2.5 w-2.5" />
                    <span>{sysStats.network.rx_rate}</span>
                  </div>
                  <div className="flex items-center justify-center gap-1 text-[10px] font-mono" style={{ color: "#fbbf24" }}>
                    <ArrowUpFromLine className="h-2.5 w-2.5" />
                    <span>{sysStats.network.tx_rate}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Load averages row */}
          {sysStats && (
            <div
              className="mt-4 pt-3 flex items-center gap-6 flex-wrap"
              style={{ borderTop: "1px solid hsl(232 18% 10%)" }}
            >
              <div className="flex items-center gap-2 text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                <span>Load avg</span>
                <span className="text-foreground/70">{sysStats.cpu.load1}</span>
                <span>/</span>
                <span className="text-foreground/70">{sysStats.cpu.load5}</span>
                <span>/</span>
                <span className="text-foreground/70">{sysStats.cpu.load15}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                <span>Memory</span>
                <span className="text-foreground/70">{sysStats.memory.used} / {sysStats.memory.total}</span>
                <span style={{ color: "hsl(232 10% 25%)" }}>·</span>
                <span className="text-foreground/50">{sysStats.memory.available} avail</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono" style={{ color: "hsl(232 10% 35%)" }}>
                <span>Net total</span>
                <span style={{ color: "#4ade8060" }}>↓ {sysStats.network.bytes_recv_total}</span>
                <span style={{ color: "#fbbf2460" }}>↑ {sysStats.network.bytes_sent_total}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Lower Grid */}
      <div className="grid md:grid-cols-2 gap-3">
        {/* Network Devices */}
        <div
          className="rounded-sm overflow-hidden"
          style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
        >
          <div
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}
          >
            <div className="flex items-center gap-2">
              <Network className="h-3.5 w-3.5" style={{ color: "#22d3ee" }} />
              <span className="text-[11px] font-mono uppercase tracking-wider font-semibold" style={{ color: "hsl(232 10% 45%)" }}>
                Live Network · 192.168.0.0/24
              </span>
            </div>
            <Button
              variant="ghost" size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={() => refetchDevices()}
              disabled={loadingDevices}
            >
              <RefreshCw className={`h-3 w-3 ${loadingDevices ? "animate-spin" : ""}`} />
            </Button>
          </div>

          {loadingDevices ? (
            <div className="p-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="shimmer h-9 rounded-sm mb-1.5" />
              ))}
            </div>
          ) : devices.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground font-mono">No devices found.</div>
          ) : (
            <div className="divide-y divide-[hsl(232_18%_10%)]">
              {devices.map((device, i) => (
                <div
                  key={i}
                  className="px-4 py-2.5 flex items-center justify-between hover:bg-white/[0.015] transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="relative flex-shrink-0">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{
                          background: device.status === "up" ? "#4ade80" : "#334155",
                          boxShadow: device.status === "up" ? "0 0 6px #4ade8060" : undefined,
                        }}
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] font-bold" style={{ color: "#9b7fef" }}>{device.ip}</div>
                      <div className="text-[10px] font-mono" style={{ color: "hsl(232 10% 38%)" }}>{device.hostname || "unknown host"}</div>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    {device.mac && <div className="font-mono text-[9px]" style={{ color: "hsl(232 10% 30%)" }}>{device.mac}</div>}
                    {device.vendor && <div className="text-[9px]" style={{ color: "hsl(232 10% 28%)" }}>{device.vendor}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Runs */}
        <div
          className="rounded-sm overflow-hidden"
          style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
        >
          <div
            className="flex items-center justify-between px-4 py-3"
            style={{ borderBottom: "1px solid hsl(232 18% 10%)" }}
          >
            <div className="flex items-center gap-2">
              <Clock className="h-3.5 w-3.5" style={{ color: "#60a5fa" }} />
              <span className="text-[11px] font-mono uppercase tracking-wider font-semibold" style={{ color: "hsl(232 10% 45%)" }}>
                Recent Runs
              </span>
            </div>
            <Button
              variant="ghost" size="icon"
              className="h-6 w-6 text-muted-foreground hover:text-foreground"
              onClick={() => setLocation("/history")}
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>

          {recentRuns.length === 0 ? (
            <div className="p-6 text-center">
              <TerminalIcon className="h-8 w-8 mx-auto mb-2" style={{ color: "hsl(263 55% 62% / 0.2)" }} />
              <p className="text-xs text-muted-foreground">No runs yet.</p>
              <button
                className="text-xs mt-1 underline underline-offset-2"
                style={{ color: "hsl(263 55% 65%)" }}
                onClick={() => setLocation("/tools")}
              >
                Launch a tool to get started
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[hsl(232_18%_10%)]">
              {recentRuns.slice(0, 8).map((run) => {
                const statusInfo = STATUS_DOT[run.status] ?? STATUS_DOT["pending"];
                return (
                  <div key={run.id} className="px-4 py-2.5 flex items-center gap-3 hover:bg-white/[0.015] transition-colors">
                    <div
                      className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: statusInfo.color, boxShadow: `0 0 4px ${statusInfo.color}60` }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[12px] font-medium truncate" style={{ color: "hsl(220 20% 88%)" }}>{run.toolName}</span>
                        {run.isFlagged && (
                          <ShieldAlert className="h-3 w-3 text-red-500 flex-shrink-0" />
                        )}
                      </div>
                      <code className="text-[10px] font-mono truncate block" style={{ color: "hsl(232 10% 38%)" }}>{run.command}</code>
                    </div>
                    <span
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm border flex-shrink-0 uppercase font-semibold"
                      style={{
                        color: statusInfo.color,
                        background: `${statusInfo.color}08`,
                        borderColor: `${statusInfo.color}20`,
                      }}
                    >
                      {run.status}
                    </span>
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

import { motion } from "framer-motion";
import { Cpu, MemoryStick, HardDrive, Clock, BarChart2, MessageSquare, FolderOpen, CalendarClock, TrendingUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useGetSystemStats, getGetSystemStatsQueryKey,
  useGetActivitySummary, getGetActivitySummaryQueryKey,
} from "@workspace/api-client-react";

function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(0)} MB`;
  return `${(bytes / 1e3).toFixed(0)} KB`;
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function Stats() {
  const { data: stats, isLoading } = useGetSystemStats({
    query: { queryKey: getGetSystemStatsQueryKey(), refetchInterval: 3000 },
  });
  const { data: activity } = useGetActivitySummary({
    query: { queryKey: getGetActivitySummaryQueryKey(), refetchInterval: 10000 },
  });

  const cpuColor = !stats ? "#818cf8" : stats.cpu > 80 ? "#f87171" : stats.cpu > 60 ? "#fb923c" : "#818cf8";
  const memColor = !stats ? "#a78bfa" : stats.memory.percent > 80 ? "#f87171" : stats.memory.percent > 60 ? "#fb923c" : "#a78bfa";

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-cyan-400" />
            System Status
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Live stats · refreshes every 3 seconds</p>
        </div>
        {stats && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>Uptime {formatUptime(stats.uptime)}</span>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-xl bg-white/5" />)}
          </div>
        ) : !stats ? (
          <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
            Could not load system stats
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* CPU */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card rounded-xl p-5 border border-white/[0.06]"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center">
                      <Cpu className="w-4 h-4 text-indigo-400" />
                    </div>
                    <span className="text-sm font-medium">CPU</span>
                  </div>
                  <span className="text-2xl font-bold font-mono" style={{ color: cpuColor }}>{stats.cpu}%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: `linear-gradient(90deg, ${cpuColor}88, ${cpuColor})` }}
                    initial={{ width: 0 }}
                    animate={{ width: `${stats.cpu}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {stats.cpu < 30 ? "Idle" : stats.cpu < 60 ? "Moderate load" : stats.cpu < 80 ? "High load" : "Very high load"}
                </p>
              </motion.div>

              {/* RAM */}
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="glass-card rounded-xl p-5 border border-white/[0.06]"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-violet-500/15 flex items-center justify-center">
                      <MemoryStick className="w-4 h-4 text-violet-400" />
                    </div>
                    <span className="text-sm font-medium">Memory</span>
                  </div>
                  <span className="text-2xl font-bold font-mono" style={{ color: memColor }}>{stats.memory.percent}%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: `linear-gradient(90deg, ${memColor}88, ${memColor})` }}
                    initial={{ width: 0 }}
                    animate={{ width: `${stats.memory.percent}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {formatBytes(stats.memory.used)} used · {formatBytes(stats.memory.free)} free · {formatBytes(stats.memory.total)} total
                </p>
              </motion.div>
            </div>

            {/* Disk */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-card rounded-xl p-5 border border-white/[0.06]"
            >
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
                  <HardDrive className="w-4 h-4 text-emerald-400" />
                </div>
                <span className="text-sm font-medium">Disk Usage</span>
              </div>
              <div className="space-y-3">
                {stats.disk.map((d, i) => {
                  const diskColor = d.percent > 90 ? "#f87171" : d.percent > 70 ? "#fb923c" : "#34d399";
                  return (
                    <div key={i} className="space-y-1.5" data-testid={`disk-${i}`}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground font-mono">{d.mount}</span>
                        <span className="text-muted-foreground">
                          {formatBytes(d.used)} / {formatBytes(d.total)}
                          <span className="ml-2 font-medium font-mono" style={{ color: diskColor }}>{d.percent}%</span>
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{ background: diskColor }}
                          initial={{ width: 0 }}
                          animate={{ width: `${d.percent}%` }}
                          transition={{ duration: 0.6, delay: i * 0.08 }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>

            {/* Quick stat cards */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="grid grid-cols-3 gap-3"
            >
              <div className="glass-card rounded-xl p-4 border border-white/[0.06] text-center">
                <Cpu className="w-4 h-4 text-indigo-400 mx-auto mb-2" />
                <div className="text-lg font-bold font-mono text-indigo-400">{stats.cpu}%</div>
                <div className="text-xs text-muted-foreground">CPU Load</div>
              </div>
              <div className="glass-card rounded-xl p-4 border border-white/[0.06] text-center">
                <MemoryStick className="w-4 h-4 text-violet-400 mx-auto mb-2" />
                <div className="text-lg font-bold font-mono text-violet-400">{formatBytes(stats.memory.used)}</div>
                <div className="text-xs text-muted-foreground">RAM Used</div>
              </div>
              <div className="glass-card rounded-xl p-4 border border-white/[0.06] text-center">
                <Clock className="w-4 h-4 text-emerald-400 mx-auto mb-2" />
                <div className="text-lg font-bold font-mono text-emerald-400">{formatUptime(stats.uptime)}</div>
                <div className="text-xs text-muted-foreground">Uptime</div>
              </div>
            </motion.div>

            {/* AXIOM Usage Stats */}
            {activity && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card rounded-xl p-5 border border-white/[0.06]"
              >
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 rounded-lg bg-sky-500/15 flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-sky-400" />
                  </div>
                  <div>
                    <span className="text-sm font-medium">AXIOM Usage</span>
                    <p className="text-[10px] text-muted-foreground">All-time activity</p>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5 text-xs">
                    <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    <span className="text-emerald-400 font-medium">{activity.recentCount} today</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div className="rounded-lg bg-sky-500/8 border border-sky-500/15 p-3 text-center">
                    <MessageSquare className="w-4 h-4 text-sky-400 mx-auto mb-1.5" />
                    <div className="text-xl font-bold font-mono text-sky-300">{activity.byType.chat ?? 0}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">Chat sessions</div>
                  </div>
                  <div className="rounded-lg bg-amber-500/8 border border-amber-500/15 p-3 text-center">
                    <FolderOpen className="w-4 h-4 text-amber-400 mx-auto mb-1.5" />
                    <div className="text-xl font-bold font-mono text-amber-300">{activity.byType.file_op ?? 0}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">File operations</div>
                  </div>
                  <div className="rounded-lg bg-emerald-500/8 border border-emerald-500/15 p-3 text-center">
                    <CalendarClock className="w-4 h-4 text-emerald-400 mx-auto mb-1.5" />
                    <div className="text-xl font-bold font-mono text-emerald-300">{activity.byType.scheduled ?? 0}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">Scheduled runs</div>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-white/[0.05] flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Total actions</span>
                  <span className="text-sm font-bold font-mono text-foreground">{activity.total}</span>
                </div>
              </motion.div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

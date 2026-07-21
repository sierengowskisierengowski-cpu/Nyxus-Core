import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  useListJobs,
  usePauseJob,
  useResumeJob,
  useStopJob,
  useGetJobLog,
  useGetSystemStats,
  getListJobsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Play, Pause, Square, Activity, Cpu, Server, HardDrive } from "lucide-react";

function TerminalIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" x2="20" y1="19" y2="19" />
    </svg>
  );
}

function fmtSpeed(speed: number | null | undefined, unit: string | undefined): string {
  if (!speed) return `0 ${unit || "H/s"}`;
  if (speed >= 1e9) return `${(speed / 1e9).toFixed(2)} G${unit || "H/s"}`;
  if (speed >= 1e6) return `${(speed / 1e6).toFixed(2)} M${unit || "H/s"}`;
  if (speed >= 1e3) return `${(speed / 1e3).toFixed(2)} K${unit || "H/s"}`;
  return `${Math.round(speed)} ${unit || "H/s"}`;
}

export default function Monitor() {
  const queryClient = useQueryClient();
  const { data: jobs } = useListJobs({ status: "active" }, { query: { refetchInterval: 2000, queryKey: ["listJobsMonitor"] } });
  const { data: stats } = useGetSystemStats({ query: { refetchInterval: 3000, queryKey: ["getSystemStatsMonitor"] } });

  const pauseMutation = usePauseJob();
  const resumeMutation = useResumeJob();
  const stopMutation = useStopJob();

  const firstJobId = jobs?.[0]?.id ?? 0;
  const { data: logData } = useGetJobLog(firstJobId, {
    query: { refetchInterval: 2000, enabled: firstJobId > 0, queryKey: ["getJobLog", firstJobId] },
  });

  const handleAction = (action: "pause" | "resume" | "stop", id: number) => {
    const mutation = action === "pause" ? pauseMutation : action === "resume" ? resumeMutation : stopMutation;
    mutation.mutate(
      { id },
      { onSuccess: () => queryClient.invalidateQueries({ queryKey: getListJobsQueryKey() }) },
    );
  };

  const logLines = (logData?.log ?? "").split("\n").filter((l) => l.trim().length > 0).slice(-200);

  return (
    <PageContainer title="Live Cracking Monitor">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {jobs?.map((job) => (
            <Card key={job.id} className="bg-card/50 border-primary/30 overflow-hidden relative">
              <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
              <CardContent className="p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-mono text-primary font-bold">{job.name}</h3>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      <Badge variant="outline" className="font-mono text-[10px] border-primary/50 text-primary/80">{job.engine || "hashcat"}</Badge>
                      <Badge variant="outline" className="font-mono text-[10px] border-primary/50 text-primary/80">{job.attackMode}</Badge>
                      <Badge variant="outline" className="font-mono text-[10px] border-secondary/50 text-secondary/80">{job.hashType}</Badge>
                      <Badge variant="outline" className="font-mono text-[10px] border-border text-muted-foreground">{job.status}</Badge>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {job.status === "running" ? (
                      <Button size="icon" variant="outline" className="h-8 w-8 border-warning text-warning hover:bg-warning/10" onClick={() => handleAction("pause", job.id)}>
                        <Pause className="w-4 h-4" />
                      </Button>
                    ) : job.status === "paused" ? (
                      <Button size="icon" variant="outline" className="h-8 w-8 border-success text-success hover:bg-success/10" onClick={() => handleAction("resume", job.id)}>
                        <Play className="w-4 h-4" />
                      </Button>
                    ) : null}
                    <Button size="icon" variant="outline" className="h-8 w-8 border-destructive text-destructive hover:bg-destructive/10" onClick={() => handleAction("stop", job.id)}>
                      <Square className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between font-mono text-xs">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="text-primary">{(job.progress || 0).toFixed(2)}%</span>
                  </div>
                  <Progress value={job.progress || 0} className="h-2 bg-background" />
                </div>

                <div className="grid grid-cols-4 gap-4 pt-4 border-t border-border/50">
                  <div>
                    <div className="text-[10px] uppercase font-mono text-muted-foreground">Speed</div>
                    <div className="font-mono text-sm">{fmtSpeed(job.speed, job.speedUnit)}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-mono text-muted-foreground">Cracks</div>
                    <div className="font-mono text-sm text-success">{job.cracksFound || 0}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-mono text-muted-foreground">Elapsed</div>
                    <div className="font-mono text-sm">{Math.floor((job.timeElapsedSeconds || 0) / 60)}m {(job.timeElapsedSeconds || 0) % 60}s</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase font-mono text-muted-foreground">ETA</div>
                    <div className="font-mono text-sm text-warning">{job.estimatedTimeSeconds ? `${Math.floor(job.estimatedTimeSeconds / 60)}m` : "—"}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {(!jobs || jobs.length === 0) && (
            <Card className="bg-card/50 border-border/50 border-dashed">
              <CardContent className="p-12 text-center">
                <Activity className="w-8 h-8 text-muted-foreground mx-auto mb-4 opacity-50" />
                <p className="font-mono text-muted-foreground">No active jobs. Launch an attack to see live monitoring.</p>
              </CardContent>
            </Card>
          )}

          <Card className="bg-black border-border/50">
            <CardHeader className="py-3 px-4 border-b border-border/50 bg-card/30">
              <CardTitle className="text-xs font-mono text-primary flex items-center gap-2">
                <TerminalIcon className="w-3 h-3" /> Tool Output {firstJobId > 0 ? `(job #${firstJobId})` : ""}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 h-64 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-0.5">
              {logLines.length > 0 ? (
                logLines.map((line, i) => (
                  <div key={i} className="text-success/80 whitespace-pre-wrap break-all">
                    {line}
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground/50">
                  {firstJobId > 0 ? "Waiting for tool output…" : "No active job."}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Server className="w-4 h-4 text-primary" /> Hardware Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {stats?.gpus?.length ? (
                stats.gpus.map((gpu) => (
                  <div key={gpu.index} className="space-y-2">
                    <div className="flex justify-between font-mono text-xs">
                      <span className="text-muted-foreground flex items-center gap-1 truncate pr-2">
                        <Server className="w-3 h-3" /> {gpu.name}
                      </span>
                      <span className="text-warning">{gpu.temperatureCelsius ?? 0}°C</span>
                    </div>
                    <Progress value={gpu.utilizationPercent ?? 0} className="h-1.5 bg-background" />
                    <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
                      <span>Usage: {gpu.utilizationPercent ?? 0}%</span>
                      <span>
                        VRAM: {Math.round((gpu.memUsedMb ?? 0) / 1024)}/{Math.round((gpu.memTotalMb ?? 0) / 1024)}GB
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="font-mono text-xs text-muted-foreground">No NVIDIA GPU detected (nvidia-smi)</div>
              )}

              <div className="space-y-2">
                <div className="flex justify-between font-mono text-xs">
                  <span className="text-muted-foreground flex items-center gap-1 truncate pr-2">
                    <Cpu className="w-3 h-3" /> {stats?.cpu?.model ?? "CPU"}
                  </span>
                  <span className="text-primary">{stats?.cpu?.usagePercent ?? 0}%</span>
                </div>
                <Progress value={stats?.cpu?.usagePercent ?? 0} className="h-1.5 bg-background" />
                <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
                  <span>Cores: {stats?.cpu?.cores ?? 0}</span>
                  <span>Load: {stats?.cpu?.loadAvg1 ?? 0}</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between font-mono text-xs">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <HardDrive className="w-3 h-3" /> Memory
                  </span>
                  <span className="text-primary">{stats?.memory?.usagePercent ?? 0}%</span>
                </div>
                <Progress value={stats?.memory?.usagePercent ?? 0} className="h-1.5 bg-background" />
                <div className="flex justify-between font-mono text-[10px] text-muted-foreground">
                  <span>
                    {Math.round((stats?.memory?.usedMb ?? 0) / 1024)}/{Math.round((stats?.memory?.totalMb ?? 0) / 1024)}GB
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

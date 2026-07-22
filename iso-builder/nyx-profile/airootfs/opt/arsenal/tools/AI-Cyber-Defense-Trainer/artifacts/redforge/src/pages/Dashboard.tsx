import { useGetDashboardSummary, getGetDashboardSummaryQueryKey } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Link } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldAlert, Crosshair, Network, BarChart } from "lucide-react";

export default function Dashboard() {
  const { data: summary, isLoading, error } = useGetDashboardSummary();

  if (isLoading) return <div className="space-y-4"><Skeleton className="h-32 w-full" /><div className="grid grid-cols-3 gap-4"><Skeleton className="h-48" /><Skeleton className="h-48" /><Skeleton className="h-48" /></div></div>;
  if (error || !summary) return <div className="text-destructive">Failed to load mission control data.</div>;

  const threatColor = summary.threatLevel === "TRAINING" ? "text-green-500" : summary.threatLevel === "ACTIVE_ATTACK" ? "text-primary" : "text-purple-500";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">MISSION CONTROL</h1>
          <p className="text-muted-foreground uppercase text-sm mt-1">Operational Overview & Status</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm border border-border px-3 py-1 rounded bg-card">
            <span className="text-muted-foreground">THREAT LEVEL:</span>
            <span className={`font-bold flex items-center gap-2 ${threatColor}`}>
              <span className={`w-2 h-2 rounded-full ${summary.threatLevel === 'ACTIVE_ATTACK' ? 'bg-primary animate-pulse' : 'bg-green-500'}`}></span>
              {summary.threatLevel}
            </span>
          </div>
        </div>
      </div>

      {summary.activeMission && (
        <Card className="border-primary shadow-[0_0_15px_rgba(239,68,68,0.2)] bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-primary flex items-center gap-2">
              <Crosshair className="animate-pulse" />
              ACTIVE MISSION DEPLOYED
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-xl font-bold">{summary.activeMission.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">Started: {new Date(summary.activeMission.startedAt || '').toLocaleString()}</p>
              </div>
              <Link href={`/missions/${summary.activeMission.id}`} className="px-4 py-2 bg-primary text-primary-foreground rounded font-bold uppercase hover:bg-primary/90 transition-colors">
                ENTER COMMAND CENTER
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2"><Network size={16}/> TOTAL MISSIONS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.stats?.totalMissions || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2"><BarChart size={16}/> TRAINING STREAK</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.stats?.streak || 0} DAYS</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground flex items-center gap-2"><ShieldAlert size={16}/> CLAUDE API</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-xl font-bold ${summary.claudeApiStatus === 'online' ? 'text-green-500' : 'text-destructive'}`}>
              {summary.claudeApiStatus.toUpperCase()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">VERSION</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{summary.redforgeVersion}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="h-full">
          <CardHeader>
            <CardTitle>QUICK LAUNCH</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Link href="/generate" className="block w-full p-4 border border-border rounded-lg hover:border-primary hover:bg-primary/5 transition-colors group">
              <h3 className="font-bold group-hover:text-primary">Random Attack</h3>
              <p className="text-sm text-muted-foreground">Generate a blind scenario</p>
            </Link>
            <Link href="/generate" className="block w-full p-4 border border-border rounded-lg hover:border-primary hover:bg-primary/5 transition-colors group">
              <h3 className="font-bold group-hover:text-primary">Specify Attack</h3>
              <p className="text-sm text-muted-foreground">Custom prompt simulation</p>
            </Link>
          </CardContent>
        </Card>
        
        {/* Placeholder for Recent Missions */}
        <Card>
          <CardHeader>
            <CardTitle>SYSTEM LOGS</CardTitle>
          </CardHeader>
          <CardContent>
             <div className="text-sm text-muted-foreground flex flex-col space-y-2 font-mono">
               <div>[+] Initializing components...</div>
               <div>[+] Loading knowledge base... {(summary.knowledgeBase?.loaded ? "OK" : "PENDING")}</div>
               <div>[+] Scanning target network... OK</div>
               <div>[+] Ready for operations.</div>
             </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

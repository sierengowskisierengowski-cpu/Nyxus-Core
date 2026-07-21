import { useGetDashboardSummary, useGetRecentMissions, useGetRecentNotes } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ShieldAlert, Activity, BookOpen, Target, TerminalSquare, AlertTriangle } from "lucide-react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";
import { format, formatDistanceToNow } from "date-fns";

export default function Dashboard() {
  useDocumentTitle("Mission Control");
  
  const { data: summary, isLoading: summaryLoading } = useGetDashboardSummary();
  const { data: missions, isLoading: missionsLoading } = useGetRecentMissions();
  const { data: notes, isLoading: notesLoading } = useGetRecentNotes();

  if (summaryLoading) return <div className="p-8 text-muted-foreground animate-pulse font-mono text-sm">LOADING TELEMETRY...</div>;
  if (!summary) return null;

  return (
    <div className="space-y-6">
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className={cn(
          "border-l-4",
          summary.threatLevel === "ELEVATED" ? "border-l-primary" : "border-l-secondary"
        )}>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <ShieldAlert className="w-4 h-4" />
              Threat Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-3xl font-bold tracking-tight",
              summary.threatLevel === "ELEVATED" ? "text-primary" : "text-secondary"
            )}>
              {summary.threatLevel}
            </div>
            <p className="text-xs text-muted-foreground mt-1">System Status: NOMINAL</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Target className="w-4 h-4" />
              Skill Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-foreground">{summary.skillLevel}</div>
            <p className="text-xs text-muted-foreground mt-1">{summary.xp} XP Accumulated</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Current Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-foreground">{summary.streakDays} Days</div>
            <p className="text-xs text-muted-foreground mt-1">{summary.missionsCompleted} Missions Completed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              Knowledge Base
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold tracking-tight text-foreground">{summary.kbStats.mitreTechniques}</div>
            <p className="text-xs text-muted-foreground mt-1">Techniques Tracked</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Recent Missions */}
        <Card className="flex flex-col h-96">
          <CardHeader className="border-b border-border pb-4">
            <div className="flex justify-between items-center">
              <CardTitle className="text-sm uppercase tracking-widest text-foreground flex items-center gap-2">
                <TerminalSquare className="w-4 h-4 text-primary" />
                Recent Operations
              </CardTitle>
              <Link href="/missions" className="text-xs text-primary hover:underline">VIEW ALL</Link>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-0">
            {missionsLoading ? (
              <div className="p-4 text-muted-foreground text-xs">Loading...</div>
            ) : missions?.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground text-sm border-dashed border border-border m-4 rounded">
                No recent missions. <Link href="/scenarios" className="text-primary hover:underline">Deploy a scenario</Link> to begin.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {missions?.map(m => (
                  <Link key={m.id} href={`/missions/${m.id}`} className="block p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-semibold text-sm">{m.scenarioName}</div>
                      <div className={cn(
                        "text-[10px] px-2 py-0.5 rounded border uppercase",
                        m.status === "completed" ? "border-secondary/50 text-secondary" : 
                        m.status === "active" ? "border-primary/50 text-primary bg-primary/10 animate-pulse" : 
                        "border-muted-foreground/50 text-muted-foreground"
                      )}>
                        {m.status}
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{formatDistanceToNow(new Date(m.startedAt), { addSuffix: true })}</span>
                      {m.score !== null && m.score !== undefined && (
                        <span>Score: {m.score}%</span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Notes */}
        <Card className="flex flex-col h-96">
          <CardHeader className="border-b border-border pb-4">
            <div className="flex justify-between items-center">
              <CardTitle className="text-sm uppercase tracking-widest text-foreground flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-secondary" />
                Intel & Notes
              </CardTitle>
              <Link href="/notes" className="text-xs text-secondary hover:underline">VIEW ALL</Link>
            </div>
          </CardHeader>
          <CardContent className="flex-1 overflow-auto p-0">
            {notesLoading ? (
              <div className="p-4 text-muted-foreground text-xs">Loading...</div>
            ) : notes?.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground text-sm border-dashed border border-border m-4 rounded">
                No recent notes. <Link href="/notes" className="text-secondary hover:underline">Document your findings</Link>.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {notes?.map(n => (
                  <Link key={n.id} href={`/notes?id=${n.id}`} className="block p-4 hover:bg-muted/50 transition-colors">
                    <div className="font-semibold text-sm mb-1 line-clamp-1">{n.title}</div>
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span className="uppercase">{n.noteType}</span>
                      <span>•</span>
                      <span>Updated {format(new Date(n.updatedAt), "MMM d, HH:mm")}</span>
                      {n.techniqueId && (
                        <>
                          <span>•</span>
                          <span className="text-secondary">{n.techniqueId}</span>
                        </>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  );
}

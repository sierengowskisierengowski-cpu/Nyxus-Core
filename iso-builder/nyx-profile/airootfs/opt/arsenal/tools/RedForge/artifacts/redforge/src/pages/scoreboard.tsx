import { useGetMyProgress, useGetSkillRadar, useGetStreak, useListAchievements, useGetWeeklySummary } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from "recharts";
import { Target, Zap, Award, Flame, Calendar, Crosshair } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

export default function Scoreboard() {
  useDocumentTitle("Operator Scoreboard");

  const { data: progress, isLoading: progressLoading } = useGetMyProgress();
  const { data: radarData } = useGetSkillRadar();
  const { data: streak } = useGetStreak();
  const { data: achievements } = useListAchievements();
  const { data: weekly } = useGetWeeklySummary();

  const xpProgress = progress && progress.xpToNextLevel 
    ? (progress.xp / (progress.xp + progress.xpToNextLevel)) * 100 
    : 100;

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">Operator Profile</h2>
          <p className="text-sm text-muted-foreground mt-1">Performance metrics and skill evaluation.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Core Progress */}
        <Card className="md:col-span-2 border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-primary flex items-center gap-2">
              <Crosshair className="w-4 h-4" />
              Current Designation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
              <div>
                <div className="text-4xl font-bold tracking-tight text-foreground">{progress?.skillLevel || "Recruit"}</div>
                <div className="text-sm text-muted-foreground mt-1 font-mono">{progress?.xp || 0} Total XP</div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono text-primary mb-1">
                  {progress?.xpToNextLevel ? `${progress.xpToNextLevel} XP to Next Level` : "Max Level Reached"}
                </div>
                <Progress value={xpProgress} className="w-full sm:w-[200px] h-2 bg-primary/20" />
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 border-t border-primary/10">
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Missions</div>
                <div className="text-xl font-bold font-mono">{progress?.missionsCompleted || 0}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Avg Score</div>
                <div className="text-xl font-bold font-mono text-secondary">{progress?.averageScore ? `${Math.round(progress.averageScore)}%` : "—"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Fastest</div>
                <div className="text-xl font-bold font-mono">{progress?.fastestDetectionSeconds ? `${Math.floor(progress.fastestDetectionSeconds / 60)}m ${progress.fastestDetectionSeconds % 60}s` : "—"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mb-1">Top Skill</div>
                <div className="text-xl font-bold font-mono truncate">{progress?.strongestCategory || "—"}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Streak */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Flame className="w-4 h-4 text-orange-500" />
              Activity Streak
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-6">
              <div className="text-5xl font-bold text-orange-500 tracking-tighter">
                {streak?.currentStreak || 0}
              </div>
              <div className="text-xs text-muted-foreground font-mono uppercase">
                <div>Current Streak (Days)</div>
                <div className="mt-1">Best: {streak?.longestStreak || 0}</div>
              </div>
            </div>
            
            {/* Simple heatmap visualization */}
            <div className="space-y-1">
              <div className="text-[10px] text-muted-foreground uppercase tracking-widest flex justify-between">
                <span>Recent Activity</span>
              </div>
              <div className="flex gap-1 h-8 items-end">
                {streak?.days.slice(-14).map((day, i) => (
                  <div 
                    key={i} 
                    className={cn(
                      "flex-1 rounded-sm min-w-[10px]",
                      day.count > 0 ? "bg-orange-500" : "bg-muted"
                    )}
                    style={{ height: day.count > 0 ? `${Math.min(100, Math.max(30, day.count * 20))}%` : '20%' }}
                    title={`${day.date}: ${day.count} missions`}
                  />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Radar Chart */}
        <Card className="flex flex-col">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
              <Target className="w-4 h-4 text-secondary" />
              Skill Radar
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 flex items-center justify-center p-6 min-h-[300px]">
            {radarData && radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="category" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10 }} />
                  <Radar
                    name="Score"
                    dataKey="score"
                    stroke="hsl(var(--secondary))"
                    fill="hsl(var(--secondary))"
                    fillOpacity={0.4}
                  />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", fontFamily: "monospace", fontSize: "12px" }}
                    itemStyle={{ color: "hsl(var(--secondary))" }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
               <div className="text-muted-foreground font-mono text-sm">INSUFFICIENT DATA</div>
            )}
          </CardContent>
        </Card>

        {/* Weekly Summary */}
        <Card className="flex flex-col">
          <CardHeader className="border-b border-border pb-4">
            <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary" />
              Weekly Debrief
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 p-6 space-y-6">
            <div className="flex gap-8">
              <div>
                <div className="text-3xl font-bold font-mono">{weekly?.missionsThisWeek || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mt-1">Missions</div>
              </div>
              <div>
                <div className="text-3xl font-bold font-mono text-secondary">{weekly?.scoreAverage ? `${Math.round(weekly.scoreAverage)}%` : "—"}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mt-1">Avg Score</div>
              </div>
              <div>
                <div className="text-3xl font-bold font-mono">{weekly?.notesCreated || 0}</div>
                <div className="text-xs text-muted-foreground uppercase tracking-widest mt-1">Notes</div>
              </div>
            </div>

            {weekly?.focusAreas && weekly.focusAreas.length > 0 && (
              <div className="space-y-2 pt-4 border-t border-border">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-widest">Focus Areas</h4>
                <div className="flex flex-wrap gap-2">
                  {weekly.focusAreas.map(area => (
                    <span key={area} className="text-xs bg-muted px-2 py-1 rounded text-muted-foreground">{area}</span>
                  ))}
                </div>
              </div>
            )}

            {weekly?.improvementAreas && weekly.improvementAreas.length > 0 && (
              <div className="space-y-2 pt-4 border-t border-border">
                <h4 className="text-xs font-bold text-destructive uppercase tracking-widest">Needs Improvement</h4>
                <div className="flex flex-wrap gap-2">
                  {weekly.improvementAreas.map(area => (
                    <span key={area} className="text-xs bg-destructive/10 border border-destructive/20 px-2 py-1 rounded text-destructive">{area}</span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

      </div>

      {/* Achievements Grid */}
      <Card>
        <CardHeader className="border-b border-border pb-4">
          <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
            <Award className="w-4 h-4 text-yellow-500" />
            Service Medals & Achievements
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {achievements?.map((ach) => (
              <div 
                key={ach.id} 
                className={cn(
                  "p-4 border rounded flex flex-col items-center text-center gap-2 transition-all",
                  ach.unlocked ? "border-yellow-500/50 bg-yellow-500/5 shadow-[0_0_10px_rgba(234,179,8,0.1)]" : "border-border bg-muted/30 opacity-50 grayscale"
                )}
              >
                <div className="w-10 h-10 rounded-full bg-background flex items-center justify-center border border-current shadow-inner text-xl">
                  {ach.icon || "🎖️"}
                </div>
                <div className="font-bold text-xs leading-tight">{ach.name}</div>
                <div className="text-[10px] text-muted-foreground line-clamp-2">{ach.description}</div>
                {ach.unlocked && ach.unlockedAt && (
                  <div className="text-[9px] font-mono text-yellow-500/70 mt-auto pt-2">
                    {format(new Date(ach.unlockedAt), "yyyy-MM-dd")}
                  </div>
                )}
              </div>
            ))}
            {(!achievements || achievements.length === 0) && (
              <div className="col-span-full py-8 text-center text-muted-foreground font-mono text-sm">
                NO ACHIEVEMENTS DATA AVAILABLE
              </div>
            )}
          </div>
        </CardContent>
      </Card>

    </div>
  );
}

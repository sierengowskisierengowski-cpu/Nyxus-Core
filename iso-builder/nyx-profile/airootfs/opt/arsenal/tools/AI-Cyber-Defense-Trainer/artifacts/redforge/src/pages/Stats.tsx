import { useGetStatsSummary, useGetSkillRadar, useGetCategoryBreakdown } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from "recharts";
import { Activity, Target, Shield, Trophy } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function Stats() {
  const { data: summary, isLoading: isLoadingSummary } = useGetStatsSummary();
  const { data: radar, isLoading: isLoadingRadar } = useGetSkillRadar();
  const { data: breakdown, isLoading: isLoadingBreakdown } = useGetCategoryBreakdown();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">TRAINING STATS</h1>
        <p className="text-muted-foreground uppercase text-sm mt-1">Operator performance and skill metrics</p>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-primary/20 bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Trophy size={14}/> AVG DETECTION SCORE</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingSummary ? <Skeleton className="h-8 w-16" /> : (
              <div className="text-3xl font-bold text-primary">{Math.round(summary?.avgDetectionScore || 0)}%</div>
            )}
          </CardContent>
        </Card>
        <Card className="border-secondary/20 bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Shield size={14}/> AVG RESPONSE SCORE</CardTitle>
          </CardHeader>
          <CardContent>
             {isLoadingSummary ? <Skeleton className="h-8 w-16" /> : (
              <div className="text-3xl font-bold text-secondary">{Math.round(summary?.avgResponseScore || 0)}%</div>
            )}
          </CardContent>
        </Card>
        <Card className="bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Target size={14}/> SUCCESS RATE</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingSummary ? <Skeleton className="h-8 w-16" /> : (
              <div className="text-3xl font-bold">
                {summary?.totalMissions ? Math.round(((summary.completedMissions || 0) / summary.totalMissions) * 100) : 0}%
              </div>
            )}
          </CardContent>
        </Card>
        <Card className="bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs text-muted-foreground flex items-center gap-2"><Activity size={14}/> TRAINING STREAK</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoadingSummary ? <Skeleton className="h-8 w-16" /> : (
              <div className="text-3xl font-bold">{summary?.streak || 0} DAYS</div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-border">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground tracking-widest">SKILL RADAR</CardTitle>
            <CardDescription>Aggregate performance across MITRE tactic categories</CardDescription>
          </CardHeader>
          <CardContent className="h-[400px]">
            {isLoadingRadar ? (
              <Skeleton className="w-full h-full rounded-full" />
            ) : radar && radar.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radar}>
                  <PolarGrid stroke="hsl(var(--border))" />
                  <PolarAngleAxis dataKey="category" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "hsl(var(--muted-foreground))" }} stroke="none" />
                  <Radar name="Score" dataKey="score" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.2} />
                  <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", fontFamily: "monospace" }} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground font-mono text-sm">NOT ENOUGH DATA</div>
            )}
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground tracking-widest">CATEGORY MASTERY</CardTitle>
            <CardDescription>Success rates by attack vector</CardDescription>
          </CardHeader>
          <CardContent className="h-[400px]">
             {isLoadingBreakdown ? (
               <Skeleton className="w-full h-full" />
             ) : breakdown && breakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={breakdown} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: "hsl(var(--muted-foreground))" }} stroke="hsl(var(--border))" />
                  <YAxis dataKey="category" type="category" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12, fontFamily: "monospace" }} stroke="none" />
                  <Tooltip cursor={{ fill: "hsl(var(--muted))" }} contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", fontFamily: "monospace" }} />
                  <Bar dataKey="successRate" fill="hsl(var(--secondary))" radius={[0, 4, 4, 0]} name="Success %" />
                </BarChart>
              </ResponsiveContainer>
             ) : (
               <div className="h-full flex items-center justify-center text-muted-foreground font-mono text-sm">NOT ENOUGH DATA</div>
             )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

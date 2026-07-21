import { PageContainer } from "@/components/page-container";
import { useGetDashboardStats, useGetRecentCracks, useGetActiveJobs } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity, Hash, Unlock, Server, AlertTriangle, Library } from "lucide-react";
import { Progress } from "@/components/ui/progress";

export default function Dashboard() {
  const { data: stats } = useGetDashboardStats({ query: { refetchInterval: 5000, queryKey: ["getDashboardStats"] } });
  const { data: recentCracks } = useGetRecentCracks({ query: { refetchInterval: 5000, queryKey: ["getRecentCracks"] } });
  const { data: activeJobs } = useGetActiveJobs({ query: { refetchInterval: 3000, queryKey: ["getActiveJobs"] } });

  return (
    <PageContainer title="Dashboard">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <Card className="bg-card/50 backdrop-blur border-primary/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Hashes</CardTitle>
            <Hash className="w-4 h-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{stats?.totalHashes?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>
        
        <Card className="bg-card/50 backdrop-blur border-success/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Total Cracked</CardTitle>
            <Unlock className="w-4 h-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-success">{stats?.totalCracked?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Crack Rate</CardTitle>
            <Activity className="w-4 h-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{stats?.crackRate ? stats.crackRate.toFixed(1) : 0}%</div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur border-warning/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Active Jobs</CardTitle>
            <Server className="w-4 h-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-warning">{stats?.activeJobCount || 0}</div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur border-secondary/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Wordlists</CardTitle>
            <Library className="w-4 h-4 text-secondary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-secondary">{stats?.wordlistCount?.toLocaleString() || 0}</div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 backdrop-blur border-destructive/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-xs font-medium text-muted-foreground">Weak Hashes</CardTitle>
            <AlertTriangle className="w-4 h-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono text-destructive">{stats?.weakHashCount || 0}</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" /> Active Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            {activeJobs?.length ? (
              <div className="space-y-4">
                {activeJobs.map(job => (
                  <div key={job.id} className="space-y-2 border border-border/50 p-4 rounded-md bg-background/50">
                    <div className="flex justify-between text-sm">
                      <span className="font-mono text-primary">{job.name}</span>
                      <span className="font-mono text-xs text-muted-foreground">{job.speed || 0} {job.speedUnit || 'H/s'}</span>
                    </div>
                    <Progress value={job.progress || 0} className="h-2" />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{job.attackMode}</span>
                      <span>{(job.progress || 0).toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground text-sm font-mono">No active jobs running</div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Unlock className="w-4 h-4 text-success" /> Recent Cracks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentCracks?.slice(0, 5).map(crack => (
                <div key={crack.id} className="flex justify-between items-center p-2 rounded bg-background/50 border border-border/30">
                  <div className="truncate flex-1 font-mono text-sm text-foreground/80 mr-2">{crack.hash.substring(0, 16)}...</div>
                  <div className="font-mono text-sm text-success">{crack.plaintext}</div>
                </div>
              ))}
              {!recentCracks?.length && (
                <div className="text-center py-4 text-muted-foreground text-xs font-mono">No recent cracks</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}

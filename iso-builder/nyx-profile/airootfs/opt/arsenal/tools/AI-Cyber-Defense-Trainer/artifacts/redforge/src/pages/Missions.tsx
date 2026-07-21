import { useState } from "react";
import { useListMissions } from "@workspace/api-client-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Link } from "wouter";
import { Search, Filter, ShieldAlert, Target, Calendar } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function Missions() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  
  const { data: missions, isLoading } = useListMissions(
    { 
      status: statusFilter !== "all" ? statusFilter as any : undefined,
      category: categoryFilter !== "all" ? categoryFilter : undefined
    }
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-primary text-primary-foreground border-primary animate-pulse";
      case "completed": return "bg-green-500/20 text-green-500 border-green-500/50";
      case "failed": return "bg-destructive/20 text-destructive border-destructive/50";
      default: return "bg-muted text-muted-foreground border-border";
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">MISSION ARCHIVE</h1>
          <p className="text-muted-foreground uppercase text-sm mt-1">Past operations and exercise logs</p>
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <div className="relative flex-1 md:w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search missions..." className="pl-8" />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid gap-4">
        {isLoading ? (
          Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
        ) : missions?.length === 0 ? (
          <div className="text-center p-12 border border-border border-dashed rounded-lg text-muted-foreground">
            <Target className="mx-auto h-12 w-12 opacity-20 mb-4" />
            <h3 className="text-lg font-bold">NO MISSIONS FOUND</h3>
            <p className="text-sm">No operations match your current filters.</p>
          </div>
        ) : (
          missions?.map((mission) => (
            <Link key={mission.id} href={`/missions/${mission.id}`}>
              <Card className="hover:border-primary/50 transition-colors cursor-pointer group bg-card">
                <CardContent className="p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground font-mono text-xs">OP-{mission.id.toString().padStart(4, '0')}</span>
                      <Badge variant="outline" className={getStatusColor(mission.status)}>
                        {mission.status.toUpperCase()}
                      </Badge>
                      {!mission.revealed && (
                        <Badge variant="outline" className="bg-secondary/20 text-secondary border-secondary/50">
                          BLIND
                        </Badge>
                      )}
                    </div>
                    <h3 className="text-lg font-bold group-hover:text-primary transition-colors">
                      {mission.title}
                    </h3>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm font-mono text-muted-foreground">
                    <div className="flex flex-col items-end">
                      <span className="flex items-center gap-1"><ShieldAlert size={14}/> {mission.category}</span>
                      <span className="text-xs">{mission.difficulty}</span>
                    </div>
                    <div className="flex flex-col items-end pl-4 border-l border-border">
                      <span className="flex items-center gap-1"><Calendar size={14}/> {new Date(mission.createdAt).toLocaleDateString()}</span>
                      {mission.status === 'completed' && (
                        <span className="text-xs text-green-500">
                          SCORE: {((mission.detectionScore || 0) + (mission.responseScore || 0)) / 2}%
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

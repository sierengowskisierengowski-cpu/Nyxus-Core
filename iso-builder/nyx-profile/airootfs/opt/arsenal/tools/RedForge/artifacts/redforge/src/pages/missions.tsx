import { useState } from "react";
import { useListMissions } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TerminalSquare, Target, Clock, Award } from "lucide-react";
import { formatDistanceToNow, format } from "date-fns";
import { Link } from "wouter";
import { cn } from "@/lib/utils";

export default function Missions() {
  useDocumentTitle("Missions Log");
  
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const { data: missions, isLoading } = useListMissions({
    status: statusFilter !== "ALL" ? statusFilter : undefined
  });

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">Mission Logs</h2>
          <p className="text-sm text-muted-foreground mt-1">Review active and historical operations.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px] font-mono">
              <SelectValue placeholder="Filter Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="given_up">Given Up</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 border-border">
        <CardHeader className="border-b border-border bg-muted/20 py-3">
          <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
            <TerminalSquare className="w-4 h-4 text-primary" />
            Operations Record
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 overflow-auto p-0">
          {isLoading ? (
             <div className="p-8 text-center text-muted-foreground animate-pulse font-mono text-sm">ACCESSING ARCHIVES...</div>
          ) : missions?.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground border border-dashed border-border m-8 rounded-lg flex flex-col items-center gap-4">
              <TerminalSquare className="w-8 h-8 text-muted-foreground/50" />
              <p>No missions found. Deploy a scenario to begin recording.</p>
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/50 sticky top-0 z-10">
                <TableRow>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground w-12">ID</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">SCENARIO</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">STATUS</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">STARTED</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">SCORE</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground text-right">ACTION</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {missions?.map((m) => (
                  <TableRow key={m.id} className="hover:bg-muted/30 transition-colors">
                    <TableCell className="font-mono text-xs text-muted-foreground">#{m.id}</TableCell>
                    <TableCell className="font-medium">
                      {m.scenarioName}
                      <div className="text-[10px] text-muted-foreground uppercase mt-0.5">{m.category} • {m.difficulty}</div>
                    </TableCell>
                    <TableCell>
                      <span className={cn(
                        "text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider font-semibold inline-block",
                        m.status === "completed" ? "border-secondary/50 text-secondary bg-secondary/10" : 
                        m.status === "active" ? "border-primary text-primary bg-primary/20 animate-pulse" : 
                        "border-muted-foreground/50 text-muted-foreground bg-muted"
                      )}>
                        {m.status}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {format(new Date(m.startedAt), "yyyy-MM-dd HH:mm")}
                    </TableCell>
                    <TableCell>
                      {m.score !== null && m.score !== undefined ? (
                        <div className="flex items-center gap-1 font-mono text-xs">
                          <Award className="w-3 h-3 text-secondary" />
                          {m.score}%
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/missions/${m.id}`} className="text-xs font-mono text-primary hover:underline uppercase">
                        {m.status === "active" ? "Resume" : "Debrief"}
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

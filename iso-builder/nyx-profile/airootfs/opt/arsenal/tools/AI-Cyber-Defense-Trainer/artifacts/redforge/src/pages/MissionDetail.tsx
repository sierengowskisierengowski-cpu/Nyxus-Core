import { useState, useEffect, useRef } from "react";
import { useRoute } from "wouter";
import { useGetMission, useRevealMission, useScoreMission, useUpdateMissionStatus, getGetMissionQueryKey, getRevealMissionQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Terminal, ShieldAlert, AlertTriangle, Eye, Crosshair, Target, CheckCircle2, XCircle, ChevronRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function MissionDetail() {
  const [, params] = useRoute("/missions/:id");
  const id = parseInt(params?.id || "0");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: mission, isLoading } = useGetMission(id, {
    query: { enabled: !!id, queryKey: getGetMissionQueryKey(id) }
  });

  const { refetch: revealMission, isFetching: isRevealing } = useRevealMission(id, {
    query: { enabled: false, queryKey: getRevealMissionQueryKey(id) }
  });
  const { mutate: scoreMission, isPending: isScoring } = useScoreMission();
  const { mutate: updateStatus, isPending: isUpdating } = useUpdateMissionStatus();

  const [detectionScore, setDetectionScore] = useState([50]);
  const [responseScore, setResponseScore] = useState([50]);
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // Sync scores when mission loads
  useEffect(() => {
    if (mission) {
      if (mission.detectionScore !== undefined && mission.detectionScore !== null) setDetectionScore([mission.detectionScore]);
      if (mission.responseScore !== undefined && mission.responseScore !== null) setResponseScore([mission.responseScore]);
    }
  }, [mission]);

  // WebSocket for live logs — streams real honeypot / journal telemetry from
  // the backend log server (see api-server/src/lib/ws-server.ts).
  useEffect(() => {
    if (mission?.status === 'active') {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${proto}://${window.location.host}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        setLogs(prev => [...prev, event.data as string].slice(-100));
      };

      ws.onclose = () => setLogs(prev => [...prev, "[-] Stream disconnected."]);

      return () => ws.close();
    }
    return undefined;
  }, [mission?.status]);

  if (isLoading || !mission) return <div className="p-8"><Skeleton className="h-64 w-full" /></div>;

  const handleReveal = () => {
    revealMission().then(() => {
      toast({ title: "MISSION REVEALED", description: "Attack details uncovered." });
      queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(id) });
    });
  };

  const handleScore = () => {
    scoreMission({ id, data: { detectionScore: detectionScore[0], responseScore: responseScore[0] } }, {
      onSuccess: () => {
        toast({ title: "SCORES LOGGED", description: "Training metrics updated." });
        queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(id) });
      }
    });
  };

  const handleStatusUpdate = (status: 'completed' | 'failed') => {
    updateStatus({ id, data: { status } }, {
      onSuccess: () => {
        toast({ title: `MISSION ${status.toUpperCase()}`, description: "Status updated." });
        queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(id) });
      }
    });
  };

  const isActive = mission.status === 'active';
  const isCompleted = mission.status === 'completed';

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Badge variant="outline" className="font-mono text-muted-foreground border-border">OP-{mission.id}</Badge>
            <Badge variant="outline" className={isActive ? "bg-primary text-primary-foreground border-primary animate-pulse" : ""}>
              {mission.status.toUpperCase()}
            </Badge>
            <Badge variant="outline" className="border-secondary text-secondary">{mission.category}</Badge>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{mission.title}</h1>
        </div>
        {isActive && (
          <div className="flex gap-2">
            <Button variant="outline" className="border-green-500 text-green-500 hover:bg-green-500/10" onClick={() => handleStatusUpdate('completed')} disabled={isUpdating}>
              <CheckCircle2 className="mr-2" size={16} /> MITIGATED
            </Button>
            <Button variant="outline" className="border-destructive text-destructive hover:bg-destructive/10" onClick={() => handleStatusUpdate('failed')} disabled={isUpdating}>
              <XCircle className="mr-2" size={16} /> BREACHED
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details & Scoring */}
        <div className="lg:col-span-1 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm text-muted-foreground">OPERATIONAL PARAMS</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 font-mono text-sm">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">TARGET</span>
                <span className="font-bold text-primary">{mission.targetIp}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">DIFFICULTY</span>
                <span>{mission.difficulty}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">MODE</span>
                <span>{mission.mode}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">STARTED</span>
                <span>{mission.startedAt ? new Date(mission.startedAt).toLocaleString() : 'N/A'}</span>
              </div>
            </CardContent>
          </Card>

          {(isCompleted || mission.status === 'failed') && (
            <Card className="border-green-500/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-green-500"><Target size={18}/> AFTER ACTION REPORT</CardTitle>
                <CardDescription>Rate your performance in detecting and responding to this threat.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <Label>Detection Score</Label>
                    <span className="font-mono text-primary font-bold">{detectionScore[0]}%</span>
                  </div>
                  <Slider value={detectionScore} onValueChange={setDetectionScore} max={100} step={1} />
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between">
                    <Label>Response Score</Label>
                    <span className="font-mono text-secondary font-bold">{responseScore[0]}%</span>
                  </div>
                  <Slider value={responseScore} onValueChange={setResponseScore} max={100} step={1} />
                </div>
                <Button className="w-full" onClick={handleScore} disabled={isScoring}>LOG SCORES</Button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Code, MITRE & Logs */}
        <div className="lg:col-span-2 space-y-6">
          {!mission.revealed ? (
            <Card className="h-64 flex flex-col items-center justify-center border-dashed border-2 border-muted-foreground/30 bg-muted/10">
              <Eye size={48} className="text-muted-foreground mb-4 opacity-50" />
              <h3 className="text-xl font-bold tracking-widest text-muted-foreground">BLIND MISSION</h3>
              <p className="text-sm text-muted-foreground mb-6 text-center max-w-md mt-2">
                Attack details, code, and MITRE mapping are hidden to simulate a realistic response scenario.
              </p>
              <Button onClick={handleReveal} disabled={isRevealing} className="font-bold tracking-widest" variant="outline">
                <ShieldAlert className="mr-2" size={16} />
                REVEAL ATTACK VECTORS
              </Button>
            </Card>
          ) : (
            <>
              <Card className="border-border">
                <CardHeader>
                  <CardTitle className="text-sm text-muted-foreground">ATTACK PRIMITIVES & MITRE MAPPING</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {mission.mitreIds?.split(',').map(id => (
                      <Badge key={id} className="bg-secondary/20 text-secondary hover:bg-secondary/30 font-mono">
                        {id.trim()}
                      </Badge>
                    ))}
                    {!mission.mitreIds && <span className="text-muted-foreground text-sm font-mono">No specific MITRE mapping available.</span>}
                  </div>
                </CardContent>
              </Card>

              <Card className="border-border overflow-hidden">
                <CardHeader className="bg-muted border-b border-border py-3">
                  <CardTitle className="text-sm text-muted-foreground font-mono flex items-center gap-2">
                    <Terminal size={14}/> payload.sh
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <pre className="p-4 text-xs font-mono text-green-400 overflow-x-auto bg-black m-0 whitespace-pre-wrap">
                    {mission.generatedCode || "# No code generated for this mission."}
                  </pre>
                </CardContent>
              </Card>
            </>
          )}

          {isActive && (
            <Card className="border-primary shadow-[0_0_10px_rgba(239,68,68,0.1)]">
              <CardHeader className="py-3 border-b border-border">
                <CardTitle className="text-sm text-primary font-mono flex items-center gap-2">
                  <AlertTriangle size={14} className="animate-pulse" /> LIVE EXECUTION LOGS
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0 bg-black relative">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-primary animate-scan opacity-50"></div>
                <div className="h-64 overflow-y-auto p-4 font-mono text-xs text-muted-foreground flex flex-col gap-1">
                  {logs.length === 0 ? (
                    <span className="text-primary/50">Awaiting telemetry...</span>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className="flex gap-2">
                        <span className="text-primary/50 opacity-50 shrink-0"><ChevronRight size={12}/></span>
                        <span className={log.includes('[+]') ? 'text-green-500' : log.includes('[-]') ? 'text-destructive' : ''}>
                          {log}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "wouter";
import { 
  useGetMission, 
  useGetMissionDebrief,
  useUpdateInvestigation, 
  useSubmitMission, 
  useRequestHint,
  useMarkMastered,
  getGetMissionQueryKey,
  getGetMissionDebriefQueryKey,
  getGetActiveMissionQueryKey
} from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { directApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { TerminalSquare, Target, Clock, ArrowLeft, Bot, ShieldAlert, Award, FileText, Lock, ChevronRight, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { TutorSidebar } from "@/components/tutor-sidebar";
import { formatDistanceToNow, differenceInSeconds } from "date-fns";
import { cn } from "@/lib/utils";
import { Slider } from "@/components/ui/slider";
import { Progress } from "@radix-ui/react-progress";
import { ScrollArea } from "@radix-ui/react-scroll-area";

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export default function MissionWorkspace() {
  const { id } = useParams();
  const missionId = Number(id);
  useDocumentTitle(`Mission Workspace`);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: mission, isLoading: missionLoading } = useGetMission(missionId);
  const { data: debrief, isLoading: debriefLoading } = useGetMissionDebrief(missionId, { query: { enabled: mission?.status === "completed" || mission?.status === "given_up", queryKey: getGetMissionDebriefQueryKey(missionId) } });
  
  const updateInvestigation = useUpdateInvestigation();
  const submitMission = useSubmitMission();
  const requestHint = useRequestHint();
  const markMastered = useMarkMastered();

  const [tutorOpen, setTutorOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("investigation");
  
  // Investigation state
  const [notes, setNotes] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [evidence, setEvidence] = useState("");
  const initializedId = useRef<number | null>(null);

  // Submit form
  const [technique, setTechnique] = useState("");
  const [confidence, setConfidence] = useState(50);
  const [isGivingUp, setIsGivingUp] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (mission && initializedId.current !== mission.id) {
      initializedId.current = mission.id;
      setNotes(mission.notes || "");
      setHypothesis(mission.hypothesis || "");
      setEvidence(mission.evidence || "");
    }
  }, [mission]);

  // Timer
  useEffect(() => {
    if (mission?.status !== "active") return;
    
    const interval = setInterval(() => {
      setElapsedSeconds(differenceInSeconds(new Date(), new Date(mission.startedAt)));
    }, 1000);
    
    return () => clearInterval(interval);
  }, [mission]);

  const handleSaveInvestigation = () => {
    updateInvestigation.mutate({
      id: missionId,
      data: { notes, hypothesis, evidence }
    }, {
      onSuccess: () => {
        toast({ title: "Investigation Saved", description: "Progress synced to local database." });
        queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(missionId) });
      }
    });
  };

  const handleHint = () => {
    requestHint.mutate({ id: missionId }, {
      onSuccess: (data) => {
        toast({ title: "Intelligence Received", description: "Hint added to your notes." });
        setNotes(prev => prev + `\n\n> **HINT [${data.hintsUsed}]:** ${data.hint}`);
      }
    });
  };

  const handleSubmit = () => {
    if (!technique.trim()) {
      toast({ title: "Validation Error", description: "Identified technique cannot be empty.", variant: "destructive" });
      return;
    }
    submitMission.mutate({
      id: missionId,
      data: { identifiedTechnique: technique, confidence, finalNotes: notes }
    }, {
      onSuccess: () => {
        toast({ title: "Mission Completed", description: "Awaiting debrief." });
        queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(missionId) });
        queryClient.invalidateQueries({ queryKey: getGetMissionDebriefQueryKey(missionId) });
        queryClient.invalidateQueries({ queryKey: getGetActiveMissionQueryKey() });
      }
    });
  };

  const handleGiveUp = async () => {
    setIsGivingUp(true);
    try {
      await directApi.missions.giveup(missionId);
      toast({ title: "Mission Aborted", description: "Proceeding to debrief." });
      queryClient.invalidateQueries({ queryKey: getGetMissionQueryKey(missionId) });
      queryClient.invalidateQueries({ queryKey: getGetMissionDebriefQueryKey(missionId) });
      queryClient.invalidateQueries({ queryKey: getGetActiveMissionQueryKey() });
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    } finally {
      setIsGivingUp(false);
    }
  };

  const handleMastered = () => {
    markMastered.mutate({ id: missionId }, {
      onSuccess: () => toast({ title: "Status Updated", description: "Marked as mastered." })
    });
  };

  if (missionLoading) return <div className="p-8 font-mono animate-pulse">ESTABLISHING SECURE LINK...</div>;
  if (!mission) return <div className="p-8 text-destructive">MISSION NOT FOUND</div>;

  const isActive = mission.status === "active";
  const isCompleted = mission.status === "completed" || mission.status === "given_up";
  
  let timeRemaining = null;
  if (isActive && mission.timeLimitMinutes) {
    const limitSecs = mission.timeLimitMinutes * 60;
    timeRemaining = limitSecs - elapsedSeconds;
  }

  return (
    <div className="h-full flex flex-col relative overflow-hidden">
      
      {/* Top Header */}
      <div className="shrink-0 mb-4 pb-4 border-b border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link href="/missions" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-2 w-fit">
            <ArrowLeft className="w-3 h-3" />
            BACK TO LOGS
          </Link>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">OP: {mission.scenarioName}</h2>
            <span className={cn(
              "text-[10px] px-2 py-0.5 rounded border uppercase tracking-wider font-semibold",
              isActive ? "border-primary text-primary bg-primary/20 animate-pulse" : 
              mission.status === "completed" ? "border-secondary/50 text-secondary bg-secondary/10" : 
              "border-muted-foreground/50 text-muted-foreground bg-muted"
            )}>
              {mission.status}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {isActive && (
            <div className={cn(
              "flex items-center gap-2 font-mono text-xl",
              timeRemaining !== null && timeRemaining < 300 ? "text-destructive animate-pulse" : "text-foreground"
            )}>
              <Clock className="w-5 h-5" />
              {timeRemaining !== null ? (
                timeRemaining > 0 ? formatDuration(timeRemaining) : "00:00"
              ) : (
                formatDuration(elapsedSeconds)
              )}
            </div>
          )}
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setTutorOpen(true)}
            className="font-mono uppercase tracking-widest text-secondary border-secondary/50 hover:bg-secondary/10"
          >
            <Bot className="w-4 h-4 mr-2" />
            AI Tutor
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-2 pb-12 scrollbar-thin">
        {isActive ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Main Investigation Panel */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="border-primary/20 shadow-lg">
                <CardHeader className="bg-muted/10 border-b border-border py-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2 text-foreground">
                    <FileText className="w-4 h-4 text-primary" />
                    Investigation Workspace
                  </CardTitle>
                  <Button 
                    size="sm" 
                    variant="ghost" 
                    onClick={handleSaveInvestigation}
                    disabled={updateInvestigation.isPending}
                    className="h-7 text-xs font-mono"
                  >
                    Save Draft
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                    <TabsList className="w-full justify-start rounded-none border-b border-border bg-background px-4 h-12">
                      <TabsTrigger value="investigation" className="font-mono text-xs uppercase tracking-widest">Notes</TabsTrigger>
                      <TabsTrigger value="hypothesis" className="font-mono text-xs uppercase tracking-widest">Hypothesis</TabsTrigger>
                      <TabsTrigger value="evidence" className="font-mono text-xs uppercase tracking-widest">Evidence</TabsTrigger>
                    </TabsList>
                    
                    <div className="p-4 bg-muted/5">
                      <TabsContent value="investigation" className="mt-0 outline-none">
                        <Textarea 
                          placeholder="Document findings, anomalous behaviors, logs..."
                          className="min-h-[300px] font-mono text-sm border-0 focus-visible:ring-0 resize-y bg-transparent"
                          value={notes}
                          onChange={e => setNotes(e.target.value)}
                        />
                      </TabsContent>
                      <TabsContent value="hypothesis" className="mt-0 outline-none">
                        <Textarea 
                          placeholder="What do you think is happening? Who, what, when, where, why?"
                          className="min-h-[300px] font-mono text-sm border-0 focus-visible:ring-0 resize-y bg-transparent"
                          value={hypothesis}
                          onChange={e => setHypothesis(e.target.value)}
                        />
                      </TabsContent>
                      <TabsContent value="evidence" className="mt-0 outline-none">
                        <Textarea 
                          placeholder="Paste raw logs, process chains, IPs, hashes here..."
                          className="min-h-[300px] font-mono text-sm border-0 focus-visible:ring-0 resize-y bg-transparent"
                          value={evidence}
                          onChange={e => setEvidence(e.target.value)}
                        />
                      </TabsContent>
                    </div>
                  </Tabs>
                </CardContent>
              </Card>

              <div className="flex justify-between items-center bg-muted/10 p-4 border border-border rounded-md">
                <div className="text-sm font-mono text-muted-foreground flex items-center gap-2">
                  <HelpCircle className="w-4 h-4" />
                  Stuck? Request intelligence hint ({mission.hintsUsed || 0} used)
                </div>
                <Button 
                  variant="outline" 
                  onClick={handleHint}
                  disabled={requestHint.isPending}
                  className="font-mono text-xs uppercase tracking-widest"
                >
                  Request Hint
                </Button>
              </div>
            </div>

            {/* Submission Panel */}
            <div className="space-y-6">
              <Card className="border-destructive/30 shadow-[0_0_15px_rgba(239,68,68,0.05)]">
                <CardHeader className="bg-destructive/5 border-b border-destructive/20 py-4">
                  <CardTitle className="text-base uppercase tracking-widest text-destructive flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4" />
                    Action Conclusion
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
                  <div className="space-y-2">
                    <Label className="text-xs uppercase tracking-widest text-muted-foreground">Identified Technique / Threat</Label>
                    <Input 
                      placeholder="e.g. Process Injection, T1055" 
                      value={technique}
                      onChange={e => setTechnique(e.target.value)}
                      className="font-mono bg-background"
                    />
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <Label className="text-xs uppercase tracking-widest text-muted-foreground">Confidence Level</Label>
                      <span className="text-xs font-mono text-primary">{confidence}%</span>
                    </div>
                    <Slider 
                      value={[confidence]} 
                      onValueChange={v => setConfidence(v[0])} 
                      max={100} 
                      step={10} 
                    />
                  </div>

                  <div className="pt-4 flex flex-col gap-3">
                    <Button 
                      onClick={handleSubmit}
                      disabled={submitMission.isPending || !technique.trim()}
                      className="w-full font-mono uppercase tracking-widest h-12 bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_10px_rgba(239,68,68,0.3)]"
                    >
                      Submit Findings
                    </Button>
                    <Button 
                      onClick={handleGiveUp}
                      disabled={isGivingUp}
                      variant="ghost"
                      className="w-full font-mono text-xs uppercase tracking-widest text-muted-foreground hover:text-destructive"
                    >
                      Abort & Reveal Answer
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          /* DEBRIEF VIEW */
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              <Card className="md:col-span-2 border-secondary/30">
                <CardHeader className="bg-secondary/5 border-b border-secondary/20">
                  <CardTitle className="text-lg uppercase tracking-widest text-secondary flex items-center gap-2">
                    <Lock className="w-5 h-5" />
                    After-Action Report: The Ground Truth
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  {debriefLoading ? (
                    <div className="text-muted-foreground font-mono animate-pulse">DECRYPTING ARCHIVES...</div>
                  ) : debrief ? (
                    <div className="space-y-8">
                      <div>
                        <h3 className="text-sm font-bold text-foreground uppercase tracking-widest border-b border-border pb-2 mb-4">The Attack Narrative</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">{debrief.reveal.description}</p>
                      </div>

                      <div>
                        <h3 className="text-sm font-bold text-foreground uppercase tracking-widest border-b border-border pb-2 mb-4">Mechanism of Action</h3>
                        <p className="text-sm text-muted-foreground leading-relaxed mb-4">{debrief.reveal.whyItWorks}</p>
                        
                        {debrief.reveal.sourceCode && (
                          <div className="bg-background border border-border rounded-md overflow-hidden">
                            <div className="bg-muted/50 px-4 py-2 border-b border-border text-xs font-mono text-muted-foreground flex justify-between">
                              <span>Adversary Code / Command</span>
                              <span>{debrief.reveal.codeLanguage || "plaintext"}</span>
                            </div>
                            <pre className="p-4 text-xs font-mono overflow-x-auto text-primary/90">
                              <code>{debrief.reveal.sourceCode}</code>
                            </pre>
                          </div>
                        )}
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-muted/10 p-4 rounded border border-border">
                          <h4 className="text-xs font-bold text-foreground uppercase tracking-widest mb-2 flex items-center gap-2">
                            <Target className="w-4 h-4 text-primary" /> Detection Vector
                          </h4>
                          <p className="text-sm text-muted-foreground">{debrief.reveal.howToDetect}</p>
                          <div className="mt-4 pt-4 border-t border-border">
                            <span className="text-[10px] text-primary uppercase font-bold">What you should have seen:</span>
                            <p className="text-xs text-muted-foreground mt-1">{debrief.reveal.whatYouShouldHaveSeen}</p>
                          </div>
                        </div>
                        <div className="bg-muted/10 p-4 rounded border border-border">
                          <h4 className="text-xs font-bold text-foreground uppercase tracking-widest mb-2 flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4 text-secondary" /> Prevention
                          </h4>
                          <p className="text-sm text-muted-foreground">{debrief.reveal.howToPrevent}</p>
                        </div>
                      </div>
                      
                      {debrief.relatedTechniques?.length > 0 && (
                        <div>
                          <h3 className="text-sm font-bold text-foreground uppercase tracking-widest border-b border-border pb-2 mb-4">Mapped Techniques</h3>
                          <div className="flex flex-wrap gap-2">
                            {debrief.relatedTechniques.map(tech => (
                              <Link key={tech.id} href={`/kb/mitre/${tech.id}`}>
                                <Badge variant="outline" className="font-mono text-secondary border-secondary/30 hover:bg-secondary/10 cursor-pointer">
                                  {tech.id}: {tech.name}
                                </Badge>
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              <div className="space-y-6">
                <Card>
                  <CardHeader className="bg-muted/20 border-b border-border py-4">
                    <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
                      <Award className="w-4 h-4 text-primary" />
                      Performance Assessment
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-6 space-y-6">
                    {debrief?.performance ? (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground uppercase tracking-widest">Overall Score</span>
                          <span className={cn(
                            "text-3xl font-bold font-mono",
                            debrief.performance.overall >= 80 ? "text-green-500" : 
                            debrief.performance.overall >= 50 ? "text-yellow-500" : "text-destructive"
                          )}>{debrief.performance.overall}%</span>
                        </div>
                        
                        <div className="space-y-3">
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs font-mono text-muted-foreground">
                              <span>Identification</span>
                              <span>{debrief.performance.identification}%</span>
                            </div>
                            <Progress value={debrief.performance.identification} className="h-1" />
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs font-mono text-muted-foreground">
                              <span>Evidence Quality</span>
                              <span>{debrief.performance.evidenceQuality}%</span>
                            </div>
                            <Progress value={debrief.performance.evidenceQuality} className="h-1" />
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between text-xs font-mono text-muted-foreground">
                              <span>Detection Speed</span>
                              <span>{debrief.performance.detectionTime}%</span>
                            </div>
                            <Progress value={debrief.performance.detectionTime} className="h-1" />
                          </div>
                        </div>
                        
                        {debrief.performance.feedback && (
                          <div className="p-3 bg-muted/30 border border-border rounded text-xs text-muted-foreground italic">
                            "{debrief.performance.feedback}"
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-xs text-muted-foreground">Assessment not available.</div>
                    )}
                    
                    <Button 
                      onClick={handleMastered} 
                      disabled={markMastered.isPending}
                      variant="outline"
                      className="w-full font-mono uppercase tracking-widest text-xs border-primary/50 text-primary hover:bg-primary/10"
                    >
                      Mark as Mastered
                    </Button>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="bg-muted/20 border-b border-border py-4">
                    <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
                      <FileText className="w-4 h-4" />
                      Your Notes
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-4">
                    <ScrollArea className="h-64 pr-4">
                      <div className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                        {mission.notes || "No notes recorded."}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>

            </div>
          </div>
        )}
      </div>

      {tutorOpen && (
        <TutorSidebar 
          onClose={() => setTutorOpen(false)} 
          context={`Mission: ${mission.scenarioName}\nStatus: ${mission.status}\nNotes:\n${notes}\nHypothesis:\n${hypothesis}`}
        />
      )}
    </div>
  );
}

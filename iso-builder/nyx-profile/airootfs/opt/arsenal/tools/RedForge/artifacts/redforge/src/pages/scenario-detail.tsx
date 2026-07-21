import { useState } from "react";
import { useGetScenario, useDeployScenario, getGetActiveMissionQueryKey } from "@workspace/api-client-react";
import { useLocation, useParams } from "wouter";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Target, Clock, ShieldAlert, Monitor, TerminalSquare, ArrowLeft } from "lucide-react";
import { Link } from "wouter";
import ReactMarkdown from "react-markdown";

export default function ScenarioDetail() {
  const { id } = useParams();
  useDocumentTitle(`Scenario: ${id}`);
  const { toast } = useToast();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  
  const { data: scenario, isLoading } = useGetScenario(id!);
  const deployMutation = useDeployScenario();

  const [mode, setMode] = useState<"blind" | "preview">("blind");
  const [timeLimit, setTimeLimit] = useState<number | "">(scenario?.timeLimitMinutes || 60);

  const handleDeploy = () => {
    deployMutation.mutate({ 
      id: id!, 
      data: { 
        mode, 
        timeLimitMinutes: timeLimit === "" ? undefined : Number(timeLimit) 
      } 
    }, {
      onSuccess: (data: any) => {
        queryClient.invalidateQueries({ queryKey: getGetActiveMissionQueryKey() });
        toast({ title: "Mission Deployed", description: "Good luck, operator." });
        setLocation(`/missions/${data.id || data.mission?.id || ""}`); // Check actual return shape, assuming standard
      },
      onError: (err) => {
        toast({ title: "Deployment Failed", description: err.message, variant: "destructive" });
      }
    });
  };

  if (isLoading) return <div className="p-8 font-mono animate-pulse">LOADING SCENARIO DATA...</div>;
  if (!scenario) return <div className="p-8 text-destructive">SCENARIO NOT FOUND</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/scenarios" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
        <ArrowLeft className="w-3 h-3" />
        BACK TO SCENARIOS
      </Link>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Badge variant="outline" className="font-mono uppercase text-primary border-primary/20">{scenario.difficulty}</Badge>
            <Badge variant="outline" className="font-mono uppercase text-secondary border-secondary/20">{scenario.category}</Badge>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{scenario.name}</h1>
          <p className="text-muted-foreground mt-2 max-w-2xl">{scenario.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="bg-muted/20 border-b border-border py-4">
              <CardTitle className="text-sm uppercase tracking-widest text-primary flex items-center gap-2">
                <Target className="w-4 h-4" />
                Intelligence Briefing
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 prose prose-sm prose-invert max-w-none">
              <ReactMarkdown>{scenario.backstory || "No additional backstory provided."}</ReactMarkdown>
            </CardContent>
          </Card>

          <div className="grid grid-cols-2 gap-4">
            <Card>
              <CardHeader className="py-3 bg-muted/10 border-b border-border">
                <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground">Platforms</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="flex flex-wrap gap-2">
                  {scenario.platforms?.map(p => (
                    <Badge key={p} variant="secondary" className="font-mono bg-muted text-muted-foreground">{p}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="py-3 bg-muted/10 border-b border-border">
                <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground">MITRE ATT&CK</CardTitle>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="flex flex-wrap gap-2">
                  {scenario.mitreTechniques?.map(t => (
                    <Badge key={t} variant="outline" className="font-mono border-secondary/30 text-secondary">{t}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="space-y-6">
          <Card className="border-primary/30 shadow-[0_0_15px_rgba(239,68,68,0.05)]">
            <CardHeader className="bg-primary/5 border-b border-primary/20">
              <CardTitle className="text-base uppercase tracking-widest text-primary flex items-center gap-2">
                <TerminalSquare className="w-4 h-4" />
                Mission Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-6">
              
              <div className="space-y-3">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground">Deployment Mode</Label>
                <RadioGroup value={mode} onValueChange={(v: any) => setMode(v)}>
                  <div className="flex items-center space-x-2 border border-border p-3 rounded-md cursor-pointer hover:bg-muted/20">
                    <RadioGroupItem value="blind" id="r-blind" />
                    <Label htmlFor="r-blind" className="cursor-pointer">
                      <div className="font-bold">Blind (Recommended)</div>
                      <div className="text-xs text-muted-foreground">Investigate with no prior knowledge of the exact technique.</div>
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2 border border-border p-3 rounded-md cursor-pointer hover:bg-muted/20">
                    <RadioGroupItem value="preview" id="r-preview" />
                    <Label htmlFor="r-preview" className="cursor-pointer">
                      <div className="font-bold">Guided Preview</div>
                      <div className="text-xs text-muted-foreground">See the technique and objective beforehand. Good for practice.</div>
                    </Label>
                  </div>
                </RadioGroup>
              </div>

              <div className="space-y-3">
                <Label className="text-xs uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                  <Clock className="w-3 h-3" /> Time Limit (Minutes)
                </Label>
                <Input 
                  type="number" 
                  value={timeLimit} 
                  onChange={(e) => setTimeLimit(e.target.value === "" ? "" : Number(e.target.value))} 
                  className="font-mono bg-background"
                  placeholder="No limit"
                />
              </div>

              <Button 
                onClick={handleDeploy} 
                disabled={deployMutation.isPending}
                className="w-full font-mono uppercase tracking-widest h-12 bg-primary hover:bg-primary/90 text-primary-foreground shadow-[0_0_10px_rgba(239,68,68,0.3)]"
              >
                {deployMutation.isPending ? "INITIALIZING..." : "DEPLOY MISSION"}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

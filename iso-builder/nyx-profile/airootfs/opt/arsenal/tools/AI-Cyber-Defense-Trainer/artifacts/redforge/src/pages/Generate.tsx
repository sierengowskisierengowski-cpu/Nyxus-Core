import { useState } from "react";
import { useGenerateMission } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useLocation } from "wouter";
import { Crosshair, Zap, BrainCircuit, Terminal } from "lucide-react";

export default function Generate() {
  const [mode, setMode] = useState<"random" | "specify">("random");
  const { mutate: generateMission, isPending } = useGenerateMission();
  const { toast } = useToast();
  const [, setLocation] = useLocation();

  // Random attack state
  const [difficulty, setDifficulty] = useState("Unknown");
  const [categories, setCategories] = useState<string[]>([]);
  const [blindMode, setBlindMode] = useState(true);

  // Specify attack state
  const [prompt, setPrompt] = useState("");
  const [generationMode, setGenerationMode] = useState("hybrid");

  const availableCategories = ["WiFi", "Web", "Network", "Malware", "Social", "Physical", "Mixed"];

  const handleGenerate = () => {
    const payload: any = {
      mode: mode === "random" ? "template" : generationMode,
      blind: blindMode
    };

    if (mode === "random") {
      payload.difficulty = difficulty;
      if (categories.length > 0) {
        payload.category = categories[Math.floor(Math.random() * categories.length)]; // simplified category selection
      }
    } else {
      payload.prompt = prompt;
    }

    generateMission(
      { data: payload },
      {
        onSuccess: (mission) => {
          toast({
            title: "MISSION DEPLOYED",
            description: `Attack ${mission.id} initialized.`,
            variant: "destructive",
          });
          setLocation(`/missions/${mission.id}`);
        },
        onError: (err: any) => {
          toast({
            title: "DEPLOYMENT FAILED",
            description: err.message,
            variant: "destructive",
          });
        }
      }
    );
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">ATTACK GENERATOR</h1>
        <p className="text-muted-foreground uppercase text-sm mt-1">Configure and deploy emulation scenarios</p>
      </div>

      <Tabs value={mode} onValueChange={(v) => setMode(v as any)} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="random" className="font-bold tracking-wider">RANDOM SCENARIO</TabsTrigger>
          <TabsTrigger value="specify" className="font-bold tracking-wider">SPECIFY ATTACK</TabsTrigger>
        </TabsList>
        
        <TabsContent value="random" className="space-y-4 mt-4">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="text-primary" />
                BLIND RANDOM EMULATION
              </CardTitle>
              <CardDescription>Generate an unexpected attack scenario to test incident response readiness.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label>DIFFICULTY LEVEL</Label>
                <Select value={difficulty} onValueChange={setDifficulty}>
                  <SelectTrigger className="font-mono">
                    <SelectValue placeholder="Select difficulty" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Unknown">Unknown (Surprise Me)</SelectItem>
                    <SelectItem value="Beginner">Beginner</SelectItem>
                    <SelectItem value="Intermediate">Intermediate</SelectItem>
                    <SelectItem value="Advanced">Advanced</SelectItem>
                    <SelectItem value="Expert">Expert</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-3">
                <Label>ALLOWED CATEGORIES</Label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {availableCategories.map((cat) => (
                    <div key={cat} className="flex items-center space-x-2">
                      <Checkbox 
                        id={`cat-${cat}`}
                        checked={categories.includes(cat)}
                        onCheckedChange={(checked) => {
                          if (checked) setCategories([...categories, cat]);
                          else setCategories(categories.filter(c => c !== cat));
                        }}
                      />
                      <label htmlFor={`cat-${cat}`} className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                        {cat}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center space-x-2 pt-4 border-t border-border">
                <Switch 
                  id="blind-mode" 
                  checked={blindMode} 
                  onCheckedChange={setBlindMode} 
                />
                <Label htmlFor="blind-mode" className="font-bold">BLIND MODE</Label>
                <span className="text-xs text-muted-foreground ml-2">(Hides attack details until revealed)</span>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="specify" className="space-y-4 mt-4">
          <Card className="border-border">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="text-primary" />
                CUSTOM ATTACK PROMPT
              </CardTitle>
              <CardDescription>Use natural language to specify exact TTPs or attack paths.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label>SCENARIO PROMPT</Label>
                <Textarea 
                  placeholder="e.g. Simulate an insider threat deploying a reverse shell via a scheduled task, then attempting lateral movement using pass-the-hash."
                  className="min-h-[150px] font-mono text-sm"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
              </div>

              <div className="space-y-3">
                <Label>GENERATION ENGINE</Label>
                <Select value={generationMode} onValueChange={setGenerationMode}>
                  <SelectTrigger className="font-mono">
                    <SelectValue placeholder="Select engine" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="template">Template Matching</SelectItem>
                    <SelectItem value="claude">Claude AI (Generative)</SelectItem>
                    <SelectItem value="hybrid">Hybrid (AI + Templates)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center space-x-2 pt-4 border-t border-border">
                <Switch 
                  id="blind-mode-specify" 
                  checked={blindMode} 
                  onCheckedChange={setBlindMode} 
                />
                <Label htmlFor="blind-mode-specify" className="font-bold">BLIND MODE</Label>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Button 
        size="lg" 
        className="w-full h-16 text-xl font-bold tracking-widest bg-primary hover:bg-primary/90 text-primary-foreground relative overflow-hidden group"
        onClick={handleGenerate}
        disabled={isPending}
      >
        <span className="relative z-10 flex items-center gap-3">
          <Crosshair className={isPending ? "animate-spin" : ""} />
          {isPending ? "INITIALIZING DEPLOYMENT..." : "GENERATE & DEPLOY ATTACK"}
        </span>
        <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
      </Button>
    </div>
  );
}

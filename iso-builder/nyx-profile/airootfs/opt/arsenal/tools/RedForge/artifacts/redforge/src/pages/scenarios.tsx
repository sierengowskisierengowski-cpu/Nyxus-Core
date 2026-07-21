import { useState } from "react";
import { useListScenarios, useDeployRandomScenario, getGetActiveMissionQueryKey } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Target, Search, Filter, Shuffle, ArrowRight } from "lucide-react";
import { Link, useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";

export default function Scenarios() {
  useDocumentTitle("Scenarios");
  const { toast } = useToast();
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  
  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState<string>("ALL");
  const [category, setCategory] = useState<string>("ALL");

  const { data: scenarios, isLoading } = useListScenarios({
    search: search || undefined,
    difficulty: difficulty !== "ALL" ? difficulty : undefined,
    category: category !== "ALL" ? category : undefined,
  });

  const deployRandomMutation = useDeployRandomScenario();

  const handleRandomScenario = () => {
    deployRandomMutation.mutate({ data: { difficulty: "Medium" } }, {
      onSuccess: (data) => {
        queryClient.invalidateQueries({ queryKey: getGetActiveMissionQueryKey() });
        toast({ title: "Random Scenario Deployed", description: `Mission started.` });
        setLocation(`/missions/${data.id}`);
      },
      onError: (err) => {
        toast({ title: "Deployment Failed", description: err.message, variant: "destructive" });
      }
    });
  };

  const getDifficultyColor = (diff: string) => {
    switch (diff?.toLowerCase()) {
      case 'easy': return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'hard': return 'bg-primary/10 text-primary border-primary/20';
      default: return 'bg-muted text-muted-foreground border-border';
    }
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">Scenarios Library</h2>
          <p className="text-sm text-muted-foreground mt-1">Curated detection and response simulations.</p>
        </div>
        <Button 
          onClick={handleRandomScenario} 
          disabled={deployRandomMutation.isPending}
          variant="outline"
          className="font-mono tracking-widest uppercase gap-2 border-primary/50 text-primary hover:bg-primary/10"
        >
          <Shuffle className="w-4 h-4" />
          {deployRandomMutation.isPending ? "Deploying..." : "Random Encounter"}
        </Button>
      </div>

      <Card className="shrink-0 border-border">
        <CardContent className="p-4 flex flex-col md:flex-row gap-4 items-center bg-muted/10">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input 
              placeholder="Search scenarios..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 font-mono bg-background"
            />
          </div>
          <div className="flex items-center gap-2 w-full md:w-auto">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <Select value={difficulty} onValueChange={setDifficulty}>
              <SelectTrigger className="w-[140px] font-mono">
                <SelectValue placeholder="Difficulty" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Difficulties</SelectItem>
                <SelectItem value="Easy">Easy</SelectItem>
                <SelectItem value="Medium">Medium</SelectItem>
                <SelectItem value="Hard">Hard</SelectItem>
              </SelectContent>
            </Select>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-[140px] font-mono">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Categories</SelectItem>
                <SelectItem value="Endpoint">Endpoint</SelectItem>
                <SelectItem value="Network">Network</SelectItem>
                <SelectItem value="Cloud">Cloud</SelectItem>
                <SelectItem value="Identity">Identity</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-muted-foreground font-mono animate-pulse">
            LOADING SCENARIOS...
          </div>
        ) : scenarios?.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 border border-dashed border-border rounded-lg text-muted-foreground">
            <Target className="w-8 h-8 mb-4 opacity-50" />
            <p>No scenarios found matching your criteria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {scenarios?.map((scenario) => (
              <Link key={scenario.id} href={`/scenarios/${scenario.id}`}>
                <Card className="h-full hover:border-primary/50 hover:bg-muted/10 transition-colors cursor-pointer flex flex-col group">
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start mb-2">
                      <Badge variant="outline" className={`font-mono text-[10px] uppercase tracking-wider ${getDifficultyColor(scenario.difficulty)}`}>
                        {scenario.difficulty}
                      </Badge>
                      <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wider text-secondary border-secondary/20">
                        {scenario.category}
                      </Badge>
                    </div>
                    <CardTitle className="text-base font-bold group-hover:text-primary transition-colors">{scenario.name}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <p className="text-sm text-muted-foreground line-clamp-3 mb-4 flex-1">
                      {scenario.description}
                    </p>
                    <div className="flex items-center justify-between mt-auto pt-4 border-t border-border">
                      <div className="flex gap-1 overflow-hidden">
                        {scenario.mitreTechniques?.slice(0, 3).map(tech => (
                          <span key={tech} className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-mono">
                            {tech}
                          </span>
                        ))}
                        {(scenario.mitreTechniques?.length || 0) > 3 && (
                          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground font-mono">
                            +{(scenario.mitreTechniques?.length || 0) - 3}
                          </span>
                        )}
                      </div>
                      <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

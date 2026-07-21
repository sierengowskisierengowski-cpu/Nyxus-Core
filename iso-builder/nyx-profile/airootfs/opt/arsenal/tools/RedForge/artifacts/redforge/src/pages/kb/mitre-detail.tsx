import { useState } from "react";
import { useGetMitreTechnique, useTutorQuiz } from "@workspace/api-client-react";
import { useLocation, useParams } from "wouter";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Shield, ArrowLeft, ExternalLink, Bot, Crosshair, Target } from "lucide-react";
import { Link } from "wouter";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { useToast } from "@/hooks/use-toast";

export default function MitreTechniqueDetail() {
  const { id } = useParams();
  useDocumentTitle(`MITRE: ${id}`);
  const { toast } = useToast();
  
  const { data: tech, isLoading } = useGetMitreTechnique(id!);
  const quizMutation = useTutorQuiz();

  const [quizQuestions, setQuizQuestions] = useState<any[] | null>(null);
  const [showAnswers, setShowAnswers] = useState(false);

  const handleQuiz = () => {
    quizMutation.mutate({ data: { topic: tech!.name, techniqueId: id, count: 3 } }, {
      onSuccess: (res) => {
        setQuizQuestions(res.questions);
        setShowAnswers(false);
      },
      onError: (err) => toast({ title: "Error", description: "Failed to generate quiz.", variant: "destructive" })
    });
  };

  if (isLoading) return <div className="p-8 font-mono animate-pulse">RETRIEVING INTELLIGENCE...</div>;
  if (!tech) return <div className="p-8 text-destructive">TECHNIQUE NOT FOUND</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/kb/mitre" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
        <ArrowLeft className="w-3 h-3" />
        BACK TO MITRE MATRIX
      </Link>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="font-mono text-xl font-bold text-blue-500">{tech.id}</span>
            <span className="text-muted-foreground px-2 py-0.5 border border-border rounded text-xs uppercase tracking-widest">
              Technique
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{tech.name}</h1>
          <div className="flex flex-wrap gap-2 mt-4">
            {tech.tactics.map(t => (
              <Badge key={t} variant="secondary" className="font-mono text-[10px] uppercase tracking-widest">{t}</Badge>
            ))}
          </div>
        </div>
        <Button 
          onClick={handleQuiz} 
          disabled={quizMutation.isPending}
          variant="outline"
          className="shrink-0 font-mono tracking-widest uppercase border-blue-500/50 text-blue-500 hover:bg-blue-500/10 gap-2"
        >
          <Bot className="w-4 h-4" />
          {quizMutation.isPending ? "GENERATING..." : "QUIZ ME ON THIS"}
        </Button>
      </div>

      {quizQuestions && (
        <Card className="border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)] bg-blue-500/5 mb-8">
          <CardHeader className="border-b border-blue-500/20 pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-widest text-blue-500 flex items-center gap-2">
              <Crosshair className="w-4 h-4" /> AI Knowledge Check
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            <div className="space-y-4">
              {quizQuestions.map((q, i) => (
                <div key={i} className="p-4 bg-background border border-border rounded">
                  <div className="font-bold text-sm mb-2 text-foreground flex gap-2">
                    <span className="text-muted-foreground font-mono">0{i+1}</span> {q.question}
                  </div>
                  {showAnswers && (
                    <div className="mt-3 pt-3 border-t border-border text-sm text-muted-foreground font-mono bg-muted/30 p-2 rounded">
                      <span className="text-primary font-bold block mb-1">ANSWER:</span>
                      {q.answer}
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-center">
              <Button 
                onClick={() => setShowAnswers(!showAnswers)} 
                className="font-mono uppercase tracking-widest text-xs"
              >
                {showAnswers ? "HIDE ANSWERS" : "REVEAL ANSWERS"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="prose prose-sm prose-invert max-w-none mb-8 bg-card p-6 border border-border rounded-lg">
        <MarkdownRenderer content={tech.description || "No description provided."} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="bg-muted/10 border-b border-border py-3">
            <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              Detection Guidance
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
             <MarkdownRenderer content={tech.detection || "No detection guidance provided."} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="bg-muted/10 border-b border-border py-3">
            <CardTitle className="text-sm uppercase tracking-widest flex items-center gap-2">
              <Shield className="w-4 h-4 text-secondary" />
              Mitigation Strategies
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
             <MarkdownRenderer content={tech.mitigation || "No mitigation guidance provided."} />
          </CardContent>
        </Card>
      </div>

      {tech.subTechniques && tech.subTechniques.length > 0 && (
        <div className="pt-8">
          <h3 className="text-sm font-bold uppercase tracking-widest border-b border-border pb-2 mb-4">Sub-Techniques</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tech.subTechniques.map(sub => (
              <Link key={sub.id} href={`/kb/mitre/${sub.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer bg-muted/5">
                  <CardContent className="p-4">
                    <div className="font-mono text-primary font-bold text-xs mb-1">{sub.id}</div>
                    <div className="font-semibold text-sm line-clamp-1">{sub.name}</div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      )}

      {tech.references && tech.references.length > 0 && (
        <div className="pt-8">
          <h3 className="text-sm font-bold uppercase tracking-widest border-b border-border pb-2 mb-4">External Intelligence</h3>
          <ul className="space-y-2">
            {tech.references.map((ref, i) => (
              <li key={i}>
                <a href={ref.url} target="_blank" rel="noreferrer" className="text-sm text-secondary hover:underline flex items-center gap-1 w-fit">
                  <ExternalLink className="w-3 h-3" />
                  {ref.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

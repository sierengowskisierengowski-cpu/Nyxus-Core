import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ShieldAlert, CheckCircle, AlertTriangle, ShieldX } from "lucide-react";
import { useState } from "react";
import { useAnalyzePassword } from "@workspace/api-client-react";
import type { PasswordAnalysis } from "@workspace/api-client-react";

export default function Analyzer() {
  const [password, setPassword] = useState("");
  const analyzeMutation = useAnalyzePassword();
  const [result, setResult] = useState<PasswordAnalysis | null>(null);

  const handleAnalyze = () => {
    if (!password) {
      setResult(null);
      return;
    }
    analyzeMutation.mutate({ data: { password } }, {
      onSuccess: (data) => setResult(data)
    });
  };

  const strengthColor =
    result && result.strengthScore > 80 ? "text-success" :
    result && result.strengthScore > 50 ? "text-warning" : "text-destructive";

  const progressStyle =
    result && result.strengthScore > 80 ? "bg-success" :
    result && result.strengthScore > 50 ? "bg-warning" : "bg-destructive";

  return (
    <PageContainer title="Password Strength Analyzer">
      <Card className="bg-card/50 border-border/50 max-w-3xl mx-auto">
        <CardHeader className="text-center pb-2">
          <ShieldAlert className="w-12 h-12 text-primary mx-auto mb-4" />
          <CardTitle className="font-mono text-xl">Deep Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex gap-2">
            <Input
              type="text"
              className="font-mono text-lg h-12 bg-background/80 border-primary/30 focus-visible:ring-primary"
              placeholder="Enter password to analyze..."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
            />
            <Button onClick={handleAnalyze} className="h-12 px-8 font-mono uppercase" disabled={analyzeMutation.isPending}>
              Analyze
            </Button>
          </div>

          {result && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-background/50 p-4 rounded-md border border-border/50 text-center">
                  <div className="text-4xl font-mono font-bold text-primary mb-1">{result.entropyBits}</div>
                  <div className="text-xs font-mono uppercase text-muted-foreground">Bits of Entropy</div>
                </div>
                <div className="bg-background/50 p-4 rounded-md border border-border/50 flex flex-col justify-center items-center gap-3">
                  <div className={`text-2xl font-mono font-bold uppercase ${strengthColor}`}>
                    {result.strengthLabel.replace('_', ' ')}
                  </div>
                  <div className="w-full max-w-[200px] h-2 bg-background rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 rounded-full ${progressStyle}`}
                      style={{ width: `${result.strengthScore}%` }}
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-3">
                  <h4 className="font-mono text-xs uppercase text-muted-foreground border-b border-border/50 pb-1">Characteristics</h4>
                  <ul className="space-y-2 font-mono text-sm">
                    <li className="flex items-center gap-2">
                      {result.dictionaryWordDetected ? <ShieldX className="text-destructive w-4 h-4"/> : <CheckCircle className="text-success w-4 h-4"/>}
                      {result.dictionaryWordDetected ? "Dictionary word detected" : "No dictionary words"}
                    </li>
                    <li className="flex items-center gap-2">
                      {result.previouslyInDatabase ? <ShieldX className="text-destructive w-4 h-4"/> : <CheckCircle className="text-success w-4 h-4"/>}
                      {result.previouslyInDatabase ? "Found in breached database" : "Not found in breaches"}
                    </li>
                    <li className="flex items-center gap-2">
                      {result.patternDetected ? <AlertTriangle className="text-warning w-4 h-4"/> : <CheckCircle className="text-success w-4 h-4"/>}
                      {result.patternDetected ? `Pattern: ${result.patternDetected}` : "No predictable pattern"}
                    </li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <h4 className="font-mono text-xs uppercase text-muted-foreground border-b border-border/50 pb-1">Estimated Crack Time</h4>
                  <div className="space-y-2">
                    {result.crackTimeEstimates.map((est, i) => (
                      <div key={i} className="flex justify-between font-mono text-xs p-2 bg-card rounded border border-border/30">
                        <span className="text-muted-foreground">{est.hardware}</span>
                        <span className="text-primary">{est.estimatedTime}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {result.weaknesses && result.weaknesses.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-mono text-xs uppercase text-muted-foreground border-b border-border/50 pb-1">Identified Weaknesses</h4>
                  <ul className="space-y-1">
                    {result.weaknesses.map((w, i) => (
                      <li key={i} className="flex items-center gap-2 font-mono text-xs text-destructive">
                        <AlertTriangle className="w-3 h-3 shrink-0" /> {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}

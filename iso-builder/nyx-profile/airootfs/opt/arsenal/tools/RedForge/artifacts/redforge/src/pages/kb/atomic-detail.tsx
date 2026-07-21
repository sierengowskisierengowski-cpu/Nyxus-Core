import { useGetAtomicTest } from "@workspace/api-client-react";
import { useParams } from "wouter";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Zap, TerminalSquare } from "lucide-react";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";

export default function AtomicTestDetail() {
  const { id } = useParams();
  useDocumentTitle(`Atomic: ${id}`);
  const { data: item, isLoading } = useGetAtomicTest(id!);

  if (isLoading) return <div className="p-8 font-mono animate-pulse">RETRIEVING TEST INTEL...</div>;
  if (!item) return <div className="p-8 text-destructive">TEST NOT FOUND</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/kb/atomic" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
        <ArrowLeft className="w-3 h-3" />
        BACK TO ATOMIC RED TEAM
      </Link>

      <div>
        <div className="flex items-center gap-3 mb-2">
          <Zap className="w-6 h-6 text-yellow-500" />
          <h1 className="text-3xl font-bold tracking-tight text-foreground">{item.name}</h1>
        </div>
        <div className="flex items-center gap-3 mt-4">
          <Badge className="font-mono bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30">{item.id}</Badge>
          <Link href={`/kb/mitre/${item.techniqueId}`}>
            <Badge variant="outline" className="font-mono border-secondary/30 text-secondary cursor-pointer hover:bg-secondary/10">
              {item.techniqueId} - {item.techniqueName}
            </Badge>
          </Link>
        </div>
      </div>

      {item.description && (
        <Card className="bg-card">
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6">
        <Card className="border-yellow-500/20 shadow-[0_0_15px_rgba(234,179,8,0.05)] bg-yellow-500/5">
          <CardHeader className="py-3 border-b border-yellow-500/10">
            <CardTitle className="text-sm font-mono text-yellow-500 flex items-center gap-2">
              <TerminalSquare className="w-4 h-4" /> Execution Command ({item.executor})
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="bg-background border border-border rounded p-4 overflow-x-auto">
              <code className="font-mono text-xs text-primary whitespace-pre-wrap">{item.command || "N/A"}</code>
            </div>
          </CardContent>
        </Card>

        {item.cleanupCommand && (
          <Card className="border-border">
            <CardHeader className="py-3 border-b border-border bg-muted/10">
              <CardTitle className="text-sm font-mono text-muted-foreground">Cleanup Command</CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="bg-background border border-border rounded p-4 overflow-x-auto">
                <code className="font-mono text-xs text-muted-foreground whitespace-pre-wrap">{item.cleanupCommand}</code>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

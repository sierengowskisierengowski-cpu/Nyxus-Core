import { useGetGtfobinsEntry } from "@workspace/api-client-react";
import { useParams } from "wouter";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Terminal, Code2 } from "lucide-react";
import { Link } from "wouter";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { Badge } from "@/components/ui/badge";

export default function GtfobinsDetail() {
  const { name } = useParams();
  useDocumentTitle(`GTFOBins: ${name}`);
  const { data: item, isLoading } = useGetGtfobinsEntry(name!);

  if (isLoading) return <div className="p-8 font-mono animate-pulse">RETRIEVING BINARY INTEL...</div>;
  if (!item) return <div className="p-8 text-destructive">ENTRY NOT FOUND</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/kb/gtfobins" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
        <ArrowLeft className="w-3 h-3" />
        BACK TO GTFOBINS
      </Link>

      <div>
        <div className="flex items-center gap-3 mb-2">
          <Terminal className="w-6 h-6 text-purple-500" />
          <h1 className="text-3xl font-bold font-mono text-purple-500">{item.name}</h1>
        </div>
        <p className="text-muted-foreground text-lg">{item.summary}</p>
        <div className="flex flex-wrap gap-2 mt-4">
          {item.tags?.map(t => (
            <Badge key={t} variant="outline" className="font-mono text-[10px] tracking-widest border-purple-500/30 text-purple-500">{t}</Badge>
          ))}
        </div>
      </div>

      {item.description && (
        <Card className="bg-card">
          <CardContent className="pt-6">
            <MarkdownRenderer content={item.description} />
          </CardContent>
        </Card>
      )}

      {item.examples && item.examples.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-widest border-b border-border pb-2">Exploitation Vectors</h3>
          {item.examples.map((ex, i) => (
            <Card key={i} className="border-purple-500/20 bg-purple-500/5">
              <CardHeader className="py-3 border-b border-purple-500/10">
                <CardTitle className="text-sm font-mono text-purple-500 flex items-center gap-2">
                  <Code2 className="w-4 h-4" /> {ex.label}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {ex.description && <p className="text-sm text-muted-foreground">{ex.description}</p>}
                <div className="bg-background border border-border rounded p-4 overflow-x-auto">
                  <code className="font-mono text-xs text-primary">{ex.code}</code>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

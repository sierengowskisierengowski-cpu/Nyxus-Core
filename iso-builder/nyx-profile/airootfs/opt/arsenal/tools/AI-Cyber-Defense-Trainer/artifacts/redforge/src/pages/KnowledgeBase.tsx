import { useGetKnowledgeBaseStatus } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { ShieldAlert, Database, Terminal, CheckCircle2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

export default function KnowledgeBase() {
  const { data: kb, isLoading } = useGetKnowledgeBaseStatus();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">KNOWLEDGE BASE</h1>
        <p className="text-muted-foreground uppercase text-sm mt-1">MITRE ATT&CK framework integration status</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-1 border-border bg-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="text-secondary" />
              SYSTEM STATUS
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {isLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <>
                <div className="space-y-2">
                  <div className={`flex items-center gap-2 font-bold font-mono ${kb?.loaded ? 'text-green-500' : 'text-destructive'}`}>
                    <CheckCircle2 size={16}/> {kb?.loaded ? 'DATASET LOADED' : 'DATASET MISSING'}
                  </div>
                  <p className="text-sm text-muted-foreground">Techniques and tactics distilled from the official MITRE ATT&CK Enterprise STIX dataset.</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 border-t border-border pt-4">
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">TOTAL TTPs</div>
                    <div className="text-2xl font-bold font-mono text-primary">{kb?.totalTechniques || 0}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground mb-1">LAST SYNC</div>
                    <div className="text-sm font-mono mt-1">
                      {kb?.lastUpdated ? new Date(kb.lastUpdated).toLocaleDateString() : 'N/A'}
                    </div>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2 border-border">
          <CardHeader>
            <CardTitle className="text-sm text-muted-foreground">TACTIC CATEGORIES INDEX</CardTitle>
            <CardDescription>Number of ATT&CK techniques &amp; sub-techniques per tactic.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="grid grid-cols-2 gap-4"><Skeleton className="h-12" /><Skeleton className="h-12" /><Skeleton className="h-12" /></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(kb?.categories || {}).map(([category, count]) => (
                  <div key={category} className="flex justify-between items-center p-3 bg-muted/30 border border-border rounded">
                    <span className="font-mono text-sm tracking-tight">{category.toUpperCase()}</span>
                    <span className="font-mono font-bold text-secondary">{count as number}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-border bg-black">
        <CardHeader className="border-b border-border py-3">
           <CardTitle className="text-sm font-mono text-muted-foreground flex items-center gap-2">
             <Terminal size={14}/> SYSTEM CONFIG
           </CardTitle>
        </CardHeader>
        <CardContent className="p-4 font-mono text-xs text-muted-foreground space-y-2">
          <div>$ cat /etc/redforge/kb.conf</div>
          <div className="text-green-500">
            SOURCE="mitre-attack-enterprise (STIX)"<br/>
            MATRIX="enterprise"<br/>
            TOTAL_TECHNIQUES={kb?.totalTechniques ?? 0}<br/>
            LAST_BUILD="{kb?.lastUpdated ? new Date(kb.lastUpdated).toISOString() : 'N/A'}"
          </div>
          <div className="mt-4 text-primary/70">
            // Distilled from the official MITRE ATT&CK STIX bundle via scripts/build-mitre-dataset.
            // Regenerate with: pnpm --filter @workspace/scripts run build-mitre
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useListRules } from "@workspace/api-client-react";
import { Braces, Lock } from "lucide-react";

export default function Rules() {
  const { data: rules } = useListRules();

  return (
    <PageContainer title="Rules Library">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          {rules?.map(rule => (
            <Card key={rule.id} className="bg-card/50 border-border/50 cursor-pointer hover:border-primary/50 transition-colors">
              <CardHeader className="py-3 px-4">
                <div className="flex justify-between items-center">
                  <CardTitle className="text-sm font-mono text-primary flex items-center gap-2">
                    <Braces className="w-4 h-4" /> {rule.name}
                  </CardTitle>
                  {rule.isBuiltin && <Lock className="w-3 h-3 text-muted-foreground" />}
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-3 pt-0">
                <div className="flex justify-between items-center mt-2">
                  <Badge variant="outline" className="text-[10px] font-mono border-secondary/50 text-secondary">{rule.format}</Badge>
                  <span className="text-xs font-mono text-muted-foreground">{rule.ruleCount} rules</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        
        <div className="lg:col-span-2">
          <Card className="bg-card/50 border-border/50 h-full min-h-[500px] flex flex-col">
            <CardHeader className="border-b border-border/50 bg-background/30">
              <CardTitle className="text-sm font-mono">Rule Editor</CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1 bg-black">
              <textarea 
                className="w-full h-full bg-transparent text-primary font-mono text-sm p-4 resize-none focus:outline-none focus:ring-0"
                defaultValue={":\nc\nl\nu\nr\nd\n$1\n$2\n$3\n$!"}
                spellCheck={false}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

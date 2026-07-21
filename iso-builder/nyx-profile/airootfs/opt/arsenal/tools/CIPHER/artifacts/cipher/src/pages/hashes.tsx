import { useState } from "react";
import { PageContainer } from "@/components/page-container";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Hash as HashIcon, Fingerprint, Plus, Trash2, Search, Loader2 } from "lucide-react";
import { 
  useSubmitHashes, 
  useIdentifyHash, 
  useListHashes, 
  useGetHashStats, 
  useGenerateHash,
  getListHashesQueryKey
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";

export default function Hashes() {
  const [hashesText, setHashesText] = useState("");
  const [hashLabel, setHashLabel] = useState("");
  const [hashSource, setHashSource] = useState("");
  const [autoDetect, setAutoDetect] = useState(true);
  const [identification, setIdentification] = useState<any>(null);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  const submitHashesMutation = useSubmitHashes();
  const identifyMutation = useIdentifyHash();
  
  const { data: hashesData, isLoading: isLoadingHashes } = useListHashes();
  const { data: statsData } = useGetHashStats();

  const handleBlur = () => {
    if (!autoDetect || !hashesText.trim()) return;
    const firstHash = hashesText.split('\n')[0].trim();
    if (firstHash) {
      identifyMutation.mutate({ data: { hash: firstHash } }, {
        onSuccess: (data) => setIdentification(data),
        onError: () => setIdentification(null)
      });
    }
  };

  const handleSubmit = () => {
    const hashList = hashesText.split('\n').map(h => h.trim()).filter(h => h);
    if (!hashList.length) return;

    submitHashesMutation.mutate({ 
      data: { 
        hashes: hashList,
        label: hashLabel || undefined,
        source: hashSource || undefined
      } 
    }, {
      onSuccess: () => {
        toast({ title: "Hashes submitted successfully" });
        setHashesText("");
        setHashLabel("");
        setHashSource("");
        setIdentification(null);
        queryClient.invalidateQueries({ queryKey: getListHashesQueryKey() });
      }
    });
  };

  return (
    <PageContainer title="Hash Submission & Database">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <Tabs defaultValue="submit" className="w-full">
            <TabsList className="w-full justify-start bg-card/50 border-b border-border/50 rounded-none h-12 px-4 mb-4">
              <TabsTrigger value="submit" className="font-mono text-xs uppercase tracking-wider">Submit Hashes</TabsTrigger>
              <TabsTrigger value="database" className="font-mono text-xs uppercase tracking-wider">Database</TabsTrigger>
            </TabsList>
            
            <TabsContent value="submit" className="space-y-6">
              <Card className="bg-card/50 border-border/50">
                <CardHeader>
                  <CardTitle className="text-sm font-mono flex items-center gap-2">
                    <Plus className="w-4 h-4 text-primary" /> New Hash Submission
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <Label className="font-mono text-xs text-muted-foreground uppercase">Hashes (one per line)</Label>
                      <div className="flex items-center space-x-2">
                        <Switch id="auto-detect" checked={autoDetect} onCheckedChange={setAutoDetect} />
                        <Label htmlFor="auto-detect" className="text-xs font-mono">Auto-detect type</Label>
                      </div>
                    </div>
                    <Textarea 
                      className="font-mono min-h-[200px] bg-background/50 border-border/50 focus:border-primary/50" 
                      placeholder="Paste hashes here..."
                      value={hashesText}
                      onChange={(e) => setHashesText(e.target.value)}
                      onBlur={handleBlur}
                    />
                  </div>

                  {identification && (
                    <div className="bg-primary/10 border border-primary/20 p-4 rounded-md animate-in fade-in slide-in-from-top-2">
                      <h4 className="text-xs font-mono text-primary uppercase mb-2 flex items-center gap-2">
                        <Fingerprint className="w-4 h-4" /> Identification Result
                      </h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm font-mono">
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Type</span>
                          {identification.hashType}
                        </div>
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Algorithm</span>
                          {identification.algorithm}
                        </div>
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Difficulty</span>
                          <Badge variant="outline" className="text-[10px] mt-1 border-primary text-primary">{identification.difficulty}</Badge>
                        </div>
                        <div>
                          <span className="text-muted-foreground block text-[10px]">Salted</span>
                          {identification.salted ? "Yes" : "No"}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="font-mono text-xs text-muted-foreground uppercase">Label (Optional)</Label>
                      <Input 
                        className="bg-background/50 border-border/50" 
                        placeholder="e.g. Corp AD Dump"
                        value={hashLabel}
                        onChange={(e) => setHashLabel(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label className="font-mono text-xs text-muted-foreground uppercase">Source (Optional)</Label>
                      <Input 
                        className="bg-background/50 border-border/50" 
                        placeholder="e.g. Domain Controller"
                        value={hashSource}
                        onChange={(e) => setHashSource(e.target.value)}
                      />
                    </div>
                  </div>

                  <Button 
                    className="w-full font-mono uppercase tracking-widest" 
                    onClick={handleSubmit}
                    disabled={!hashesText.trim() || submitHashesMutation.isPending}
                  >
                    {submitHashesMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <HashIcon className="w-4 h-4 mr-2" />}
                    Submit Hashes to Queue
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="database">
              <Card className="bg-card/50 border-border/50">
                <CardContent className="p-0">
                  <div className="p-4 border-b border-border/50 flex justify-between items-center">
                    <div className="relative w-64">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input placeholder="Search hashes..." className="pl-8 bg-background/50 h-9 font-mono text-xs" />
                    </div>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow className="border-border/50 hover:bg-transparent">
                        <TableHead className="font-mono text-xs uppercase">Hash</TableHead>
                        <TableHead className="font-mono text-xs uppercase">Type</TableHead>
                        <TableHead className="font-mono text-xs uppercase">Status</TableHead>
                        <TableHead className="font-mono text-xs uppercase text-right">Plaintext</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {isLoadingHashes ? (
                        <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground font-mono">Loading...</TableCell></TableRow>
                      ) : hashesData?.hashes?.map((hash) => (
                        <TableRow key={hash.id} className="border-border/50 hover:bg-muted/50 group">
                          <TableCell className="font-mono text-xs truncate max-w-[200px]">{hash.value}</TableCell>
                          <TableCell className="font-mono text-xs">{hash.hashType}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className={`font-mono text-[10px] ${
                              hash.status === 'cracked' ? 'border-success text-success' :
                              hash.status === 'cracking' ? 'border-primary text-primary' :
                              hash.status === 'failed' ? 'border-destructive text-destructive' :
                              'border-warning text-warning'
                            }`}>
                              {hash.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right text-success">
                            {hash.plaintext || '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <HashIcon className="w-4 h-4 text-primary" /> Database Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between items-center text-sm font-mono border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Total</span>
                <span>{statsData?.totalSubmitted || 0}</span>
              </div>
              <div className="flex justify-between items-center text-sm font-mono border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Cracked</span>
                <span className="text-success">{statsData?.totalCracked || 0}</span>
              </div>
              <div className="flex justify-between items-center text-sm font-mono border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Crack Rate</span>
                <span>{statsData?.crackRate ? statsData.crackRate.toFixed(1) : 0}%</span>
              </div>
              <div className="mt-4">
                <h4 className="text-xs font-mono text-muted-foreground uppercase mb-2">By Type</h4>
                {statsData?.byType?.map(type => (
                  <div key={type.hashType} className="flex justify-between items-center text-xs font-mono mb-1">
                    <span>{type.hashType}</span>
                    <span className="text-muted-foreground">{type.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

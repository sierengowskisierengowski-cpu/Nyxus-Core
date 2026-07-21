import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useCreateJob,
  useListHashes,
  useListWordlists,
  useListRules,
  getListJobsQueryKey,
} from "@workspace/api-client-react";
import { useMemo, useState } from "react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { Play, Server, Crosshair } from "lucide-react";

// Hash types supported by the backend orchestration for each engine.
const HASH_TYPES = [
  "md5",
  "sha1",
  "sha256",
  "sha512",
  "ntlm",
  "md5crypt",
  "bcrypt",
  "sha256crypt",
  "sha512crypt",
];

type AttackMode = "dictionary" | "bruteforce" | "hybrid";

export default function Attack() {
  const [jobName, setJobName] = useState("");
  const [engine, setEngine] = useState<"hashcat" | "john">("hashcat");
  const [hashType, setHashType] = useState("md5");
  const [attackMode, setAttackMode] = useState<AttackMode>("dictionary");
  const [wordlistId, setWordlistId] = useState<number | null>(null);
  const [ruleId, setRuleId] = useState<number | null>(null);
  const [mask, setMask] = useState("?a?a?a?a?a?a");
  const [useGpu, setUseGpu] = useState(true);

  const { toast } = useToast();
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const createJobMutation = useCreateJob();

  const { data: hashesData } = useListHashes({ status: "uncracked" });
  const { data: wordlists } = useListWordlists();
  const { data: rules } = useListRules();

  const targetHashes = useMemo(
    () => (hashesData?.hashes ?? []).filter((h) => h.hashType?.toLowerCase() === hashType && h.status !== "cracked"),
    [hashesData, hashType],
  );

  const handleLaunch = () => {
    if (!jobName.trim()) {
      toast({ title: "Please enter a job name", variant: "destructive" });
      return;
    }
    const hashIds = targetHashes.map((h) => h.id);
    if (hashIds.length === 0) {
      toast({ title: `No uncracked ${hashType} hashes to attack`, variant: "destructive" });
      return;
    }
    if ((attackMode === "dictionary" || attackMode === "hybrid") && !wordlistId) {
      toast({ title: "Select a wordlist for this attack mode", variant: "destructive" });
      return;
    }
    if (engine === "john" && attackMode === "hybrid") {
      toast({ title: "John does not support hybrid mode; use hashcat", variant: "destructive" });
      return;
    }

    createJobMutation.mutate(
      {
        data: {
          name: jobName.trim(),
          engine,
          attackMode,
          hashType,
          hashIds,
          wordlistId: attackMode === "bruteforce" ? null : wordlistId,
          ruleId: engine === "hashcat" && attackMode === "dictionary" ? ruleId : null,
          mask: attackMode !== "dictionary" ? mask : null,
          useGpu,
        },
      },
      {
        onSuccess: () => {
          toast({ title: `Launched ${engine} ${attackMode} job against ${hashIds.length} hash(es)` });
          setJobName("");
          queryClient.invalidateQueries({ queryKey: getListJobsQueryKey() });
          navigate("/monitor");
        },
        onError: (err: unknown) => {
          toast({
            title: "Failed to launch job",
            description: err instanceof Error ? err.message : String(err),
            variant: "destructive",
          });
        },
      },
    );
  };

  return (
    <PageContainer title="Attack Engine">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-sm font-mono uppercase">Job Configuration</CardTitle>
              <CardDescription className="font-mono text-xs">
                Runs the real {engine} binary against your loaded hashes.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">Job Name</Label>
                <Input
                  className="bg-background/50 border-border/50 font-mono text-sm"
                  placeholder="e.g. MD5 audit"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">Engine</Label>
                <select
                  value={engine}
                  onChange={(e) => setEngine(e.target.value as "hashcat" | "john")}
                  className="w-full bg-background/50 border border-border/50 rounded-md h-9 px-2 font-mono text-sm"
                >
                  <option value="hashcat">hashcat</option>
                  <option value="john">John the Ripper</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label className="font-mono text-xs text-muted-foreground">Target Hash Type</Label>
                <select
                  value={hashType}
                  onChange={(e) => setHashType(e.target.value)}
                  className="w-full bg-background/50 border border-border/50 rounded-md h-9 px-2 font-mono text-sm"
                >
                  {HASH_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <Label className="font-mono text-xs flex items-center gap-2">
                  <Server className="w-4 h-4 text-primary" /> Use GPU
                </Label>
                <Switch checked={useGpu} onCheckedChange={setUseGpu} />
              </div>

              <div className="pt-2 border-t border-border/50">
                <div className="text-xs font-mono text-muted-foreground mb-2">Target Queue</div>
                <div className="bg-background/50 p-3 rounded border border-border/30 text-xs font-mono">
                  <span className="text-primary text-lg">{targetHashes.length}</span> uncracked {hashType} hash(es) will be targeted
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="text-lg font-mono text-primary flex items-center gap-2">
                <Crosshair className="w-5 h-5" /> Attack Mode
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <Tabs value={attackMode} onValueChange={(v) => setAttackMode(v as AttackMode)}>
                <TabsList className="bg-background/50">
                  <TabsTrigger value="dictionary" className="font-mono text-xs uppercase">
                    Dictionary
                  </TabsTrigger>
                  <TabsTrigger value="bruteforce" className="font-mono text-xs uppercase">
                    Brute Force
                  </TabsTrigger>
                  <TabsTrigger value="hybrid" className="font-mono text-xs uppercase" disabled={engine === "john"}>
                    Hybrid
                  </TabsTrigger>
                </TabsList>
              </Tabs>

              {(attackMode === "dictionary" || attackMode === "hybrid") && (
                <div className="space-y-2">
                  <Label className="font-mono text-xs text-muted-foreground">Wordlist</Label>
                  <select
                    value={wordlistId ?? ""}
                    onChange={(e) => setWordlistId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full bg-background/50 border border-border/50 rounded-md h-9 px-2 font-mono text-sm"
                  >
                    <option value="">Select a wordlist…</option>
                    {wordlists?.map((wl) => (
                      <option key={wl.id} value={wl.id}>
                        {wl.name} ({wl.wordCount.toLocaleString()} words)
                      </option>
                    ))}
                  </select>
                  {!wordlists?.length && (
                    <p className="text-xs text-muted-foreground font-mono">
                      No wordlists yet — upload one on the Wordlists page.
                    </p>
                  )}
                </div>
              )}

              {engine === "hashcat" && attackMode === "dictionary" && (
                <div className="space-y-2">
                  <Label className="font-mono text-xs text-muted-foreground">Rule Set (optional)</Label>
                  <select
                    value={ruleId ?? ""}
                    onChange={(e) => setRuleId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full bg-background/50 border border-border/50 rounded-md h-9 px-2 font-mono text-sm"
                  >
                    <option value="">No rules</option>
                    {rules?.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.ruleCount} rules)
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {(attackMode === "bruteforce" || attackMode === "hybrid") && (
                <div className="space-y-2">
                  <Label className="font-mono text-xs text-muted-foreground">
                    {engine === "hashcat" ? "Mask (hashcat charset syntax)" : "Incremental mode"}
                  </Label>
                  {engine === "hashcat" ? (
                    <>
                      <Input
                        className="bg-background/50 border-border/50 font-mono text-sm"
                        value={mask}
                        onChange={(e) => setMask(e.target.value)}
                        placeholder="?a?a?a?a?a?a"
                      />
                      <p className="text-xs text-muted-foreground font-mono">
                        ?l lower · ?u upper · ?d digit · ?s symbol · ?a all
                      </p>
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground font-mono">
                      John will run its built-in incremental (exhaustive) mode for brute force.
                    </p>
                  )}
                </div>
              )}

              <div className="flex justify-end pt-4 border-t border-border/50">
                <Button
                  onClick={handleLaunch}
                  disabled={createJobMutation.isPending}
                  className="font-mono uppercase tracking-widest gap-2"
                >
                  <Play className="w-4 h-4" /> Launch Attack
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}

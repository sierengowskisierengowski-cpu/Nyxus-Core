import { useState } from "react";
import { useListMitreTechniques, useListMitreTactics } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { Search, Shield, ArrowLeft } from "lucide-react";
import { Link } from "wouter";

export default function MitreTechniques() {
  useDocumentTitle("MITRE ATT&CK");
  
  const [search, setSearch] = useState("");
  const [tactic, setTactic] = useState("ALL");
  const [platform, setPlatform] = useState("ALL");

  const { data: tactics } = useListMitreTactics();
  const { data: techniques, isLoading } = useListMitreTechniques({
    search: search || undefined,
    tactic: tactic !== "ALL" ? tactic : undefined,
    platform: platform !== "ALL" ? platform : undefined
  });

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="shrink-0">
        <Link href="/kb" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
          <ArrowLeft className="w-3 h-3" />
          BACK TO KNOWLEDGE BASE
        </Link>
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-blue-500" />
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">MITRE ATT&CK Framework</h2>
        </div>
      </div>

      <Card className="shrink-0 border-border p-4 flex flex-col md:flex-row gap-4 items-center bg-muted/10">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search by ID (T1055) or Name..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 font-mono bg-background"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Select value={tactic} onValueChange={setTactic}>
            <SelectTrigger className="w-[180px] font-mono text-xs">
              <SelectValue placeholder="Tactic Phase" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Tactics</SelectItem>
              {tactics?.map(t => (
                <SelectItem key={t.id} value={t.name}>{t.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={platform} onValueChange={setPlatform}>
            <SelectTrigger className="w-[140px] font-mono text-xs">
              <SelectValue placeholder="Platform" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Platforms</SelectItem>
              <SelectItem value="Windows">Windows</SelectItem>
              <SelectItem value="Linux">Linux</SelectItem>
              <SelectItem value="macOS">macOS</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground font-mono animate-pulse text-sm">QUERYING MITRE MATRIX...</div>
          ) : techniques?.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-mono text-sm">NO TECHNIQUES FOUND MATCHING PARAMS</div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/50 sticky top-0 z-10">
                <TableRow>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground w-[100px]">ID</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">TECHNIQUE NAME</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">TACTICS</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest text-muted-foreground">PLATFORMS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {techniques?.map(tech => (
                  <TableRow key={tech.id} className="hover:bg-muted/30">
                    <TableCell className="font-mono font-bold text-primary">
                      <Link href={`/kb/mitre/${tech.id}`} className="hover:underline">{tech.id}</Link>
                    </TableCell>
                    <TableCell className="font-medium">
                      <Link href={`/kb/mitre/${tech.id}`} className="hover:underline">{tech.name}</Link>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {tech.tactics.join(", ")}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {tech.platforms.slice(0, 3).join(", ")}
                      {tech.platforms.length > 3 && " ..."}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </Card>
    </div>
  );
}

import { useState } from "react";
import { useListCves } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { Search, Bug, ArrowLeft } from "lucide-react";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";

export default function CvesList() {
  useDocumentTitle("CVEs");
  const [search, setSearch] = useState("");
  const { data: items, isLoading } = useListCves({ search: search || undefined });

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="shrink-0">
        <Link href="/kb" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-2 mb-4 w-fit">
          <ArrowLeft className="w-3 h-3" />
          BACK TO KNOWLEDGE BASE
        </Link>
        <div className="flex items-center gap-3">
          <Bug className="w-6 h-6 text-red-500" />
          <h2 className="text-2xl font-bold tracking-widest text-primary uppercase">CVE Registry</h2>
        </div>
      </div>

      <Card className="shrink-0 border-border p-4 bg-muted/10">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search CVEs..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 font-mono bg-background"
          />
        </div>
      </Card>

      <Card className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-8 text-center text-muted-foreground font-mono animate-pulse">QUERYING CVE INDEX...</div>
          ) : !items || items.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-mono">NO ENTRIES FOUND</div>
          ) : (
            <Table>
              <TableHeader className="bg-muted/50 sticky top-0">
                <TableRow>
                  <TableHead className="font-mono text-[10px] tracking-widest">ID</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest">SEVERITY</TableHead>
                  <TableHead className="font-mono text-[10px] tracking-widest">SUMMARY</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map(item => (
                  <TableRow key={item.id} className="hover:bg-muted/30">
                    <TableCell className="font-mono font-bold text-red-500">
                      <Link href={`/kb/cves/${item.id}`} className="hover:underline">{item.id}</Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={`font-mono text-[9px] uppercase ${
                        item.severity === "CRITICAL" || item.severity === "HIGH" ? "border-red-500 text-red-500" : 
                        item.severity === "MEDIUM" ? "border-yellow-500 text-yellow-500" : "border-border text-muted-foreground"
                      }`}>
                        {item.severity} {item.cvss ? `(${item.cvss})` : ""}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm line-clamp-1">{item.summary}</TableCell>
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

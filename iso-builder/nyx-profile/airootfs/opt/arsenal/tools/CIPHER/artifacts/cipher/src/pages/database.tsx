import { PageContainer } from "@/components/page-container";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useListHashes } from "@workspace/api-client-react";
import { Search, Database } from "lucide-react";

export default function DatabasePage() {
  const { data: hashesData, isLoading } = useListHashes();

  return (
    <PageContainer title="Full Hash Database">
      <Card className="bg-card/50 border-border/50 mb-6">
        <div className="p-4 border-b border-border/50 flex justify-between items-center bg-card/30">
          <div className="relative w-72">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search hash, plaintext, or label..." className="pl-8 bg-background/50 h-9 font-mono text-xs" />
          </div>
          <div className="flex gap-4">
            <Badge variant="outline" className="font-mono bg-background text-primary border-primary/30 py-1 px-3">Total: {hashesData?.total || 0}</Badge>
          </div>
        </div>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="font-mono text-xs uppercase">Hash / Label</TableHead>
                <TableHead className="font-mono text-xs uppercase">Type</TableHead>
                <TableHead className="font-mono text-xs uppercase">Status</TableHead>
                <TableHead className="font-mono text-xs uppercase">Source</TableHead>
                <TableHead className="font-mono text-xs uppercase text-right">Plaintext</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground font-mono">Loading...</TableCell></TableRow>
              ) : hashesData?.hashes?.map((hash) => (
                <TableRow key={hash.id} className="border-border/50 hover:bg-muted/50 group">
                  <TableCell>
                    <div className="font-mono text-xs truncate max-w-[200px] text-foreground">{hash.value}</div>
                    {hash.label && <div className="font-mono text-[10px] text-muted-foreground mt-1">{hash.label}</div>}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{hash.hashType}</TableCell>
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
                  <TableCell className="font-mono text-xs text-muted-foreground">{hash.source || '-'}</TableCell>
                  <TableCell className="font-mono text-xs text-right text-success font-bold">
                    {hash.plaintext || '-'}
                  </TableCell>
                </TableRow>
              ))}
              {(!hashesData?.hashes || hashesData.hashes.length === 0) && !isLoading && (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground font-mono">Database empty.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </PageContainer>
  );
}

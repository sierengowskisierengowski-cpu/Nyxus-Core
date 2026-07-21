import { PageContainer } from "@/components/page-container";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useListResults, useExportResults } from "@workspace/api-client-react";
import { Download, FileSearch } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function Results() {
  const { data: resultsData, isLoading } = useListResults();
  const exportMutation = useExportResults();
  const { toast } = useToast();

  const handleExport = () => {
    exportMutation.mutate({ data: { format: 'csv' } }, {
      onSuccess: () => toast({ title: "Results exported to CSV" })
    });
  };

  return (
    <PageContainer title="Results & Analysis">
      <Card className="bg-card/50 border-border/50 mb-6">
        <div className="p-4 border-b border-border/50 flex justify-between items-center bg-card/30">
          <div className="flex gap-4">
            <Badge variant="outline" className="font-mono bg-background text-primary border-primary/30 py-1 px-3">Total: {resultsData?.total || 0}</Badge>
          </div>
          <Button variant="outline" size="sm" className="font-mono text-xs border-primary/50 text-primary hover:bg-primary/10" onClick={handleExport} disabled={exportMutation.isPending}>
            <Download className="w-3 h-3 mr-2" /> Export CSV
          </Button>
        </div>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="font-mono text-xs uppercase">Hash</TableHead>
                <TableHead className="font-mono text-xs uppercase text-success">Plaintext</TableHead>
                <TableHead className="font-mono text-xs uppercase">Type</TableHead>
                <TableHead className="font-mono text-xs uppercase">Attack Mode</TableHead>
                <TableHead className="font-mono text-xs uppercase text-right">Cracked At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground font-mono">Loading...</TableCell></TableRow>
              ) : resultsData?.results?.map((result) => (
                <TableRow key={result.id} className="border-border/50 hover:bg-muted/50 group">
                  <TableCell className="font-mono text-xs truncate max-w-[150px] text-muted-foreground">{result.hash}</TableCell>
                  <TableCell className="font-mono text-sm text-success font-bold">{result.plaintext}</TableCell>
                  <TableCell><Badge variant="outline" className="text-[10px] font-mono border-border text-foreground/70">{result.hashType}</Badge></TableCell>
                  <TableCell><span className="text-xs font-mono">{result.attackMode}</span></TableCell>
                  <TableCell className="font-mono text-xs text-right text-muted-foreground">
                    {new Date(result.crackedAt).toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
              {(!resultsData?.results || resultsData.results.length === 0) && !isLoading && (
                <TableRow><TableCell colSpan={5} className="text-center py-8 text-muted-foreground font-mono">No cracked hashes yet.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </PageContainer>
  );
}

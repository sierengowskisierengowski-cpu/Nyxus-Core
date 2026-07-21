import { useRef, useState } from "react";
import { PageContainer } from "@/components/page-container";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useListWordlists, useDeleteWordlist, useCreateWordlist, getListWordlistsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Lock, Trash2, Upload, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function Wordlists() {
  const { data: wordlists } = useListWordlists();
  const deleteMutation = useDeleteWordlist();
  const createMutation = useCreateWordlist();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: getListWordlistsQueryKey() });

  const handleDelete = (id: number) => {
    deleteMutation.mutate({ id }, { onSuccess: () => { toast({ title: "Wordlist deleted" }); invalidate(); } });
  };

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const content = await file.text();
      createMutation.mutate(
        { data: { name: file.name, content, description: `Uploaded ${new Date().toLocaleString()}` } },
        {
          onSuccess: () => { toast({ title: `Uploaded ${file.name}` }); invalidate(); },
          onError: (err: unknown) =>
            toast({ title: "Upload failed", description: err instanceof Error ? err.message : String(err), variant: "destructive" }),
          onSettled: () => setUploading(false),
        },
      );
    } catch {
      toast({ title: "Could not read file", variant: "destructive" });
      setUploading(false);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(2)} KB`;
  };

  return (
    <PageContainer title="Wordlist Library">
      <div className="flex justify-between items-center mb-6">
        <div className="text-sm font-mono text-muted-foreground">Upload your own wordlists for real hashcat/john jobs</div>
        <div className="flex gap-2">
          <input ref={fileInputRef} type="file" accept=".txt,.lst,.dic,text/plain" className="hidden" onChange={handleFile} />
          <Button
            className="font-mono text-xs uppercase tracking-widest"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />} Upload List
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {wordlists?.map((wl) => (
          <Card key={wl.id} className="bg-card/50 border-border/50 flex flex-col">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <CardTitle className="text-sm font-mono text-primary truncate pr-2">{wl.name}</CardTitle>
                {wl.isBuiltin && <Lock className="w-3 h-3 text-muted-foreground shrink-0" />}
              </div>
              <Badge variant="outline" className="w-fit text-[10px] font-mono mt-1 border-primary/30 text-primary/80">
                {wl.source}
              </Badge>
            </CardHeader>
            <CardContent className="text-xs font-mono text-muted-foreground flex-1 flex flex-col justify-between">
              <div className="space-y-1 mb-4">
                <div className="flex justify-between">
                  <span>Words:</span>
                  <span className="text-foreground">{wl.wordCount.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Size:</span>
                  <span className="text-foreground">{formatSize(wl.sizeBytes)}</span>
                </div>
              </div>
              <div className="flex justify-between items-center pt-3 border-t border-border/50">
                <span className="text-[10px]">{wl.lastUsed ? new Date(wl.lastUsed).toLocaleDateString() : "Never used"}</span>
                {!wl.isBuiltin && (
                  <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive hover:text-destructive hover:bg-destructive/10" onClick={() => handleDelete(wl.id)}>
                    <Trash2 className="w-3 h-3" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        {!wordlists?.length && (
          <div className="col-span-full text-center py-12 text-muted-foreground font-mono text-sm">
            No wordlists yet. Upload a .txt wordlist to get started.
          </div>
        )}
      </div>
    </PageContainer>
  );
}

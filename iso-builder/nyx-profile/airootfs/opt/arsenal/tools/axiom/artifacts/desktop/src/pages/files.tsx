import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FolderSearch, Plus, Trash2, Scan, Eye, Play, AlertTriangle, FolderOpen, File, Loader2, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useGetAllowedPaths, getGetAllowedPathsQueryKey,
  useAddAllowedPath, useRemoveAllowedPath,
  useScanFiles, usePreviewFileOp, useExecuteFileOp,
} from "@workspace/api-client-react";
import type { FileEntry, FileOpPreview } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`;
  return `${bytes} B`;
}

const OPERATIONS = [
  { value: "delete",   label: "Delete files" },
  { value: "organize", label: "Organize by type" },
  { value: "move",     label: "Move to folder" },
  { value: "dedup",    label: "Remove duplicates" },
] as const;

export default function Files() {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<{ files: FileEntry[]; totalCount: number; totalSize: number } | null>(null);
  const [operation, setOperation] = useState<"delete" | "organize" | "move" | "dedup">("organize");
  const [criteria, setCriteria] = useState("");
  const [destination, setDestination] = useState("");
  const [preview, setPreview] = useState<FileOpPreview | null>(null);
  const [showAddPath, setShowAddPath] = useState(false);
  const [newPath, setNewPath] = useState("");
  const [newPathLabel, setNewPathLabel] = useState("");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: allowedPaths = [], isLoading: pathsLoading } = useGetAllowedPaths({ query: { queryKey: getGetAllowedPathsQueryKey() } });
  const addPath = useAddAllowedPath();
  const removePath = useRemoveAllowedPath();
  const scanFiles = useScanFiles();
  const previewOp = usePreviewFileOp();
  const executeOp = useExecuteFileOp();

  const handleAddPath = () => {
    if (!newPath.trim()) return;
    addPath.mutate({ data: { path: newPath.trim(), label: newPathLabel.trim() || undefined } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() });
        setShowAddPath(false);
        setNewPath(""); setNewPathLabel("");
        toast({ title: "Path added" });
      },
      onError: (err: unknown) => {
        const message = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Could not add path";
        toast({ title: message, variant: "destructive" });
      },
    });
  };

  const handleRemovePath = (id: number) => {
    removePath.mutate({ id }, { onSuccess: () => queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() }) });
  };

  const handleScan = () => {
    if (!selectedPath) return;
    scanFiles.mutate({ data: { path: selectedPath, recursive: true } }, {
      onSuccess: (r) => setScanResult(r),
      onError: () => toast({ title: "Scan failed", variant: "destructive" }),
    });
  };

  const handlePreview = () => {
    if (!selectedPath) return;
    previewOp.mutate({
      data: { path: selectedPath, operation, criteria: criteria || undefined, destination: destination || undefined }
    }, {
      onSuccess: (r) => setPreview(r),
      onError: () => toast({ title: "Preview failed", variant: "destructive" }),
    });
  };

  const handleExecute = () => {
    if (!selectedPath || !preview) return;
    executeOp.mutate({
      data: { path: selectedPath, operation, criteria: criteria || undefined, destination: destination || undefined, confirmed: true }
    }, {
      onSuccess: (r) => {
        setPreview(null);
        setScanResult(null);
        toast({ title: r.success ? `Done — ${r.filesProcessed} files processed` : "Operation failed", description: r.summary });
        queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() });
      },
      onError: () => toast({ title: "Execution failed", variant: "destructive" }),
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07]">
        <h1 className="text-base font-semibold flex items-center gap-2">
          <FolderSearch className="w-4 h-4 text-orange-400" />
          File Operations
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">Scan, organize, and clean your approved paths</p>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Left: allowed paths */}
        <div className="w-52 shrink-0 border-r border-white/[0.07] flex flex-col">
          <div className="p-3 border-b border-white/[0.07] flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Shield className="w-3 h-3 text-orange-400" />
              <span className="text-xs font-medium">Allowed Paths</span>
            </div>
            <Button
              size="icon"
              variant="ghost"
              className="w-6 h-6 hover:bg-white/10 text-muted-foreground hover:text-foreground"
              onClick={() => setShowAddPath(true)}
              data-testid="button-add-path"
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          </div>
          <ScrollArea className="flex-1">
            <div className="p-2 space-y-1">
              {pathsLoading ? (
                Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-lg bg-white/5" />)
              ) : allowedPaths.length === 0 ? (
                <div className="px-2 py-6 text-center">
                  <p className="text-xs text-muted-foreground">No approved paths yet</p>
                  <p className="text-[10px] text-muted-foreground/50 mt-1">Add a folder to get started</p>
                </div>
              ) : (
                allowedPaths.map(ap => (
                  <div
                    key={ap.id}
                    className={cn(
                      "group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-all border",
                      selectedPath === ap.path
                        ? "bg-orange-500/10 border-orange-400/25 text-foreground"
                        : "border-transparent hover:bg-white/5 hover:border-white/10"
                    )}
                    onClick={() => { setSelectedPath(ap.path); setScanResult(null); setPreview(null); }}
                    data-testid={`path-item-${ap.id}`}
                  >
                    <FolderOpen className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">{ap.label || ap.path.split("/").pop()}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{ap.path}</p>
                    </div>
                    <button
                      className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                      onClick={e => { e.stopPropagation(); handleRemovePath(ap.id); }}
                      data-testid={`button-remove-path-${ap.id}`}
                    >
                      <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>

        {/* Right: scan + operations */}
        <div className="flex-1 flex flex-col min-w-0 p-5 space-y-4 overflow-auto">
          {!selectedPath ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4">
              <div className="w-14 h-14 rounded-2xl bg-orange-500/10 border border-orange-400/20 flex items-center justify-center">
                <FolderSearch className="w-7 h-7 text-orange-400" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium">No path selected</p>
                <p className="text-xs text-muted-foreground mt-1">Select an approved path from the left, or add a new one</p>
              </div>
              <Button size="sm" className="btn-amber" onClick={() => setShowAddPath(true)}>
                <Plus className="w-3.5 h-3.5 mr-1.5" />Add Path
              </Button>
            </div>
          ) : (
            <>
              {/* Path info + scan */}
              <div className="glass-card rounded-xl p-4 border border-white/[0.06]">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{selectedPath.split("/").pop()}</p>
                    <p className="text-xs text-muted-foreground font-mono mt-0.5">{selectedPath}</p>
                    {scanResult && (
                      <p className="text-xs text-orange-400/80 mt-1">
                        {scanResult.totalCount} files · {formatBytes(scanResult.totalSize)}
                      </p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    className="h-7 text-xs glass-button"
                    onClick={handleScan}
                    disabled={scanFiles.isPending}
                    data-testid="button-scan-files"
                  >
                    {scanFiles.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Scan className="w-3 h-3 mr-1" />}
                    Scan
                  </Button>
                </div>

                {scanResult && scanResult.files.length > 0 && (
                  <div className="mt-3 border-t border-white/[0.06] pt-3">
                    <ScrollArea className="h-28">
                      <div className="space-y-0.5">
                        {scanResult.files.slice(0, 30).map((f, i) => (
                          <div key={i} className="flex items-center gap-2 py-0.5 text-xs">
                            {f.type === "directory"
                              ? <FolderOpen className="w-3 h-3 text-amber-400 shrink-0" />
                              : <File className="w-3 h-3 text-muted-foreground shrink-0" />}
                            <span className="flex-1 truncate text-foreground/70">{f.name}</span>
                            <span className="text-muted-foreground/50 shrink-0">{f.type === "file" ? formatBytes(f.size) : ""}</span>
                          </div>
                        ))}
                        {scanResult.totalCount > 30 && (
                          <p className="text-[10px] text-muted-foreground text-center py-1">+{scanResult.totalCount - 30} more files</p>
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                )}
              </div>

              {/* Operation builder */}
              <div className="glass-card rounded-xl p-4 border border-white/[0.06] space-y-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">File Operation</p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Operation</Label>
                    <Select value={operation} onValueChange={v => { setOperation(v as typeof operation); setPreview(null); }}>
                      <SelectTrigger className="glass-input h-8 text-sm" data-testid="select-operation">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="glass-panel border-white/[0.08]">
                        {OPERATIONS.map(op => (
                          <SelectItem key={op.value} value={op.value} className="text-sm">{op.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  {operation === "delete" && (
                    <div className="space-y-1.5">
                      <Label className="text-xs text-muted-foreground">Criteria (optional)</Label>
                      <Input value={criteria} onChange={e => setCriteria(e.target.value)} placeholder="older than 30 days, .log files…" className="glass-input h-8 text-xs" data-testid="input-criteria" />
                    </div>
                  )}
                  {operation === "move" && (
                    <div className="space-y-1.5">
                      <Label className="text-xs text-muted-foreground">Destination Path</Label>
                      <Input value={destination} onChange={e => setDestination(e.target.value)} placeholder="/path/to/destination" className="glass-input h-8 text-xs font-mono" data-testid="input-destination" />
                    </div>
                  )}
                </div>
                <Button
                  size="sm"
                  className="h-7 text-xs glass-button"
                  onClick={handlePreview}
                  disabled={previewOp.isPending}
                  data-testid="button-preview-op"
                >
                  {previewOp.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Eye className="w-3 h-3 mr-1" />}
                  Preview Changes
                </Button>
              </div>

              {/* Preview */}
              <AnimatePresence>
                {preview && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="glass-card rounded-xl p-4 border border-amber-500/25 space-y-3"
                  >
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <p className="text-sm font-medium">{preview.summary}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {formatBytes(preview.totalSize ?? 0)} affected · {preview.reversible ? "Reversible (undo available)" : "Irreversible"}
                        </p>
                      </div>
                    </div>
                    {preview.affectedFiles.length > 0 && (
                      <ScrollArea className="h-24 border-t border-white/[0.06] pt-2">
                        <div className="space-y-0.5">
                          {preview.affectedFiles.slice(0, 20).map((f, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                              <File className="w-3 h-3 text-amber-400 shrink-0" />
                              <span className="flex-1 truncate text-foreground/70 font-mono">{f.name}</span>
                              <span className="text-muted-foreground/50">{formatBytes(f.size)}</span>
                            </div>
                          ))}
                          {preview.affectedFiles.length > 20 && (
                            <p className="text-[10px] text-muted-foreground text-center">+{preview.affectedFiles.length - 20} more</p>
                          )}
                        </div>
                      </ScrollArea>
                    )}
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        className="h-7 text-xs btn-amber"
                        onClick={handleExecute}
                        disabled={executeOp.isPending}
                        data-testid="button-execute-op"
                      >
                        {executeOp.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <Play className="w-3 h-3 mr-1" />}
                        Confirm & Execute
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setPreview(null)}>Cancel</Button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </>
          )}
        </div>
      </div>

      <Dialog open={showAddPath} onOpenChange={setShowAddPath}>
        <DialogContent className="glass-panel border-white/[0.08] bg-card/90 max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold">Add Allowed Path</DialogTitle>
          </DialogHeader>
          <p className="text-xs text-muted-foreground -mt-1">AXIOM will only operate on paths you approve here.</p>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Directory Path</Label>
              <Input value={newPath} onChange={e => setNewPath(e.target.value)} placeholder="/Users/me/Downloads" className="glass-input h-8 text-sm font-mono" data-testid="input-new-path" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Label (optional)</Label>
              <Input value={newPathLabel} onChange={e => setNewPathLabel(e.target.value)} placeholder="Downloads" className="glass-input h-8 text-sm" data-testid="input-path-label" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" size="sm" className="text-xs" onClick={() => setShowAddPath(false)}>Cancel</Button>
            <Button
              size="sm"
              className="text-xs btn-action"
              onClick={handleAddPath}
              disabled={!newPath.trim() || addPath.isPending}
              data-testid="button-confirm-add-path"
            >
              {addPath.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
              Add Path
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Pin, Trash2, Download, Upload, BookOpen, Loader2, PinOff, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useListKnowledgeNotes, getListKnowledgeNotesQueryKey,
  useCreateKnowledgeNote, useUpdateKnowledgeNote, useDeleteKnowledgeNote,
  useImportKnowledge,
} from "@workspace/api-client-react";
import type { KnowledgeNote } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

function NoteCard({ note, onSave, onPin, onDelete }: {
  note: KnowledgeNote;
  onSave: (id: number, title: string, content: string) => void;
  onPin: (id: number, pinned: boolean) => void;
  onDelete: (id: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);

  const handleBlur = () => {
    if (title !== note.title || content !== note.content) onSave(note.id, title, content);
    setEditing(false);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.94 }}
      className={cn(
        "glass-card rounded-xl p-4 border transition-all duration-200 group cursor-pointer",
        editing
          ? "border-violet-400/30 shadow-[0_0_16px_rgba(167,139,250,0.08)]"
          : note.pinned
            ? "border-violet-400/20 hover:border-violet-400/35"
            : "border-white/[0.06] hover:border-white/15"
      )}
      onClick={() => !editing && setEditing(true)}
      data-testid={`note-card-${note.id}`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        {editing ? (
          <Input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="glass-input h-7 text-sm font-medium py-0 px-2"
            onClick={e => e.stopPropagation()}
            data-testid={`input-note-title-${note.id}`}
          />
        ) : (
          <div className="flex items-center gap-2 min-w-0">
            {note.pinned && <Pin className="w-3 h-3 text-violet-400 shrink-0" />}
            <span className="text-sm font-medium truncate">{note.title}</span>
          </div>
        )}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-white/10 transition-colors"
            onClick={e => { e.stopPropagation(); onPin(note.id, !note.pinned); }}
            title={note.pinned ? "Unpin" : "Pin"}
            data-testid={`button-pin-note-${note.id}`}
          >
            {note.pinned
              ? <PinOff className="w-3 h-3 text-violet-400" />
              : <Pin className="w-3 h-3 text-muted-foreground" />}
          </button>
          <button
            className="w-6 h-6 flex items-center justify-center rounded hover:bg-destructive/10 transition-colors"
            onClick={e => { e.stopPropagation(); onDelete(note.id); }}
            data-testid={`button-delete-note-${note.id}`}
          >
            <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
          </button>
        </div>
      </div>

      {editing ? (
        <Textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          onBlur={handleBlur}
          className="glass-input text-xs min-h-[100px] resize-none"
          autoFocus
          onClick={e => e.stopPropagation()}
          data-testid={`textarea-note-content-${note.id}`}
        />
      ) : (
        <p className="text-xs text-muted-foreground line-clamp-4 whitespace-pre-wrap">
          {note.content || <span className="italic opacity-50">Click to add content…</span>}
        </p>
      )}

      <div className="flex items-center justify-between mt-3">
        <span className="text-[10px] text-muted-foreground/40">
          {new Date(note.updatedAt).toLocaleDateString()}
        </span>
        {note.pinned && (
          <Badge className="text-[10px] h-4 px-1.5 bg-violet-500/10 text-violet-300 border-violet-500/25">Pinned</Badge>
        )}
      </div>
    </motion.div>
  );
}

export default function Knowledge() {
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [search, setSearch] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: notes = [], isLoading } = useListKnowledgeNotes({ query: { queryKey: getListKnowledgeNotesQueryKey() } });
  const createNote = useCreateKnowledgeNote();
  const updateNote = useUpdateKnowledgeNote();
  const deleteNote = useDeleteKnowledgeNote();
  const importNotes = useImportKnowledge();

  const invalidate = () => queryClient.invalidateQueries({ queryKey: getListKnowledgeNotesQueryKey() });

  const handleCreate = () => {
    if (!newTitle.trim()) return;
    createNote.mutate(
      { data: { title: newTitle, content: newContent } },
      {
        onSuccess: () => {
          invalidate();
          setShowAdd(false);
          setNewTitle(""); setNewContent("");
          toast({ title: "Note created" });
        },
      }
    );
  };

  const handleSave = (id: number, title: string, content: string) => {
    updateNote.mutate({ id, data: { title, content } }, { onSuccess: () => invalidate() });
  };
  const handlePin = (id: number, pinned: boolean) => {
    updateNote.mutate({ id, data: { pinned } }, { onSuccess: () => invalidate() });
  };
  const handleDelete = (id: number) => {
    deleteNote.mutate({ id }, { onSuccess: () => invalidate() });
  };

  const handleExport = () => {
    const data = { notes: notes.map(n => ({ title: n.title, content: n.content, pinned: n.pinned })) };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "axiom-knowledge.json"; a.click();
    URL.revokeObjectURL(url);
    toast({ title: "Knowledge base exported" });
  };

  const handleImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string) as { notes: Array<{ title: string; content: string; pinned?: boolean }> };
        const data = {
          exportedAt: new Date().toISOString(),
          notes: parsed.notes.map(n => ({
            ...n, id: 0,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          }))
        };
        importNotes.mutate({ data }, {
          onSuccess: (r) => {
            invalidate();
            toast({ title: `Imported ${r.imported} notes`, description: r.skipped > 0 ? `${r.skipped} skipped (already exist)` : undefined });
          },
          onError: () => toast({ title: "Import failed", variant: "destructive" }),
        });
      } catch {
        toast({ title: "Invalid JSON file", variant: "destructive" });
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const filtered = notes.filter(n =>
    !search ||
    n.title.toLowerCase().includes(search.toLowerCase()) ||
    n.content.toLowerCase().includes(search.toLowerCase())
  );
  const pinnedNotes = filtered.filter(n => n.pinned);
  const unpinnedNotes = filtered.filter(n => !n.pinned);

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07] flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-base font-semibold flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-violet-400 shrink-0" />
            Knowledge Base
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            {notes.length} note{notes.length !== 1 ? "s" : ""} · Always injected into AI context
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground pointer-events-none" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search notes…"
              className="glass-input h-7 text-xs pl-7 w-36"
            />
            {search && (
              <button className="absolute right-2 top-1/2 -translate-y-1/2" onClick={() => setSearch("")}>
                <X className="w-3 h-3 text-muted-foreground hover:text-foreground" />
              </button>
            )}
          </div>
          <input ref={fileInputRef} type="file" accept=".json" className="hidden" onChange={handleImportFile} />
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-muted-foreground hover:text-foreground h-7"
            onClick={() => fileInputRef.current?.click()}
            disabled={importNotes.isPending}
            data-testid="button-import-knowledge"
          >
            <Upload className="w-3 h-3 mr-1.5" />Import
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-muted-foreground hover:text-foreground h-7"
            onClick={handleExport}
            data-testid="button-export-knowledge"
          >
            <Download className="w-3 h-3 mr-1.5" />Export
          </Button>
          <Button
            size="sm"
            className="btn-action h-7 text-xs"
            onClick={() => setShowAdd(true)}
            data-testid="button-add-note"
          >
            <Plus className="w-3 h-3 mr-1" />Add Note
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-36 rounded-xl bg-white/5" />)}
          </div>
        ) : notes.length === 0 && !showAdd ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[300px] gap-4">
            <div className="w-14 h-14 rounded-2xl bg-violet-500/10 border border-violet-400/20 flex items-center justify-center">
              <BookOpen className="w-7 h-7 text-violet-400" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium">No notes yet</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-xs">
                Add notes about your system, preferences, and file structure. AXIOM reads them on every request.
              </p>
            </div>
            <Button size="sm" className="btn-action" onClick={() => setShowAdd(true)}>
              <Plus className="w-3.5 h-3.5 mr-1.5" />Create First Note
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            <AnimatePresence>
              {showAdd && (
                <motion.div
                  initial={{ opacity: 0, y: -12, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                  className="glass-card rounded-xl p-4 border border-violet-400/25"
                >
                  <div className="space-y-3">
                    <Input
                      value={newTitle}
                      onChange={e => setNewTitle(e.target.value)}
                      placeholder="Note title…"
                      className="glass-input h-8 text-sm"
                      autoFocus
                      data-testid="input-new-note-title"
                    />
                    <Textarea
                      value={newContent}
                      onChange={e => setNewContent(e.target.value)}
                      placeholder="Note content…"
                      className="glass-input text-xs min-h-[80px] resize-none"
                      data-testid="textarea-new-note-content"
                    />
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setShowAdd(false); setNewTitle(""); setNewContent(""); }}>
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        className="h-7 text-xs btn-action"
                        onClick={handleCreate}
                        disabled={!newTitle.trim() || createNote.isPending}
                        data-testid="button-save-note"
                      >
                        {createNote.isPending ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : null}
                        Save
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {search && filtered.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-12">No notes match "{search}"</p>
            )}

            {pinnedNotes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                  <Pin className="w-3 h-3 text-violet-400" /> Pinned
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <AnimatePresence>
                    {pinnedNotes.map(note => (
                      <NoteCard key={note.id} note={note} onSave={handleSave} onPin={handlePin} onDelete={handleDelete} />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            )}

            {unpinnedNotes.length > 0 && (
              <div>
                {pinnedNotes.length > 0 && (
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2.5">Notes</p>
                )}
                <div className="grid grid-cols-2 gap-3">
                  <AnimatePresence>
                    {unpinnedNotes.map(note => (
                      <NoteCard key={note.id} note={note} onSave={handleSave} onPin={handlePin} onDelete={handleDelete} />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { useListNotes, useListNotebooks, useListTags, getListNotesQueryKey } from "@workspace/api-client-react";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { directApi } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { BookOpen, Search, Plus, Save, Trash2, Pin, Archive, Tag as TagIcon, Hash } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "@/components/markdown-renderer";

export default function Notes() {
  useDocumentTitle("Intelligence Notes");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [selectedNoteId, setSelectedNoteId] = useState<number | null>(null);
  
  // Editor state
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [isPreview, setIsPreview] = useState(false);

  const { data: notes, isLoading: notesLoading } = useListNotes({ search: search || undefined });
  const { data: notebooks } = useListNotebooks();
  const { data: tags } = useListTags();

  const selectedNote = notes?.find(n => n.id === selectedNoteId);

  // Sync editor when selection changes
  useState(() => {
    if (selectedNote) {
      setTitle(selectedNote.title);
      setBody(selectedNote.body);
    } else {
      setTitle("");
      setBody("");
    }
  });

  const handleCreate = async () => {
    try {
      const newNote = await directApi.notes.create({ title: "New Note", body: "" }) as { id: number; title: string; body: string };
      queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
      setSelectedNoteId(newNote.id);
      setTitle(newNote.title);
      setBody(newNote.body);
    } catch (e: any) {
      toast({ title: "Error", description: "Failed to create note.", variant: "destructive" });
    }
  };

  const handleSave = async () => {
    if (!selectedNoteId) return;
    try {
      await directApi.notes.update(selectedNoteId, { title, body });
      queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
      toast({ title: "Saved", description: "Note updated." });
    } catch (e: any) {
      toast({ title: "Error", description: "Failed to save note.", variant: "destructive" });
    }
  };

  const handleDelete = async () => {
    if (!selectedNoteId) return;
    if (!confirm("Delete this note permanently?")) return;
    try {
      await directApi.notes.delete(selectedNoteId);
      queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
      setSelectedNoteId(null);
      toast({ title: "Deleted", description: "Note removed." });
    } catch (e: any) {
      toast({ title: "Error", description: "Failed to delete note.", variant: "destructive" });
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row gap-6 overflow-hidden">
      
      {/* Sidebar - Notebooks & Tags */}
      <div className="w-full md:w-48 shrink-0 flex flex-col gap-6 overflow-y-auto">
        <div>
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
            <BookOpen className="w-3 h-3" /> Notebooks
          </h3>
          <div className="space-y-1">
            <Button variant="ghost" className="w-full justify-start h-8 text-xs font-mono" size="sm">All Notes</Button>
            {notebooks?.map(nb => (
              <Button key={nb.id} variant="ghost" className="w-full justify-start h-8 text-xs font-mono" size="sm">
                <span className="w-2 h-2 rounded-full mr-2" style={{ backgroundColor: nb.color || 'var(--primary)' }} />
                {nb.name}
              </Button>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
            <TagIcon className="w-3 h-3" /> Tags
          </h3>
          <div className="space-y-1">
            {tags?.map(t => (
              <Button key={t.name} variant="ghost" className="w-full justify-between h-8 text-xs font-mono text-muted-foreground" size="sm">
                <span className="flex items-center gap-1"><Hash className="w-3 h-3" />{t.name}</span>
                <span className="opacity-50">{t.count}</span>
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Note List */}
      <Card className="w-full md:w-80 shrink-0 flex flex-col rounded-sm border-border bg-card">
        <div className="p-3 border-b border-border flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
            <Input 
              placeholder="Search..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-7 h-8 text-xs font-mono bg-background border-none shadow-none"
            />
          </div>
          <Button size="icon" variant="ghost" className="h-8 w-8 text-primary hover:text-primary hover:bg-primary/10" onClick={handleCreate}>
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <ScrollArea className="flex-1">
          {notesLoading ? (
            <div className="p-4 text-xs font-mono text-muted-foreground text-center">LOADING...</div>
          ) : notes?.length === 0 ? (
            <div className="p-4 text-xs font-mono text-muted-foreground text-center">NO NOTES FOUND</div>
          ) : (
            <div className="flex flex-col divide-y divide-border">
              {notes?.map(note => (
                <button
                  key={note.id}
                  onClick={() => {
                    setSelectedNoteId(note.id);
                    setTitle(note.title);
                    setBody(note.body);
                    setIsPreview(false);
                  }}
                  className={cn(
                    "text-left p-4 transition-colors",
                    selectedNoteId === note.id ? "bg-primary/10 border-l-2 border-primary" : "hover:bg-muted/30 border-l-2 border-transparent"
                  )}
                >
                  <div className="font-semibold text-sm line-clamp-1 mb-1">{note.title}</div>
                  <div className="text-[10px] font-mono text-muted-foreground flex justify-between">
                    <span>{format(new Date(note.updatedAt), "yyyy-MM-dd")}</span>
                    {note.pinned && <Pin className="w-3 h-3 text-secondary" />}
                  </div>
                </button>
              ))}
            </div>
          )}
        </ScrollArea>
      </Card>

      {/* Editor */}
      <Card className="flex-1 flex flex-col rounded-sm border-border bg-card overflow-hidden">
        {selectedNoteId ? (
          <>
            <div className="p-3 border-b border-border flex items-center justify-between bg-muted/10">
              <Input 
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="font-bold text-lg border-none shadow-none focus-visible:ring-0 px-0 rounded-none bg-transparent h-auto py-1 max-w-md"
              />
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => setIsPreview(!isPreview)} className="text-xs font-mono h-8">
                  {isPreview ? "EDIT" : "PREVIEW"}
                </Button>
                <Button variant="ghost" size="icon" onClick={handleSave} className="h-8 w-8 text-primary hover:text-primary hover:bg-primary/10">
                  <Save className="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={handleDelete} className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <div className="flex-1 relative">
              {isPreview ? (
                <ScrollArea className="h-full absolute inset-0 p-6 bg-background">
                  <MarkdownRenderer content={body} />
                </ScrollArea>
              ) : (
                <Textarea 
                  value={body}
                  onChange={e => setBody(e.target.value)}
                  className="absolute inset-0 h-full w-full border-none shadow-none focus-visible:ring-0 rounded-none resize-none p-6 font-mono text-sm bg-transparent leading-relaxed"
                  placeholder="Start typing markdown..."
                />
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
            <BookOpen className="w-12 h-12 mb-4 opacity-20" />
            <p className="font-mono text-sm uppercase tracking-widest">Select a note or create new</p>
          </div>
        )}
      </Card>

    </div>
  );
}

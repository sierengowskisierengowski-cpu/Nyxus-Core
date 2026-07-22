import { useState } from "react";
import { useListNotes, useCreateNote, useDeleteNote, getListNotesQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { BookOpen, Plus, Trash2, Search, Tag } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "wouter";

export default function Notes() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: notes, isLoading } = useListNotes();
  const { mutate: createNote, isPending: isCreating } = useCreateNote();
  const { mutate: deleteNote } = useDeleteNote();

  const [newContent, setNewContent] = useState("");
  const [newTags, setNewTags] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const handleCreate = () => {
    if (!newContent.trim()) return;
    createNote({ data: { content: newContent, tags: newTags } }, {
      onSuccess: () => {
        setNewContent("");
        setNewTags("");
        queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
        toast({ title: "NOTE LOGGED", description: "Entry added to study base." });
      }
    });
  };

  const handleDelete = (id: number) => {
    deleteNote({ id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListNotesQueryKey() });
      }
    });
  };

  const filteredNotes = notes?.filter(n => 
    n.content.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (n.tags && n.tags.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">STUDY NOTES</h1>
          <p className="text-muted-foreground uppercase text-sm mt-1">Research, findings, and operator logs</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-4">
          <Card className="border-border sticky top-6">
            <CardHeader className="pb-3 border-b border-border">
              <CardTitle className="text-sm font-mono text-muted-foreground flex items-center gap-2">
                <Plus size={14}/> NEW ENTRY
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <Textarea 
                placeholder="Log findings, command outputs, or research here (Markdown supported)..."
                className="min-h-[200px] font-mono text-sm bg-muted/50 border-border"
                value={newContent}
                onChange={e => setNewContent(e.target.value)}
              />
              <div className="flex gap-2">
                <Tag className="text-muted-foreground mt-2" size={16}/>
                <Input 
                  placeholder="Tags (comma separated)" 
                  className="font-mono text-xs"
                  value={newTags}
                  onChange={e => setNewTags(e.target.value)}
                />
              </div>
              <Button className="w-full font-bold tracking-widest" onClick={handleCreate} disabled={isCreating || !newContent.trim()}>
                COMMIT TO LOG
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search database..." 
              className="pl-9 bg-card border-border font-mono"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="space-y-4">
            {isLoading ? (
              Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)
            ) : filteredNotes?.length === 0 ? (
              <div className="text-center p-12 border border-border border-dashed rounded-lg text-muted-foreground">
                <BookOpen className="mx-auto h-12 w-12 opacity-20 mb-4" />
                <p className="text-sm">No notes found.</p>
              </div>
            ) : (
              filteredNotes?.map(note => (
                <Card key={note.id} className="bg-card">
                  <CardContent className="p-5 font-mono text-sm whitespace-pre-wrap text-foreground">
                    {note.content}
                  </CardContent>
                  <CardFooter className="bg-muted/30 px-5 py-2 border-t border-border flex justify-between items-center text-xs">
                    <div className="flex items-center gap-4 text-muted-foreground">
                      <span>{new Date(note.createdAt).toLocaleString()}</span>
                      {note.missionId && (
                        <Link href={`/missions/${note.missionId}`} className="text-primary hover:underline">
                          [OP-{note.missionId}]
                        </Link>
                      )}
                      {note.tags && (
                        <div className="flex gap-1">
                          {note.tags.split(',').map(t => (
                            <Badge key={t} variant="secondary" className="text-[10px] px-1 py-0">{t.trim()}</Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(note.id)}>
                      <Trash2 size={12}/>
                    </Button>
                  </CardFooter>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

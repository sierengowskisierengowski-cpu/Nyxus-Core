import { PageContainer } from "@/components/page-container";
import { Card, CardContent } from "@/components/ui/card";
import { useListNotes } from "@workspace/api-client-react";
import { BookOpen, Search, Pin } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import type { Note } from "@workspace/api-client-react";

export default function Notes() {
  const { data: notes } = useListNotes();
  const [selected, setSelected] = useState<Note | null>(null);

  const displayNote = selected || notes?.[0] || null;

  return (
    <PageContainer title="Research Notes">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-12rem)]">
        <Card className="lg:col-span-1 bg-card/50 border-border/50 flex flex-col h-full">
          <div className="p-4 border-b border-border/50">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search notes..." className="pl-8 bg-background/50 h-9 font-mono text-xs" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {notes?.map(note => (
              <div
                key={note.id}
                onClick={() => setSelected(note)}
                className="p-3 rounded-md hover:bg-muted/50 cursor-pointer border border-transparent hover:border-border/50 transition-colors"
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="font-mono text-sm text-primary truncate pr-2">{note.title}</span>
                  {note.isPinned && <Pin className="w-3 h-3 text-secondary shrink-0" />}
                </div>
                <div className="text-[10px] font-mono text-muted-foreground truncate">
                  {note.notebook}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-3 bg-card/50 border-border/50 flex flex-col h-full">
          {displayNote ? (
            <>
              <div className="p-4 border-b border-border/50 bg-background/30 flex justify-between items-center">
                <input
                  type="text"
                  className="bg-transparent border-none text-lg font-mono font-bold text-foreground focus:outline-none w-full"
                  defaultValue={displayNote.title}
                  key={displayNote.id}
                />
              </div>
              <div className="flex-1 p-0">
                <textarea
                  className="w-full h-full bg-transparent text-muted-foreground font-mono text-sm p-6 resize-none focus:outline-none"
                  defaultValue={displayNote.content}
                  key={`content-${displayNote.id}`}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground opacity-50">
              <BookOpen className="w-12 h-12 mb-4" />
              <p className="font-mono text-sm">Select or create a note</p>
            </div>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}

import React from "react";
import {
  useListNotes,
  useCreateNote,
  useGetNote,
  useUpdateNote,
  useDeleteNote,
  useListNotebooks,
  getListNotesQueryKey,
  getGetNoteQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, Pin, Star, BookOpen } from "lucide-react";

const NOTE_TYPES = ["Threat", "Technique", "Detection", "Research", "Quick Capture"];
const NOTE_TEMPLATES: Record<string, string> = {
  Threat: "## Threat Analysis\n\n**Technique:** \n**MITRE ID:** \n**Platform:** \n\n## Technical Notes\n\n## Detection Opportunities\n\n## References\n",
  Detection: "## Detection Logic\n\n**Rule Type:** Sigma/Snort/YARA\n**Trigger:** \n**False Positive Rate:** \n\n## Implementation\n\n```\n# Rule here\n```\n",
  Research: "## Research Notes\n\n**Topic:** \n**Date:** \n\n## Key Findings\n\n## Open Questions\n\n## Next Steps\n",
  "Quick Capture": "",
  Technique: "## Technique Notes\n\n**MITRE ATT&CK:** \n**Sub-technique:** \n\n## How It Works\n\n## Variants\n\n## Detection\n",
};

const typeStyle: Record<string, React.CSSProperties> = {
  Threat: { background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)', color: '#f87171' },
  Technique: { background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', color: '#fb923c' },
  Detection: { background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' },
  Research: { background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', color: '#60a5fa' },
  "Quick Capture": { background: '#0f0f1a', border: '1px solid #111118', color: '#64748b' },
};

const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

export default function Notes() {
  const queryClient = useQueryClient();
  const [selectedNotebook, setSelectedNotebook] = React.useState<string | undefined>(undefined);
  const [selectedType, setSelectedType] = React.useState<string | undefined>(undefined);
  const [activeNoteId, setActiveNoteId] = React.useState<number | null>(null);
  const [preview, setPreview] = React.useState(false);
  const [showCreate, setShowCreate] = React.useState(false);
  const [newTitle, setNewTitle] = React.useState("");
  const [newType, setNewType] = React.useState("Research");
  const [newNotebook, setNewNotebook] = React.useState("Research");
  const [editTitle, setEditTitle] = React.useState("");
  const [editContent, setEditContent] = React.useState("");
  const [saved, setSaved] = React.useState(false);
  const saveTimer = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const listParams = { notebook: selectedNotebook, noteType: selectedType };
  const { data: notes, isLoading } = useListNotes(listParams, { query: { queryKey: getListNotesQueryKey(listParams) } });
  const { data: notebooks } = useListNotebooks({});
  const { data: activeNote } = useGetNote(activeNoteId!, { query: { queryKey: getGetNoteQueryKey(activeNoteId!), enabled: !!activeNoteId } });
  const createNote = useCreateNote();
  const updateNote = useUpdateNote();
  const deleteNote = useDeleteNote();

  React.useEffect(() => {
    if (activeNote) {
      setEditTitle(activeNote.title);
      setEditContent(activeNote.content ?? "");
    }
  }, [activeNote?.id]);

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "n") {
        e.preventDefault();
        setShowCreate(true);
        setNewType("Quick Capture");
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleContentChange = (val: string) => {
    setEditContent(val);
    setSaved(false);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      if (!activeNoteId) return;
      await updateNote.mutateAsync({ id: activeNoteId, data: { content: val } });
      queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
      setSaved(true);
    }, 1000);
  };

  const handleTitleBlur = async () => {
    if (!activeNoteId || editTitle === activeNote?.title) return;
    await updateNote.mutateAsync({ id: activeNoteId, data: { title: editTitle } });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    const note = await createNote.mutateAsync({
      data: {
        title: newTitle,
        noteType: newType,
        notebook: newNotebook,
        content: NOTE_TEMPLATES[newType] ?? "",
        tags: [],
        pinned: false,
      },
    });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
    setShowCreate(false);
    setNewTitle("");
    setActiveNoteId((note as { id: number }).id);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this note?")) return;
    await deleteNote.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
    if (activeNoteId === id) setActiveNoteId(null);
  };

  const togglePin = async (id: number, pinned: boolean) => {
    await updateNote.mutateAsync({ id, data: { pinned: !pinned } });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
  };

  const toggleStar = async (id: number, starred: boolean) => {
    await updateNote.mutateAsync({ id, data: { starred: !starred } });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
  };

  const manualSave = async () => {
    if (!activeNoteId) return;
    await updateNote.mutateAsync({ id: activeNoteId, data: { content: editContent, title: editTitle } });
    queryClient.invalidateQueries({ queryKey: getListNotesQueryKey(listParams) });
    setSaved(true);
  };

  const allNotebooks = notebooks ?? ["Research", "Quick Capture"];

  return (
    <div className="p-8 max-w-7xl space-y-5 h-[calc(100vh-2rem)] flex flex-col">
      {/* Page Header */}
      <div className="flex items-center justify-between shrink-0 pb-5" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Research Notes</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Ctrl+N for quick capture
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
          style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
          onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
        >
          <Plus className="w-3.5 h-3.5" />New Note
        </button>
      </div>

      {showCreate && (
        <div
          className="rounded-lg p-4 space-y-3 shrink-0"
          style={{ background: 'rgba(249,115,22,0.04)', border: '1px solid rgba(249,115,22,0.2)' }}
        >
          <Input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="Note title..."
            className="font-mono text-sm h-9"
            style={inputStyle}
            autoFocus
            onKeyDown={e => e.key === "Enter" && handleCreate()}
          />
          <div className="flex gap-2">
            <Select value={newType} onValueChange={setNewType}>
              <SelectTrigger className="font-mono text-xs flex-1 h-9" style={inputStyle}><SelectValue placeholder="Type" /></SelectTrigger>
              <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                {NOTE_TYPES.map(t => <SelectItem key={t} value={t} className="font-mono text-xs">{t}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={newNotebook} onValueChange={setNewNotebook}>
              <SelectTrigger className="font-mono text-xs flex-1 h-9" style={inputStyle}><SelectValue placeholder="Notebook" /></SelectTrigger>
              <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                {allNotebooks.map((nb: string) => <SelectItem key={nb} value={nb} className="font-mono text-xs">{nb}</SelectItem>)}
              </SelectContent>
            </Select>
            <button
              onClick={handleCreate}
              disabled={!newTitle.trim() || createNote.isPending}
              className="px-4 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono disabled:opacity-40"
              style={{ background: '#f97316', color: 'white' }}
            >
              Create
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-3 rounded-lg text-[11px] font-mono"
              style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Sidebar */}
        <div className="lg:col-span-1 flex flex-col gap-3 min-h-0">
          {/* Notebooks */}
          <div className="rounded-lg p-3 shrink-0" style={{ background: '#0d0d1a', border: '1px solid #111118' }}>
            <div className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono mb-2" style={{ color: '#475569' }}>Notebooks</div>
            <div className="space-y-0.5">
              {[undefined, ...allNotebooks].map((nb: string | undefined) => (
                <button
                  key={nb ?? "__all__"}
                  onClick={() => setSelectedNotebook(nb)}
                  className="w-full text-left px-2.5 py-1.5 rounded text-[11px] font-mono flex items-center gap-2 transition-all"
                  style={selectedNotebook === nb
                    ? { background: 'rgba(249,115,22,0.1)', color: '#f97316' }
                    : { color: '#475569' }
                  }
                  onMouseEnter={e => { if (selectedNotebook !== nb) (e.currentTarget as HTMLElement).style.color = '#374151'; }}
                  onMouseLeave={e => { if (selectedNotebook !== nb) (e.currentTarget as HTMLElement).style.color = '#475569'; }}
                >
                  <BookOpen className="w-3 h-3 shrink-0" />
                  {nb ?? "All Notes"}
                </button>
              ))}
            </div>
          </div>

          {/* Type Filter */}
          <div className="rounded-lg p-3 shrink-0" style={{ background: '#0d0d1a', border: '1px solid #111118' }}>
            <div className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono mb-2" style={{ color: '#475569' }}>Type</div>
            <div className="flex flex-wrap gap-1">
              {[undefined, ...NOTE_TYPES].map(t => (
                <button
                  key={t ?? "__all__"}
                  onClick={() => setSelectedType(t)}
                  className="px-2 py-0.5 rounded text-[9px] font-mono transition-all"
                  style={selectedType === t
                    ? { background: 'rgba(249,115,22,0.12)', border: '1px solid rgba(249,115,22,0.3)', color: '#f97316' }
                    : { background: '#09090f', border: '1px solid #0f0f1a', color: '#475569' }
                  }
                >
                  {t ?? "All"}
                </button>
              ))}
            </div>
          </div>

          {/* Note List */}
          <div className="rounded-lg p-3 flex-1 min-h-0 overflow-y-auto" style={{ background: '#0d0d1a', border: '1px solid #111118' }}>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-12 w-full" style={{ background: '#0a0a14' }} />)}
              </div>
            ) : notes?.length === 0 ? (
              <p className="text-[11px] font-mono text-center py-4" style={{ color: '#64748b' }}>No notes yet.</p>
            ) : (
              <div className="space-y-0.5">
                {notes?.map(note => (
                  <div
                    key={note.id}
                    className="p-2.5 rounded cursor-pointer group transition-all"
                    style={activeNoteId === note.id
                      ? { background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)' }
                      : { border: '1px solid transparent' }
                    }
                    onClick={() => setActiveNoteId(note.id)}
                    onMouseEnter={e => { if (activeNoteId !== note.id) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'; }}
                    onMouseLeave={e => { if (activeNoteId !== note.id) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-semibold truncate mb-1" style={{ color: activeNoteId === note.id ? '#f97316' : '#64748b' }}>{note.title}</div>
                        <div className="flex items-center gap-1">
                          <span className="text-[8px] font-mono tracking-wider px-1.5 py-0.5 rounded" style={typeStyle[note.noteType] ?? typeStyle["Quick Capture"]}>
                            {note.noteType}
                          </span>
                          {note.pinned && <Pin className="w-2.5 h-2.5" style={{ color: '#f97316' }} />}
                          {note.starred && <Star className="w-2.5 h-2.5" style={{ color: '#eab308' }} />}
                        </div>
                      </div>
                      <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button onClick={e => { e.stopPropagation(); togglePin(note.id, note.pinned); }} className="p-0.5" style={{ color: '#475569' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#f97316')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                        >
                          <Pin className="w-2.5 h-2.5" />
                        </button>
                        <button onClick={e => { e.stopPropagation(); toggleStar(note.id, note.starred); }} className="p-0.5" style={{ color: '#475569' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#eab308')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                        >
                          <Star className="w-2.5 h-2.5" />
                        </button>
                        <button onClick={e => { e.stopPropagation(); handleDelete(note.id); }} className="p-0.5" style={{ color: '#475569' }}
                          onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                          onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Note Editor */}
        <div className="lg:col-span-3 flex flex-col min-h-0">
          {activeNote ? (
            <div
              className="flex-1 min-h-0 p-5 flex flex-col gap-3 rounded-lg"
              style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}
            >
              <div className="flex items-center justify-between gap-3 shrink-0">
                <Input
                  value={editTitle}
                  onChange={e => setEditTitle(e.target.value)}
                  onBlur={handleTitleBlur}
                  className="font-mono text-sm font-bold flex-1 border-transparent bg-transparent px-0 focus-visible:ring-0 text-base"
                  style={{ color: '#e2e8f0', fontWeight: 800 }}
                />
                <div className="flex items-center gap-2 shrink-0">
                  {saved && <span className="text-[10px] font-mono" style={{ color: '#4ade80' }}>Saved</span>}
                  <button
                    onClick={() => setPreview(!preview)}
                    className="px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                    style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
                  >
                    {preview ? "Edit" : "Preview"}
                  </button>
                  <button
                    onClick={manualSave}
                    className="px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                    style={{ background: '#f97316', color: 'white' }}
                  >
                    Save
                  </button>
                </div>
              </div>
              {preview ? (
                <div className="flex-1 overflow-y-auto prose prose-invert prose-sm max-w-none font-mono text-sm leading-relaxed whitespace-pre-wrap" style={{ color: '#64748b' }}>
                  {editContent}
                </div>
              ) : (
                <Textarea
                  value={editContent}
                  onChange={e => handleContentChange(e.target.value)}
                  className="flex-1 font-mono text-sm resize-none leading-relaxed"
                  style={{ background: '#07070e', borderColor: '#0f0f1a', color: '#64748b' }}
                  placeholder="Start writing..."
                />
              )}
            </div>
          ) : (
            <div
              className="flex-1 flex items-center justify-center rounded-lg"
              style={{ background: '#09090f', border: '1px solid #0f0f1a' }}
            >
              <div className="text-center">
                <BookOpen className="w-10 h-10 mx-auto mb-3" style={{ color: '#0f0f1a' }} />
                <p className="text-sm font-mono" style={{ color: '#64748b' }}>Select a note or create a new one</p>
                <p className="text-[10px] font-mono mt-2" style={{ color: '#2e3a50' }}>Ctrl+N for quick capture</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

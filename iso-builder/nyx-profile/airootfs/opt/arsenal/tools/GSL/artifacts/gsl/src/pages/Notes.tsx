import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Trash2, Edit2, Save, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";

interface Note {
  id: number;
  toolId?: string;
  runId?: number;
  content: string;
  title?: string;
  createdAt: string;
  updatedAt: string;
}

function timeAgo(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function NoteCard({
  note,
  onEdit,
  onDelete,
}: {
  note: Note;
  onEdit: (note: Note) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <div
      className="group rounded-sm overflow-hidden transition-all duration-150"
      style={{
        background: "hsl(235 28% 6%)",
        border: "1px solid hsl(232 18% 12%)",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "hsl(263 55% 62% / 0.25)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "hsl(232 18% 12%)";
      }}
    >
      {/* Top accent */}
      <div className="h-px w-full" style={{ background: "linear-gradient(90deg, transparent, hsl(263 55% 62% / 0.2), transparent)" }} />

      <div className="px-4 pt-3.5 pb-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-sm mb-1 truncate" style={{ color: "hsl(220 20% 92%)" }}>
              {note.title || <span style={{ color: "hsl(232 10% 35%)", fontWeight: 400, fontStyle: "italic" }}>Untitled note</span>}
            </h3>
            <div className="flex items-center gap-2 text-[10px] font-mono" style={{ color: "hsl(232 10% 32%)" }}>
              <span>Updated {timeAgo(note.updatedAt)}</span>
              {note.toolId && (
                <>
                  <span style={{ color: "hsl(232 10% 22%)" }}>·</span>
                  <span style={{ color: "hsl(263 55% 55%)" }}>{note.toolId}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
            <button
              className="h-6 w-6 flex items-center justify-center rounded-sm transition-colors"
              style={{ color: "hsl(232 10% 35%)" }}
              onClick={() => onEdit(note)}
              onMouseEnter={(e) => (e.currentTarget.style.color = "hsl(263 55% 65%)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "hsl(232 10% 35%)")}
              title="Edit note"
            >
              <Edit2 className="h-3 w-3" />
            </button>
            <button
              className="h-6 w-6 flex items-center justify-center rounded-sm transition-colors"
              style={{ color: "hsl(232 10% 35%)" }}
              onClick={() => onDelete(note.id)}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#f87171")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "hsl(232 10% 35%)")}
              title="Delete note"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        </div>

        {/* Content */}
        <pre
          className="text-[12px] font-mono leading-relaxed whitespace-pre-wrap break-words line-clamp-6"
          style={{ color: "hsl(232 10% 50%)", fontFamily: "'JetBrains Mono', monospace" }}
        >
          {note.content}
        </pre>
      </div>
    </div>
  );
}

function NoteForm({
  title: initTitle,
  content: initContent,
  onSave,
  onCancel,
  label,
  isPending,
}: {
  title: string;
  content: string;
  onSave: (title: string, content: string) => void;
  onCancel: () => void;
  label: string;
  isPending: boolean;
}) {
  const [title, setTitle] = useState(initTitle);
  const [content, setContent] = useState(initContent);

  return (
    <div
      className="rounded-sm overflow-hidden"
      style={{
        background: "hsl(235 28% 6%)",
        border: "1px solid hsl(263 55% 62% / 0.3)",
        boxShadow: "0 0 20px hsl(263 55% 62% / 0.06)",
      }}
    >
      <div
        className="px-4 py-2.5 flex items-center gap-2 text-[11px] font-mono font-semibold uppercase tracking-wider"
        style={{ borderBottom: "1px solid hsl(232 18% 11%)", color: "hsl(263 55% 62%)" }}
      >
        <FileText className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="p-4 space-y-3">
        <Input
          placeholder="Title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="bg-background border-border/60 text-sm font-medium h-9"
          style={{ borderColor: "hsl(232 18% 14%)" }}
        />
        <textarea
          placeholder="Write your notes here... supports markdown, code blocks, IPs, commands..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          autoFocus
          className="note-editor w-full rounded-sm p-3"
          rows={7}
        />
        <div className="flex gap-2 justify-end">
          <button
            className="px-3 py-1.5 rounded-sm text-xs font-medium transition-colors"
            style={{ background: "hsl(235 22% 9%)", border: "1px solid hsl(232 18% 14%)", color: "hsl(232 10% 55%)" }}
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            className="px-3 py-1.5 rounded-sm text-xs font-semibold transition-all disabled:opacity-40"
            style={{
              background: "hsl(263 55% 62% / 0.15)",
              border: "1px solid hsl(263 55% 62% / 0.35)",
              color: "hsl(263 55% 75%)",
            }}
            onClick={() => onSave(title, content)}
            disabled={!content.trim() || isPending}
          >
            <Save className="h-3 w-3 inline mr-1" />
            Save Note
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Notes() {
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNote, setEditNote] = useState<Note | null>(null);
  const qc = useQueryClient();

  const { data: notes = [], isLoading } = useQuery<Note[]>({
    queryKey: ["notes"],
    queryFn: () => apiFetch<Note[]>("/api/notes"),
  });

  const createMutation = useMutation({
    mutationFn: ({ title, content }: { title?: string; content: string }) =>
      apiFetch("/api/notes", { method: "POST", body: JSON.stringify({ title: title || undefined, content }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notes"] }); setCreating(false); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, title, content }: { id: number; title?: string; content: string }) =>
      apiFetch(`/api/notes/${id}`, { method: "PATCH", body: JSON.stringify({ title: title || undefined, content }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["notes"] }); setEditingId(null); setEditNote(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/notes/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notes"] }),
  });

  const startEdit = (note: Note) => {
    setEditingId(note.id);
    setEditNote(note);
  };

  return (
    <div className="p-5 max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div
              className="w-8 h-8 rounded flex items-center justify-center"
              style={{ background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.2)" }}
            >
              <FileText className="h-4 w-4" style={{ color: "#fbbf24" }} />
            </div>
            <h2 className="text-xl font-bold tracking-tight">Research Notes</h2>
          </div>
          <p className="text-[11px] font-mono pl-0.5" style={{ color: "hsl(232 10% 38%)" }}>
            Document findings, credentials, attack chains, and methodology
          </p>
        </div>
        {!creating && (
          <button
            className="flex items-center gap-1.5 px-3 py-2 rounded-sm text-sm font-medium transition-all"
            style={{
              background: "hsl(263 55% 62% / 0.12)",
              border: "1px solid hsl(263 55% 62% / 0.3)",
              color: "hsl(263 55% 72%)",
            }}
            onClick={() => setCreating(true)}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "hsl(263 55% 62% / 0.18)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 0 12px hsl(263 55% 62% / 0.1)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "hsl(263 55% 62% / 0.12)";
              (e.currentTarget as HTMLButtonElement).style.boxShadow = "";
            }}
          >
            <Plus className="h-4 w-4" />
            New Note
          </button>
        )}
      </div>

      {/* Create form */}
      {creating && (
        <NoteForm
          title="" content=""
          label="New Note"
          isPending={createMutation.isPending}
          onSave={(title, content) => createMutation.mutate({ title, content })}
          onCancel={() => setCreating(false)}
        />
      )}

      {/* Notes list */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => <div key={i} className="shimmer h-36 rounded-sm" />)}
        </div>
      ) : notes.length === 0 && !creating ? (
        <div
          className="flex flex-col items-center justify-center py-24 rounded-sm text-center"
          style={{ background: "hsl(235 28% 6%)", border: "1px solid hsl(232 18% 12%)" }}
        >
          <div
            className="w-14 h-14 rounded-full flex items-center justify-center mb-4"
            style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.15)" }}
          >
            <FileText className="h-7 w-7" style={{ color: "#fbbf24" }} />
          </div>
          <h3 className="font-semibold text-base mb-1" style={{ color: "hsl(220 20% 75%)" }}>No notes yet</h3>
          <p className="text-sm max-w-sm mb-4" style={{ color: "hsl(232 10% 38%)" }}>
            Create a note to document findings, credentials, or research methodology.
          </p>
          <button
            className="flex items-center gap-1.5 px-3 py-2 rounded-sm text-sm font-medium"
            style={{
              background: "hsl(263 55% 62% / 0.12)",
              border: "1px solid hsl(263 55% 62% / 0.3)",
              color: "hsl(263 55% 72%)",
            }}
            onClick={() => setCreating(true)}
          >
            <Plus className="h-4 w-4" />
            Create First Note
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {notes.map((note) =>
            editingId === note.id && editNote ? (
              <NoteForm
                key={note.id}
                title={editNote.title ?? ""}
                content={editNote.content}
                label={`Editing: ${editNote.title || "Untitled"}`}
                isPending={updateMutation.isPending}
                onSave={(title, content) => updateMutation.mutate({ id: note.id, title, content })}
                onCancel={() => { setEditingId(null); setEditNote(null); }}
              />
            ) : (
              <NoteCard
                key={note.id}
                note={note}
                onEdit={startEdit}
                onDelete={(id) => deleteMutation.mutate(id)}
              />
            )
          )}
        </div>
      )}
    </div>
  );
}

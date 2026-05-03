import { useState, useEffect, useRef } from "react";
import { useStickies, NYXUS_COLORS, COLOR_LABELS, NoteColor, Note } from "@/hooks/use-stickies";
import { Pin, X, Plus, Trash2, Search } from "lucide-react";

// Ink color for each sticky background (dark for readability)
const INK: Record<string, string> = {
  '#fef08a': '#2a2000',
  '#fda4af': '#2a0008',
  '#93c5fd': '#001428',
  '#86efac': '#002214',
  '#e9d5ff': '#1a0030',
  '#fdba74': '#2a1200',
};

const LINE_COLOR: Record<string, string> = {
  '#fef08a': 'rgba(0,0,0,0.08)',
  '#fda4af': 'rgba(0,0,0,0.07)',
  '#93c5fd': 'rgba(0,0,0,0.07)',
  '#86efac': 'rgba(0,0,0,0.07)',
  '#e9d5ff': 'rgba(0,0,0,0.07)',
  '#fdba74': 'rgba(0,0,0,0.08)',
};

// Neon glow colors for the app chrome
const NEON_PINK  = '#ff00ff';
const NEON_BLUE  = '#0088ff';
const NEON_GREEN = '#39ff14';

function StickyNote({ note, updateNote, deleteNote, togglePin }:
  { note: Note; updateNote: (id: string, u: Partial<Note>) => void;
    deleteNote: (id: string) => void; togglePin: (id: string) => void; }) {

  const [title, setTitle]     = useState(note.title);
  const [content, setContent] = useState(note.content);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ink = INK[note.color] ?? '#1a1a2e';
  const lineCol = LINE_COLOR[note.color] ?? 'rgba(0,0,0,0.07)';

  // auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [content]);

  // debounced save
  useEffect(() => {
    const t = setTimeout(() => {
      if (title !== note.title || content !== note.content)
        updateNote(note.id, { title, content });
    }, 600);
    return () => clearTimeout(t);
  }, [title, content]);

  return (
    <div
      className="group relative flex flex-col select-none"
      style={{
        width: 210,
        minHeight: 200,
        background: note.color,
        transform: `rotate(${note.rotation}deg)`,
        boxShadow: `4px 6px 20px rgba(0,0,0,0.55), 1px 1px 0 rgba(255,255,255,0.25) inset`,
        fontFamily: "'Caveat', 'Patrick Hand', cursive",
        color: ink,
        borderRadius: 2,
        cursor: 'default',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease',
        backgroundImage: [
          `repeating-linear-gradient(transparent, transparent 27px, ${lineCol} 27px, ${lineCol} 28px)`,
        ].join(','),
        backgroundSize: '100% 28px',
        backgroundPositionY: '36px',
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.transform = `rotate(${note.rotation * 0.4}deg) scale(1.04)`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = `8px 14px 32px rgba(0,0,0,0.70), 1px 1px 0 rgba(255,255,255,0.25) inset`;
        (e.currentTarget as HTMLDivElement).style.zIndex = '50';
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.transform = `rotate(${note.rotation}deg) scale(1)`;
        (e.currentTarget as HTMLDivElement).style.boxShadow = `4px 6px 20px rgba(0,0,0,0.55), 1px 1px 0 rgba(255,255,255,0.25) inset`;
        (e.currentTarget as HTMLDivElement).style.zIndex = '1';
      }}
    >
      {/* Top tape strip */}
      <div style={{
        position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
        width: 52, height: 20, borderRadius: 2,
        background: 'rgba(255,255,255,0.45)',
        backdropFilter: 'blur(2px)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
      }} />

      {/* Header bar */}
      <div style={{ padding: '14px 10px 6px', borderBottom: `1px solid ${lineCol}`, display: 'flex', alignItems: 'center', gap: 4 }}>
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Title…"
          style={{
            flex: 1, background: 'transparent', border: 'none', outline: 'none',
            fontFamily: "'Caveat', cursive", fontSize: 18, fontWeight: 700,
            color: ink, width: '100%',
          }}
        />
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            onClick={() => togglePin(note.id)}
            title="Pin"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: note.isPinned ? '#ff2255' : ink, opacity: 0.7 }}
          >
            <Pin size={13} fill={note.isPinned ? 'currentColor' : 'none'} />
          </button>
          <button
            onClick={() => deleteNote(note.id)}
            title="Delete"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: '#cc0022', opacity: 0.7 }}
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '6px 10px 10px', flex: 1 }}>
        <textarea
          ref={textareaRef}
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="Write something…"
          style={{
            width: '100%', minHeight: 80,
            background: 'transparent', border: 'none', outline: 'none', resize: 'none',
            fontFamily: "'Caveat', cursive", fontSize: 16, lineHeight: '28px',
            color: ink, overflow: 'hidden',
          }}
          spellCheck={false}
        />
      </div>

      {/* Color picker — hover footer */}
      <div
        className="opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ padding: '6px 10px', display: 'flex', gap: 6, justifyContent: 'center', background: 'rgba(0,0,0,0.08)', borderTop: `1px solid ${lineCol}` }}
      >
        {NYXUS_COLORS.map(c => (
          <button
            key={c}
            onClick={() => updateNote(note.id, { color: c as NoteColor })}
            title={COLOR_LABELS[c as NoteColor]}
            style={{
              width: 16, height: 16, borderRadius: '50%',
              background: c, border: note.color === c ? '2.5px solid #222' : '2px solid rgba(0,0,0,0.25)',
              cursor: 'pointer', transform: note.color === c ? 'scale(1.3)' : 'scale(1)',
              transition: 'transform 0.15s',
              boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
            }}
          />
        ))}
      </div>

      {/* Pin badge */}
      {note.isPinned && (
        <div style={{
          position: 'absolute', top: -6, right: 10,
          background: '#ff2255', borderRadius: '50%', width: 14, height: 14,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 6px rgba(255,34,85,0.6)',
        }}>
          <Pin size={8} color="#fff" fill="#fff" />
        </div>
      )}
    </div>
  );
}

export default function Stickies() {
  const { notes, addNote, updateNote, deleteNote, clearAll, togglePin, isLoaded } = useStickies();
  const [search, setSearch] = useState('');
  const [confirmClear, setConfirmClear] = useState(false);

  if (!isLoaded) return null;

  const visible = search
    ? notes.filter(n =>
        n.title.toLowerCase().includes(search.toLowerCase()) ||
        n.content.toLowerCase().includes(search.toLowerCase()))
    : notes;

  return (
    <div
      className="flex flex-col"
      style={{
        width: '100%', height: '100vh',
        background: '#0a0a12',
        backgroundImage: 'repeating-linear-gradient(transparent, transparent 27px, rgba(255,255,255,0.045) 27px, rgba(255,255,255,0.045) 28px)',
        fontFamily: "'Caveat', 'Patrick Hand', cursive",
        overflow: 'hidden',
      }}
    >
      {/* ── Toolbar ─────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '0 18px',
        height: 56, flexShrink: 0,
        borderBottom: `2px solid ${NEON_PINK}33`,
        background: 'rgba(10,10,20,0.96)',
        boxShadow: `0 0 24px rgba(255,0,255,0.08)`,
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 4 }}>
          <span style={{
            fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: 22,
            color: NEON_PINK, textShadow: `0 0 12px ${NEON_PINK}88, 0 0 24px ${NEON_PINK}44`,
            letterSpacing: 1,
          }}>◈ NYXUS Stickies</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: `${NEON_PINK}55`, letterSpacing: '0.22em', marginLeft: 4 }}>NYX-J5W-2026</span>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', flex: 1, maxWidth: 280 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'rgba(255,255,255,0.3)' }} />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="search notes…"
            style={{
              width: '100%', paddingLeft: 32, paddingRight: 12, paddingTop: 6, paddingBottom: 6,
              background: 'rgba(255,255,255,0.05)',
              border: `1.5px solid rgba(255,255,255,0.12)`,
              borderRadius: 6, outline: 'none',
              fontFamily: "'Caveat', cursive", fontSize: 16,
              color: 'rgba(255,255,255,0.75)',
            }}
          />
        </div>

        {/* Note count */}
        <span style={{
          fontFamily: "'Caveat', cursive", fontSize: 15,
          color: NEON_BLUE, borderRadius: 20,
          border: `1.5px solid ${NEON_BLUE}55`,
          padding: '2px 12px',
          background: `${NEON_BLUE}11`,
        }}>
          {visible.length} note{visible.length !== 1 ? 's' : ''}
        </span>

        <div style={{ flex: 1 }} />

        {/* Clear */}
        {notes.length > 0 && (
          confirmClear ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: '#ff7755', fontSize: 15, fontFamily: "'Caveat', cursive" }}>Delete all?</span>
              <button onClick={() => { clearAll(); setConfirmClear(false); }} style={dangerBtnStyle}>Yes</button>
              <button onClick={() => setConfirmClear(false)} style={ghostBtnStyle}>No</button>
            </div>
          ) : (
            <button onClick={() => setConfirmClear(true)} style={{ ...ghostBtnStyle, display: 'flex', alignItems: 'center', gap: 5 }}>
              <Trash2 size={13} /> Clear
            </button>
          )
        )}

        {/* Add note */}
        <button
          onClick={addNote}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: 17,
            color: '#000', background: NEON_GREEN,
            border: 'none', borderRadius: 6, padding: '6px 18px',
            cursor: 'pointer', boxShadow: `0 0 16px ${NEON_GREEN}55`,
            transition: 'box-shadow 0.2s',
          }}
          onMouseEnter={e => (e.currentTarget.style.boxShadow = `0 0 28px ${NEON_GREEN}88`)}
          onMouseLeave={e => (e.currentTarget.style.boxShadow = `0 0 16px ${NEON_GREEN}55`)}
        >
          <Plus size={16} /> New Note
        </button>
      </div>

      {/* ── Color key strip ─────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '6px 20px',
        background: 'rgba(0,0,0,0.25)', borderBottom: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
      }}>
        <span style={{ color: 'rgba(255,255,255,0.3)', fontFamily: "'Caveat', cursive", fontSize: 14 }}>Colors:</span>
        {NYXUS_COLORS.map(c => (
          <span key={c} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{
              display: 'inline-block', width: 14, height: 14, borderRadius: '50%',
              background: c, border: '1.5px solid rgba(0,0,0,0.3)',
              boxShadow: '0 1px 4px rgba(0,0,0,0.4)',
            }} />
            <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, fontFamily: "'Caveat', cursive" }}>{COLOR_LABELS[c as NoteColor]}</span>
          </span>
        ))}
      </div>

      {/* ── Board ───────────────────────────────────────────────── */}
      <div
        className="flex-1 overflow-auto"
        style={{ padding: 32 }}
      >
        {visible.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            height: '100%', gap: 20,
          }}>
            <div style={{
              fontFamily: "'Caveat', cursive", fontSize: 22,
              color: 'rgba(255,255,255,0.2)', border: '2px dashed rgba(255,255,255,0.1)',
              padding: '24px 40px', borderRadius: 8, textAlign: 'center',
            }}>
              {search ? `No notes match "${search}"` : 'Board is empty — add your first note!'}
            </div>
            {!search && (
              <button
                onClick={addNote}
                style={{
                  fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: 20,
                  color: NEON_PINK, background: `${NEON_PINK}18`,
                  border: `2px solid ${NEON_PINK}55`, borderRadius: 6,
                  padding: '10px 32px', cursor: 'pointer',
                  boxShadow: `0 0 20px ${NEON_PINK}30`,
                }}
              >
                + Create Note
              </button>
            )}
          </div>
        ) : (
          <div
            style={{
              display: 'flex', flexWrap: 'wrap', gap: 36,
              alignItems: 'flex-start', alignContent: 'flex-start',
            }}
          >
            {visible.map(note => (
              <StickyNote
                key={note.id}
                note={note}
                updateNote={updateNote}
                deleteNote={deleteNote}
                togglePin={togglePin}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const ghostBtnStyle: React.CSSProperties = {
  fontFamily: "'Caveat', cursive", fontWeight: 600, fontSize: 16,
  color: 'rgba(255,255,255,0.5)', background: 'transparent',
  border: '1px solid rgba(255,255,255,0.15)', borderRadius: 6,
  padding: '4px 12px', cursor: 'pointer',
};

const dangerBtnStyle: React.CSSProperties = {
  fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: 16,
  color: '#fff', background: '#cc2233',
  border: 'none', borderRadius: 6,
  padding: '4px 12px', cursor: 'pointer',
};

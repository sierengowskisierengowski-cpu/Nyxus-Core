import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Plus, Search, Star, Trash2, Eye, Edit2, Copy, Download,
  Bold, Italic, Heading1, List, Code, X, Check, Save, Clipboard
} from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import { format } from 'date-fns';
import { useToast } from '@/hooks/use-toast';

/* ── Design tokens ──────────────────────────────────────────────── */
const BG       = '#08080e';
const PANEL    = '#0d0d1a';
const BORDER   = 'rgba(255,255,255,0.07)';
const RULED    = 'rgba(255,255,255,0.05)';
const PINK     = '#ff00ff';
const PURPLE   = '#cc00ff';
const BLUE     = '#0088ff';
const GREEN    = '#39ff14';
const ORANGE   = '#ff5500';
const DIM      = 'rgba(255,255,255,0.35)';
const TEXT     = 'rgba(255,255,255,0.88)';
const FONT     = "'Caveat', 'Patrick Hand', cursive";

const ruledBg = {
  backgroundImage: `repeating-linear-gradient(transparent, transparent 27px, ${RULED} 27px, ${RULED} 28px)`,
};

/* ── Types ──────────────────────────────────────────────────────── */
interface Note {
  id: string; title: string; content: string;
  createdAt: number; updatedAt: number; isPinned: boolean;
}
interface ClipEntry {
  id: string; text: string; timestamp: number; charCount: number;
}

/* ── Small components ───────────────────────────────────────────── */
function NeonButton({ children, onClick, color = PINK, small = false, filled = false, style: extra = {} }:
  { children: React.ReactNode; onClick?: () => void; color?: string; small?: boolean; filled?: boolean; style?: React.CSSProperties }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        fontFamily: FONT, fontWeight: 700, fontSize: small ? 14 : 17,
        color: filled ? '#000' : color,
        background: filled ? color : hov ? `${color}22` : 'transparent',
        border: `2px solid ${color}`,
        borderRadius: 5, padding: small ? '3px 10px' : '6px 16px',
        cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5,
        boxShadow: hov ? `0 0 16px ${color}55` : `0 0 6px ${color}22`,
        transition: 'all 0.15s',
        ...extra,
      }}>
      {children}
    </button>
  );
}

function IconBtn({ icon: Icon, onClick, color = DIM, title = '' }: { icon: any; onClick?: () => void; color?: string; title?: string }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} title={title}
      onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? `${color}22` : 'transparent',
        border: 'none', borderRadius: 4, padding: '5px 6px',
        color: hov ? color : DIM, cursor: 'pointer', display: 'flex', alignItems: 'center',
        transition: 'all 0.15s',
      }}>
      <Icon size={15} />
    </button>
  );
}

/* ── Main component ──────────────────────────────────────────────── */
export default function Notepad() {
  const { toast } = useToast();

  const [notes, setNotes] = useState<Note[]>(() => {
    try { return JSON.parse(localStorage.getItem('nyxus_notes') || '[]'); } catch { return []; }
  });
  const [clipboardHistory, setClipboardHistory] = useState<ClipEntry[]>(() => {
    try { return JSON.parse(localStorage.getItem('nyxus_clipboard') || '[]'); } catch { return []; }
  });
  const [activeNoteId, setActiveNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery]   = useState('');
  const [isPreview, setIsPreview]       = useState(false);
  const [content, setContent]           = useState('');
  const [title, setTitle]               = useState('');
  const [isSaving, setIsSaving]         = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  const activeNote = notes.find(n => n.id === activeNoteId) ?? null;
  const wordCount  = content.trim() ? content.trim().split(/\s+/).length : 0;

  const filteredNotes = notes.filter(n =>
    n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    n.content.toLowerCase().includes(searchQuery.toLowerCase())
  ).sort((a, b) => {
    if (a.isPinned !== b.isPinned) return a.isPinned ? -1 : 1;
    return b.updatedAt - a.updatedAt;
  });

  // init first note selection
  useEffect(() => {
    if (notes.length > 0 && !activeNoteId) setActiveNoteId(notes[0].id);
  }, []);

  useEffect(() => {
    if (activeNote) { setContent(activeNote.content); setTitle(activeNote.title); }
    else { setContent(''); setTitle(''); }
  }, [activeNoteId]);

  useEffect(() => { localStorage.setItem('nyxus_notes', JSON.stringify(notes)); }, [notes]);
  useEffect(() => { localStorage.setItem('nyxus_clipboard', JSON.stringify(clipboardHistory)); }, [clipboardHistory]);

  // autosave
  useEffect(() => {
    if (!activeNoteId || !activeNote) return;
    if (content === activeNote.content && title === activeNote.title) return;
    setIsSaving(true);
    const t = setTimeout(() => {
      setNotes(prev => prev.map(n => n.id === activeNoteId ? { ...n, content, title, updatedAt: Date.now() } : n));
      setIsSaving(false);
    }, 1800);
    return () => clearTimeout(t);
  }, [content, title, activeNoteId]);

  // keyboard
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') { e.preventDefault(); createNote(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (activeNoteId) { setNotes(prev => prev.map(n => n.id === activeNoteId ? { ...n, content, title, updatedAt: Date.now() } : n)); setIsSaving(false); }
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'p') { e.preventDefault(); setIsPreview(p => !p); }
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [activeNoteId, content, title]);

  const createNote = () => {
    const n: Note = { id: uuidv4(), title: '', content: '', createdAt: Date.now(), updatedAt: Date.now(), isPinned: false };
    setNotes(prev => [n, ...prev]); setActiveNoteId(n.id); setIsPreview(false);
    setTimeout(() => document.getElementById('note-title-input')?.focus(), 50);
  };

  const deleteNote = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!confirm('Delete this note?')) return;
    setNotes(prev => prev.filter(n => n.id !== id));
    if (activeNoteId === id) setActiveNoteId(null);
  };

  const togglePin = (id: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setNotes(prev => prev.map(n => n.id === id ? { ...n, isPinned: !n.isPinned, updatedAt: Date.now() } : n));
  };

  const insertMarkdown = (pre: string, suf = '') => {
    if (!editorRef.current) return;
    const { selectionStart: s, selectionEnd: e } = editorRef.current;
    const sel = content.substring(s, e);
    const next = content.substring(0, s) + pre + sel + suf + content.substring(e);
    setContent(next);
    setTimeout(() => editorRef.current?.setSelectionRange(s + pre.length, e + pre.length), 0);
  };

  const addClipEntry = (text: string) => {
    setClipboardHistory(prev => {
      if (prev.length && prev[0].text === text) return prev;
      return [{ id: uuidv4(), text, timestamp: Date.now(), charCount: text.length }, ...prev].slice(0, 50);
    });
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const t = e.clipboardData.getData('text');
    if (t) addClipEntry(t);
  };

  const captureClipboard = async () => {
    try {
      const t = await navigator.clipboard.readText();
      if (t) { addClipEntry(t); toast({ title: 'Captured', description: 'Clipboard added to history.' }); }
    } catch {
      toast({ title: 'Error', description: 'Clipboard permission denied.', variant: 'destructive' });
    }
  };

  const downloadNote = () => {
    if (!activeNote) return;
    const blob = new Blob([content], { type: 'text/plain' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: `${title || 'note'}.md` });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  const renderMarkdown = (text: string) => {
    if (!text) return { __html: `<p style="color:${DIM};font-style:italic">Empty note…</p>` };
    const html = text
      .replace(/^### (.*)$/gim, `<h3 style="color:${PURPLE};font-size:22px;margin:16px 0 6px;font-family:${FONT}">$1</h3>`)
      .replace(/^## (.*)$/gim,  `<h2 style="color:${PINK};font-size:26px;margin:20px 0 8px;font-family:${FONT};text-shadow:0 0 8px ${PINK}66">$1</h2>`)
      .replace(/^# (.*)$/gim,   `<h1 style="color:${GREEN};font-size:32px;margin:24px 0 10px;font-family:${FONT};text-shadow:0 0 12px ${GREEN}66">$1</h1>`)
      .replace(/\*\*(.*?)\*\*/gim, `<strong style="color:${TEXT}">$1</strong>`)
      .replace(/\*(.*?)\*/gim,     `<em>$1</em>`)
      .replace(/```([\s\S]*?)```/gim, `<pre style="background:#0d0020;border:1px solid ${PURPLE}44;padding:12px;margin:10px 0;border-radius:4px;overflow-x:auto"><code style="font-family:monospace;font-size:14px;color:${GREEN}">$1</code></pre>`)
      .replace(/`(.*?)`/gim, `<code style="background:rgba(204,0,255,0.15);padding:1px 5px;border-radius:3px;font-family:monospace;font-size:14px;color:${PURPLE}">$1</code>`)
      .replace(/^\- (.*)$/gim, `<li style="margin-left:16px;list-style:disc;color:${TEXT}">$1</li>`)
      .replace(/^\> (.*)$/gim, `<blockquote style="border-left:3px solid ${PINK};padding-left:12px;color:${DIM};font-style:italic;margin:8px 0">$1</blockquote>`)
      .replace(/\n/g, '<br/>');
    return { __html: html };
  };

  /* ── Layout ──────────────────────────────────────────────────── */
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', background: BG, fontFamily: FONT, color: TEXT, overflow: 'hidden' }}>

      {/* ══ LEFT SIDEBAR ══════════════════════════════════════════ */}
      <div style={{
        width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column',
        borderRight: `1px solid ${PINK}33`, background: PANEL, ...ruledBg,
      }}>
        {/* Logo */}
        <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>📓</span>
          <span style={{ fontFamily: FONT, fontWeight: 700, fontSize: 22, color: PINK, textShadow: `0 0 14px ${PINK}66` }}>NYXUS Notepad</span>
        </div>

        {/* New note btn */}
        <div style={{ padding: '10px 12px' }}>
          <button onClick={createNote} style={{
            width: '100%', fontFamily: FONT, fontWeight: 700, fontSize: 18,
            color: '#000', background: PINK, border: 'none', borderRadius: 6,
            padding: '8px 0', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            boxShadow: `0 0 20px ${PINK}44`,
          }}>
            <Plus size={17} /> New Note
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: '0 12px 10px', position: 'relative' }}>
          <Search size={13} style={{ position: 'absolute', left: 22, top: '50%', transform: 'translateY(-50%)', color: DIM }} />
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)} placeholder="Search notes…"
            style={{
              width: '100%', paddingLeft: 30, paddingRight: 10, paddingTop: 6, paddingBottom: 6,
              background: 'rgba(255,255,255,0.05)', border: `1px solid ${BORDER}`, borderRadius: 5,
              fontFamily: FONT, fontSize: 16, color: TEXT, outline: 'none',
            }}
          />
        </div>

        {/* Note list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px 8px' }}>
          {filteredNotes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 12px', color: DIM, fontSize: 16, border: `1px dashed ${BORDER}`, margin: '8px 4px', borderRadius: 6 }}>
              {searchQuery ? 'No matches found.' : 'No notes yet.'}
            </div>
          ) : filteredNotes.map(note => (
            <div key={note.id} onClick={() => setActiveNoteId(note.id)}
              style={{
                padding: '10px 12px', borderRadius: 6, cursor: 'pointer', marginBottom: 4,
                background: activeNoteId === note.id ? `${PINK}18` : 'transparent',
                borderLeft: activeNoteId === note.id ? `3px solid ${PINK}` : '3px solid transparent',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { if (activeNoteId !== note.id) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)'; }}
              onMouseLeave={e => { if (activeNoteId !== note.id) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontWeight: 700, fontSize: 17, color: activeNoteId === note.id ? PINK : TEXT, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {note.title || 'Untitled Note'}
                </span>
                <div style={{ display: 'flex', gap: 3, marginLeft: 4 }}>
                  <button onClick={e => togglePin(note.id, e)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: note.isPinned ? '#ffcc00' : DIM, padding: 2 }}>
                    <Star size={11} fill={note.isPinned ? 'currentColor' : 'none'} />
                  </button>
                  <button onClick={e => deleteNote(note.id, e)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ff4444', padding: 2 }}>
                    <Trash2 size={11} />
                  </button>
                </div>
              </div>
              <p style={{ fontSize: 14, color: DIM, marginTop: 3, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {note.content || '…'}
              </p>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', marginTop: 4 }}>
                {format(note.updatedAt, 'MMM dd, HH:mm')}
              </div>
            </div>
          ))}
        </div>

        {/* Stats footer */}
        <div style={{ padding: '8px 14px', borderTop: `1px solid ${BORDER}`, fontSize: 13, color: DIM, display: 'flex', gap: 12 }}>
          <span style={{ color: PINK }}>{notes.length}</span> notes
          <span style={{ color: BLUE }}>{wordCount}</span> words
        </div>
      </div>

      {/* ══ EDITOR ════════════════════════════════════════════════ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: BG, ...ruledBg }}>
        {activeNote ? (<>
          {/* Editor toolbar */}
          <div style={{
            height: 54, borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center',
            padding: '0 16px', gap: 8, background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)', flexShrink: 0,
          }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <input id="note-title-input" value={title} onChange={e => setTitle(e.target.value)}
                placeholder="Note title…"
                style={{
                  background: 'transparent', border: 'none', outline: 'none',
                  fontFamily: FONT, fontWeight: 700, fontSize: 22, color: TEXT,
                  width: '100%',
                }}
              />
              <div style={{ fontSize: 12, color: DIM, marginTop: -2 }}>
                {format(activeNote.createdAt, 'MMM dd yyyy')} · {format(activeNote.updatedAt, 'HH:mm')}
              </div>
            </div>

            {/* Markdown tools */}
            {!isPreview && (
              <div style={{ display: 'flex', gap: 2, padding: '3px 6px', background: 'rgba(255,255,255,0.04)', borderRadius: 6, border: `1px solid ${BORDER}` }}>
                <IconBtn icon={Bold}    onClick={() => insertMarkdown('**','**')} color={PINK}   title="Bold" />
                <IconBtn icon={Italic}  onClick={() => insertMarkdown('*','*')}   color={PURPLE} title="Italic" />
                <IconBtn icon={Heading1} onClick={() => insertMarkdown('# ','')} color={GREEN}  title="Heading" />
                <IconBtn icon={List}    onClick={() => insertMarkdown('- ','')}   color={BLUE}   title="List" />
                <IconBtn icon={Code}    onClick={() => insertMarkdown('```\n','\n```')} color={ORANGE} title="Code" />
              </div>
            )}

            <NeonButton color={isPreview ? GREEN : BLUE} small onClick={() => setIsPreview(p => !p)}>
              {isPreview ? <><Edit2 size={13}/> Edit</> : <><Eye size={13}/> Preview</>}
            </NeonButton>
            <IconBtn icon={Download} onClick={downloadNote} color={PURPLE} title="Download .md" />
          </div>

          {/* Editor area */}
          <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
            {isPreview ? (
              <div style={{ position: 'absolute', inset: 0, overflowY: 'auto', padding: '28px 36px', maxWidth: 740, margin: '0 auto' }}>
                <div style={{ fontFamily: FONT, fontSize: 18, lineHeight: '28px', color: TEXT }}
                  dangerouslySetInnerHTML={renderMarkdown(content)} />
              </div>
            ) : (
              <textarea ref={editorRef} value={content}
                onChange={e => setContent(e.target.value)} onPaste={handlePaste}
                placeholder="Start writing…"
                style={{
                  position: 'absolute', inset: 0, width: '100%', height: '100%',
                  background: 'transparent', border: 'none', outline: 'none', resize: 'none',
                  fontFamily: FONT, fontSize: 18, lineHeight: '28px',
                  color: TEXT, padding: '8px 36px',
                  caretColor: PINK,
                }}
                spellCheck={false}
              />
            )}
          </div>

          {/* Status bar */}
          <div style={{
            height: 32, borderTop: `1px solid ${BORDER}`, display: 'flex',
            alignItems: 'center', justifyContent: 'space-between', padding: '0 16px',
            background: 'rgba(0,0,0,0.5)', fontSize: 13, color: DIM, flexShrink: 0,
          }}>
            <div style={{ display: 'flex', gap: 16 }}>
              <span><span style={{ color: PINK }}>{wordCount}</span> words</span>
              <span><span style={{ color: BLUE }}>{content.length}</span> chars</span>
              <span><span style={{ color: GREEN }}>{notes.length}</span> notes total</span>
            </div>
            <div>
              {isSaving
                ? <span style={{ color: ORANGE, display: 'flex', alignItems: 'center', gap: 4 }}><Save size={11}/> saving…</span>
                : <span style={{ color: GREEN, display: 'flex', alignItems: 'center', gap: 4 }}><Check size={11}/> saved</span>}
            </div>
          </div>
        </>) : (
          /* Empty state */
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
            <div style={{ fontSize: 60 }}>📝</div>
            <div style={{ fontFamily: FONT, fontSize: 26, color: DIM, textAlign: 'center' }}>
              Select a note or create one
            </div>
            <button onClick={createNote} style={{
              fontFamily: FONT, fontWeight: 700, fontSize: 20, color: '#000',
              background: PINK, border: 'none', borderRadius: 6, padding: '10px 32px',
              cursor: 'pointer', boxShadow: `0 0 24px ${PINK}44`,
            }}>
              + New Note
            </button>
          </div>
        )}
      </div>

      {/* ══ CLIPBOARD SIDEBAR ════════════════════════════════════ */}
      <div style={{
        width: 280, flexShrink: 0, display: 'flex', flexDirection: 'column',
        borderLeft: `1px solid ${BLUE}44`, background: PANEL, ...ruledBg,
      }}>
        {/* Header */}
        <div style={{ padding: '14px 14px 10px', borderBottom: `1px solid ${BORDER}`, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: FONT, fontWeight: 700, fontSize: 18, color: BLUE, textShadow: `0 0 10px ${BLUE}66` }}>
            <Clipboard size={15} /> Clipboard
          </div>
          <button onClick={captureClipboard} style={{
            fontFamily: FONT, fontWeight: 600, fontSize: 14, color: BLUE,
            background: `${BLUE}18`, border: `1.5px solid ${BLUE}55`, borderRadius: 5,
            padding: '3px 10px', cursor: 'pointer',
          }}>Capture</button>
        </div>

        {/* Entries */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
          {clipboardHistory.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 12px', color: DIM, fontSize: 15, border: `1px dashed ${BORDER}`, margin: '8px 4px', borderRadius: 6 }}>
              Copy text or click Capture<br/>to fill history.
            </div>
          ) : (<>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
              <button onClick={() => { if (confirm('Clear clipboard history?')) setClipboardHistory([]); }}
                style={{ fontFamily: FONT, fontSize: 13, color: ORANGE, background: 'none', border: 'none', cursor: 'pointer' }}>
                Clear all
              </button>
            </div>
            {clipboardHistory.map(entry => (
              <div key={entry.id} style={{
                background: 'rgba(255,255,255,0.04)', border: `1px solid ${BORDER}`, borderRadius: 5,
                padding: '8px 10px', marginBottom: 6,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 6 }}>
                  <p style={{
                    fontFamily: FONT, fontSize: 15, color: TEXT, margin: 0, flex: 1,
                    overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                  }}>
                    {entry.text}
                  </p>
                  <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                    <button onClick={() => { navigator.clipboard.writeText(entry.text); toast({ title: 'Copied' }); }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: BLUE, padding: 2 }}>
                      <Copy size={12} />
                    </button>
                    {activeNoteId && (
                      <button onClick={() => setContent(p => p + '\n' + entry.text)}
                        style={{ fontFamily: FONT, fontSize: 11, color: GREEN, background: 'none', border: `1px solid ${GREEN}55`, borderRadius: 3, padding: '1px 5px', cursor: 'pointer' }}>
                        Insert
                      </button>
                    )}
                    <button onClick={() => setClipboardHistory(p => p.filter(e => e.id !== entry.id))}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ff4444', padding: 2 }}>
                      <X size={12} />
                    </button>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 12, color: DIM }}>
                  <span>{entry.charCount} chars</span>
                  <span>{format(entry.timestamp, 'HH:mm')}</span>
                </div>
              </div>
            ))}
          </>)}
        </div>
      </div>
    </div>
  );
}

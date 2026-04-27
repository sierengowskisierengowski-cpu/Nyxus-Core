import { useState, useEffect, useRef } from "react";
import { useStickies, NYXUS_COLORS, NoteColor, Note } from "@/hooks/use-stickies";
import { Plus, X, Pin, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";

function StickyNote({ 
  note, 
  updateNote, 
  deleteNote, 
  togglePin 
}: { 
  note: Note; 
  updateNote: (id: string, updates: Partial<Note>) => void;
  deleteNote: (id: string) => void;
  togglePin: (id: string) => void;
}) {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);
  
  // Debounced save
  useEffect(() => {
    const timer = setTimeout(() => {
      if (title !== note.title || content !== note.content) {
        updateNote(note.id, { title, content });
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [title, content, note.id, note.title, note.content, updateNote]);

  // Adjust textarea height automatically
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [content]);

  return (
    <div 
      className={`group relative flex flex-col w-[200px] min-h-[120px] transition-all duration-300 ease-out hover:scale-[1.02] hover:z-10 animate-in fade-in zoom-in-95 ${note.isPinned ? 'animate-neon-pulse' : 'neon-border'}`}
      style={{
        color: note.color,
        transform: `rotate(${note.rotation}deg)`,
        backgroundColor: `${note.color}10`, // 10% opacity background
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b border-current border-opacity-30 bg-black/40">
        <input 
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="bg-transparent border-none outline-none text-xs font-bold w-full mr-2 neon-text focus:ring-0 uppercase placeholder:text-current/50"
          placeholder="TITLE..."
        />
        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button 
            onClick={() => togglePin(note.id)}
            className={`p-1 rounded hover:bg-current/20 transition-colors ${note.isPinned ? 'opacity-100 bg-current/20' : 'opacity-70'}`}
          >
            <Pin size={12} className={note.isPinned ? 'fill-current' : ''} />
          </button>
          <button 
            onClick={() => deleteNote(note.id)}
            className="p-1 rounded hover:bg-red-500/20 text-red-500 transition-colors"
          >
            <X size={12} />
          </button>
        </div>
      </div>
      
      {/* Body */}
      <div className="p-3 flex-1 flex flex-col">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="flex-1 bg-transparent border-none outline-none text-sm resize-none overflow-hidden text-[#e8e0f5] placeholder:text-[#e8e0f5]/30 focus:ring-0 font-mono leading-relaxed"
          placeholder="Enter memory data..."
          spellCheck={false}
        />
      </div>

      {/* Color Picker Footer (only on hover) */}
      <div className="absolute bottom-0 left-0 right-0 p-2 flex justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/80 to-transparent pointer-events-none group-hover:pointer-events-auto">
        {NYXUS_COLORS.map(color => (
          <button
            key={color}
            onClick={() => updateNote(note.id, { color })}
            className={`w-3 h-3 rounded-full cursor-pointer transition-transform hover:scale-125 ${note.color === color ? 'ring-2 ring-white scale-110' : ''}`}
            style={{ backgroundColor: color, boxShadow: `0 0 5px ${color}` }}
            aria-label={`Set color to ${color}`}
          />
        ))}
      </div>
    </div>
  );
}

export default function Stickies() {
  const { notes, addNote, updateNote, deleteNote, clearAll, togglePin, isLoaded } = useStickies();
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  if (!isLoaded) return null;

  return (
    <div className="w-full min-h-screen sm:h-screen sm:w-full flex flex-col bg-background text-foreground bg-grid-pattern relative overflow-hidden font-mono">
      {/* Toolbar */}
      <div className="h-12 border-b border-nyxus-pink/30 flex items-center justify-between px-4 bg-black/60 backdrop-blur-sm z-20 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-nyxus-pink font-bold text-sm tracking-wider neon-text" style={{ color: '#ff00ff' }}>
            NYXUS_STICKIES
          </h1>
          <div className="text-xs px-2 py-0.5 rounded border border-nyxus-blue/50 text-nyxus-blue bg-nyxus-blue/10">
            {notes.length} MEMORIES
          </div>
        </div>

        <div className="flex items-center gap-3">
          {notes.length > 0 && (
            <div className="relative">
              {showClearConfirm ? (
                <div className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4">
                  <span className="text-xs text-nyxus-orange uppercase">Confirm Purge?</span>
                  <button 
                    onClick={() => { clearAll(); setShowClearConfirm(false); }}
                    className="text-xs bg-nyxus-orange/20 text-nyxus-orange border border-nyxus-orange px-2 py-1 hover:bg-nyxus-orange hover:text-black transition-colors font-bold"
                  >
                    YES
                  </button>
                  <button 
                    onClick={() => setShowClearConfirm(false)}
                    className="text-xs text-muted-foreground hover:text-white transition-colors px-2 py-1"
                  >
                    NO
                  </button>
                </div>
              ) : (
                <button 
                  onClick={() => setShowClearConfirm(true)}
                  className="flex items-center gap-1 text-xs text-nyxus-orange/80 hover:text-nyxus-orange transition-colors"
                >
                  <Trash2 size={14} /> PURGE
                </button>
              )}
            </div>
          )}
          <button 
            onClick={addNote}
            className="flex items-center gap-1 text-xs font-bold px-3 py-1.5 bg-nyxus-pink/10 border border-nyxus-pink text-nyxus-pink hover:bg-nyxus-pink hover:text-black transition-colors"
            style={{ color: '#ff00ff', borderColor: '#ff00ff' }}
          >
            <Plus size={14} /> NEW NOTE
          </button>
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-6 z-10 relative">
        {notes.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-6 animate-in fade-in duration-700">
            <div className="text-nyxus-blue opacity-50 text-sm tracking-[0.2em] border border-nyxus-blue/20 p-4 rounded-sm border-dashed">
              NO NOTES PINNED TO MEMORY
            </div>
            <button 
              onClick={addNote}
              className="text-nyxus-pink font-bold border border-nyxus-pink px-6 py-2 bg-nyxus-pink/5 hover:bg-nyxus-pink hover:text-black transition-all animate-neon-pulse"
              style={{ color: '#ff00ff' }}
            >
              INITIALIZE NOTE
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-6 items-start content-start">
            {notes.map(note => (
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

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FileText, Plus, Search, Star, Trash2, Edit3, Settings,
  Bold, Italic, Heading1, Heading2, List, ListOrdered,
  Code, Minus, Eye, Edit2, Copy, Download, HelpCircle,
  X, Check, Save, TerminalSquare
} from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import { format } from 'date-fns';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface Note {
  id: string;
  title: string;
  content: string;
  createdAt: number;
  updatedAt: number;
  isPinned: boolean;
}

interface ClipboardEntry {
  id: string;
  text: string;
  timestamp: number;
  charCount: number;
}

export default function Notepad() {
  const { toast } = useToast();

  // State
  const [notes, setNotes] = useState<Note[]>(() => {
    const saved = localStorage.getItem('nyxus_notes');
    if (saved) return JSON.parse(saved);
    return [];
  });
  
  const [clipboardHistory, setClipboardHistory] = useState<ClipboardEntry[]>(() => {
    const saved = localStorage.getItem('nyxus_clipboard');
    if (saved) return JSON.parse(saved);
    return [];
  });

  const [activeNoteId, setActiveNoteId] = useState<string | null>(notes.length > 0 ? notes[0].id : null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  
  // Editor state
  const [content, setContent] = useState('');
  const [title, setTitle] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  // Derived state
  const activeNote = notes.find(n => n.id === activeNoteId) || null;
  const filteredNotes = notes.filter(n => 
    n.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
    n.content.toLowerCase().includes(searchQuery.toLowerCase())
  ).sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.updatedAt - a.updatedAt;
  });

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
  const charCount = content.length;

  // Sync active note to editor
  useEffect(() => {
    if (activeNote) {
      setContent(activeNote.content);
      setTitle(activeNote.title);
    } else {
      setContent('');
      setTitle('');
    }
  }, [activeNoteId]);

  // Persist notes
  useEffect(() => {
    localStorage.setItem('nyxus_notes', JSON.stringify(notes));
  }, [notes]);

  // Persist clipboard
  useEffect(() => {
    localStorage.setItem('nyxus_clipboard', JSON.stringify(clipboardHistory));
  }, [clipboardHistory]);

  // Auto-save
  useEffect(() => {
    if (!activeNoteId || !activeNote) return;

    // Only save if changed
    if (content === activeNote.content && title === activeNote.title) return;

    setIsSaving(true);
    const timer = setTimeout(() => {
      setNotes(prev => prev.map(n => 
        n.id === activeNoteId 
          ? { ...n, content, title, updatedAt: Date.now() } 
          : n
      ));
      setIsSaving(false);
    }, 2000);

    return () => clearTimeout(timer);
  }, [content, title, activeNoteId]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === 'n') {
          e.preventDefault();
          createNewNote();
        } else if (e.key === 's') {
          e.preventDefault();
          if (activeNoteId) {
            setNotes(prev => prev.map(n => 
              n.id === activeNoteId 
                ? { ...n, content, title, updatedAt: Date.now() } 
                : n
            ));
            setIsSaving(false);
            toast({
              title: "Note Saved",
              description: "Changes persisted successfully.",
              className: "border-primary bg-background text-foreground",
            });
          }
        } else if (e.key === 'p') {
          e.preventDefault();
          setIsPreviewMode(prev => !prev);
        } else if (e.key === '?') {
          e.preventDefault();
          setShowShortcuts(prev => !prev);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeNoteId, content, title]);

  // Clipboard capture on paste
  const handlePaste = (e: React.ClipboardEvent) => {
    const text = e.clipboardData.getData('text');
    if (text) {
      addClipboardEntry(text);
    }
  };

  const captureClipboardNow = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        addClipboardEntry(text);
        toast({
          title: "Captured",
          description: "Clipboard content saved to history.",
        });
      }
    } catch (err) {
      toast({
        title: "Error",
        description: "Could not read clipboard. Permission denied?",
        variant: "destructive"
      });
    }
  };

  const addClipboardEntry = (text: string) => {
    setClipboardHistory(prev => {
      // Don't add duplicates consecutively
      if (prev.length > 0 && prev[0].text === text) return prev;
      
      const newEntry: ClipboardEntry = {
        id: uuidv4(),
        text,
        timestamp: Date.now(),
        charCount: text.length
      };
      return [newEntry, ...prev].slice(0, 50); // Keep last 50
    });
  };

  const createNewNote = () => {
    const newNote: Note = {
      id: uuidv4(),
      title: 'Untitled Note',
      content: '',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isPinned: false
    };
    setNotes(prev => [newNote, ...prev]);
    setActiveNoteId(newNote.id);
    setIsPreviewMode(false);
    
    // Focus title soon after creation
    setTimeout(() => {
      const titleInput = document.getElementById('note-title-input');
      if (titleInput) titleInput.focus();
    }, 50);
  };

  const deleteNote = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (confirm('Are you sure you want to delete this note?')) {
      setNotes(prev => prev.filter(n => n.id !== id));
      if (activeNoteId === id) {
        setActiveNoteId(null);
      }
    }
  };

  const togglePin = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setNotes(prev => prev.map(n => 
      n.id === id ? { ...n, isPinned: !n.isPinned, updatedAt: Date.now() } : n
    ));
  };

  const insertMarkdown = (prefix: string, suffix: string = '') => {
    if (!editorRef.current) return;
    
    const start = editorRef.current.selectionStart;
    const end = editorRef.current.selectionEnd;
    const selectedText = content.substring(start, end);
    const before = content.substring(0, start);
    const after = content.substring(end);
    
    const newContent = before + prefix + selectedText + suffix + after;
    setContent(newContent);
    
    // Restore focus and selection
    setTimeout(() => {
      if (editorRef.current) {
        editorRef.current.focus();
        editorRef.current.setSelectionRange(
          start + prefix.length,
          end + prefix.length
        );
      }
    }, 0);
  };

  const downloadNote = (format: 'md' | 'txt') => {
    if (!activeNote) return;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'note'}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: "Copied",
      description: "Copied to clipboard.",
    });
  };

  // Simple Markdown parser for the preview
  const renderMarkdown = (text: string) => {
    if (!text) return { __html: '<p class="text-muted-foreground italic">Empty note...</p>' };
    
    let html = text
      // Headers
      .replace(/^### (.*$)/gim, '<h3 class="text-xl font-bold text-primary mt-6 mb-2">$1</h3>')
      .replace(/^## (.*$)/gim, '<h2 class="text-2xl font-bold text-primary mt-8 mb-3 shadow-[0_2px_0_0_hsl(var(--primary))] border-b border-primary/30 pb-1">$1</h2>')
      .replace(/^# (.*$)/gim, '<h1 class="text-3xl font-bold text-secondary mt-8 mb-4 tracking-tight drop-shadow-[0_0_8px_hsl(var(--secondary))]">$1</h1>')
      // Bold
      .replace(/\*\*(.*)\*\*/gim, '<strong class="text-foreground font-bold">$1</strong>')
      // Italic
      .replace(/\*(.*)\*/gim, '<em class="italic">$1</em>')
      // Code blocks
      .replace(/```([\s\S]*?)```/gim, '<pre class="bg-card p-4 rounded-sm border border-primary/20 my-4 overflow-x-auto"><code class="font-mono text-sm text-primary/90">$1</code></pre>')
      // Inline code
      .replace(/`(.*?)`/gim, '<code class="bg-muted px-1.5 py-0.5 rounded-sm font-mono text-sm text-secondary/90">$1</code>')
      // Lists
      .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc marker:text-primary">$1</li>')
      .replace(/^[0-9]\. (.*$)/gim, '<li class="ml-4 list-decimal marker:text-secondary">$1</li>')
      // Blockquotes
      .replace(/^\> (.*$)/gim, '<blockquote class="border-l-4 border-primary pl-4 py-1 my-4 bg-muted/30 italic text-muted-foreground">$1</blockquote>')
      // Horizontal rules
      .replace(/^\-\-\-/gim, '<hr class="border-primary/30 my-8 shadow-[0_0_8px_hsl(var(--primary))]" />')
      // Paragraphs
      .replace(/\n$/gim, '<br />');

    return { __html: html };
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden font-sans selection:bg-primary/30">
      
      {/* LEFT SIDEBAR: NOTES */}
      <div className="w-[280px] flex-shrink-0 border-r border-primary/20 flex flex-col bg-card/40 z-10">
        <div className="p-4 border-b border-primary/20 flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono text-lg font-bold tracking-wider text-primary drop-shadow-[0_0_8px_hsl(var(--primary))]">
            <TerminalSquare className="w-5 h-5 text-secondary" />
            <span>NYXUS_OS</span>
          </div>
        </div>
        
        <div className="p-3">
          <Button 
            onClick={createNewNote} 
            className="w-full gap-2 font-mono shadow-[0_0_12px_hsl(var(--primary))] border border-primary/50 hover:bg-primary hover:text-primary-foreground transition-all duration-300"
          >
            <Plus className="w-4 h-4" /> NEW_NOTE
          </Button>
        </div>
        
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input 
              placeholder="Search notes..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-9 bg-card border-primary/20 focus-visible:ring-primary font-mono text-sm"
            />
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-3 space-y-2">
            {filteredNotes.length === 0 ? (
              <div className="text-center p-4 text-muted-foreground font-mono text-sm border border-dashed border-muted-foreground/30 rounded-sm">
                No notes found.
              </div>
            ) : (
              filteredNotes.map(note => (
                <div 
                  key={note.id}
                  onClick={() => setActiveNoteId(note.id)}
                  className={`p-3 rounded-sm cursor-pointer transition-all duration-200 border group ${
                    activeNoteId === note.id 
                      ? 'bg-primary/10 border-primary shadow-[inset_4px_0_0_hsl(var(--primary))]' 
                      : 'bg-card border-transparent hover:border-primary/30 hover:bg-primary/5'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className={`font-medium truncate pr-2 ${activeNoteId === note.id ? 'text-primary' : 'text-foreground'}`}>
                      {note.title || 'Untitled Note'}
                    </h3>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={(e) => togglePin(note.id, e)}
                        className="text-muted-foreground hover:text-secondary transition-colors"
                      >
                        <Star className={`w-3.5 h-3.5 ${note.isPinned ? 'fill-secondary text-secondary opacity-100' : ''}`} />
                      </button>
                      <button 
                        onClick={(e) => deleteNote(note.id, e)}
                        className="text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 font-mono leading-relaxed opacity-70">
                    {note.content || '...'}
                  </p>
                  <div className="mt-2 text-[10px] text-muted-foreground/50 font-mono">
                    {format(note.updatedAt, 'MMM dd, HH:mm')}
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* CENTER: EDITOR */}
      <div className="flex-1 flex flex-col relative z-0 min-w-0 bg-background bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]">
        {activeNote ? (
          <>
            {/* Editor Toolbar */}
            <div className="h-14 border-b border-primary/20 flex items-center justify-between px-4 bg-background/80 backdrop-blur-sm z-10">
              <div className="flex flex-col">
                <Input 
                  id="note-title-input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="h-7 p-0 border-none bg-transparent focus-visible:ring-0 text-xl font-bold text-foreground placeholder:text-muted-foreground w-[300px]"
                  placeholder="Note Title"
                />
                <div className="flex items-center gap-4 text-[10px] text-muted-foreground font-mono">
                  <span>CREATED: {format(activeNote.createdAt, 'yyyy-MM-dd HH:mm')}</span>
                  <span>MODIFIED: {format(activeNote.updatedAt, 'yyyy-MM-dd HH:mm')}</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {!isPreviewMode && (
                  <div className="flex items-center gap-1 bg-card/50 border border-primary/20 p-1 rounded-sm mr-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => insertMarkdown('**', '**')}>
                          <Bold className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Bold (Ctrl+B)</p></TooltipContent>
                    </Tooltip>
                    
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => insertMarkdown('*', '*')}>
                          <Italic className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Italic (Ctrl+I)</p></TooltipContent>
                    </Tooltip>

                    <div className="w-px h-4 bg-primary/20 mx-1"></div>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-secondary hover:bg-secondary/10" onClick={() => insertMarkdown('# ', '')}>
                          <Heading1 className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Heading 1</p></TooltipContent>
                    </Tooltip>
                    
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-secondary hover:bg-secondary/10" onClick={() => insertMarkdown('## ', '')}>
                          <Heading2 className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Heading 2</p></TooltipContent>
                    </Tooltip>

                    <div className="w-px h-4 bg-primary/20 mx-1"></div>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => insertMarkdown('- ', '')}>
                          <List className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Bullet List</p></TooltipContent>
                    </Tooltip>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-primary hover:bg-primary/10" onClick={() => insertMarkdown('1. ', '')}>
                          <ListOrdered className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Numbered List</p></TooltipContent>
                    </Tooltip>

                    <div className="w-px h-4 bg-primary/20 mx-1"></div>

                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-accent hover:bg-accent/10" onClick={() => insertMarkdown('```\n', '\n```')}>
                          <Code className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Code Block</p></TooltipContent>
                    </Tooltip>
                    
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-accent hover:bg-accent/10" onClick={() => insertMarkdown('\n---\n', '')}>
                          <Minus className="w-4 h-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>Horizontal Rule</p></TooltipContent>
                    </Tooltip>
                  </div>
                )}

                <Button 
                  variant="outline" 
                  size="sm" 
                  className={`h-8 border-primary/50 font-mono text-xs gap-2 transition-all ${isPreviewMode ? 'bg-primary text-primary-foreground shadow-[0_0_8px_hsl(var(--primary))]' : 'hover:bg-primary/20'}`}
                  onClick={() => setIsPreviewMode(!isPreviewMode)}
                >
                  {isPreviewMode ? <Edit2 className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  {isPreviewMode ? 'EDIT' : 'PREVIEW'}
                </Button>

                <div className="w-px h-6 bg-primary/20 mx-1"></div>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-secondary" onClick={() => downloadNote('md')}>
                      <Download className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent><p>Download .md</p></TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-secondary" onClick={() => setShowShortcuts(true)}>
                      <HelpCircle className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent><p>Shortcuts</p></TooltipContent>
                </Tooltip>
              </div>
            </div>

            {/* Editor Area */}
            <div className="flex-1 overflow-hidden relative">
              {isPreviewMode ? (
                <div className="absolute inset-0 overflow-y-auto p-8 max-w-4xl mx-auto">
                  <div 
                    className="prose prose-invert prose-p:text-foreground prose-headings:text-primary max-w-none font-sans"
                    dangerouslySetInnerHTML={renderMarkdown(content)}
                  />
                </div>
              ) : (
                <textarea
                  ref={editorRef}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  onPaste={handlePaste}
                  className="absolute inset-0 w-full h-full resize-none bg-transparent p-8 font-mono text-sm leading-relaxed text-foreground focus:outline-none placeholder:text-muted-foreground/30"
                  placeholder="Start typing..."
                  spellCheck={false}
                />
              )}
            </div>

            {/* Status Bar */}
            <div className="h-8 border-t border-primary/20 bg-card/80 flex items-center justify-between px-4 font-mono text-[10px] text-muted-foreground z-10 backdrop-blur-sm">
              <div className="flex items-center gap-4">
                <span>{wordCount} WORDS</span>
                <span>{charCount} CHARS</span>
                <span>{notes.length} TOTAL NOTES</span>
              </div>
              
              <div className="flex items-center gap-2">
                {isSaving ? (
                  <span className="text-secondary animate-pulse flex items-center gap-1">
                    <Save className="w-3 h-3" /> SAVING...
                  </span>
                ) : (
                  <span className="text-primary flex items-center gap-1 opacity-70">
                    <Check className="w-3 h-3" /> SAVED
                  </span>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center flex-col gap-6 relative">
            <div className="absolute inset-0 bg-primary/5 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-background to-background"></div>
            
            <div className="relative z-10 flex flex-col items-center">
              <div className="w-24 h-24 mb-6 rounded-full border-2 border-primary/30 flex items-center justify-center shadow-[0_0_30px_hsl(var(--primary)_/_0.2)] bg-card/50">
                <FileText className="w-10 h-10 text-primary drop-shadow-[0_0_8px_hsl(var(--primary))]" />
              </div>
              <h2 className="text-2xl font-bold font-mono text-foreground mb-2">SYSTEM_IDLE</h2>
              <p className="text-muted-foreground mb-8 font-mono text-sm max-w-md text-center">
                Awaiting input sequence. Create a new note to initialize memory buffer or select an existing record from the sidebar.
              </p>
              
              <Button 
                onClick={createNewNote}
                size="lg"
                className="gap-2 font-mono tracking-widest bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_20px_hsl(var(--primary)_/_0.6)]"
              >
                <Plus className="w-5 h-5" /> INITIALIZE_NOTE
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* RIGHT SIDEBAR: CLIPBOARD HISTORY */}
      <div className="w-[300px] flex-shrink-0 border-l border-primary/20 flex flex-col bg-card/60 z-10 backdrop-blur-md">
        <div className="p-4 border-b border-primary/20 flex items-center justify-between">
          <div className="font-mono text-sm font-bold tracking-wider text-secondary drop-shadow-[0_0_5px_hsl(var(--secondary))]">
            CLIPBOARD_BUFFER
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={captureClipboardNow}
            className="h-7 text-[10px] font-mono border-secondary/50 text-secondary hover:bg-secondary hover:text-secondary-foreground"
          >
            CAPTURE
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-3 space-y-3">
            {clipboardHistory.length === 0 ? (
              <div className="text-center p-6 text-muted-foreground/50 font-mono text-xs border border-dashed border-muted-foreground/20 rounded-sm">
                BUFFER EMPTY<br/><br/>
                Copy text or use CAPTURE to populate buffer memory.
              </div>
            ) : (
              <>
                <div className="flex justify-end mb-1">
                  <button 
                    onClick={() => {
                      if(confirm('Clear entire clipboard history?')) {
                        setClipboardHistory([]);
                      }
                    }}
                    className="text-[10px] font-mono text-destructive hover:text-destructive hover:underline"
                  >
                    CLEAR_ALL
                  </button>
                </div>
                
                {clipboardHistory.map((item, i) => (
                  <div key={item.id} className="bg-background border border-primary/10 rounded-sm p-2 group hover:border-secondary/50 transition-colors">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[9px] font-mono text-muted-foreground/70">
                        {format(item.timestamp, 'HH:mm:ss')} • {item.charCount}ch
                      </span>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => copyToClipboard(item.text)}
                          className="p-1 hover:bg-primary/20 text-primary rounded"
                          title="Copy to clipboard"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        <button 
                          onClick={() => {
                            if (!activeNoteId || isPreviewMode) return;
                            insertMarkdown(item.text, '');
                          }}
                          className={`p-1 hover:bg-secondary/20 text-secondary rounded ${(!activeNoteId || isPreviewMode) ? 'opacity-50 cursor-not-allowed' : ''}`}
                          title="Insert at cursor"
                          disabled={!activeNoteId || isPreviewMode}
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                        <button 
                          onClick={() => setClipboardHistory(prev => prev.filter(x => x.id !== item.id))}
                          className="p-1 hover:bg-destructive/20 text-destructive rounded"
                          title="Remove entry"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-foreground/80 line-clamp-3 bg-muted/30 p-1.5 rounded-sm border border-transparent group-hover:border-secondary/20 break-all whitespace-pre-wrap">
                      {item.text}
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* KEYBOARD SHORTCUTS MODAL */}
      {showShortcuts && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4">
          <div className="bg-card border border-primary/50 shadow-[0_0_30px_hsl(var(--primary)_/_0.3)] rounded-md w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-primary/20 bg-primary/5">
              <h3 className="font-mono font-bold text-primary flex items-center gap-2">
                <TerminalSquare className="w-4 h-4" /> SYSTEM_MANUAL
              </h3>
              <button onClick={() => setShowShortcuts(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 font-mono text-sm space-y-4">
              <div className="flex justify-between items-center pb-2 border-b border-muted">
                <span className="text-foreground">Create New Note</span>
                <span className="text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/30">Ctrl + N</span>
              </div>
              <div className="flex justify-between items-center pb-2 border-b border-muted">
                <span className="text-foreground">Save Note (Manual)</span>
                <span className="text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/30">Ctrl + S</span>
              </div>
              <div className="flex justify-between items-center pb-2 border-b border-muted">
                <span className="text-foreground">Toggle Preview</span>
                <span className="text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/30">Ctrl + P</span>
              </div>
              <div className="flex justify-between items-center pb-2 border-b border-muted">
                <span className="text-foreground">Show Shortcuts</span>
                <span className="text-secondary bg-secondary/10 px-2 py-0.5 rounded border border-secondary/30">Ctrl + ?</span>
              </div>
              
              <div className="pt-4 text-xs text-muted-foreground border-t border-primary/20 mt-6">
                <p className="mb-2 uppercase text-primary tracking-wider">Editor Features</p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>Use the toolbar to insert Markdown syntax</li>
                  <li>Paste into the editor to automatically capture clipboard history</li>
                  <li>Notes auto-save every 2 seconds</li>
                </ul>
              </div>
            </div>
            
            <div className="p-4 border-t border-primary/20 bg-muted/20 flex justify-end">
              <Button onClick={() => setShowShortcuts(false)} className="font-mono text-xs bg-primary hover:bg-primary/80">
                ACKNOWLEDGE
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
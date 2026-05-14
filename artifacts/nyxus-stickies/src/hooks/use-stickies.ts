import { useState, useEffect, useRef } from 'react';

export type NoteColor =
  | '#f4ead5'
  | '#d4b89c'
  | '#c4b491'
  | '#e8dcc1'
  | '#a89175'
  | '#b8865a';

export const NYXUS_COLORS: NoteColor[] = [
  '#f4ead5',
  '#d4b89c',
  '#c4b491',
  '#e8dcc1',
  '#a89175',
  '#b8865a',
];

export const COLOR_LABELS: Record<NoteColor, string> = {
  '#f4ead5': 'Cream',
  '#d4b89c': 'Warm',
  '#c4b491': 'Sand',
  '#e8dcc1': 'Linen',
  '#a89175': 'Wheat',
  '#b8865a': 'Copper',
};

export interface Note {
  id: string;
  title: string;
  content: string;
  color: NoteColor;
  rotation: number;
  isPinned: boolean;
  createdAt: number;
}

export function useStickies() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoaded, setIsLoaded] = useState(false);
  const colorIndexRef = useRef<number>(
    parseInt(localStorage.getItem('nyxus_stickies_colorindex') || '0', 10)
  );

  useEffect(() => {
    const saved = localStorage.getItem('nyxus_stickies');
    if (saved) {
      try {
        const parsed = JSON.parse(saved) as Note[];
        const valid = parsed.map(n => ({
          ...n,
          color: NYXUS_COLORS.includes(n.color as NoteColor) ? n.color : NYXUS_COLORS[Math.floor(Math.random() * NYXUS_COLORS.length)],
        }));
        setNotes(valid);
      } catch {
        setNotes([]);
      }
    }
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (isLoaded) localStorage.setItem('nyxus_stickies', JSON.stringify(notes));
  }, [notes, isLoaded]);

  const addNote = () => {
    const idx = colorIndexRef.current % NYXUS_COLORS.length;
    colorIndexRef.current += 1;
    localStorage.setItem('nyxus_stickies_colorindex', String(colorIndexRef.current));
    const color = NYXUS_COLORS[idx];
    const rotation = (Math.random() * 8) - 4;
    const newNote: Note = {
      id: crypto.randomUUID(),
      title: '',
      content: '',
      color,
      rotation,
      isPinned: false,
      createdAt: Date.now(),
    };
    setNotes(prev => [newNote, ...prev]);
  };

  const updateNote = (id: string, updates: Partial<Note>) =>
    setNotes(prev => prev.map(n => (n.id === id ? { ...n, ...updates } : n)));

  const deleteNote = (id: string) =>
    setNotes(prev => prev.filter(n => n.id !== id));

  const clearAll = () => setNotes([]);

  const togglePin = (id: string) =>
    setNotes(prev => prev.map(n => (n.id === id ? { ...n, isPinned: !n.isPinned } : n)));

  const sortedNotes = [...notes].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.createdAt - a.createdAt;
  });

  return { notes: sortedNotes, addNote, updateNote, deleteNote, clearAll, togglePin, isLoaded };
}

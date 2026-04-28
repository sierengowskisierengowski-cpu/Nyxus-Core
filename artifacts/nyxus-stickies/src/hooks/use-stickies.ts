import { useState, useEffect } from 'react';

export type NoteColor =
  | '#fef08a'
  | '#fda4af'
  | '#93c5fd'
  | '#86efac'
  | '#e9d5ff'
  | '#fdba74';

export const NYXUS_COLORS: NoteColor[] = [
  '#fef08a',
  '#fda4af',
  '#93c5fd',
  '#86efac',
  '#e9d5ff',
  '#fdba74',
];

export const COLOR_LABELS: Record<NoteColor, string> = {
  '#fef08a': 'Lemon',
  '#fda4af': 'Rose',
  '#93c5fd': 'Sky',
  '#86efac': 'Mint',
  '#e9d5ff': 'Lavender',
  '#fdba74': 'Peach',
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
    const color = NYXUS_COLORS[Math.floor(Math.random() * NYXUS_COLORS.length)];
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

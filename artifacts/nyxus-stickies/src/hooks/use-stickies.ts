import { useState, useEffect } from 'react';

export type NoteColor = 
  | '#ff00ff' // pink
  | '#cc00ff' // purple
  | '#0088ff' // blue
  | '#39ff14' // green
  | '#ffff00' // yellow
  | '#ff5500'; // orange

export const NYXUS_COLORS: NoteColor[] = [
  '#ff00ff', '#cc00ff', '#0088ff', '#39ff14', '#ffff00', '#ff5500'
];

export interface Note {
  id: string;
  title: string;
  content: string;
  color: NoteColor;
  rotation: number; // degrees
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
        setNotes(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse stickies', e);
      }
    }
    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (isLoaded) {
      localStorage.setItem('nyxus_stickies', JSON.stringify(notes));
    }
  }, [notes, isLoaded]);

  const addNote = () => {
    const newNote: Note = {
      id: crypto.randomUUID(),
      title: 'NEW_NOTE',
      content: '',
      color: NYXUS_COLORS[Math.floor(Math.random() * NYXUS_COLORS.length)],
      rotation: (Math.random() * 6) - 3, // -3 to +3
      isPinned: false,
      createdAt: Date.now()
    };
    setNotes([newNote, ...notes]);
  };

  const updateNote = (id: string, updates: Partial<Note>) => {
    setNotes(notes.map(n => n.id === id ? { ...n, ...updates } : n));
  };

  const deleteNote = (id: string) => {
    setNotes(notes.filter(n => n.id !== id));
  };

  const clearAll = () => {
    setNotes([]);
  };

  const togglePin = (id: string) => {
    setNotes(notes.map(n => {
      if (n.id === id) {
        return { ...n, isPinned: !n.isPinned };
      }
      return n;
    }));
  };

  // Sort notes: pinned first, then by createdAt desc
  const sortedNotes = [...notes].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.createdAt - a.createdAt;
  });

  return {
    notes: sortedNotes,
    addNote,
    updateNote,
    deleteNote,
    clearAll,
    togglePin,
    isLoaded
  };
}

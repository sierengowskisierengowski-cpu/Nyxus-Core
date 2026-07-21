import { Router } from "express";
import { db } from "@workspace/db";
import { notesTable } from "@workspace/db";
import { eq, desc, and, like, or, sql } from "drizzle-orm";

const router = Router();

function formatNote(n: typeof notesTable.$inferSelect) {
  return {
    ...n,
    tags: (() => { try { return n.tags ? JSON.parse(n.tags) : []; } catch { return []; } })(),
    createdAt: n.createdAt.toISOString(),
    updatedAt: n.updatedAt.toISOString(),
  };
}

router.get("/notes", async (req, res) => {
  try {
    const tagFilter = req.query.tag as string;
    const notebookFilter = req.query.notebook as string;
    const search = req.query.search as string;

    let query = db.select().from(notesTable);
    const conditions = [eq(notesTable.isArchived, false)];

    if (notebookFilter) conditions.push(eq(notesTable.notebook, notebookFilter));
    if (search) conditions.push(or(like(notesTable.title, `%${search}%`), like(notesTable.content, `%${search}%`))!);

    const notes = await db.select().from(notesTable)
      .where(and(...conditions))
      .orderBy(desc(notesTable.isPinned), desc(notesTable.isFavorite), desc(notesTable.updatedAt));

    const filtered = tagFilter
      ? notes.filter(n => { try { const tags = JSON.parse(n.tags || "[]"); return tags.includes(tagFilter); } catch { return false; } })
      : notes;

    res.json(filtered.map(formatNote));
  } catch (err) {
    req.log.error(err, "Failed to list notes");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/notes", async (req, res) => {
  try {
    const { title, content, noteType, notebook, tags, linkedJobId, linkedHashId } = req.body;
    if (!title) return res.status(400).json({ error: "title is required" });

    const [note] = await db.insert(notesTable).values({
      title,
      content: content || "",
      noteType: noteType || "quick_capture",
      notebook: notebook || "general",
      tags: JSON.stringify(tags || []),
      linkedJobId: linkedJobId || null,
      linkedHashId: linkedHashId || null,
      isPinned: false,
      isFavorite: false,
      isArchived: false,
    }).returning();

    res.status(201).json(formatNote(note));
  } catch (err) {
    req.log.error(err, "Failed to create note");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/notes/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [note] = await db.select().from(notesTable).where(eq(notesTable.id, id)).limit(1);
    if (!note) return res.status(404).json({ error: "Note not found" });
    res.json(formatNote(note));
  } catch (err) {
    req.log.error(err, "Failed to get note");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/notes/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const { title, content, noteType, notebook, tags, isPinned, isFavorite, isArchived } = req.body;
    const updates: Record<string, unknown> = { updatedAt: new Date() };
    if (title !== undefined) updates.title = title;
    if (content !== undefined) updates.content = content;
    if (noteType !== undefined) updates.noteType = noteType;
    if (notebook !== undefined) updates.notebook = notebook;
    if (tags !== undefined) updates.tags = JSON.stringify(tags);
    if (isPinned !== undefined) updates.isPinned = isPinned;
    if (isFavorite !== undefined) updates.isFavorite = isFavorite;
    if (isArchived !== undefined) updates.isArchived = isArchived;

    const [note] = await db.update(notesTable).set(updates).where(eq(notesTable.id, id)).returning();
    if (!note) return res.status(404).json({ error: "Note not found" });
    res.json(formatNote(note));
  } catch (err) {
    req.log.error(err, "Failed to update note");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/notes/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    await db.delete(notesTable).where(eq(notesTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error(err, "Failed to delete note");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

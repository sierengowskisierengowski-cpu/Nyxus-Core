import { Router } from "express";
import { db } from "@workspace/db";
import { knowledgeNotesTable } from "@workspace/db";
import { eq, desc } from "drizzle-orm";
import {
  CreateKnowledgeNoteBody,
  UpdateKnowledgeNoteBody,
  ImportKnowledgeBody,
} from "@workspace/api-zod";

const router = Router();

// GET /knowledge/notes
router.get("/knowledge/notes", async (_req, res) => {
  const notes = await db.select().from(knowledgeNotesTable)
    .orderBy(desc(knowledgeNotesTable.pinned), desc(knowledgeNotesTable.updatedAt));
  res.json(notes);
});

// POST /knowledge/notes
router.post("/knowledge/notes", async (req, res) => {
  const body = CreateKnowledgeNoteBody.parse(req.body);
  const [note] = await db.insert(knowledgeNotesTable).values({
    title: body.title,
    content: body.content,
    pinned: body.pinned ?? false,
  }).returning();
  res.status(201).json(note);
});

// PATCH /knowledge/notes/:id
router.patch("/knowledge/notes/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  const body = UpdateKnowledgeNoteBody.parse(req.body);
  const [note] = await db.update(knowledgeNotesTable)
    .set({ ...body, updatedAt: new Date().toISOString() })
    .where(eq(knowledgeNotesTable.id, id))
    .returning();
  if (!note) return res.status(404).json({ error: "Not found" });
  res.json(note);
});

// DELETE /knowledge/notes/:id
router.delete("/knowledge/notes/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  await db.delete(knowledgeNotesTable).where(eq(knowledgeNotesTable.id, id));
  res.status(204).send();
});

// GET /knowledge/export
router.get("/knowledge/export", async (_req, res) => {
  const notes = await db.select().from(knowledgeNotesTable).orderBy(knowledgeNotesTable.id);
  res.json({ notes, exportedAt: new Date().toISOString() });
});

// POST /knowledge/import
router.post("/knowledge/import", async (req, res) => {
  const body = ImportKnowledgeBody.parse(req.body);
  const existing = await db.select().from(knowledgeNotesTable);
  const existingTitles = new Set(existing.map(n => n.title));
  let imported = 0;
  let skipped = 0;
  for (const note of body.notes) {
    if (existingTitles.has(note.title)) {
      skipped++;
    } else {
      await db.insert(knowledgeNotesTable).values({
        title: note.title,
        content: note.content,
        pinned: note.pinned ?? false,
      });
      imported++;
    }
  }
  res.json({ imported, skipped });
});

export default router;

import { Router } from "express";
import { db, notesTable } from "@workspace/db";
import { eq, desc } from "drizzle-orm";
import { ListNotesQueryParams, CreateNoteBody, UpdateNoteBody, GetNoteParams, UpdateNoteParams, DeleteNoteParams } from "@workspace/api-zod";

const router = Router();

router.get("/notes", async (req, res) => {
  try {
    const parsed = ListNotesQueryParams.safeParse(req.query);
    const limit = parsed.success ? (parsed.data.limit ?? 50) : 50;
    const missionId = parsed.success ? parsed.data.missionId : undefined;

    let query = db.select().from(notesTable).orderBy(desc(notesTable.createdAt)).$dynamic();
    if (missionId) {
      query = query.where(eq(notesTable.missionId, missionId));
    }
    const notes = await query.limit(limit);
    res.json(notes.map(formatNote));
  } catch (err) {
    req.log.error({ err }, "List notes error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/notes/recent", async (_req, res) => {
  try {
    const notes = await db.select().from(notesTable).orderBy(desc(notesTable.createdAt)).limit(3);
    res.json(notes.map(formatNote));
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/notes/:id", async (req, res) => {
  try {
    const { id } = GetNoteParams.parse({ id: Number(req.params.id) });
    const [note] = await db.select().from(notesTable).where(eq(notesTable.id, id));
    if (!note) {
      res.status(404).json({ error: "Note not found" });
      return;
    }
    res.json(formatNote(note));
  } catch (err) {
    req.log.error({ err }, "Get note error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/notes", async (req, res) => {
  try {
    const body = CreateNoteBody.parse(req.body);
    const [note] = await db.insert(notesTable).values(body).returning();
    res.status(201).json(formatNote(note));
  } catch (err) {
    req.log.error({ err }, "Create note error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/notes/:id", async (req, res) => {
  try {
    const { id } = UpdateNoteParams.parse({ id: Number(req.params.id) });
    const body = UpdateNoteBody.parse(req.body);
    const [note] = await db.update(notesTable).set(body).where(eq(notesTable.id, id)).returning();
    if (!note) {
      res.status(404).json({ error: "Note not found" });
      return;
    }
    res.json(formatNote(note));
  } catch (err) {
    req.log.error({ err }, "Update note error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/notes/:id", async (req, res) => {
  try {
    const { id } = DeleteNoteParams.parse({ id: Number(req.params.id) });
    await db.delete(notesTable).where(eq(notesTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error({ err }, "Delete note error");
    res.status(500).json({ error: "Internal server error" });
  }
});

function formatNote(n: typeof notesTable.$inferSelect) {
  return {
    id: n.id,
    missionId: n.missionId,
    content: n.content,
    tags: n.tags,
    createdAt: n.createdAt.toISOString(),
    updatedAt: n.updatedAt.toISOString(),
  };
}

export default router;

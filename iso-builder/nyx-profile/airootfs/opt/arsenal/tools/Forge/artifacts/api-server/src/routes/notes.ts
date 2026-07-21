import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { notesTable } from "@workspace/db";
import { eq, like, and } from "drizzle-orm";
import {
  CreateNoteBody,
  GetNoteParams,
  UpdateNoteParams,
  UpdateNoteBody,
  DeleteNoteParams,
  ListNotesQueryParams,
} from "@workspace/api-zod";
import { sql } from "drizzle-orm";

const router: IRouter = Router();

router.get("/notes", async (req, res): Promise<void> => {
  const params = ListNotesQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { notebook, noteType, search, pinned, starred } = params.data;
  const conditions = [];
  if (notebook) conditions.push(eq(notesTable.notebook, notebook));
  if (noteType) conditions.push(eq(notesTable.noteType, noteType));
  if (search) conditions.push(like(notesTable.title, `%${search}%`));
  if (pinned !== undefined) conditions.push(eq(notesTable.pinned, pinned));
  if (starred !== undefined) conditions.push(eq(notesTable.starred, starred));

  const notes = conditions.length > 0
    ? await db.select().from(notesTable).where(and(...conditions))
    : await db.select().from(notesTable);
  res.json(notes);
});

router.get("/notebooks", async (_req, res): Promise<void> => {
  const rows = await db.selectDistinct({ notebook: notesTable.notebook }).from(notesTable);
  const notebooks = rows.map(r => r.notebook);
  if (!notebooks.includes("Research")) notebooks.unshift("Research");
  if (!notebooks.includes("Quick Capture")) notebooks.unshift("Quick Capture");
  res.json(notebooks);
});

router.post("/notes", async (req, res): Promise<void> => {
  const parsed = CreateNoteBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [note] = await db.insert(notesTable).values({
    ...parsed.data,
    content: parsed.data.content ?? "",
    tags: parsed.data.tags ?? [],
    pinned: parsed.data.pinned ?? false,
    starred: false,
    archived: false,
  }).returning();
  res.status(201).json(note);
});

router.get("/notes/:id", async (req, res): Promise<void> => {
  const params = GetNoteParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [note] = await db.select().from(notesTable).where(eq(notesTable.id, params.data.id));
  if (!note) {
    res.status(404).json({ error: "Note not found" });
    return;
  }
  res.json(note);
});

router.patch("/notes/:id", async (req, res): Promise<void> => {
  const params = UpdateNoteParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const body = UpdateNoteBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }
  const [note] = await db.update(notesTable)
    .set({ ...body.data, updatedAt: new Date() })
    .where(eq(notesTable.id, params.data.id))
    .returning();
  if (!note) {
    res.status(404).json({ error: "Note not found" });
    return;
  }
  res.json(note);
});

router.delete("/notes/:id", async (req, res): Promise<void> => {
  const params = DeleteNoteParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [deleted] = await db.delete(notesTable).where(eq(notesTable.id, params.data.id)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Note not found" });
    return;
  }
  res.sendStatus(204);
});

export default router;

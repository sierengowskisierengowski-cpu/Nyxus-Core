import { Router, type IRouter } from "express";
import { eq, and, desc, asc, sql, type SQL } from "drizzle-orm";
import { db, notes, noteVersions, notebooks } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { CreateNoteBody, UpdateNoteBody, CreateNotebookBody, UpdateNotebookBody } from "@workspace/api-zod";
import { NOTE_TEMPLATES } from "../lib/kb-data";

const router: IRouter = Router();

function noteRow(n: typeof notes.$inferSelect) {
  return {
    id: n.id,
    title: n.title,
    body: n.body,
    noteType: n.noteType,
    notebookId: n.notebookId,
    missionId: n.missionId,
    techniqueId: n.techniqueId,
    tags: n.tags,
    pinned: n.pinned,
    favorited: n.favorited,
    archived: n.archived,
    wordCount: n.body.split(/\s+/).filter(Boolean).length,
    createdAt: n.createdAt.toISOString(),
    updatedAt: n.updatedAt.toISOString(),
    lastViewedAt: n.lastViewedAt?.toISOString() ?? null,
  };
}

router.get("/notes", requireAuth, async (req, res) => {
  const q = (k: string): string | undefined => (typeof req.query[k] === "string" ? (req.query[k] as string) : undefined);
  const notebookId = q("notebookId");
  const tag = q("tag");
  const noteType = q("noteType");
  const search = q("search");
  const archived = q("archived");
  const pinned = q("pinned");
  const favorited = q("favorited");
  const sort = q("sort");
  const conds: SQL[] = [];
  if (notebookId) conds.push(eq(notes.notebookId, Number(notebookId)));
  if (noteType) conds.push(eq(notes.noteType, noteType));
  if (archived !== undefined) conds.push(eq(notes.archived, archived === "true"));
  else conds.push(eq(notes.archived, false));
  if (pinned !== undefined) conds.push(eq(notes.pinned, pinned === "true"));
  if (favorited !== undefined) conds.push(eq(notes.favorited, favorited === "true"));
  if (tag) conds.push(sql`${tag} = ANY(${notes.tags})`);
  if (search) {
    const q = `%${search.toLowerCase()}%`;
    conds.push(sql`(LOWER(${notes.title}) LIKE ${q} OR LOWER(${notes.body}) LIKE ${q})`);
  }
  const order =
    sort === "title" ? asc(notes.title) : sort === "created" ? desc(notes.createdAt) : desc(notes.updatedAt);
  const rows = await db
    .select()
    .from(notes)
    .where(conds.length > 0 ? and(...conds) : undefined)
    .orderBy(desc(notes.pinned), order);
  res.json(rows.map(noteRow));
});

router.post("/notes", requireAuth, async (req, res) => {
  const parsed = CreateNoteBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const data = parsed.data;
  const [row] = await db
    .insert(notes)
    .values({
      title: data.title,
      body: data.body ?? "",
      noteType: data.noteType ?? "general",
      notebookId: data.notebookId ?? null,
      missionId: data.missionId ?? null,
      techniqueId: data.techniqueId ?? null,
      tags: data.tags ?? [],
    })
    .returning();
  res.status(201).json(noteRow(row));
});

router.get("/notes/:id", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [row] = await db
    .update(notes)
    .set({ lastViewedAt: new Date() })
    .where(eq(notes.id, id))
    .returning();
  if (!row) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(noteRow(row));
});

router.patch("/notes/:id", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const parsed = UpdateNoteBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const [existing] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (!existing) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  // Save version if body/title changed
  if (
    (parsed.data.body !== undefined && parsed.data.body !== existing.body) ||
    (parsed.data.title !== undefined && parsed.data.title !== existing.title)
  ) {
    await db.insert(noteVersions).values({
      noteId: existing.id,
      title: existing.title,
      body: existing.body,
    });
  }
  const patch: Partial<typeof notes.$inferInsert> = { updatedAt: new Date() };
  if (parsed.data.title !== undefined) patch.title = parsed.data.title;
  if (parsed.data.body !== undefined) patch.body = parsed.data.body;
  if (parsed.data.noteType !== undefined) patch.noteType = parsed.data.noteType;
  if (parsed.data.notebookId !== undefined) patch.notebookId = parsed.data.notebookId;
  if (parsed.data.techniqueId !== undefined) patch.techniqueId = parsed.data.techniqueId;
  if (parsed.data.tags !== undefined) patch.tags = parsed.data.tags;
  const [row] = await db.update(notes).set(patch).where(eq(notes.id, id)).returning();
  res.json(noteRow(row));
});

router.delete("/notes/:id", requireAuth, async (req, res) => {
  await db.delete(notes).where(eq(notes.id, Number(req.params.id)));
  res.status(204).end();
});

router.post("/notes/:id/pin", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [existing] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (!existing) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const [row] = await db.update(notes).set({ pinned: !existing.pinned }).where(eq(notes.id, id)).returning();
  res.json(noteRow(row));
});

router.post("/notes/:id/favorite", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [existing] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (!existing) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const [row] = await db
    .update(notes)
    .set({ favorited: !existing.favorited })
    .where(eq(notes.id, id))
    .returning();
  res.json(noteRow(row));
});

router.post("/notes/:id/archive", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [existing] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (!existing) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const [row] = await db
    .update(notes)
    .set({ archived: !existing.archived })
    .where(eq(notes.id, id))
    .returning();
  res.json(noteRow(row));
});

router.get("/notes/:id/versions", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const rows = await db
    .select()
    .from(noteVersions)
    .where(eq(noteVersions.noteId, id))
    .orderBy(desc(noteVersions.createdAt));
  res.json(rows.map((v) => ({ ...v, createdAt: v.createdAt.toISOString() })));
});

router.post("/notes/:id/restore/:versionId", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const versionId = Number(req.params.versionId);
  const [v] = await db.select().from(noteVersions).where(eq(noteVersions.id, versionId)).limit(1);
  if (!v || v.noteId !== id) {
    res.status(404).json({ error: "Version not found" });
    return;
  }
  const [existing] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (existing) {
    await db.insert(noteVersions).values({ noteId: id, title: existing.title, body: existing.body });
  }
  const [row] = await db
    .update(notes)
    .set({ title: v.title, body: v.body, updatedAt: new Date() })
    .where(eq(notes.id, id))
    .returning();
  res.json(noteRow(row));
});

router.post("/notes/:id/duplicate", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [n] = await db.select().from(notes).where(eq(notes.id, id)).limit(1);
  if (!n) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const [row] = await db
    .insert(notes)
    .values({
      title: `${n.title} (copy)`,
      body: n.body,
      noteType: n.noteType,
      notebookId: n.notebookId,
      missionId: n.missionId,
      techniqueId: n.techniqueId,
      tags: n.tags,
    })
    .returning();
  res.status(201).json(noteRow(row));
});

router.get("/note-templates", requireAuth, (_req, res) => {
  res.json(NOTE_TEMPLATES);
});

router.get("/tags", requireAuth, async (_req, res) => {
  const rows = await db.execute<{ tag: string; count: number }>(sql`
    SELECT unnest(${notes.tags}) AS tag, COUNT(*)::int AS count
    FROM ${notes}
    WHERE ${notes.archived} = false
    GROUP BY tag
    ORDER BY count DESC
  `);
  res.json(rows.rows.map((r) => ({ name: r.tag, count: r.count })));
});

// Notebooks
router.get("/notebooks", requireAuth, async (_req, res) => {
  const counts = await db.execute<{ notebook_id: number; cnt: number }>(sql`
    SELECT ${notes.notebookId} AS notebook_id, COUNT(*)::int AS cnt
    FROM ${notes}
    WHERE ${notes.notebookId} IS NOT NULL AND ${notes.archived} = false
    GROUP BY ${notes.notebookId}
  `);
  const countMap = new Map(counts.rows.map((r) => [r.notebook_id, r.cnt]));
  const rows = await db.select().from(notebooks).orderBy(asc(notebooks.name));
  res.json(
    rows.map((nb) => ({
      id: nb.id,
      name: nb.name,
      description: nb.description,
      color: nb.color,
      noteCount: countMap.get(nb.id) ?? 0,
      createdAt: nb.createdAt.toISOString(),
    })),
  );
});

router.post("/notebooks", requireAuth, async (req, res) => {
  const parsed = CreateNotebookBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const [row] = await db
    .insert(notebooks)
    .values({
      name: parsed.data.name,
      description: parsed.data.description ?? "",
      color: parsed.data.color ?? "#ef4444",
    })
    .returning();
  res.status(201).json({ ...row, noteCount: 0, createdAt: row.createdAt.toISOString() });
});

router.patch("/notebooks/:id", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const parsed = UpdateNotebookBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const [row] = await db.update(notebooks).set(parsed.data).where(eq(notebooks.id, id)).returning();
  if (!row) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json({ ...row, createdAt: row.createdAt.toISOString() });
});

router.delete("/notebooks/:id", requireAuth, async (req, res) => {
  await db.delete(notebooks).where(eq(notebooks.id, Number(req.params.id)));
  res.status(204).end();
});

export default router;

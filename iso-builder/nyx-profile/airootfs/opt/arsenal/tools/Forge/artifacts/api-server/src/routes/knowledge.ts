import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { knowledgeEntriesTable } from "@workspace/db";
import { eq, like, and } from "drizzle-orm";
import {
  CreateKnowledgeEntryBody,
  DeleteKnowledgeEntryParams,
  ListKnowledgeEntriesQueryParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/knowledge-entries", async (req, res): Promise<void> => {
  const params = ListKnowledgeEntriesQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { category, search } = params.data;
  const conditions = [];
  if (category) conditions.push(eq(knowledgeEntriesTable.category, category));
  if (search) conditions.push(like(knowledgeEntriesTable.title, `%${search}%`));

  const entries = conditions.length > 0
    ? await db.select().from(knowledgeEntriesTable).where(and(...conditions))
    : await db.select().from(knowledgeEntriesTable);
  res.json(entries);
});

router.post("/knowledge-entries", async (req, res): Promise<void> => {
  const parsed = CreateKnowledgeEntryBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [entry] = await db.insert(knowledgeEntriesTable).values({
    ...parsed.data,
    tags: parsed.data.tags ?? [],
  }).returning();
  res.status(201).json(entry);
});

router.delete("/knowledge-entries/:id", async (req, res): Promise<void> => {
  const params = DeleteKnowledgeEntryParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [deleted] = await db.delete(knowledgeEntriesTable).where(eq(knowledgeEntriesTable.id, params.data.id)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Entry not found" });
    return;
  }
  res.sendStatus(204);
});

router.get("/knowledge-stats", async (_req, res): Promise<void> => {
  const entries = await db.select({ category: knowledgeEntriesTable.category }).from(knowledgeEntriesTable);
  const byCategoryMap: Record<string, number> = {};
  for (const e of entries) {
    byCategoryMap[e.category] = (byCategoryMap[e.category] ?? 0) + 1;
  }
  const byCategory = Object.entries(byCategoryMap).map(([category, count]) => ({ category, count }));
  const lastEntry = await db.select({ createdAt: knowledgeEntriesTable.createdAt }).from(knowledgeEntriesTable).limit(1);
  res.json({
    total: entries.length,
    byCategory,
    lastUpdated: lastEntry[0]?.createdAt ?? new Date().toISOString(),
  });
});

export default router;

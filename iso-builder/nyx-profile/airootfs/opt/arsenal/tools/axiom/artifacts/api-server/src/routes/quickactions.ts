import { Router } from "express";
import { db } from "@workspace/db";
import { quickActionsTable } from "@workspace/db";
import { eq, asc } from "drizzle-orm";
import {
  CreateQuickActionBody,
  UpdateQuickActionBody,
  ReorderQuickActionsBody,
} from "@workspace/api-zod";

const router = Router();

// GET /quickactions
router.get("/quickactions", async (_req, res) => {
  const actions = await db.select().from(quickActionsTable).orderBy(asc(quickActionsTable.order), asc(quickActionsTable.id));
  res.json(actions);
});

// POST /quickactions
router.post("/quickactions", async (req, res) => {
  const body = CreateQuickActionBody.parse(req.body);
  const existing = await db.select().from(quickActionsTable);
  const maxOrder = existing.length > 0 ? Math.max(...existing.map(a => a.order)) : -1;
  const [action] = await db.insert(quickActionsTable).values({
    label: body.label,
    command: body.command,
    icon: body.icon,
    color: body.color,
    order: maxOrder + 1,
  }).returning();
  res.status(201).json(action);
});

// PATCH /quickactions/:id
router.patch("/quickactions/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  const body = UpdateQuickActionBody.parse(req.body);
  const [action] = await db.update(quickActionsTable).set(body).where(eq(quickActionsTable.id, id)).returning();
  if (!action) return res.status(404).json({ error: "Not found" });
  res.json(action);
});

// DELETE /quickactions/:id
router.delete("/quickactions/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  await db.delete(quickActionsTable).where(eq(quickActionsTable.id, id));
  res.status(204).send();
});

// POST /quickactions/reorder
router.post("/quickactions/reorder", async (req, res) => {
  const body = ReorderQuickActionsBody.parse(req.body);
  const updates = body.ids.map((id, idx) =>
    db.update(quickActionsTable).set({ order: idx }).where(eq(quickActionsTable.id, id)).returning()
  );
  const results = await Promise.all(updates);
  const actions = results.flat().sort((a, b) => a.order - b.order);
  res.json(actions);
});

export default router;

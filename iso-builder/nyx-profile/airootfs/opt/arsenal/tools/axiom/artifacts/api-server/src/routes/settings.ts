import { Router } from "express";
import { db } from "@workspace/db";
import { settingsTable } from "@workspace/db";
import { UpdateSettingsBody } from "@workspace/api-zod";
import { sql } from "drizzle-orm";

const router = Router();

async function getOrCreateSettings() {
  const [existing] = await db.select().from(settingsTable).limit(1);
  if (existing) return existing;
  const [created] = await db.insert(settingsTable).values({}).returning();
  return created;
}

// GET /settings
router.get("/settings", async (_req, res) => {
  const settings = await getOrCreateSettings();
  res.json(settings);
});

// PATCH /settings
router.patch("/settings", async (req, res) => {
  const body = UpdateSettingsBody.parse(req.body);
  await getOrCreateSettings();
  const [updated] = await db.update(settingsTable)
    .set(body)
    .where(sql`1=1`)
    .returning();
  res.json(updated);
});

export default router;

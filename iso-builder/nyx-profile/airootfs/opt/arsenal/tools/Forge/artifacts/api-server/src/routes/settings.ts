import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { settingsTable } from "@workspace/db";
import { UpdateSettingsBody } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/settings", async (_req, res): Promise<void> => {
  let rows = await db.select().from(settingsTable).limit(1);
  if (rows.length === 0) {
    const [created] = await db.insert(settingsTable).values({}).returning();
    rows = [created];
  }
  res.json(rows[0]);
});

router.patch("/settings", async (req, res): Promise<void> => {
  const parsed = UpdateSettingsBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  let rows = await db.select().from(settingsTable).limit(1);
  if (rows.length === 0) {
    await db.insert(settingsTable).values({});
    rows = await db.select().from(settingsTable).limit(1);
  }

  const [updated] = await db.update(settingsTable)
    .set(parsed.data)
    .returning();
  res.json(updated);
});

export default router;

import { Router, type IRouter } from "express";
import { eq } from "drizzle-orm";
import { db, settings as settingsTable, users } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { UpdateSettingsBody, ChangePasswordBody } from "@workspace/api-zod";
import { hashPassword, verifyPassword } from "../lib/auth";

const router: IRouter = Router();

async function ensureSettings() {
  const rows = await db.select().from(settingsTable).limit(1);
  if (rows[0]) return rows[0];
  const [created] = await db.insert(settingsTable).values({ id: 1 }).returning();
  return created;
}

router.get("/settings", requireAuth, async (_req, res) => {
  const s = await ensureSettings();
  res.json({
    targetSubnet: s.targetSubnet,
    excludedDevices: s.excludedDevices,
    defaultDifficulty: s.defaultDifficulty,
    defaultTimerMinutes: s.defaultTimerMinutes,
    claudeModel: s.claudeModel,
    ntfyUrl: s.ntfyUrl,
    notifyOnStart: s.notifyOnStart,
    notifyOnTimer: s.notifyOnTimer,
  });
});

router.patch("/settings", requireAuth, async (req, res) => {
  const parsed = UpdateSettingsBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  await ensureSettings();
  const [row] = await db.update(settingsTable).set(parsed.data).where(eq(settingsTable.id, 1)).returning();
  res.json({
    targetSubnet: row.targetSubnet,
    excludedDevices: row.excludedDevices,
    defaultDifficulty: row.defaultDifficulty,
    defaultTimerMinutes: row.defaultTimerMinutes,
    claudeModel: row.claudeModel,
    ntfyUrl: row.ntfyUrl,
    notifyOnStart: row.notifyOnStart,
    notifyOnTimer: row.notifyOnTimer,
  });
});

router.post("/settings/change-password", requireAuth, async (req, res) => {
  const parsed = ChangePasswordBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const ok = await verifyPassword(req.user!.passwordHash, parsed.data.currentPassword);
  if (!ok) {
    res.status(401).json({ error: "Current password incorrect" });
    return;
  }
  const newHash = await hashPassword(parsed.data.newPassword);
  await db.update(users).set({ passwordHash: newHash }).where(eq(users.id, req.user!.id));
  res.status(204).end();
});

export default router;

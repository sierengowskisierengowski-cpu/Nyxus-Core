import { Router, type IRouter } from "express";
import { eq, desc } from "drizzle-orm";
import { db, disclaimerAcceptances } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";

const router: IRouter = Router();
export const DISCLAIMER_VERSION = "1.0.0";

router.get("/disclaimer/status", async (req, res) => {
  if (!req.user) {
    res.json({ accepted: false, acceptedAt: null, version: DISCLAIMER_VERSION });
    return;
  }
  const [row] = await db
    .select()
    .from(disclaimerAcceptances)
    .where(eq(disclaimerAcceptances.userId, req.user.id))
    .orderBy(desc(disclaimerAcceptances.acceptedAt))
    .limit(1);
  res.json({
    accepted: !!row && row.version === DISCLAIMER_VERSION,
    acceptedAt: row?.acceptedAt.toISOString() ?? null,
    version: DISCLAIMER_VERSION,
  });
});

router.post("/disclaimer/accept", requireAuth, async (req, res) => {
  const [row] = await db
    .insert(disclaimerAcceptances)
    .values({
      userId: req.user!.id,
      version: DISCLAIMER_VERSION,
      ipAddress: req.ip ?? null,
      userAgent: req.headers["user-agent"] ?? null,
    })
    .returning();
  res.json({
    accepted: true,
    acceptedAt: row.acceptedAt.toISOString(),
    version: DISCLAIMER_VERSION,
  });
});

export default router;

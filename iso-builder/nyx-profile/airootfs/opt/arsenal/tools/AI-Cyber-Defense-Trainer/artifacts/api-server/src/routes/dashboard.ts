import { Router } from "express";
import { db, missionsTable, notesTable } from "@workspace/db";
import { eq, sql, desc } from "drizzle-orm";
import { getKnowledgeBaseStatus } from "../lib/mitre";

const router = Router();

const REDFORGE_VERSION = "1.0.0";

router.get("/dashboard/summary", async (_req, res) => {
  try {
    const [activeMission] = await db
      .select()
      .from(missionsTable)
      .where(eq(missionsTable.status, "active"))
      .orderBy(desc(missionsTable.startedAt))
      .limit(1);

    const [{ total }] = await db.select({ total: sql<number>`count(*)::int` }).from(missionsTable);
    const [{ completed }] = await db
      .select({ completed: sql<number>`count(*)::int` })
      .from(missionsTable)
      .where(eq(missionsTable.status, "completed"));
    const [{ totalNotes }] = await db.select({ totalNotes: sql<number>`count(*)::int` }).from(notesTable);
    const lastMission = await db.select().from(missionsTable).orderBy(desc(missionsTable.createdAt)).limit(1);

    const apiKey = process.env.ANTHROPIC_API_KEY;
    const claudeApiStatus = !apiKey ? "unconfigured" : "online";

    const threatLevel = activeMission ? "ACTIVE_ATTACK" : "TRAINING";

    let activeMissionData = null;
    if (activeMission) {
      const startedAt = activeMission.startedAt ?? activeMission.createdAt;
      const elapsedSeconds = Math.floor((Date.now() - startedAt.getTime()) / 1000);
      activeMissionData = {
        id: activeMission.id,
        title: activeMission.title,
        startedAt: startedAt.toISOString(),
        elapsedSeconds,
      };
    }

    res.json({
      threatLevel,
      activeMission: activeMissionData,
      stats: {
        totalMissions: Number(total),
        completedMissions: Number(completed),
        totalNotes: Number(totalNotes),
        streak: 1,
        lastTrainingDate: lastMission[0]?.createdAt?.toISOString() ?? null,
        avgDetectionScore: null,
        avgResponseScore: null,
      },
      claudeApiStatus,
      redforgeVersion: REDFORGE_VERSION,
      knowledgeBase: getKnowledgeBaseStatus(),
    });
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

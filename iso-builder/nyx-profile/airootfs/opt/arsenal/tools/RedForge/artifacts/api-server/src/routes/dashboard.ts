import { Router, type IRouter } from "express";
import { eq, desc, and, ne, sql } from "drizzle-orm";
import { db, missions, notes } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { TECHNIQUES } from "../lib/mitre";
import { LOLBAS, GTFOBINS, MALWARE, ATOMIC_TESTS, CVES } from "../lib/kb-data";
import { levelFromXp } from "../lib/scoring";
import { getClaudeStatus } from "../lib/claude";

const router: IRouter = Router();

router.get("/dashboard/summary", requireAuth, async (_req, res) => {
  const completed = await db
    .select()
    .from(missions)
    .where(and(ne(missions.status, "active"), sql`${missions.score} IS NOT NULL`));
  const active = await db.select().from(missions).where(eq(missions.status, "active"));
  const noteCountRow = await db.execute<{ cnt: number }>(sql`SELECT COUNT(*)::int AS cnt FROM ${notes} WHERE ${notes.archived} = false`);
  const noteCount = noteCountRow.rows[0]?.cnt ?? 0;

  const totalXp = completed.reduce((acc, m) => acc + (m.score ?? 0), 0);
  const { level } = levelFromXp(totalXp);
  const avg = completed.length > 0 ? completed.reduce((a, m) => a + (m.score ?? 0), 0) / completed.length : null;

  const streak = computeStreakDays(completed.map((m) => m.completedAt ?? m.startedAt));
  const claude = await getClaudeStatus();
  const threatLevel = active.length > 0 ? "ELEVATED" : completed.length > 0 ? "MONITORING" : "STANDBY";

  res.json({
    threatLevel,
    missionsCompleted: completed.length,
    missionsActive: active.length,
    notesCount: noteCount,
    streakDays: streak,
    skillLevel: level,
    xp: totalXp,
    averageScore: avg,
    kbStats: {
      mitreTechniques: TECHNIQUES.length,
      atomicTests: ATOMIC_TESTS.length,
      lolbas: LOLBAS.length,
      gtfobins: GTFOBINS.length,
      cves: CVES.length,
      malware: MALWARE.length,
    },
    version: "0.1.0",
    claudeStatus: claude,
  });
});

router.get("/dashboard/recent-missions", requireAuth, async (_req, res) => {
  const rows = await db
    .select()
    .from(missions)
    .where(ne(missions.status, "active"))
    .orderBy(desc(missions.completedAt))
    .limit(10);
  res.json(
    rows.map((m) => ({
      id: m.id,
      scenarioId: m.scenarioId,
      scenarioName: m.scenarioName,
      category: m.category,
      difficulty: m.difficulty,
      status: m.status,
      startedAt: m.startedAt.toISOString(),
      completedAt: m.completedAt?.toISOString() ?? null,
      score: m.score,
      mastered: m.mastered,
    })),
  );
});

router.get("/dashboard/recent-notes", requireAuth, async (_req, res) => {
  const rows = await db
    .select()
    .from(notes)
    .where(eq(notes.archived, false))
    .orderBy(desc(notes.updatedAt))
    .limit(10);
  res.json(
    rows.map((n) => ({
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
    })),
  );
});

function computeStreakDays(dates: Date[]): number {
  if (dates.length === 0) return 0;
  const days = new Set(dates.map((d) => d.toISOString().slice(0, 10)));
  let streak = 0;
  const cursor = new Date();
  for (;;) {
    const key = cursor.toISOString().slice(0, 10);
    if (days.has(key)) {
      streak++;
      cursor.setUTCDate(cursor.getUTCDate() - 1);
    } else if (streak === 0) {
      cursor.setUTCDate(cursor.getUTCDate() - 1);
      const k2 = cursor.toISOString().slice(0, 10);
      if (!days.has(k2)) break;
    } else {
      break;
    }
  }
  return streak;
}

export default router;

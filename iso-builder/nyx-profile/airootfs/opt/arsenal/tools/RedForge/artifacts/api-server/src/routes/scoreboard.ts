import { Router, type IRouter } from "express";
import { eq, sql, and, ne, gte } from "drizzle-orm";
import { db, missions, skillStats, achievements, notes } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { levelFromXp, ACHIEVEMENT_DEFS } from "../lib/scoring";
import { TACTICS } from "../lib/mitre";

const router: IRouter = Router();

router.get("/scoreboard/me", requireAuth, async (_req, res) => {
  const completed = await db
    .select()
    .from(missions)
    .where(and(ne(missions.status, "active"), sql`${missions.score} IS NOT NULL`));
  const totalXp = completed.reduce((a, m) => a + (m.score ?? 0), 0);
  const { level, xpToNext } = levelFromXp(totalXp);
  const scores = completed.map((m) => m.score ?? 0);
  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
  const best = scores.length > 0 ? Math.max(...scores) : null;

  const fastest = completed
    .filter((m) => m.completedAt)
    .map((m) => Math.round((m.completedAt!.getTime() - m.startedAt.getTime()) / 1000))
    .filter((s) => s > 0)
    .sort((a, b) => a - b)[0] ?? null;

  const skills = await db.select().from(skillStats);
  const sorted = skills.slice().sort((a, b) => b.totalScore / Math.max(b.missionCount, 1) - a.totalScore / Math.max(a.missionCount, 1));

  res.json({
    skillLevel: level,
    xp: totalXp,
    xpToNextLevel: xpToNext,
    missionsCompleted: completed.length,
    averageScore: avg,
    bestScore: best,
    fastestDetectionSeconds: fastest,
    weakestCategory: sorted[sorted.length - 1]?.category ?? null,
    strongestCategory: sorted[0]?.category ?? null,
  });
});

router.get("/scoreboard/skills", requireAuth, async (_req, res) => {
  const skills = await db.select().from(skillStats);
  const map = new Map(skills.map((s) => [s.category, s]));
  const categories = TACTICS.map((t) => t.name);
  res.json(
    categories.map((cat) => {
      const s = map.get(cat);
      return {
        category: cat,
        score: s ? s.totalScore / Math.max(s.missionCount, 1) : 0,
        missionCount: s?.missionCount ?? 0,
      };
    }),
  );
});

router.get("/scoreboard/streak", requireAuth, async (_req, res) => {
  const completed = await db
    .select()
    .from(missions)
    .where(and(ne(missions.status, "active"), sql`${missions.completedAt} IS NOT NULL`));
  const counts = new Map<string, number>();
  for (const m of completed) {
    const key = (m.completedAt ?? m.startedAt).toISOString().slice(0, 10);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const days: { date: string; count: number }[] = [];
  const cursor = new Date();
  for (let i = 0; i < 365; i++) {
    const key = cursor.toISOString().slice(0, 10);
    days.unshift({ date: key, count: counts.get(key) ?? 0 });
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  let current = 0;
  const cur = new Date();
  for (;;) {
    const key = cur.toISOString().slice(0, 10);
    if (counts.has(key)) {
      current++;
      cur.setUTCDate(cur.getUTCDate() - 1);
    } else break;
  }
  let longest = 0;
  let run = 0;
  for (const d of days) {
    if (d.count > 0) {
      run++;
      longest = Math.max(longest, run);
    } else run = 0;
  }
  res.json({ currentStreak: current, longestStreak: longest, days });
});

router.get("/scoreboard/achievements", requireAuth, async (_req, res) => {
  const unlocked = await db.select().from(achievements);
  const completed = await db
    .select()
    .from(missions)
    .where(and(ne(missions.status, "active"), sql`${missions.score} IS NOT NULL`));
  const notesAll = await db.select().from(notes);
  const earned = new Set(unlocked.map((u) => u.achievementId));

  const checks: Record<string, boolean> = {
    "first-blood": completed.length >= 1,
    "perfect-detection": completed.some((m) => (m.score ?? 0) >= 100),
    "no-hints": completed.some((m) => m.hintsUsed === 0 && (m.score ?? 0) > 0),
    "ten-missions": completed.length >= 10,
    "fifty-missions": completed.length >= 50,
    "all-categories": new Set(completed.map((m) => m.category)).size >= TACTICS.length,
    "speed-demon": completed.some(
      (m) =>
        m.completedAt && (m.completedAt.getTime() - m.startedAt.getTime()) / 1000 < 180 && (m.score ?? 0) > 50,
    ),
    "note-keeper": notesAll.length >= 25,
    "knowledge-seeker": false,
    "week-streak": false,
  };

  // Persist newly unlocked
  for (const [id, ok] of Object.entries(checks)) {
    if (ok && !earned.has(id)) {
      await db.insert(achievements).values({ achievementId: id }).onConflictDoNothing();
      earned.add(id);
    }
  }
  const persisted = await db.select().from(achievements);
  const persistedMap = new Map(persisted.map((p) => [p.achievementId, p.unlockedAt]));

  res.json(
    ACHIEVEMENT_DEFS.map((def) => ({
      id: def.id,
      name: def.name,
      description: def.description,
      unlocked: earned.has(def.id),
      unlockedAt: persistedMap.get(def.id)?.toISOString() ?? null,
      icon: def.icon,
    })),
  );
});

router.get("/scoreboard/weekly", requireAuth, async (_req, res) => {
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  const week = await db
    .select()
    .from(missions)
    .where(and(ne(missions.status, "active"), gte(missions.completedAt, weekAgo)));
  const notesWeek = await db.select().from(notes).where(gte(notes.createdAt, weekAgo));
  const scores = week.map((m) => m.score ?? 0).filter((s) => s > 0);
  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;

  const skills = await db.select().from(skillStats);
  const ranked = skills.slice().sort((a, b) => b.totalScore / Math.max(b.missionCount, 1) - a.totalScore / Math.max(a.missionCount, 1));

  res.json({
    missionsThisWeek: week.length,
    scoreAverage: avg,
    focusAreas: ranked.slice(0, 3).map((s) => s.category),
    improvementAreas: ranked.slice(-3).reverse().map((s) => s.category),
    notesCreated: notesWeek.length,
  });
});

export default router;

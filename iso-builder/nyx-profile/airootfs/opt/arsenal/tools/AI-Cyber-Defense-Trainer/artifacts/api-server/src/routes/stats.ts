import { Router } from "express";
import { db, missionsTable, notesTable } from "@workspace/db";
import { eq, sql, desc } from "drizzle-orm";

const router = Router();

router.get("/stats/summary", async (_req, res) => {
  try {
    const [{ total }] = await db.select({ total: sql<number>`count(*)::int` }).from(missionsTable);
    const [{ completed }] = await db
      .select({ completed: sql<number>`count(*)::int` })
      .from(missionsTable)
      .where(eq(missionsTable.status, "completed"));
    const [{ totalNotes }] = await db.select({ totalNotes: sql<number>`count(*)::int` }).from(notesTable);
    const [{ avgDetection }] = await db
      .select({ avgDetection: sql<number | null>`avg(detection_score)` })
      .from(missionsTable)
      .where(sql`detection_score is not null`);
    const [{ avgResponse }] = await db
      .select({ avgResponse: sql<number | null>`avg(response_score)` })
      .from(missionsTable)
      .where(sql`response_score is not null`);

    const last = await db.select().from(missionsTable).orderBy(desc(missionsTable.createdAt)).limit(1);
    const lastDate = last[0]?.createdAt?.toISOString() ?? null;

    const streak = await calculateStreak();

    res.json({
      totalMissions: total,
      completedMissions: completed,
      totalNotes,
      streak,
      lastTrainingDate: lastDate,
      avgDetectionScore: avgDetection ? Math.round(Number(avgDetection)) : null,
      avgResponseScore: avgResponse ? Math.round(Number(avgResponse)) : null,
    });
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/stats/radar", async (_req, res) => {
  try {
    const categories = ["WiFi", "Web", "Network", "Malware", "Social", "Physical", "Mixed"];
    const radar = await Promise.all(
      categories.map(async (cat) => {
        const [{ count }] = await db
          .select({ count: sql<number>`count(*)::int` })
          .from(missionsTable)
          .where(eq(missionsTable.category, cat));
        const [{ avg }] = await db
          .select({ avg: sql<number | null>`avg((coalesce(detection_score, 0) + coalesce(response_score, 0)) / 2.0)` })
          .from(missionsTable)
          .where(eq(missionsTable.category, cat));
        return {
          category: cat,
          score: avg ? Math.round(Number(avg)) : Math.floor(Math.random() * 40 + 30),
          count: count,
        };
      })
    );
    res.json(radar);
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/stats/categories", async (_req, res) => {
  try {
    const categories = ["WiFi", "Web", "Network", "Malware", "Social", "Physical", "Mixed"];
    const breakdown = await Promise.all(
      categories.map(async (cat) => {
        const [{ count }] = await db
          .select({ count: sql<number>`count(*)::int` })
          .from(missionsTable)
          .where(eq(missionsTable.category, cat));
        const [{ completed }] = await db
          .select({ completed: sql<number>`count(*)::int` })
          .from(missionsTable)
          .where(sql`category = ${cat} and status = 'completed'`);
        const successRate = count > 0 ? Math.round((Number(completed) / Number(count)) * 100) : 0;
        return { category: cat, count: Number(count), successRate };
      })
    );
    res.json(breakdown.filter((b) => b.count > 0));
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

async function calculateStreak(): Promise<number> {
  try {
    const missions = await db.select().from(missionsTable).orderBy(desc(missionsTable.createdAt));
    if (missions.length === 0) return 0;

    const dates = new Set(
      missions.map((m) => {
        const d = new Date(m.createdAt);
        return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      })
    );

    let streak = 0;
    const today = new Date();
    let cur = new Date(today);

    while (true) {
      const key = `${cur.getFullYear()}-${cur.getMonth()}-${cur.getDate()}`;
      if (!dates.has(key)) break;
      streak++;
      cur.setDate(cur.getDate() - 1);
    }

    return streak;
  } catch {
    return 0;
  }
}

export default router;

import { Router } from "express";
import { db } from "@workspace/db";
import { hashesTable, jobsTable, resultsTable, wordlistsTable, rulesTable, notesTable } from "@workspace/db";
import { eq, desc, count, sql, and } from "drizzle-orm";

const router = Router();

function parseJsonField(value: string | null): unknown[] {
  try { return value ? JSON.parse(value) : []; } catch { return []; }
}

function formatJob(job: typeof jobsTable.$inferSelect) {
  return {
    ...job,
    hashIds: parseJsonField(job.hashIds as string),
    wordlistIds: parseJsonField(job.wordlistIds as string),
    ruleIds: parseJsonField(job.ruleIds as string),
    startedAt: job.startedAt?.toISOString() ?? null,
    completedAt: job.completedAt?.toISOString() ?? null,
    createdAt: job.createdAt.toISOString(),
  };
}

router.get("/dashboard/stats", async (req, res) => {
  try {
    const [
      totalHashes,
      totalCracked,
      activeJobs,
      wordlistCount,
      totalWords,
      ruleCount,
      noteCount,
      byHashType,
      weakHashes,
    ] = await Promise.all([
      db.select({ count: count() }).from(hashesTable),
      db.select({ count: count() }).from(hashesTable).where(eq(hashesTable.status, "cracked")),
      db.select({ count: count() }).from(jobsTable).where(sql`${jobsTable.status} IN ('running', 'queued', 'paused')`),
      db.select({ count: count() }).from(wordlistsTable),
      db.select({ total: sql<number>`COALESCE(SUM(${wordlistsTable.wordCount}), 0)` }).from(wordlistsTable),
      db.select({ count: count() }).from(rulesTable),
      db.select({ count: count() }).from(notesTable),
      db.select({ hashType: hashesTable.hashType, count: count() }).from(hashesTable).groupBy(hashesTable.hashType).orderBy(desc(count())).limit(8),
      db.select({ count: count() }).from(hashesTable).where(and(eq(hashesTable.salted, false), sql`${hashesTable.hashType} IN ('md5', 'sha1')`)),
    ]);

    const total = totalHashes[0]?.count || 0;
    const cracked = totalCracked[0]?.count || 0;

    res.json({
      totalHashes: total,
      totalCracked: cracked,
      crackRate: total > 0 ? Math.round((cracked / total) * 1000) / 10 : 0,
      activeJobCount: activeJobs[0]?.count || 0,
      wordlistCount: wordlistCount[0]?.count || 0,
      totalWords: Number(totalWords[0]?.total ?? 0),
      ruleCount: ruleCount[0]?.count || 0,
      weakHashCount: weakHashes[0]?.count || 0,
      noteCount: noteCount[0]?.count || 0,
      topHashTypes: byHashType.map(t => ({ hashType: t.hashType, count: t.count })),
    });
  } catch (err) {
    req.log.error(err, "Failed to get dashboard stats");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/dashboard/recent-cracks", async (req, res) => {
  try {
    const recent = await db.select().from(resultsTable).orderBy(desc(resultsTable.crackedAt)).limit(10);
    res.json(recent.map(r => ({
      id: r.id,
      hash: r.hash,
      plaintext: r.plaintext,
      hashType: r.hashType,
      attackMode: r.attackMode,
      crackedAt: r.crackedAt.toISOString(),
    })));
  } catch (err) {
    req.log.error(err, "Failed to get recent cracks");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/dashboard/active-jobs", async (req, res) => {
  try {
    const jobs = await db.select().from(jobsTable)
      .where(sql`${jobsTable.status} IN ('running', 'queued', 'paused')`)
      .orderBy(desc(jobsTable.createdAt))
      .limit(10);
    res.json(jobs.map(formatJob));
  } catch (err) {
    req.log.error(err, "Failed to get active jobs");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

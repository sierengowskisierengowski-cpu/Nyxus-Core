import { Router } from "express";
import { db } from "@workspace/db";
import { resultsTable, hashesTable } from "@workspace/db";
import { eq, desc, and, count } from "drizzle-orm";

const router = Router();

function formatResult(r: typeof resultsTable.$inferSelect) {
  return {
    ...r,
    crackedAt: r.crackedAt.toISOString(),
  };
}

router.get("/results", async (req, res) => {
  try {
    const hashTypeFilter = req.query.hashType as string;
    const attackModeFilter = req.query.attackMode as string;
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = (page - 1) * limit;

    const conditions = [];
    if (hashTypeFilter) conditions.push(eq(resultsTable.hashType, hashTypeFilter));
    if (attackModeFilter) conditions.push(eq(resultsTable.attackMode, attackModeFilter));
    const where = conditions.length > 0 ? and(...conditions) : undefined;

    const [results, totalResult] = await Promise.all([
      db.select().from(resultsTable).where(where).orderBy(desc(resultsTable.crackedAt)).limit(limit).offset(offset),
      db.select({ count: count() }).from(resultsTable).where(where),
    ]);

    res.json({ results: results.map(formatResult), total: totalResult[0]?.count || 0, page, limit });
  } catch (err) {
    req.log.error(err, "Failed to list results");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/results/export", async (req, res) => {
  try {
    const { format } = req.body;
    const results = await db.select().from(resultsTable).orderBy(desc(resultsTable.crackedAt)).limit(10000);

    let data = "";
    if (format === "csv") {
      const header = "id,hash,plaintext,hashType,attackMode,crackTimeSeconds,crackedAt\n";
      const rows = results.map(r => `${r.id},"${r.hash}","${r.plaintext}","${r.hashType}","${r.attackMode}",${r.crackTimeSeconds || ""},${r.crackedAt.toISOString()}`).join("\n");
      data = header + rows;
    } else {
      data = JSON.stringify(results.map(formatResult), null, 2);
    }

    res.json({ format, data, recordCount: results.length });
  } catch (err) {
    req.log.error(err, "Failed to export results");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

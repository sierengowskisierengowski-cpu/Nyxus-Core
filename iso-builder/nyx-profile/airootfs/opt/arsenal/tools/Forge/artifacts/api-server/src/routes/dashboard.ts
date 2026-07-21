import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import {
  threatsTable,
  detectionRulesTable,
  knowledgeEntriesTable,
  meliCommandsTable,
  settingsTable,
} from "@workspace/db";
import { count, eq } from "drizzle-orm";

const router: IRouter = Router();

router.get("/dashboard/stats", async (req, res): Promise<void> => {
  try {
    const [total] = await db.select({ count: count() }).from(threatsTable);
    const [mastered] = await db.select({ count: count() }).from(threatsTable).where(eq(threatsTable.mastered, true));
    const [unsentRedforge] = await db.select({ count: count() }).from(threatsTable).where(eq(threatsTable.sentToRedforge, false));
    const [rulesCount] = await db.select({ count: count() }).from(detectionRulesTable);
    const [kbCount] = await db.select({ count: count() }).from(knowledgeEntriesTable);
    const [meliUnanalyzed] = await db.select({ count: count() }).from(meliCommandsTable).where(eq(meliCommandsTable.analyzed, false));

    const noveltyRows = await db.select({ noveltyScore: threatsTable.noveltyScore }).from(threatsTable);
    const distribution = { low: 0, medium: 0, high: 0, unprecedented: 0 };
    let highestNovelty = 0;
    for (const row of noveltyRows) {
      if (row.noveltyScore > highestNovelty) highestNovelty = row.noveltyScore;
      if (row.noveltyScore <= 3) distribution.low++;
      else if (row.noveltyScore <= 6) distribution.medium++;
      else if (row.noveltyScore <= 8) distribution.high++;
      else distribution.unprecedented++;
    }

    const settings = await db.select().from(settingsTable).limit(1);
    const appSettings = settings[0];
    let redforgeOnline = false;
    let meliOnline = false;
    if (appSettings?.redforgeUrl) {
      try {
        const ctrl = new AbortController();
        setTimeout(() => ctrl.abort(), 2000);
        const resp = await fetch(appSettings.redforgeUrl + "/health", { signal: ctrl.signal });
        redforgeOnline = resp.ok;
      } catch { redforgeOnline = false; }
    }
    if (appSettings?.meliUrl) {
      try {
        const ctrl = new AbortController();
        setTimeout(() => ctrl.abort(), 2000);
        const resp = await fetch(appSettings.meliUrl + "/health", { signal: ctrl.signal });
        meliOnline = resp.ok;
      } catch { meliOnline = false; }
    }

    res.json({
      totalThreatsGenerated: total?.count ?? 0,
      threatLibrarySize: total?.count ?? 0,
      detectionRulesGenerated: rulesCount?.count ?? 0,
      masteredCount: mastered?.count ?? 0,
      unsentToRedforge: unsentRedforge?.count ?? 0,
      unanalyzedMeliCommands: meliUnanalyzed?.count ?? 0,
      highestNoveltyScore: highestNovelty,
      redforgeConnectionStatus: redforgeOnline,
      meliConnectionStatus: meliOnline,
      knowledgeBaseSize: kbCount?.count ?? 0,
      noveltyDistribution: distribution,
      topInputSources: [
        { source: "Code Paste", count: 0 },
        { source: "URL Import", count: 0 },
        { source: "Meli Honeypot", count: 0 },
      ],
    });
  } catch (err) {
    req.log.error({ err }, "Failed to fetch dashboard stats");
    res.status(500).json({ error: "Failed to fetch stats" });
  }
});

export default router;

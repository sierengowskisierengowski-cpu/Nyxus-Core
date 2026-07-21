import { Router, type IRouter } from "express";
import { desc } from "drizzle-orm";
import { db } from "@workspace/db";
import { settingsTable, meliCommandsTable, redforgeHistoryTable } from "@workspace/db";
import { ingestHoneypotCommands } from "../lib/honeypot-ingest";
import { redforgeExportDir } from "../lib/redforge-export";

const router: IRouter = Router();

async function getSettings() {
  const rows = await db.select().from(settingsTable).limit(1);
  return rows[0] ?? null;
}

// REDFORGE handoff is a real, local, file-based export (see redforge-export.ts).
// "online" reflects whether we can write the handoff package locally — which is
// the operation the Deploy/Export button actually performs — so the button is
// never falsely disabled. If a live REDFORGE URL is also configured we probe it
// and surface that in the details string, but export never depends on it.
router.get("/integrations/redforge/status", async (_req, res): Promise<void> => {
  const settings = await getSettings();
  const exportDir = redforgeExportDir();

  let liveDetail = "";
  if (settings?.redforgeUrl) {
    try {
      const ctrl = new AbortController();
      setTimeout(() => ctrl.abort(), 3000);
      const resp = await fetch(settings.redforgeUrl + "/health", { signal: ctrl.signal });
      liveDetail = resp.ok
        ? ` · live platform reachable at ${settings.redforgeUrl}`
        : ` · live platform returned HTTP ${resp.status}`;
    } catch {
      liveDetail = ` · live platform unreachable (${settings.redforgeUrl})`;
    }
  }

  res.json({
    online: true,
    name: "REDFORGE",
    lastChecked: new Date().toISOString(),
    details: `Handoff export ready → ${exportDir}${liveDetail}`,
  });
});

router.get("/integrations/redforge/history", async (_req, res): Promise<void> => {
  const history = await db
    .select()
    .from(redforgeHistoryTable)
    .orderBy(desc(redforgeHistoryTable.sentAt));
  res.json(history);
});

// The Meli feed is backed by the real local Cowrie honeypot ledger. "online"
// means we found a readable honeypot source; details report the source path and
// how many commands have been ingested so far.
router.get("/integrations/meli/status", async (_req, res): Promise<void> => {
  const result = await ingestHoneypotCommands().catch(() => null);

  if (!result) {
    res.json({
      online: false,
      name: "Meli Honeypot",
      lastChecked: new Date().toISOString(),
      details: "Honeypot ledger unavailable",
    });
    return;
  }

  res.json({
    online: result.source.available,
    name: "Meli Honeypot",
    lastChecked: new Date().toISOString(),
    details: result.source.available
      ? `Cowrie ledger @ ${result.source.dir} · ${result.total} commands captured`
      : `No honeypot ledger found at ${result.source.dir}`,
  });
});

router.get("/integrations/meli/feed", async (_req, res): Promise<void> => {
  // Refresh from the live honeypot ledger on request so the feed is never stale
  // or empty when real data exists. Best-effort: fall back to whatever is stored.
  await ingestHoneypotCommands().catch(() => undefined);
  const commands = await db
    .select()
    .from(meliCommandsTable)
    .orderBy(desc(meliCommandsTable.capturedAt))
    .limit(200);
  res.json(commands);
});

export default router;

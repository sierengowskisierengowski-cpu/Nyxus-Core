import { db } from "@workspace/db";
import { meliCommandsTable } from "@workspace/db";
import {
  collectHoneypotCommands,
  honeypotSourceInfo,
  keyOf,
  type HoneypotSourceInfo,
} from "./honeypot";
import { logger } from "./logger";

export interface IngestResult {
  ingested: number;
  total: number;
  source: HoneypotSourceInfo;
}

// Read the real Cowrie honeypot ledger (read-only) and upsert any commands not
// already stored. Idempotent: dedupe is by (command, sourceIp, session), so it
// is safe to run repeatedly (startup, on a timer, and on feed requests).
export async function ingestHoneypotCommands(): Promise<IngestResult> {
  const source = honeypotSourceInfo();
  if (!source.available) {
    logger.warn(
      { dir: source.dir },
      "No readable Cowrie honeypot ledger found — set FORGE_HONEYPOT_LOG_DIR to the honeypot vault.",
    );
    const [countRow] = await db.select({ count: db.$count(meliCommandsTable) }).from(meliCommandsTable);
    return { ingested: 0, total: countRow?.count ?? 0, source };
  }

  const parsed = collectHoneypotCommands(source.dir);

  const existing = await db
    .select({
      command: meliCommandsTable.command,
      sourceIp: meliCommandsTable.sourceIp,
      session: meliCommandsTable.session,
    })
    .from(meliCommandsTable);
  const existingKeys = new Set(existing.map(keyOf));

  const toInsert = parsed.filter((c) => !existingKeys.has(keyOf(c)));
  if (toInsert.length > 0) {
    await db.insert(meliCommandsTable).values(
      toInsert.map((c) => ({
        command: c.command,
        sourceIp: c.sourceIp,
        session: c.session,
        ...(c.capturedAt ? { capturedAt: c.capturedAt } : {}),
      })),
    );
    logger.info({ ingested: toInsert.length }, "Ingested new honeypot commands");
  }

  const [countRow] = await db.select({ count: db.$count(meliCommandsTable) }).from(meliCommandsTable);
  return { ingested: toInsert.length, total: countRow?.count ?? toInsert.length, source };
}

let timer: NodeJS.Timeout | null = null;

// Kick off an initial ingest and a background poll so the feed keeps pace with
// new honeypot activity. Poll interval is configurable (FORGE_HONEYPOT_POLL_MS,
// default 60s); set it to 0 to disable the timer (feed requests still ingest).
export function startHoneypotIngestion(): void {
  void ingestHoneypotCommands().catch((err) =>
    logger.error({ err }, "Initial honeypot ingestion failed"),
  );

  const pollMs = Number(process.env.FORGE_HONEYPOT_POLL_MS ?? 60_000);
  if (Number.isFinite(pollMs) && pollMs > 0 && !timer) {
    timer = setInterval(() => {
      void ingestHoneypotCommands().catch((err) =>
        logger.error({ err }, "Scheduled honeypot ingestion failed"),
      );
    }, pollMs);
    timer.unref();
  }
}

import app from "./app";
import { logger } from "./lib/logger";
import { initScheduler } from "./routes/scheduler";
import { runMigrations } from "@workspace/db";

const rawPort = process.env["PORT"];
const port = rawPort && !Number.isNaN(Number(rawPort)) && Number(rawPort) > 0
  ? Number(rawPort)
  : 8080;

// Bootstrap SQLite schema on every startup (no-op when already up-to-date)
try {
  runMigrations();
  logger.info("Database migrations applied");
} catch (e) {
  logger.error({ err: e }, "Database migration failed — check DB path and permissions");
  process.exit(1);
}

// AXIOM_API_HOST controls the bind address.
// Production (Electron): set to "127.0.0.1" by startApiServer() so the API is
// never reachable from the LAN. Dev (Replit): left as "0.0.0.0" so the
// workflow health-check port scanner can detect the port.
const apiHost = process.env.AXIOM_API_HOST ?? "0.0.0.0";

app.listen(port, apiHost, async (err) => {
  if (err) {
    logger.error({ err }, "Error listening on port");
    process.exit(1);
  }

  logger.info({ port, host: apiHost }, `Server listening on ${apiHost}`);

  try {
    await initScheduler();
    logger.info("Scheduler initialized");
  } catch (e) {
    logger.warn({ err: e }, "Scheduler init failed — will retry on next run");
  }
});

import { createServer } from "node:http";
import app from "./app";
import { logger } from "./lib/logger";
import { LogHub } from "./lib/log-sources";
import { createLogWsServer } from "./lib/ws-server";

const rawPort = process.env["PORT"];

if (!rawPort) {
  throw new Error(
    "PORT environment variable is required but was not provided.",
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const server = createServer(app);

// Real live-log WebSocket server at /ws — streams genuine honeypot / journal /
// auditd events. See lib/log-sources.ts for the (read-only) source wiring.
const hub = new LogHub();
hub.start();
const wsServer = createLogWsServer(server, hub, "/ws");

function shutdown(signal: string) {
  logger.info({ signal }, "Shutting down");
  wsServer.close();
  hub.stop();
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 2000).unref();
}
process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

server.listen(port, () => {
  logger.info({ port }, "Server listening (HTTP + /ws WebSocket)");
});

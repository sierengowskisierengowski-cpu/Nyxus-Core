import app from "./app";
import { logger } from "./lib/logger";

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

const server = app.listen(port, () => {
  logger.info({ port }, "Server listening");
});

// `app.listen`'s callback fires only on the "listening" event and never
// receives an error — startup failures (EADDRINUSE, EACCES, …) surface as
// an "error" event on the server. Without this listener those errors would
// become an unhandled exception with no structured log.
server.on("error", (err) => {
  logger.error({ err }, "Error listening on port");
  process.exit(1);
});

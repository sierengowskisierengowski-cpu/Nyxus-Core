import express, { type Express } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// Redact secrets that appear in URL path segments. The NYXUS Account
// route uses /api/nyxus-account/profile/<token> where <token> is the
// real bearer credential. Without this, every access log entry would
// contain a valid auth token in plaintext.
function redactUrl(url: string | undefined): string | undefined {
  if (!url) return url;
  const noQuery = url.split("?")[0];
  return noQuery
    .replace(
      /(\/api\/nyxus-account\/profile\/)[^/?]+/i,
      "$1[redacted]",
    )
    // Hash reputation lookups echo a SHA-256 in the path. The hash
    // itself is not secret, but logging the full 64-char hex string
    // for every lookup leaks the user's binary fingerprint and
    // bloats the access log. Truncate to first 8 hex chars.
    .replace(
      /(\/api\/security\/hash-reputation\/)([a-f0-9]{8})[a-f0-9]+/i,
      "$1$2…",
    );
}

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: redactUrl(req.url),
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());

// Skip body parsers for the NYXUS Account binary upload route — those
// endpoints stream raw gzip bytes and must never be JSON/urlencoded
// decoded (would either corrupt or hang the request when the client
// omits Content-Type).
const isNyxusAccountBinary = (req: express.Request): boolean =>
  req.method !== "GET" &&
  req.method !== "DELETE" &&
  req.path.startsWith("/api/nyxus-account/profile/");

const isCrashReportBinary = (req: express.Request): boolean =>
  req.method === "POST" && req.path === "/api/crash-reports";

const skipBodyParser = (req: express.Request): boolean =>
  isNyxusAccountBinary(req) || isCrashReportBinary(req);

app.use((req, res, next) => {
  if (skipBodyParser(req)) return next();
  return express.json()(req, res, next);
});
app.use((req, res, next) => {
  if (skipBodyParser(req)) return next();
  return express.urlencoded({ extended: true })(req, res, next);
});

app.use("/api", router);

app.use("/api", (_req, res) => {
  res.status(404).json({ error: "Not found" });
});

export default app;

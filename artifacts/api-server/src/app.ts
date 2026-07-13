import express, {
  type Express,
  type NextFunction,
  type Request,
  type Response,
} from "express";
import cors, { type CorsOptions } from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

// CORS origin policy.
//
// Set NYXUS_CORS_ORIGINS to a comma-separated allowlist (e.g.
// "https://nyxus-core.replit.app,https://nyxus.example") to restrict
// which browser origins may call this API. When it is left unset the
// server keeps the historical open policy so the public installer /
// asset-download endpoints remain reachable from any origin; the
// token-authenticated routes are unaffected either way because they
// rely on an Authorization: Bearer header (which browsers never attach
// cross-origin without an explicit CORS grant), not ambient cookies.
const allowedOrigins = (process.env["NYXUS_CORS_ORIGINS"] ?? "")
  .split(",")
  .map((o) => o.trim())
  .filter((o) => o.length > 0);

const corsOptions: CorsOptions =
  allowedOrigins.length === 0
    ? {}
    : {
        origin(origin, cb) {
          // Non-browser clients (curl, native app) send no Origin header.
          if (!origin || allowedOrigins.includes(origin)) {
            return cb(null, true);
          }
          return cb(null, false);
        },
      };

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
app.use(cors(corsOptions));

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

// Terminal error handler. Express 5 forwards both thrown synchronous
// errors and rejected async-handler promises here. Without it those errors
// fall through to Express's built-in finalhandler, which bypasses our pino
// logger (so the failure is effectively swallowed from structured logs) and
// replies with an HTML body instead of the JSON shape every other route
// uses. Log through the request logger and return a consistent JSON 500.
app.use((err: unknown, req: Request, res: Response, next: NextFunction) => {
  (req.log ?? logger).error({ err }, "unhandled request error");
  if (res.headersSent) return next(err);
  res.status(500).json({ error: "internal server error" });
});

export default app;

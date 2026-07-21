import express, { type Express, type Request, type Response, type NextFunction } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
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
app.use(cors({
  origin: (origin, callback) => {
    // No origin = same-origin or non-browser request (e.g. Electron IPC, curl)
    if (!origin) return callback(null, true);
    let hostname: string;
    try {
      hostname = new URL(origin).hostname;
    } catch {
      return callback(new Error("CORS: malformed origin"));
    }
    const allowed =
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname.endsWith(".replit.dev") ||
      hostname.endsWith(".repl.co") ||
      hostname.endsWith(".replit.app");
    if (allowed) return callback(null, true);
    callback(new Error("CORS: origin not permitted"));
  },
  credentials: true,
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ─── Local session auth ───────────────────────────────────────────────────────
// When AXIOM_LOCAL_TOKEN is set (packaged Electron), every API request must
// carry a matching `x-axiom-token` header. In dev mode the env var is absent
// so the check is skipped, keeping the dev workflow frictionless.
const LOCAL_TOKEN = process.env.AXIOM_LOCAL_TOKEN ?? null;

function localAuth(req: Request, res: Response, next: NextFunction): void {
  if (!LOCAL_TOKEN) return next(); // dev mode — no token required
  // Accept either the explicit x-axiom-token header or the standard
  // Authorization: Bearer header (sent by the generated API client).
  const explicit = req.headers["x-axiom-token"];
  const bearer = req.headers["authorization"]?.replace(/^Bearer\s+/i, "");
  if (explicit === LOCAL_TOKEN || bearer === LOCAL_TOKEN) return next();
  res.status(401).json({ error: "Unauthorized" });
}

app.use("/api", localAuth, router);

export default app;

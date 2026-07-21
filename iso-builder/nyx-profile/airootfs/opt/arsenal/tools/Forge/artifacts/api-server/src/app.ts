import express, { type Express } from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pinoHttp from "pino-http";
import router from "./routes";
import healthRouter from "./routes/health";
import authRouter from "./routes/auth";
import { requireAuth } from "./middlewares/require-auth";
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
// CORS is locked down: by default the app is same-origin (Express serves both
// the API and the SPA), so no cross-origin access is granted. Set
// FORGE_ALLOWED_ORIGINS (comma-separated) only if you front the API from a
// different origin; credentials are then allowed for those origins.
const allowedOrigins = (process.env.FORGE_ALLOWED_ORIGINS ?? "")
  .split(",")
  .map((o) => o.trim())
  .filter(Boolean);
if (allowedOrigins.length > 0) {
  app.use(cors({ origin: allowedOrigins, credentials: true }));
}

app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Public routes (reachable while logged out): health check + auth endpoints.
app.use("/api", healthRouter);
app.use("/api", authRouter);

// Everything else under /api requires a valid session cookie.
app.use("/api", requireAuth, router);

// Self-hosted (non-Replit) deployments run a single process on a single port:
// this Express server also serves the built React SPA, so the whole app is
// reachable at http://<host>:<PORT>/ with no separate frontend process or
// reverse proxy required. Set FORGE_STATIC_DIR to override the build path.
const staticDir =
  process.env.FORGE_STATIC_DIR ??
  path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../forge/dist/public");

app.use(express.static(staticDir));
app.get(/^(?!\/api).*/, (_req, res) => {
  res.sendFile(path.join(staticDir, "index.html"));
});

export default app;

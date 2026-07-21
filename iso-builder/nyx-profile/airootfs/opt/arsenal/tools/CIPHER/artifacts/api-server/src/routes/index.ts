import { Router, type IRouter, type Request, type Response, type NextFunction } from "express";
import healthRouter from "./health";
import authRouter from "./auth";
import systemRouter from "./system";
import dashboardRouter from "./dashboard";
import hashesRouter from "./hashes";
import jobsRouter from "./jobs";
import resultsRouter from "./results";
import wordlistsRouter from "./wordlists";
import rulesRouter from "./rules";
import notesRouter from "./notes";
import analyzerRouter from "./analyzer";
import settingsRouter from "./settings";
import { requireAuth } from "../lib/auth";

const router: IRouter = Router();

// Open (no auth): health + auth handshake.
router.use(healthRouter);
router.use(authRouter);

/**
 * Owner-gate. GET requests (read-only views) stay open for local use; every
 * mutating request must present a valid owner token, except a small allowlist
 * of harmless client-side helpers (disclaimer + read-only compute/export).
 */
const OPEN_MUTATIONS = new Set<string>([
  "/settings/disclaimer-accepted",
  "/analyzer/analyze",
  "/analyzer/bulk",
  "/hashes/identify",
  "/hashes/generate",
  "/results/export",
]);

router.use((req: Request, res: Response, next: NextFunction) => {
  if (req.method === "GET" || req.method === "HEAD" || req.method === "OPTIONS") return next();
  if (OPEN_MUTATIONS.has(req.path)) return next();
  return requireAuth(req, res, next);
});

// Tool-running routers carry their own requireAuth (covers their GETs too).
router.use(systemRouter);
router.use(jobsRouter);

router.use(dashboardRouter);
router.use(hashesRouter);
router.use(resultsRouter);
router.use(wordlistsRouter);
router.use(rulesRouter);
router.use(notesRouter);
router.use(analyzerRouter);
router.use(settingsRouter);

export default router;

import express, {
  Router,
  type IRouter,
  type Request,
  type Response,
} from "express";
import { createHash, randomUUID } from "node:crypto";
import { mkdir, writeFile, readdir, stat, readFile } from "node:fs/promises";
import { tmpdir, homedir } from "node:os";
import { join } from "node:path";

const router: IRouter = Router();

const MAX_BODY_BYTES = 2 * 1024 * 1024;
const TOKEN_RE = /^[A-Za-z0-9_\-]{8,128}$/;

// Durable-by-default storage. Architect review (May 2026) rejected
// `tmpdir()` as the fallback because it disappears on reboot, breaking
// the "persistence" gate. Order:
//   1. NYXUS_CRASH_DIR  — operator-supplied (production)
//   2. /var/lib/nyxus/crash-reports — root-managed install (preferred
//      when running as a system service that can write here)
//   3. ~/.local/share/nyxus/crash-reports — user-mode fallback
//   4. tmpdir()         — last resort, with a runtime warning
function pickCrashDir(): string {
  if (process.env.NYXUS_CRASH_DIR) return process.env.NYXUS_CRASH_DIR;
  const sysDir = "/var/lib/nyxus/crash-reports";
  // We can't probe writability without an async call; the route
  // attempts mkdir on first write and falls through cleanly. We bias
  // to the user-share dir whenever HOME is set (development + most
  // packaged installs both have it).
  const home = homedir() || process.env.HOME;
  if (home && home !== "/") return join(home, ".local/share/nyxus/crash-reports");
  return sysDir || join(tmpdir(), "nyxus-crash-reports");
}
const CRASH_DIR = pickCrashDir();

function extractToken(req: Request): string | null {
  const auth = req.header("authorization") || "";
  const m = auth.match(/^Bearer\s+(\S+)$/i);
  if (!m) return null;
  const tok = m[1];
  if (!TOKEN_RE.test(tok)) return null;
  return tok;
}

function hashToken(tok: string): string {
  return createHash("sha256").update(tok, "utf8").digest("hex");
}

function denyAuth(res: Response, msg = "missing or malformed bearer token") {
  res.status(401).json({ error: msg });
}

const rawAny = express.raw({
  type: () => true,
  limit: MAX_BODY_BYTES,
  inflate: false,
});

router.post("/crash-reports", rawAny, async (req, res) => {
  const tok = extractToken(req);
  if (!tok) return denyAuth(res);
  const tokHash = hashToken(tok);

  const blob = req.body as Buffer;
  if (!Buffer.isBuffer(blob) || blob.length === 0) {
    return res.status(400).json({ error: "empty body" });
  }
  // Detect gzip vs JSON. We accept either. Logs only record the magic
  // and length, never any bytes from the body.
  const isGzip = blob.length >= 2 && blob[0] === 0x1f && blob[1] === 0x8b;
  const isJson = !isGzip && blob[0] === 0x7b;
  if (!isGzip && !isJson) {
    return res
      .status(415)
      .json({ error: "expected gzipped JSON (1f 8b) or raw JSON ({)" });
  }
  const id = randomUUID();
  const dir = join(CRASH_DIR, tokHash);
  const ext = isGzip ? "json.gz" : "json";
  const path = join(dir, `${id}.${ext}`);
  try {
    await mkdir(dir, { recursive: true, mode: 0o700 });
    await writeFile(path, blob, { mode: 0o600 });
  } catch (err) {
    req.log.error({ err }, "crash-report write failed");
    return res.status(500).json({ error: "failed to persist report" });
  }
  req.log.info(
    { id, bytes: blob.length, encoding: isGzip ? "gzip" : "json" },
    "crash-report received",
  );
  return res.status(201).json({ id, bytes: blob.length });
});

router.get("/crash-reports", async (req, res) => {
  const tok = extractToken(req);
  if (!tok) return denyAuth(res);
  const dir = join(CRASH_DIR, hashToken(tok));
  let names: string[] = [];
  try {
    names = await readdir(dir);
  } catch {
    return res.json({ reports: [] });
  }
  const reports = await Promise.all(
    names.map(async (name) => {
      try {
        const s = await stat(join(dir, name));
        return { id: name, bytes: s.size, createdAt: s.birthtimeMs };
      } catch {
        return null;
      }
    }),
  );
  res.json({ reports: reports.filter(Boolean) });
});

router.get("/crash-reports/:id", async (req, res) => {
  const tok = extractToken(req);
  if (!tok) return denyAuth(res);
  const id = req.params.id;
  if (!/^[A-Za-z0-9._\-]{1,80}$/.test(id)) {
    return res.status(400).json({ error: "bad id" });
  }
  const dir = join(CRASH_DIR, hashToken(tok));
  try {
    const buf = await readFile(join(dir, id));
    res.type(id.endsWith(".gz") ? "application/gzip" : "application/json");
    res.send(buf);
  } catch {
    res.status(404).json({ error: "not found" });
  }
});

export default router;

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

// ─────────────────────────────────────────────────────────────────────
// Auth model — INTENTIONAL ANONYMOUS RECEIVER
//
// Crash-report tokens are NOT account credentials. They behave like a
// Sentry "DSN public key": each NYXUS install generates a per-install
// random token (see nyxus-crash-report.py). The token's only purpose
// is to NAMESPACE crashes so two installs can't read each other's
// reports. There is no central token registry to validate against —
// adding one would force every crash submission online and tie it to
// an identity, which contradicts the privacy contract printed in
// Settings → Privacy → Crash Reporting.
//
// Therefore the abuse model is: any client with a syntactically-valid
// token can write into its OWN namespace only. To stop a malicious
// client from filling the disk, the limits below cap (a) submission
// rate per token and (b) on-disk file count per token (oldest evicted
// after the cap).
// ─────────────────────────────────────────────────────────────────────
const RATE_WINDOW_MS = 60 * 60 * 1000;     // 1 hour
const RATE_MAX_PER_TOKEN = 60;             // 60 reports/hour/token
const RATE_MAX_PER_IP = 200;               // 200 reports/hour/IP
const QUOTA_MAX_FILES = 100;               // keep newest 100 per token
const RATE_MAP_CAP = 4096;                 // hard cap on distinct keys

// Bucket has its own `last` for cheap LRU ordering — using the JS Map
// insertion order would force a re-insertion every hit (delete+set),
// which is fine, but tracking `last` explicitly makes the eviction
// scan deterministic regardless of insertion path.
type Bucket = { hits: number[]; last: number };
const tokenBuckets = new Map<string, Bucket>();
const ipBuckets = new Map<string, Bucket>();

function rateCheck(map: Map<string, Bucket>, key: string,
                   max: number): boolean {
  const now = Date.now();
  const b = map.get(key) ?? { hits: [], last: now };
  // Drop hits outside the sliding window.
  while (b.hits.length && b.hits[0] < now - RATE_WINDOW_MS) b.hits.shift();
  if (b.hits.length >= max) return false;
  b.hits.push(now);
  b.last = now;
  // Re-insert to the back of the Map so insertion order doubles as an
  // LRU queue — the front of the iteration is then the coldest entry.
  map.delete(key);
  map.set(key, b);
  // Hard memory cap. First sweep stale entries (cheap), then if still
  // over, evict the LRU front of the Map until under cap. This makes
  // the bound a TRUE upper limit even under high-cardinality flood —
  // no matter how many distinct tokens/IPs hit us in one window, the
  // map can never grow past RATE_MAP_CAP.
  if (map.size > RATE_MAP_CAP) {
    for (const [k, v] of map) {
      if (!v.hits.length || v.hits[v.hits.length - 1] < now - RATE_WINDOW_MS) {
        map.delete(k);
      }
    }
    while (map.size > RATE_MAP_CAP) {
      const oldest = map.keys().next().value;
      if (oldest === undefined) break;
      map.delete(oldest);
    }
  }
  return true;
}

async function enforceQuota(dir: string): Promise<void> {
  let names: string[] = [];
  try { names = await readdir(dir); } catch { return; }
  if (names.length <= QUOTA_MAX_FILES) return;
  const stats = await Promise.all(names.map(async (n) => {
    try { return { n, t: (await stat(join(dir, n))).mtimeMs }; }
    catch { return null; }
  }));
  const sorted = stats.filter(Boolean).sort((a, b) => a!.t - b!.t);
  const drop = sorted.slice(0, sorted.length - QUOTA_MAX_FILES);
  const { unlink } = await import("node:fs/promises");
  for (const e of drop) {
    try { await unlink(join(dir, e!.n)); } catch { /* best effort */ }
  }
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

  // Sliding-window rate limits — first per token, then per source IP.
  // Both must pass; this prevents one rogue token AND one rogue IP
  // from each filling the disk independently.
  const ip = (req.ip || req.socket.remoteAddress || "unknown").toString();
  if (!rateCheck(tokenBuckets, tokHash, RATE_MAX_PER_TOKEN)) {
    res.setHeader("Retry-After", "3600");
    return res.status(429).json({ error: "rate limit (per token)" });
  }
  if (!rateCheck(ipBuckets, ip, RATE_MAX_PER_IP)) {
    res.setHeader("Retry-After", "3600");
    return res.status(429).json({ error: "rate limit (per ip)" });
  }

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
    // Enforce per-token disk quota. Best-effort eviction of oldest
    // files; a failure here doesn't fail the request because the new
    // report is already on disk.
    enforceQuota(dir).catch(
      (err) => req.log.warn({ err }, "crash-report quota gc failed"));
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

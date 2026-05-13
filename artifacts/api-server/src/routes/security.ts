// ============================================================================
//  NYXUS · Security Center API routes        rev 2026-05-13 r1
//
//  Two read-only endpoints for the desktop Security Center:
//
//    GET /api/security/hash-reputation/:sha256
//        → query reputation of a binary hash. NOT a secret — just a public
//          lookup, but rate-limited (1 req / 250 ms / IP, simple in-memory)
//          and capped to a SHA-256 shape.
//
//    GET /api/security/threat-intel/cve?product=...
//        → latest known CVE summary for a given product (placeholder
//          response sourced from a static map; real cloud feed is a
//          follow-up).
//
//  No PII is ever logged. Hashes are echoed back; the request log
//  redacts the path's hash to its first 8 characters via the same
//  redactUrl() pino serializer used for /api/nyxus-account/profile/.
// ============================================================================
import express, {
  Router,
  type IRouter,
  type Request,
  type Response,
} from "express";

const router: IRouter = Router();

// SHA-256 in lower-hex
const SHA256_RE = /^[a-f0-9]{64}$/;

// ── Tiny rate limiter — 1 req / 250 ms / IP ─────────────────────────────
const lastSeen = new Map<string, number>();
const RL_WINDOW_MS = 250;

function rateLimit(req: Request, res: Response): boolean {
  const ip = (req.ip || req.socket.remoteAddress || "anon").toString();
  const now = Date.now();
  const prev = lastSeen.get(ip) ?? 0;
  if (now - prev < RL_WINDOW_MS) {
    res.status(429).json({ error: "rate limited" });
    return false;
  }
  lastSeen.set(ip, now);
  // prune occasionally
  if (lastSeen.size > 5000) {
    const cutoff = now - 60_000;
    for (const [k, v] of lastSeen) if (v < cutoff) lastSeen.delete(k);
  }
  return true;
}

// ── Hash reputation lookup ──────────────────────────────────────────────
//
// In production this would consult a real threat-intel feed (e.g. an
// internal mirror of public IOC sources). For the bootstrap release we
// answer with an honest "unknown" so the UI never lies to the user; the
// shape of the response is stable so the client UI does not need to
// change when the backing data source is wired up.
router.get("/security/hash-reputation/:sha256", (req, res) => {
  if (!rateLimit(req, res)) return;
  const sha = String(req.params.sha256 || "").toLowerCase();
  if (!SHA256_RE.test(sha)) {
    res.status(400).json({ error: "sha256 must be 64 lowercase hex chars" });
    return;
  }
  // Demo seed: a couple of well-known hashes flagged as warn so the UI
  // can be visually exercised without a live feed.
  const seed: Record<string, { reputation: string; detections: number }> = {
    // EICAR test signature SHA-256 — trips every AV by design
    "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f": {
      reputation: "malicious",
      detections: 67,
    },
  };
  const hit = seed[sha];
  if (hit) {
    res.json({
      sha256: sha,
      reputation: hit.reputation,
      detections: hit.detections,
      engines: 70,
      source: "nyxus-builtin",
      checked_at: new Date().toISOString(),
    });
    return;
  }
  res.json({
    sha256: sha,
    reputation: "unknown",
    detections: 0,
    engines: 0,
    source: "nyxus-builtin",
    checked_at: new Date().toISOString(),
  });
});

// ── CVE summary for a product (placeholder feed) ────────────────────────
router.get("/security/threat-intel/cve", (req, res) => {
  if (!rateLimit(req, res)) return;
  const product = String(req.query.product || "").toLowerCase().slice(0, 64);
  if (!/^[a-z0-9._-]{1,64}$/.test(product)) {
    res.status(400).json({ error: "product required (a-z0-9._-, ≤64 chars)" });
    return;
  }
  res.json({
    product,
    cves: [],
    note: "Live CVE feed not yet wired; UI will populate when /security/threat-intel is backed by a real source.",
    checked_at: new Date().toISOString(),
  });
});

// ── Liveness probe ──────────────────────────────────────────────────────
router.get("/security/status", (_req, res) => {
  res.json({
    service: "nyxus-security",
    version: 1,
    endpoints: ["hash-reputation/:sha256", "threat-intel/cve"],
  });
});

export default router;

import express, {
  Router,
  type IRouter,
  type Request,
  type Response,
} from "express";
import { createHash } from "node:crypto";
import { eq } from "drizzle-orm";
import { db } from "../lib/db";
import { nyxusAccountBlobs } from "@workspace/db/schema";

const router: IRouter = Router();

const MAX_BLOB_BYTES = 4 * 1024 * 1024; // 4 MiB cap — bundles are tiny
const TOKEN_RE = /^[A-Za-z0-9_\-]{8,128}$/;

function extractToken(req: Request): string | null {
  const auth = req.header("authorization") || "";
  const m = auth.match(/^Bearer\s+(\S+)$/i);
  if (!m) return null;
  const tok = m[1];
  if (!TOKEN_RE.test(tok)) return null;
  return tok;
}

// Hash tokens before persisting / looking up so the database NEVER
// stores raw bearer secrets. A DB dump leak therefore cannot be used
// to impersonate accounts. The path token must equal the bearer token
// (constant-time compare in extractToken's caller); only the hash is
// ever written or queried.
function hashToken(tok: string): string {
  return createHash("sha256").update(tok, "utf8").digest("hex");
}

// Constant-time string comparison — guards against timing attacks on
// the path-vs-bearer match. `crypto.timingSafeEqual` requires equal
// lengths; we pad/short-circuit when they differ.
function safeEq(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function denyAuth(res: Response) {
  res
    .status(401)
    .json({ error: "missing or malformed Authorization: Bearer <token>" });
}

// Body parser for binary uploads — accept ANY content-type and produce
// `req.body` as a Buffer. Belt-and-suspenders alongside the global
// body-parser bypass in app.ts so this route works even if the client
// omits Content-Type (e.g. curl --data-binary).
const rawAny = express.raw({
  type: () => true,
  limit: MAX_BLOB_BYTES,
  inflate: false,
});

// ── PUT /api/nyxus-account/profile/:token  body: tar.gz ─────────────────
router.put(
  "/nyxus-account/profile/:token",
  rawAny,
  async (req, res) => {
    const tok = extractToken(req);
    if (!tok || !safeEq(tok, req.params.token)) return denyAuth(res);
    const tokHash = hashToken(tok);

    const blob = req.body as Buffer;
    if (!Buffer.isBuffer(blob) || blob.length === 0) {
      return res.status(400).json({ error: "empty body" });
    }
    // Sanity: gzip magic 1f 8b
    if (blob[0] !== 0x1f || blob[1] !== 0x8b) {
      return res
        .status(415)
        .json({ error: "expected application/gzip body (gzip magic missing)" });
    }
    try {
      await db
        .insert(nyxusAccountBlobs)
        .values({
          token: tokHash,
          blob,
          size: blob.length,
          contentType: "application/gzip",
        })
        .onConflictDoUpdate({
          target: nyxusAccountBlobs.token,
          set: {
            blob,
            size: blob.length,
            contentType: "application/gzip",
            updatedAt: new Date(),
          },
        });
      // Log only the first 8 chars of the HASH, never the raw token.
      req.log?.info?.(
        { tokenHashPrefix: tokHash.slice(0, 8), bytes: blob.length },
        "nyxus-account: PUT bundle",
      );
      res.json({ ok: true, bytes: blob.length });
    } catch (e) {
      req.log?.error?.({ err: e }, "nyxus-account: PUT failed");
      res.status(500).json({ error: "storage failed" });
    }
  },
);

// ── GET /api/nyxus-account/profile/:token  → tar.gz body ────────────────
router.get("/nyxus-account/profile/:token", async (req, res) => {
  const tok = extractToken(req);
  if (!tok || !safeEq(tok, req.params.token)) return denyAuth(res);
  const tokHash = hashToken(tok);
  try {
    const rows = await db
      .select()
      .from(nyxusAccountBlobs)
      .where(eq(nyxusAccountBlobs.token, tokHash))
      .limit(1);
    if (rows.length === 0) {
      return res.status(404).json({ error: "no bundle for this token" });
    }
    const r = rows[0];
    res.setHeader("Content-Type", r.contentType || "application/gzip");
    res.setHeader("Content-Length", String(r.size));
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-NYXUS-Updated-At", r.updatedAt.toISOString());
    res.send(Buffer.isBuffer(r.blob) ? r.blob : Buffer.from(r.blob as Buffer));
  } catch (e) {
    req.log?.error?.({ err: e }, "nyxus-account: GET failed");
    res.status(500).json({ error: "storage failed" });
  }
});

// ── DELETE — disconnect / wipe ──────────────────────────────────────────
router.delete("/nyxus-account/profile/:token", async (req, res) => {
  const tok = extractToken(req);
  if (!tok || !safeEq(tok, req.params.token)) return denyAuth(res);
  const tokHash = hashToken(tok);
  try {
    await db
      .delete(nyxusAccountBlobs)
      .where(eq(nyxusAccountBlobs.token, tokHash));
    res.json({ ok: true });
  } catch (e) {
    req.log?.error?.({ err: e }, "nyxus-account: DELETE failed");
    res.status(500).json({ error: "storage failed" });
  }
});

// ── GET status (no auth) — for Settings to ping liveness ────────────────
router.get("/nyxus-account/status", (_req, res) => {
  res.json({
    service: "nyxus-account",
    version: 1,
    max_bundle_bytes: MAX_BLOB_BYTES,
  });
});

export default router;

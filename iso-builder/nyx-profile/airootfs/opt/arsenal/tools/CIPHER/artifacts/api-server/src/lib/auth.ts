import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import type { Request, Response, NextFunction } from "express";
import { WORK_DIR, ensureWorkspace } from "./workspace-paths";

const SCRYPT_KEYLEN = 64;
const SCRYPT_PARAMS = { N: 16384, r: 8, p: 1 } as const;
const TOKEN_TTL_MS = 12 * 60 * 60 * 1000; // 12 hours

/**
 * Hash a plaintext password with scrypt. Format:
 *   scrypt$<N>$<r>$<p>$<saltHex>$<hashHex>
 * Uses only Node's built-in crypto (no native modules).
 */
export function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(16);
  const derived = crypto.scryptSync(plain, salt, SCRYPT_KEYLEN, {
    N: SCRYPT_PARAMS.N,
    r: SCRYPT_PARAMS.r,
    p: SCRYPT_PARAMS.p,
    maxmem: 256 * 1024 * 1024,
  });
  return `scrypt$${SCRYPT_PARAMS.N}$${SCRYPT_PARAMS.r}$${SCRYPT_PARAMS.p}$${salt.toString("hex")}$${derived.toString("hex")}`;
}

export function verifyPassword(plain: string, stored: string): boolean {
  try {
    const parts = stored.split("$");
    if (parts.length !== 6 || parts[0] !== "scrypt") return false;
    const N = Number(parts[1]);
    const r = Number(parts[2]);
    const p = Number(parts[3]);
    const salt = Buffer.from(parts[4], "hex");
    const expected = Buffer.from(parts[5], "hex");
    const derived = crypto.scryptSync(plain, salt, expected.length, {
      N,
      r,
      p,
      maxmem: 256 * 1024 * 1024,
    });
    return crypto.timingSafeEqual(derived, expected);
  } catch {
    return false;
  }
}

/**
 * The configured owner password hash comes from the environment only — never
 * from source. Prefer a pre-hashed value (CIPHER_PASSWORD_HASH); as a
 * convenience for local labs CIPHER_PASSWORD (plaintext) is hashed at startup.
 */
let cachedPasswordHash: string | null | undefined;
export function getConfiguredPasswordHash(): string | null {
  if (cachedPasswordHash !== undefined) return cachedPasswordHash;

  const preHashed = process.env["CIPHER_PASSWORD_HASH"]?.trim();
  if (preHashed) {
    cachedPasswordHash = preHashed;
    return cachedPasswordHash;
  }
  const plain = process.env["CIPHER_PASSWORD"];
  if (plain && plain.length > 0) {
    cachedPasswordHash = hashPassword(plain);
    return cachedPasswordHash;
  }
  cachedPasswordHash = null;
  return cachedPasswordHash;
}

export function isAuthConfigured(): boolean {
  return getConfiguredPasswordHash() !== null;
}

/**
 * HMAC signing secret. Prefer CIPHER_AUTH_SECRET; otherwise persist a random
 * secret to the app-owned working dir so tokens survive restarts without any
 * hardcoded fallback secret in the source.
 */
let cachedSecret: Buffer | null = null;
function getSecret(): Buffer {
  if (cachedSecret) return cachedSecret;
  const fromEnv = process.env["CIPHER_AUTH_SECRET"]?.trim();
  if (fromEnv) {
    cachedSecret = Buffer.from(fromEnv, "utf8");
    return cachedSecret;
  }
  ensureWorkspace();
  const secretPath = path.join(WORK_DIR, ".auth-secret");
  try {
    if (fs.existsSync(secretPath)) {
      cachedSecret = fs.readFileSync(secretPath);
      if (cachedSecret.length >= 32) return cachedSecret;
    }
  } catch {
    /* fall through to regenerate */
  }
  const generated = crypto.randomBytes(48);
  fs.writeFileSync(secretPath, generated, { mode: 0o600 });
  cachedSecret = generated;
  return cachedSecret;
}

function b64url(buf: Buffer): string {
  return buf.toString("base64url");
}

export function signToken(subject = "owner"): string {
  const payload = { sub: subject, exp: Date.now() + TOKEN_TTL_MS };
  const body = b64url(Buffer.from(JSON.stringify(payload), "utf8"));
  const sig = b64url(crypto.createHmac("sha256", getSecret()).update(body).digest());
  return `${body}.${sig}`;
}

export function verifyToken(token: string | undefined | null): { sub: string; exp: number } | null {
  if (!token) return null;
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const [body, sig] = parts;
  const expected = b64url(crypto.createHmac("sha256", getSecret()).update(body).digest());
  const sigBuf = Buffer.from(sig);
  const expBuf = Buffer.from(expected);
  if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) {
    return null;
  }
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8"));
    if (typeof payload.exp !== "number" || payload.exp < Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}

function extractToken(req: Request): string | null {
  const header = req.headers["authorization"];
  if (typeof header === "string" && header.toLowerCase().startsWith("bearer ")) {
    return header.slice(7).trim();
  }
  const cookie = (req as Request & { cookies?: Record<string, string> }).cookies?.["cipher_token"];
  return cookie ?? null;
}

/**
 * Express middleware protecting the tool-running / mutating endpoints.
 * - 503 when no owner password is configured (fail closed, with guidance).
 * - 401 when the bearer token is missing or invalid.
 */
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (!isAuthConfigured()) {
    res.status(503).json({
      error:
        "Authentication is not configured. Set CIPHER_PASSWORD (or CIPHER_PASSWORD_HASH) in the server environment before using protected features.",
    });
    return;
  }
  const payload = verifyToken(extractToken(req));
  if (!payload) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }
  next();
}

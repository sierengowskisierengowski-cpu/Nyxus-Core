import crypto from "node:crypto";
import { logger } from "./logger";

// ─── Password hashing (scrypt, Node built-in — no native deps) ────────────────
//
// We deliberately use Node's built-in `crypto.scrypt` rather than bcrypt/argon2
// so there is no native addon to compile and no extra supply-chain surface
// (the workspace enforces a strict npm minimumReleaseAge). scrypt is a memory-
// hard KDF and is a genuinely safe choice for password storage.
//
// Stored format: `scrypt$<saltHex>$<derivedKeyHex>`

const SCRYPT_KEYLEN = 64;

export function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(16);
  const derived = crypto.scryptSync(plain, salt, SCRYPT_KEYLEN);
  return `scrypt$${salt.toString("hex")}$${derived.toString("hex")}`;
}

export function verifyPassword(plain: string, stored: string): boolean {
  const parts = stored.split("$");
  if (parts.length !== 3 || parts[0] !== "scrypt") return false;
  const salt = Buffer.from(parts[1], "hex");
  const expected = Buffer.from(parts[2], "hex");
  let derived: Buffer;
  try {
    derived = crypto.scryptSync(plain, salt, expected.length);
  } catch {
    return false;
  }
  return expected.length === derived.length && crypto.timingSafeEqual(expected, derived);
}

// ─── Auth configuration (resolved once from the environment) ──────────────────
//
// Credentials come exclusively from the environment — never hardcoded:
//   FORGE_AUTH_USERNAME       login username (default "admin")
//   FORGE_AUTH_PASSWORD_HASH  a `scrypt$…` hash produced by `scripts/hash-password`
//   FORGE_AUTH_PASSWORD       plaintext password (hashed in memory at startup;
//                             convenient for local use, less ideal than the hash)
//   SESSION_SECRET            HMAC key used to sign session cookies
//   FORGE_SESSION_TTL_HOURS   session lifetime in hours (default 168 = 7 days)
//
// If no password is configured we generate a random one-time password and log
// it, so a fresh local checkout is still usable without silently shipping a
// hardcoded secret. If SESSION_SECRET is unset we generate an ephemeral one
// (sessions then reset on restart).

export interface AuthConfig {
  username: string;
  passwordHash: string;
  sessionSecret: string;
  sessionTtlMs: number;
}

let cached: AuthConfig | null = null;

export function getAuthConfig(): AuthConfig {
  if (cached) return cached;

  const username = process.env.FORGE_AUTH_USERNAME?.trim() || "admin";

  let passwordHash: string;
  if (process.env.FORGE_AUTH_PASSWORD_HASH?.trim()) {
    passwordHash = process.env.FORGE_AUTH_PASSWORD_HASH.trim();
  } else if (process.env.FORGE_AUTH_PASSWORD) {
    passwordHash = hashPassword(process.env.FORGE_AUTH_PASSWORD);
  } else {
    const generated = crypto.randomBytes(12).toString("base64url");
    passwordHash = hashPassword(generated);
    logger.warn(
      { username },
      `No FORGE_AUTH_PASSWORD / FORGE_AUTH_PASSWORD_HASH set. Generated a temporary ` +
        `password for this session — set FORGE_AUTH_PASSWORD to make it permanent.`,
    );
    // Printed to stderr (not the structured log) so it is easy to spot locally.
    process.stderr.write(
      `\n  FORGE login → username: ${username}  password: ${generated}\n\n`,
    );
  }

  let sessionSecret = process.env.SESSION_SECRET?.trim() ?? "";
  if (!sessionSecret) {
    sessionSecret = crypto.randomBytes(32).toString("hex");
    logger.warn(
      "SESSION_SECRET is not set — using an ephemeral secret. Sessions will be " +
        "invalidated on restart. Set SESSION_SECRET to persist logins.",
    );
  }

  const ttlHours = Number(process.env.FORGE_SESSION_TTL_HOURS ?? 168);
  const sessionTtlMs = (Number.isFinite(ttlHours) && ttlHours > 0 ? ttlHours : 168) * 3600_000;

  cached = { username, passwordHash, sessionSecret, sessionTtlMs };
  return cached;
}

// ─── Stateless signed session tokens ──────────────────────────────────────────
//
// token = base64url(JSON payload) + "." + base64url(HMAC-SHA256(payload))
// Stored in an httpOnly cookie. No server-side session store needed for a
// single-owner local deployment.

interface SessionPayload {
  u: string;
  iat: number;
  exp: number;
}

function sign(data: string, secret: string): string {
  return crypto.createHmac("sha256", secret).update(data).digest("base64url");
}

export function createSessionToken(username: string, cfg: AuthConfig = getAuthConfig()): string {
  const now = Date.now();
  const payload: SessionPayload = { u: username, iat: now, exp: now + cfg.sessionTtlMs };
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${encoded}.${sign(encoded, cfg.sessionSecret)}`;
}

export function verifySessionToken(
  token: string | undefined,
  cfg: AuthConfig = getAuthConfig(),
): { username: string } | null {
  if (!token) return null;
  const dot = token.indexOf(".");
  if (dot <= 0) return null;
  const encoded = token.slice(0, dot);
  const sig = token.slice(dot + 1);

  const expectedSig = sign(encoded, cfg.sessionSecret);
  const sigBuf = Buffer.from(sig);
  const expBuf = Buffer.from(expectedSig);
  if (sigBuf.length !== expBuf.length || !crypto.timingSafeEqual(sigBuf, expBuf)) {
    return null;
  }

  try {
    const payload = JSON.parse(Buffer.from(encoded, "base64url").toString()) as SessionPayload;
    if (typeof payload.exp !== "number" || Date.now() > payload.exp) return null;
    if (typeof payload.u !== "string") return null;
    return { username: payload.u };
  } catch {
    return null;
  }
}

export const SESSION_COOKIE = "forge_session";

export function verifyCredentials(username: string, password: string): boolean {
  const cfg = getAuthConfig();
  // Compare username in constant-ish time then verify password hash.
  const userBuf = Buffer.from(username);
  const expUserBuf = Buffer.from(cfg.username);
  const userOk =
    userBuf.length === expUserBuf.length && crypto.timingSafeEqual(userBuf, expUserBuf);
  const passOk = verifyPassword(password, cfg.passwordHash);
  return userOk && passOk;
}

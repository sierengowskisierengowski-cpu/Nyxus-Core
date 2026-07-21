import crypto from "node:crypto";

// Password hashing uses scrypt from Node's built-in crypto module. scrypt is a
// memory-hard KDF (no native addon required, unlike argon2/bcrypt) which keeps
// the esbuild bundle portable while still being a real, salted, slow hash.
const SCRYPT_N = 16384; // CPU/memory cost
const SCRYPT_R = 8; // block size
const SCRYPT_P = 1; // parallelisation
const KEY_LEN = 64;

/** Hashes a plaintext password, returning a self-describing encoded string. */
export function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16);
  const derived = crypto.scryptSync(password, salt, KEY_LEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
  });
  return [
    "scrypt",
    SCRYPT_N,
    SCRYPT_R,
    SCRYPT_P,
    salt.toString("hex"),
    derived.toString("hex"),
  ].join("$");
}

/**
 * Verifies a plaintext password against a stored hash. Supports the current
 * scrypt format and the legacy static-salt SHA-256 format (so any pre-existing
 * users created before this change can still log in).
 */
export function verifyPassword(password: string, stored: string): boolean {
  const parts = stored.split("$");

  if (parts[0] === "scrypt" && parts.length === 6) {
    const [, n, r, p, saltHex, hashHex] = parts;
    const salt = Buffer.from(saltHex, "hex");
    const expected = Buffer.from(hashHex, "hex");
    const derived = crypto.scryptSync(password, salt, expected.length, {
      N: Number(n),
      r: Number(r),
      p: Number(p),
    });
    return (
      derived.length === expected.length &&
      crypto.timingSafeEqual(derived, expected)
    );
  }

  // Legacy fallback: SHA-256(password + static salt).
  const legacy = crypto
    .createHash("sha256")
    .update(password + "redforge-salt")
    .digest("hex");
  const a = Buffer.from(legacy);
  const b = Buffer.from(stored);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

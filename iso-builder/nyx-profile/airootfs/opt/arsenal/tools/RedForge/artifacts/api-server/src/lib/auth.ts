import argon2 from "argon2";
import speakeasy from "speakeasy";
import { randomBytes } from "crypto";

const ARGON_OPTS = {
  type: argon2.argon2id,
  memoryCost: 65536,
  timeCost: 3,
  parallelism: 4,
} as const;

export async function hashPassword(password: string): Promise<string> {
  return argon2.hash(password, ARGON_OPTS);
}

export async function verifyPassword(hash: string, password: string): Promise<boolean> {
  try {
    return await argon2.verify(hash, password);
  } catch {
    return false;
  }
}

export function generateTotpSecret(label: string): { secret: string; otpauthUrl: string } {
  const s = speakeasy.generateSecret({ length: 20, name: `REDFORGE (${label})`, issuer: "GowskiNet REDFORGE" });
  return { secret: s.base32, otpauthUrl: s.otpauth_url ?? "" };
}

export function verifyTotp(secret: string, token: string): boolean {
  if (!/^\d{6}$/.test(token)) return false;
  return speakeasy.totp.verify({ secret, encoding: "base32", token, window: 1 });
}

export function generateRecoveryCodes(count = 8): string[] {
  return Array.from({ length: count }, () =>
    randomBytes(5).toString("hex").match(/.{1,5}/g)!.join("-")
  );
}

export function newSessionId(): string {
  return randomBytes(32).toString("base64url");
}

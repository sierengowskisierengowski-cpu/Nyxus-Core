import crypto from "node:crypto";
import readline from "node:readline";

// Produce a scrypt password hash for FORGE_AUTH_PASSWORD_HASH.
// Format matches artifacts/api-server/src/lib/auth.ts: `scrypt$<saltHex>$<keyHex>`.
//
// Usage:
//   pnpm --filter @workspace/scripts run hash-password -- 'my-password'
//   echo 'my-password' | pnpm --filter @workspace/scripts run hash-password

const SCRYPT_KEYLEN = 64;

function hashPassword(plain: string): string {
  const salt = crypto.randomBytes(16);
  const derived = crypto.scryptSync(plain, salt, SCRYPT_KEYLEN);
  return `scrypt$${salt.toString("hex")}$${derived.toString("hex")}`;
}

async function readPassword(): Promise<string> {
  const arg = process.argv[2];
  if (arg && arg.trim()) return arg;

  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin });
    let line = "";
    rl.on("line", (l) => {
      line = l;
      rl.close();
    });
    rl.on("close", () => resolve(line));
  });
}

const password = (await readPassword()).trim();
if (!password) {
  console.error("No password provided. Pass it as an argument or via stdin.");
  process.exit(1);
}

process.stdout.write(hashPassword(password) + "\n");

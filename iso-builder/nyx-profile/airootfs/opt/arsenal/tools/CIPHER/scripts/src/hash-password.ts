import crypto from "node:crypto";

/**
 * Print a scrypt password hash compatible with the API server's auth verifier.
 * Format: scrypt$<N>$<r>$<p>$<saltHex>$<hashHex>
 *
 * Usage: pnpm --filter @workspace/scripts run hash-password 'your-password'
 */
const password = process.argv[2];
if (!password) {
  console.error("Usage: pnpm --filter @workspace/scripts run hash-password '<password>'");
  process.exit(1);
}

const N = 16384;
const r = 8;
const p = 1;
const salt = crypto.randomBytes(16);
const derived = crypto.scryptSync(password, salt, 64, { N, r, p, maxmem: 256 * 1024 * 1024 });
const hash = `scrypt$${N}$${r}$${p}$${salt.toString("hex")}$${derived.toString("hex")}`;

console.log(hash);
console.log("\nSet it in the server environment as:");
console.log(`CIPHER_PASSWORD_HASH='${hash}'`);

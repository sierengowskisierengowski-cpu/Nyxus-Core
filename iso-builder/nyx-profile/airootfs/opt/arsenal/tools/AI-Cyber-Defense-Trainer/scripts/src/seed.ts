#!/usr/bin/env tsx
/**
 * Database seed: creates the initial admin operator so the app is usable on a
 * fresh database. The password is taken from the environment and stored only as
 * a salted scrypt hash — NO plaintext or default secret is committed anywhere.
 *
 * Run order on a fresh DB:
 *   pnpm --filter @workspace/db run push        # create tables
 *   SEED_ADMIN_PASSWORD=... pnpm --filter @workspace/scripts run seed
 *
 * Env:
 *   SEED_ADMIN_USERNAME  admin username        (default "admin")
 *   SEED_ADMIN_PASSWORD  admin password        (REQUIRED, min 8 chars)
 *   SEED_FORCE=1         reset password if the user already exists
 */
import { db, usersTable, hashPassword, closeDb } from "@workspace/db";
import { eq } from "drizzle-orm";

async function main(): Promise<void> {
  const username = process.env.SEED_ADMIN_USERNAME ?? "admin";
  const password = process.env.SEED_ADMIN_PASSWORD;

  if (!password) {
    console.error(
      "SEED_ADMIN_PASSWORD is required. No default password is committed.\n" +
        "Example: SEED_ADMIN_PASSWORD='choose-a-strong-pass' pnpm --filter @workspace/scripts run seed",
    );
    process.exit(1);
  }
  if (password.length < 8) {
    console.error("SEED_ADMIN_PASSWORD must be at least 8 characters.");
    process.exit(1);
  }

  const [existing] = await db
    .select()
    .from(usersTable)
    .where(eq(usersTable.username, username));

  if (existing) {
    if (process.env.SEED_FORCE === "1") {
      await db
        .update(usersTable)
        .set({ passwordHash: hashPassword(password) })
        .where(eq(usersTable.username, username));
      console.log(`Reset password for existing operator '${username}'.`);
    } else {
      console.log(
        `Operator '${username}' already exists — skipping. Set SEED_FORCE=1 to reset the password.`,
      );
    }
  } else {
    await db.insert(usersTable).values({
      username,
      passwordHash: hashPassword(password),
    });
    console.log(`Created admin operator '${username}'. You can now log in.`);
  }

  await closeDb();
}

main().catch(async (err) => {
  console.error(err instanceof Error ? err.message : err);
  await closeDb().catch(() => {});
  process.exit(1);
});

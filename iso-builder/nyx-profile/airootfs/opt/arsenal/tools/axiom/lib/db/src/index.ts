import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import Database from "better-sqlite3";
import * as schema from "./schema";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const dbPath = process.env.AXIOM_DB_PATH || path.join(process.cwd(), "axiom.db");

const dbDir = path.dirname(dbPath);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

const sqlite = new Database(dbPath);

sqlite.pragma("journal_mode = WAL");
sqlite.pragma("foreign_keys = ON");

export const db = drizzle(sqlite, { schema });

// Resolve the migrations folder relative to this file, so it works regardless
// of the process working directory (Electron production, dev server, etc.)
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const migrationsFolder = path.join(__dirname, "..", "drizzle");

/**
 * Apply all pending SQLite migrations. Safe to call on every startup — it is
 * a no-op when the DB is already up-to-date.
 */
export function runMigrations(): void {
  migrate(db, { migrationsFolder });
}

export * from "./schema";

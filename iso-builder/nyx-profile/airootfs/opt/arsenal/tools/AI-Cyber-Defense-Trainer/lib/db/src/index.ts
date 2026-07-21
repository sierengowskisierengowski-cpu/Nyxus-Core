import { drizzle, type NodePgDatabase } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "./schema";

const { Pool } = pg;

// The database connection is initialised lazily on first use rather than at
// import time. This lets non-DB code paths (health check, the WebSocket log
// server, smoke tests) import this package without requiring DATABASE_URL to
// be set, while still failing loudly the moment a query is actually run.
let _pool: pg.Pool | null = null;
let _db: NodePgDatabase<typeof schema> | null = null;

function ensureDb(): NodePgDatabase<typeof schema> {
  if (_db) return _db;
  if (!process.env.DATABASE_URL) {
    throw new Error(
      "DATABASE_URL must be set. Did you forget to provision a database?",
    );
  }
  _pool = new Pool({ connectionString: process.env.DATABASE_URL });
  _db = drizzle(_pool, { schema });
  return _db;
}

/** Returns the underlying pg Pool, initialising the connection if needed. */
export function getPool(): pg.Pool {
  ensureDb();
  return _pool as pg.Pool;
}

/** Closes the pool (used by seed/scan scripts so the process can exit). */
export async function closeDb(): Promise<void> {
  if (_pool) {
    await _pool.end();
    _pool = null;
    _db = null;
  }
}

export const db: NodePgDatabase<typeof schema> = new Proxy(
  {} as NodePgDatabase<typeof schema>,
  {
    get(_target, prop, receiver) {
      const real = ensureDb();
      const value = Reflect.get(real as object, prop, receiver);
      return typeof value === "function" ? value.bind(real) : value;
    },
  },
);

export * from "./schema";
export * from "./password";

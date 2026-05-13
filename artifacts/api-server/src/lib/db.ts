import { drizzle } from "drizzle-orm/node-postgres";
import pg from "pg";
import * as schema from "@workspace/db/schema";
import { logger } from "./logger";

const url = process.env.DATABASE_URL;
if (!url) {
  logger.warn(
    "DATABASE_URL is unset — features that require persistence (NYXUS Account sync) will return 500 until it is provided.",
  );
}

export const pool = new pg.Pool({
  connectionString: url,
  // Keep the pool light — this app is small.
  max: 5,
  idleTimeoutMillis: 30_000,
});

pool.on("error", (err) => {
  logger.error({ err }, "pg pool error");
});

export const db = drizzle(pool, { schema });

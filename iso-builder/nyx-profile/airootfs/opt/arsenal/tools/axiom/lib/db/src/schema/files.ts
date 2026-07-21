import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { sql } from "drizzle-orm";

export const allowedPathsTable = sqliteTable("allowed_paths", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  path: text("path").notNull().unique(),
  label: text("label"),
  createdAt: text("created_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
});

export const insertAllowedPathSchema = createInsertSchema(allowedPathsTable).omit({ id: true, createdAt: true });

export type AllowedPath = typeof allowedPathsTable.$inferSelect;
export type InsertAllowedPath = z.infer<typeof insertAllowedPathSchema>;

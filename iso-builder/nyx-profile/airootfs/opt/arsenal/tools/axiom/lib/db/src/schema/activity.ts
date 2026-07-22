import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { sql } from "drizzle-orm";

export const activityLogTable = sqliteTable("activity_log", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  type: text("type").notNull().$type<"chat" | "file_op" | "scheduled">(),
  description: text("description").notNull(),
  detail: text("detail"),
  filesAffected: text("files_affected").notNull().default("[]"),
  undoable: integer("undoable", { mode: "boolean" }).notNull().default(false),
  undone: integer("undone", { mode: "boolean" }).notNull().default(false),
  undoData: text("undo_data"),
  createdAt: text("created_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
});

export const insertActivitySchema = createInsertSchema(activityLogTable).omit({ id: true, createdAt: true, undone: true });

export type ActivityEntry = typeof activityLogTable.$inferSelect;
export type InsertActivity = z.infer<typeof insertActivitySchema>;

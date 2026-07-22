import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { sql } from "drizzle-orm";

export const quickActionsTable = sqliteTable("quick_actions", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  label: text("label").notNull(),
  command: text("command").notNull(),
  icon: text("icon"),
  color: text("color"),
  order: integer("order").notNull().default(0),
  createdAt: text("created_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
});

export const insertQuickActionSchema = createInsertSchema(quickActionsTable).omit({ id: true, createdAt: true });
export const updateQuickActionSchema = insertQuickActionSchema.partial();

export type QuickAction = typeof quickActionsTable.$inferSelect;
export type InsertQuickAction = z.infer<typeof insertQuickActionSchema>;
export type UpdateQuickAction = z.infer<typeof updateQuickActionSchema>;

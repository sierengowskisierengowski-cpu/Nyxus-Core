import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { sql } from "drizzle-orm";

export const scheduledTasksTable = sqliteTable("scheduled_tasks", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  command: text("command").notNull(),
  schedule: text("schedule").notNull(),
  scheduleLabel: text("schedule_label"),
  enabled: integer("enabled", { mode: "boolean" }).notNull().default(true),
  lastRunAt: text("last_run_at"),
  lastRunStatus: text("last_run_status"),
  nextRunAt: text("next_run_at"),
  createdAt: text("created_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
});

export const insertScheduledTaskSchema = createInsertSchema(scheduledTasksTable).omit({ id: true, createdAt: true, lastRunAt: true, lastRunStatus: true, nextRunAt: true });
export const updateScheduledTaskSchema = insertScheduledTaskSchema.partial();

export type ScheduledTask = typeof scheduledTasksTable.$inferSelect;
export type InsertScheduledTask = z.infer<typeof insertScheduledTaskSchema>;
export type UpdateScheduledTask = z.infer<typeof updateScheduledTaskSchema>;

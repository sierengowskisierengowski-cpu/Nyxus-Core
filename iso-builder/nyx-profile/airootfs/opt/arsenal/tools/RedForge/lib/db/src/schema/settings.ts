import { pgTable, integer, text, boolean } from "drizzle-orm/pg-core";

export const settings = pgTable("settings", {
  id: integer("id").primaryKey().default(1),
  targetSubnet: text("target_subnet").notNull().default("192.168.56.0/24"),
  excludedDevices: text("excluded_devices").array().notNull().default([]),
  defaultDifficulty: text("default_difficulty").notNull().default("intermediate"),
  defaultTimerMinutes: integer("default_timer_minutes").notNull().default(30),
  claudeModel: text("claude_model").notNull().default("claude-sonnet-4-5"),
  ntfyUrl: text("ntfy_url").notNull().default(""),
  notifyOnStart: boolean("notify_on_start").notNull().default(false),
  notifyOnTimer: boolean("notify_on_timer").notNull().default(false),
});

export type Settings = typeof settings.$inferSelect;

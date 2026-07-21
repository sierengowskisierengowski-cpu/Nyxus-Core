import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const settingsTable = sqliteTable("settings", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  hotkey: text("hotkey").notNull().default("CommandOrControl+Shift+Space"),
  aiMode: text("ai_mode").notNull().default("cloud").$type<"local" | "cloud">(),
  aiModel: text("ai_model").notNull().default("gpt-4o-mini"),
  cloudApiKey: text("cloud_api_key"),
  cloudBaseUrl: text("cloud_base_url"),
  ollamaBaseUrl: text("ollama_base_url").notNull().default("http://localhost:11434"),
  theme: text("theme").notNull().default("dark").$type<"light" | "dark" | "system">(),
  launchAtLogin: integer("launch_at_login", { mode: "boolean" }).notNull().default(false),
  startMinimized: integer("start_minimized", { mode: "boolean" }).notNull().default(false),
  dismissOnBlur: integer("dismiss_on_blur", { mode: "boolean" }).notNull().default(true),
  notifyOnSchedule: integer("notify_on_schedule", { mode: "boolean" }).notNull().default(true),
  notifyOnError: integer("notify_on_error", { mode: "boolean" }).notNull().default(true),
  windowWidth: integer("window_width").notNull().default(780),
  windowHeight: integer("window_height").notNull().default(640),
  onboardingCompleted: integer("onboarding_completed", { mode: "boolean" }).notNull().default(false),
});

export const insertSettingsSchema = createInsertSchema(settingsTable).omit({ id: true });
export const updateSettingsSchema = insertSettingsSchema.partial();

export type Settings = typeof settingsTable.$inferSelect;
export type InsertSettings = z.infer<typeof insertSettingsSchema>;
export type UpdateSettings = z.infer<typeof updateSettingsSchema>;

import { pgTable, text, serial, timestamp, boolean, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const settingsTable = pgTable("settings", {
  id: serial("id").primaryKey(),
  claudeModel: text("claude_model").notNull().default("claude-sonnet-4-20250514"),
  hashcatPath: text("hashcat_path").notNull().default("/usr/bin/hashcat"),
  johnPath: text("john_path").notNull().default("/usr/bin/john"),
  gpuEnabled: boolean("gpu_enabled").notNull().default(true),
  gpuDevice: integer("gpu_device").notNull().default(0),
  gpuMemoryLimit: integer("gpu_memory_limit"),
  gpuTempLimit: integer("gpu_temp_limit").notNull().default(85),
  cpuThreads: integer("cpu_threads").notNull().default(4),
  defaultAttackMode: text("default_attack_mode").notNull().default("dictionary"),
  meliEndpoint: text("meli_endpoint"),
  ntfyTopic: text("ntfy_topic"),
  notificationsEnabled: boolean("notifications_enabled").notNull().default(false),
  dataRetentionDays: integer("data_retention_days").notNull().default(90),
  disclaimerAccepted: boolean("disclaimer_accepted").notNull().default(false),
  disclaimerAcceptedAt: timestamp("disclaimer_accepted_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow().$onUpdate(() => new Date()),
});

export const insertSettingsSchema = createInsertSchema(settingsTable).omit({ id: true, createdAt: true, updatedAt: true });
export type InsertSettings = z.infer<typeof insertSettingsSchema>;
export type Settings = typeof settingsTable.$inferSelect;

import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

// ─── Threat Inputs ────────────────────────────────────────────────────────────
export const threatInputsTable = pgTable("threat_inputs", {
  id: serial("id").primaryKey(),
  inputType: text("input_type").notNull(),
  content: text("content").notNull(),
  sourceUrl: text("source_url"),
  language: text("language"),
  label: text("label"),
  analyzed: boolean("analyzed").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertThreatInputSchema = createInsertSchema(threatInputsTable).omit({ id: true, createdAt: true });
export type InsertThreatInput = z.infer<typeof insertThreatInputSchema>;
export type ThreatInput = typeof threatInputsTable.$inferSelect;

// ─── Generated Threats ────────────────────────────────────────────────────────
export const threatsTable = pgTable("threats", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  noveltyScore: integer("novelty_score").notNull(),
  estimatedDetectionRate: integer("estimated_detection_rate").notNull(),
  platform: text("platform").notNull(),
  category: text("category"),
  description: text("description"),
  code: text("code").notNull(),
  technicalBreakdown: text("technical_breakdown").notNull(),
  mitreIds: jsonb("mitre_ids").$type<string[]>().default([]).notNull(),
  realWorldFeasibility: text("real_world_feasibility").notNull(),
  sigmaRule: text("sigma_rule"),
  snortRule: text("snort_rule"),
  yaraRule: text("yara_rule"),
  behavioralIndicators: jsonb("behavioral_indicators").$type<string[]>().default([]).notNull(),
  networkIndicators: jsonb("network_indicators").$type<string[]>().default([]).notNull(),
  defensiveRecommendations: text("defensive_recommendations").notNull(),
  hardeningConfig: text("hardening_config").notNull(),
  testPlan: text("test_plan").notNull(),
  mutationEnginesUsed: jsonb("mutation_engines_used").$type<string[]>().default([]).notNull(),
  parentInputIds: jsonb("parent_input_ids").$type<number[]>().default([]).notNull(),
  userNotes: text("user_notes"),
  mastered: boolean("mastered").default(false).notNull(),
  sentToRedforge: boolean("sent_to_redforge").default(false).notNull(),
  sentToRedforgeAt: timestamp("sent_to_redforge_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertThreatSchema = createInsertSchema(threatsTable).omit({ id: true, createdAt: true });
export type InsertThreat = z.infer<typeof insertThreatSchema>;
export type Threat = typeof threatsTable.$inferSelect;

// ─── Detection Rules ──────────────────────────────────────────────────────────
export const detectionRulesTable = pgTable("detection_rules", {
  id: serial("id").primaryKey(),
  ruleType: text("rule_type").notNull(),
  name: text("name").notNull(),
  content: text("content").notNull(),
  threatId: integer("threat_id"),
  mitreIds: jsonb("mitre_ids").$type<string[]>().default([]).notNull(),
  tested: boolean("tested").default(false).notNull(),
  effective: boolean("effective"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertDetectionRuleSchema = createInsertSchema(detectionRulesTable).omit({ id: true, createdAt: true });
export type InsertDetectionRule = z.infer<typeof insertDetectionRuleSchema>;
export type DetectionRule = typeof detectionRulesTable.$inferSelect;

// ─── Research Notes ───────────────────────────────────────────────────────────
export const notesTable = pgTable("notes", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  content: text("content").default("").notNull(),
  noteType: text("note_type").notNull(),
  notebook: text("notebook").notNull(),
  tags: jsonb("tags").$type<string[]>().default([]).notNull(),
  threatId: integer("threat_id"),
  pinned: boolean("pinned").default(false).notNull(),
  starred: boolean("starred").default(false).notNull(),
  archived: boolean("archived").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertNoteSchema = createInsertSchema(notesTable).omit({ id: true, createdAt: true, updatedAt: true });
export type InsertNote = z.infer<typeof insertNoteSchema>;
export type Note = typeof notesTable.$inferSelect;

// ─── Knowledge Base ───────────────────────────────────────────────────────────
export const knowledgeEntriesTable = pgTable("knowledge_entries", {
  id: serial("id").primaryKey(),
  category: text("category").notNull(),
  title: text("title").notNull(),
  content: text("content").notNull(),
  source: text("source").notNull(),
  tags: jsonb("tags").$type<string[]>().default([]).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertKnowledgeEntrySchema = createInsertSchema(knowledgeEntriesTable).omit({ id: true, createdAt: true });
export type InsertKnowledgeEntry = z.infer<typeof insertKnowledgeEntrySchema>;
export type KnowledgeEntry = typeof knowledgeEntriesTable.$inferSelect;

// ─── REDFORGE History ────────────────────────────────────────────────────────
export const redforgeHistoryTable = pgTable("redforge_history", {
  id: serial("id").primaryKey(),
  threatId: integer("threat_id").notNull(),
  threatName: text("threat_name").notNull(),
  sentAt: timestamp("sent_at", { withTimezone: true }).defaultNow().notNull(),
  missionId: text("mission_id"),
  outcome: text("outcome"),
  score: integer("score"),
});

export const insertRedforgeHistorySchema = createInsertSchema(redforgeHistoryTable).omit({ id: true, sentAt: true });
export type InsertRedforgeHistory = z.infer<typeof insertRedforgeHistorySchema>;
export type RedforgeHistory = typeof redforgeHistoryTable.$inferSelect;

// ─── Meli Commands ────────────────────────────────────────────────────────────
export const meliCommandsTable = pgTable("meli_commands", {
  id: serial("id").primaryKey(),
  command: text("command").notNull(),
  sourceIp: text("source_ip").notNull(),
  session: text("session").default("").notNull(),
  capturedAt: timestamp("captured_at", { withTimezone: true }).defaultNow().notNull(),
  analyzed: boolean("analyzed").default(false).notNull(),
  importedAsInputId: integer("imported_as_input_id"),
});

export const insertMeliCommandSchema = createInsertSchema(meliCommandsTable).omit({ id: true, capturedAt: true });
export type InsertMeliCommand = z.infer<typeof insertMeliCommandSchema>;
export type MeliCommand = typeof meliCommandsTable.$inferSelect;

// ─── App Settings ─────────────────────────────────────────────────────────────
export const settingsTable = pgTable("settings", {
  id: serial("id").primaryKey(),
  claudeModel: text("claude_model").default("forge-sec").notNull(),
  defaultNoveltyTarget: integer("default_novelty_target").default(7).notNull(),
  defaultComplexity: text("default_complexity").default("moderate").notNull(),
  defaultPlatform: text("default_platform").default("linux").notNull(),
  defaultEvasionPriority: integer("default_evasion_priority").default(3).notNull(),
  redforgeUrl: text("redforge_url"),
  meliUrl: text("meli_url"),
  sandboxEnabled: boolean("sandbox_enabled").default(true).notNull(),
  maxCpuPercent: integer("max_cpu_percent").default(25).notNull(),
  maxRamMb: integer("max_ram_mb").default(512).notNull(),
  maxExecutionSeconds: integer("max_execution_seconds").default(60).notNull(),
  disclaimerAccepted: boolean("disclaimer_accepted").default(false).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const insertSettingsSchema = createInsertSchema(settingsTable).omit({ id: true, createdAt: true });
export type InsertSettings = z.infer<typeof insertSettingsSchema>;
export type Settings = typeof settingsTable.$inferSelect;

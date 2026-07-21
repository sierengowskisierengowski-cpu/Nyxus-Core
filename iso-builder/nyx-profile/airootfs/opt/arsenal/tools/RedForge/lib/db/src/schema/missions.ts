import { pgTable, serial, text, timestamp, integer, boolean, jsonb } from "drizzle-orm/pg-core";

export const missions = pgTable("missions", {
  id: serial("id").primaryKey(),
  scenarioId: text("scenario_id").notNull(),
  scenarioName: text("scenario_name").notNull(),
  category: text("category").notNull(),
  difficulty: text("difficulty").notNull(),
  status: text("status").notNull().default("active"),
  mode: text("mode").notNull().default("blind"),
  notes: text("notes").notNull().default(""),
  hypothesis: text("hypothesis").notNull().default(""),
  evidence: text("evidence").notNull().default(""),
  hintsUsed: integer("hints_used").notNull().default(0),
  score: integer("score"),
  identifiedTechnique: text("identified_technique"),
  identifiedCategory: text("identified_category"),
  confidence: integer("confidence"),
  performance: jsonb("performance"),
  mastered: boolean("mastered").notNull().default(false),
  timeLimitMinutes: integer("time_limit_minutes"),
  startedAt: timestamp("started_at", { withTimezone: true }).defaultNow().notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

export type Mission = typeof missions.$inferSelect;

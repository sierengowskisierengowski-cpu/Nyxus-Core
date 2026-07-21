import { pgTable, text, serial, timestamp, boolean, integer, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const rulesTable = pgTable("rule_sets", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  rules: text("rules").notNull().default(""),
  ruleCount: integer("rule_count").notNull().default(0),
  format: text("format").notNull().default("hashcat"),
  isBuiltin: boolean("is_builtin").notNull().default(false),
  successRate: real("success_rate"),
  cracksProduced: integer("cracks_produced").notNull().default(0),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertRuleSchema = createInsertSchema(rulesTable).omit({ id: true, createdAt: true });
export type InsertRule = z.infer<typeof insertRuleSchema>;
export type RuleSet = typeof rulesTable.$inferSelect;

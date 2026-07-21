import { pgTable, text, serial, timestamp, boolean, integer, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const jobsTable = pgTable("crack_jobs", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  status: text("status").notNull().default("queued"),
  attackMode: text("attack_mode").notNull(),
  engine: text("engine").notNull().default("hashcat"),
  hashIds: text("hash_ids").notNull().default("[]"),
  hashType: text("hash_type"),
  wordlistIds: text("wordlist_ids").notNull().default("[]"),
  ruleIds: text("rule_ids").notNull().default("[]"),
  mask: text("mask"),
  progress: real("progress").notNull().default(0),
  speed: real("speed"),
  speedUnit: text("speed_unit").notNull().default("H/s"),
  cracksFound: integer("cracks_found").notNull().default(0),
  totalCandidates: integer("total_candidates"),
  candidatesTried: integer("candidates_tried"),
  estimatedTimeSeconds: integer("estimated_time_seconds"),
  timeElapsedSeconds: integer("time_elapsed_seconds").notNull().default(0),
  useGpu: boolean("use_gpu").notNull().default(true),
  aiTargetContext: text("ai_target_context"),
  bruteForceCharset: text("brute_force_charset"),
  bruteForceLengthMin: integer("brute_force_length_min"),
  bruteForceLengthMax: integer("brute_force_length_max"),
  patternTemplate: text("pattern_template"),
  fingerprint: text("fingerprint"),
  errorMessage: text("error_message"),
  logPath: text("log_path"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  startedAt: timestamp("started_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
});

export const insertJobSchema = createInsertSchema(jobsTable).omit({ id: true, createdAt: true });
export type InsertJob = z.infer<typeof insertJobSchema>;
export type Job = typeof jobsTable.$inferSelect;

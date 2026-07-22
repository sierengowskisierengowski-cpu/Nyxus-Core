import { pgTable, text, serial, timestamp, integer, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const resultsTable = pgTable("crack_results", {
  id: serial("id").primaryKey(),
  hashId: integer("hash_id").notNull(),
  jobId: integer("job_id"),
  hash: text("hash").notNull(),
  plaintext: text("plaintext").notNull(),
  hashType: text("hash_type").notNull(),
  attackMode: text("attack_mode").notNull(),
  crackTimeSeconds: real("crack_time_seconds"),
  wordlistUsed: text("wordlist_used"),
  entropyScore: real("entropy_score"),
  patternIdentified: text("pattern_identified"),
  crackedAt: timestamp("cracked_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertResultSchema = createInsertSchema(resultsTable).omit({ id: true, crackedAt: true });
export type InsertResult = z.infer<typeof insertResultSchema>;
export type Result = typeof resultsTable.$inferSelect;

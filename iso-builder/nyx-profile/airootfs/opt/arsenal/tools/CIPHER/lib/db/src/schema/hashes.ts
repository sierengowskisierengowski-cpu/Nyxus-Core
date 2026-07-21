import { pgTable, text, serial, timestamp, boolean, integer } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const hashesTable = pgTable("hashes", {
  id: serial("id").primaryKey(),
  value: text("value").notNull(),
  hashType: text("hash_type").notNull().default("unknown"),
  status: text("status").notNull().default("pending"),
  plaintext: text("plaintext"),
  label: text("label"),
  source: text("source"),
  difficulty: text("difficulty"),
  salted: boolean("salted").notNull().default(false),
  submittedAt: timestamp("submitted_at", { withTimezone: true }).notNull().defaultNow(),
  crackedAt: timestamp("cracked_at", { withTimezone: true }),
});

export const insertHashSchema = createInsertSchema(hashesTable).omit({ id: true, submittedAt: true });
export type InsertHash = z.infer<typeof insertHashSchema>;
export type Hash = typeof hashesTable.$inferSelect;

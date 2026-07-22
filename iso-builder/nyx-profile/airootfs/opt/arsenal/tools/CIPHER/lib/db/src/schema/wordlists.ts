import { pgTable, text, serial, timestamp, boolean, integer, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const wordlistsTable = pgTable("wordlists", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description"),
  wordCount: integer("word_count").notNull().default(0),
  sizeBytes: integer("size_bytes").notNull().default(0),
  source: text("source").notNull().default("custom"),
  isBuiltin: boolean("is_builtin").notNull().default(false),
  tags: text("tags").notNull().default("[]"),
  filePath: text("file_path"),
  words: text("words"),
  lastUsed: timestamp("last_used", { withTimezone: true }),
  successRate: real("success_rate"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertWordlistSchema = createInsertSchema(wordlistsTable).omit({ id: true, createdAt: true });
export type InsertWordlist = z.infer<typeof insertWordlistSchema>;
export type Wordlist = typeof wordlistsTable.$inferSelect;

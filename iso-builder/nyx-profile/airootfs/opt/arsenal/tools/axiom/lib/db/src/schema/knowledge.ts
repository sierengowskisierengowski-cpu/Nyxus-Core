import { sqliteTable, integer, text } from "drizzle-orm/sqlite-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";
import { sql } from "drizzle-orm";

export const knowledgeNotesTable = sqliteTable("knowledge_notes", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  content: text("content").notNull().default(""),
  pinned: integer("pinned", { mode: "boolean" }).notNull().default(false),
  createdAt: text("created_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
  updatedAt: text("updated_at").notNull().default(sql`(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))`),
});

export const insertKnowledgeNoteSchema = createInsertSchema(knowledgeNotesTable).omit({ id: true, createdAt: true, updatedAt: true });
export const updateKnowledgeNoteSchema = insertKnowledgeNoteSchema.partial();

export type KnowledgeNote = typeof knowledgeNotesTable.$inferSelect;
export type InsertKnowledgeNote = z.infer<typeof insertKnowledgeNoteSchema>;
export type UpdateKnowledgeNote = z.infer<typeof updateKnowledgeNoteSchema>;

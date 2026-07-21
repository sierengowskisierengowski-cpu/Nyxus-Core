import { pgTable, serial, text, timestamp } from "drizzle-orm/pg-core";

export const notebooks = pgTable("notebooks", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  description: text("description").notNull().default(""),
  color: text("color").notNull().default("#ef4444"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export type Notebook = typeof notebooks.$inferSelect;

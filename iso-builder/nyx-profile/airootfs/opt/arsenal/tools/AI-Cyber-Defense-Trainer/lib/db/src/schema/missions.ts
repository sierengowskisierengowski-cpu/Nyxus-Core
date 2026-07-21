import { pgTable, text, serial, timestamp, integer, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const missionsTable = pgTable("missions", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  description: text("description"),
  category: text("category").notNull().default("Mixed"),
  difficulty: text("difficulty").notNull().default("Unknown"),
  mode: text("mode").notNull().default("hybrid"),
  status: text("status").notNull().default("pending"),
  targetIp: text("target_ip").notNull().default("192.168.0.1"),
  revealed: boolean("revealed").notNull().default(false),
  blind: boolean("blind").notNull().default(false),
  detectionScore: integer("detection_score"),
  responseScore: integer("response_score"),
  generatedCode: text("generated_code"),
  mitreIds: text("mitre_ids"),
  primitives: text("primitives"),
  startedAt: timestamp("started_at", { withTimezone: true }),
  completedAt: timestamp("completed_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertMissionSchema = createInsertSchema(missionsTable).omit({
  id: true,
  createdAt: true,
});
export type InsertMission = z.infer<typeof insertMissionSchema>;
export type Mission = typeof missionsTable.$inferSelect;

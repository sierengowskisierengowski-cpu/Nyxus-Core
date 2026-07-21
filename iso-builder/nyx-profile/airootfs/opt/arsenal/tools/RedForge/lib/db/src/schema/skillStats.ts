import { pgTable, serial, text, integer, timestamp } from "drizzle-orm/pg-core";

export const skillStats = pgTable("skill_stats", {
  id: serial("id").primaryKey(),
  category: text("category").notNull().unique(),
  totalScore: integer("total_score").notNull().default(0),
  missionCount: integer("mission_count").notNull().default(0),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const achievements = pgTable("achievements", {
  id: serial("id").primaryKey(),
  achievementId: text("achievement_id").notNull().unique(),
  unlockedAt: timestamp("unlocked_at", { withTimezone: true }).defaultNow().notNull(),
});

export type SkillStat = typeof skillStats.$inferSelect;
export type Achievement = typeof achievements.$inferSelect;

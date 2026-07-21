import { pgTable, serial, text, timestamp, integer } from "drizzle-orm/pg-core";

export const disclaimerAcceptances = pgTable("disclaimer_acceptances", {
  id: serial("id").primaryKey(),
  userId: integer("user_id"),
  version: text("version").notNull(),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }).defaultNow().notNull(),
  ipAddress: text("ip_address"),
  userAgent: text("user_agent"),
});

export type DisclaimerAcceptance = typeof disclaimerAcceptances.$inferSelect;

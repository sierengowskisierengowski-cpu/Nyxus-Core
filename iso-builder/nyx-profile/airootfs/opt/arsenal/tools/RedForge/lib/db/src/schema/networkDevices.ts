import { pgTable, serial, text, timestamp, boolean } from "drizzle-orm/pg-core";

export const networkDevices = pgTable("network_devices", {
  id: serial("id").primaryKey(),
  ip: text("ip").notNull().unique(),
  hostname: text("hostname").notNull().default(""),
  mac: text("mac").notNull().default(""),
  vendor: text("vendor").notNull().default(""),
  excluded: boolean("excluded").notNull().default(false),
  lastSeen: timestamp("last_seen", { withTimezone: true }).defaultNow().notNull(),
});

export type NetworkDevice = typeof networkDevices.$inferSelect;

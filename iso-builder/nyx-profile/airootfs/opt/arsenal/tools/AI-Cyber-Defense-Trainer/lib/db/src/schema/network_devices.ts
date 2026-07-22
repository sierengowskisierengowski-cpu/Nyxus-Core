import { pgTable, text, serial, timestamp, boolean } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const networkDevicesTable = pgTable("network_devices", {
  id: serial("id").primaryKey(),
  ip: text("ip").notNull().unique(),
  hostname: text("hostname"),
  mac: text("mac"),
  vendor: text("vendor"),
  status: text("status").notNull().default("unknown"),
  isTarget: boolean("is_target").notNull().default(false),
  openPorts: text("open_ports").notNull().default("[]"),
  lastSeen: timestamp("last_seen", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertNetworkDeviceSchema = createInsertSchema(networkDevicesTable).omit({
  id: true,
  createdAt: true,
});
export type InsertNetworkDevice = z.infer<typeof insertNetworkDeviceSchema>;
export type NetworkDevice = typeof networkDevicesTable.$inferSelect;

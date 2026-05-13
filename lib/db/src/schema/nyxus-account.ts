import {
  pgTable,
  text,
  integer,
  timestamp,
  customType,
} from "drizzle-orm/pg-core";

const bytea = customType<{ data: Buffer; default: false }>({
  dataType() {
    return "bytea";
  },
});

export const nyxusAccountBlobs = pgTable("nyxus_account_blobs", {
  token: text("token").primaryKey(),
  blob: bytea("blob").notNull(),
  size: integer("size").notNull(),
  contentType: text("content_type").notNull().default("application/gzip"),
  updatedAt: timestamp("updated_at", { withTimezone: true })
    .defaultNow()
    .notNull(),
});

export type NyxusAccountBlob = typeof nyxusAccountBlobs.$inferSelect;

import { defineConfig } from "drizzle-kit";
import path from "path";

const dbPath = process.env.AXIOM_DB_PATH || path.join(process.cwd(), "axiom.db");

export default defineConfig({
  schema: path.join(__dirname, "./src/schema/index.ts"),
  dialect: "sqlite",
  dbCredentials: {
    url: dbPath,
  },
});

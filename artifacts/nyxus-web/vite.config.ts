import { createViteConfig } from "../../lib/web-preset/src/vite.ts";

export default createViteConfig({
  rootDir: import.meta.dirname,
  defaultPort: "18304",
  defaultBasePath: "/",
});

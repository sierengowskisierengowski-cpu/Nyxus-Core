import { createViteConfig } from "../../lib/web-preset/src/vite.ts";

export default createViteConfig({
  rootDir: import.meta.dirname,
  defaultPort: "20682",
  defaultBasePath: "/nyxus-stickies/",
});

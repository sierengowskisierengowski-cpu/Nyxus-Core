import { createViteConfig } from "../../lib/web-preset/src/vite.ts";

export default createViteConfig({
  rootDir: import.meta.dirname,
  defaultPort: "26053",
  defaultBasePath: "/nyxus-sysmon/",
});

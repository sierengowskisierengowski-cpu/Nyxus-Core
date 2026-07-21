import { build } from "esbuild";
import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, "..", "dist-electron");

const shared = {
  bundle: true,
  platform: "node",
  target: "node18",
  external: ["electron"],
  sourcemap: true,
  minify: false,
};

await Promise.all([
  build({
    ...shared,
    entryPoints: [path.join(__dirname, "main.ts")],
    outfile: path.join(outDir, "main.js"),
    format: "cjs",
  }),
  build({
    ...shared,
    entryPoints: [path.join(__dirname, "preload.ts")],
    outfile: path.join(outDir, "preload.js"),
    format: "cjs",
  }),
]);

console.log("✓ Electron main + preload compiled to dist-electron/");

import path from "path";
import { defineConfig, type PluginOption, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import runtimeErrorOverlay from "@replit/vite-plugin-runtime-error-modal";

export interface NyxusViteConfigOptions {
  /** Directory of the consuming app (pass `import.meta.dirname`). */
  rootDir: string;
  /** Port used when the `PORT` env var is not set. */
  defaultPort: string;
  /** Base path used when the `BASE_PATH` env var is not set. */
  defaultBasePath: string;
}

function resolvePort(defaultPort: string): number {
  const rawPort = process.env.PORT ?? defaultPort;
  const port = Number(rawPort);
  if (Number.isNaN(port) || port <= 0) {
    throw new Error(`Invalid PORT value: "${rawPort}"`);
  }
  return port;
}

async function replitDevPlugins(rootDir: string): Promise<PluginOption[]> {
  if (process.env.NODE_ENV === "production" || process.env.REPL_ID === undefined) {
    return [];
  }
  return [
    await import("@replit/vite-plugin-cartographer").then((m) =>
      m.cartographer({
        root: path.resolve(rootDir, ".."),
      }),
    ),
    await import("@replit/vite-plugin-dev-banner").then((m) => m.devBanner()),
  ];
}

/**
 * Shared Vite configuration for the NYXUS web surfaces. Each app supplies its
 * own `rootDir`, default port, and base path; everything else (React,
 * Tailwind, Replit dev plugins, aliases, build output, dev/preview server) is
 * identical across apps and lives here.
 */
export function createViteConfig(options: NyxusViteConfigOptions) {
  const { rootDir, defaultPort, defaultBasePath } = options;

  return defineConfig(async (): Promise<UserConfig> => {
    const port = resolvePort(defaultPort);
    const basePath = process.env.BASE_PATH ?? defaultBasePath;

    return {
      base: basePath,
      plugins: [
        react(),
        tailwindcss(),
        runtimeErrorOverlay(),
        ...(await replitDevPlugins(rootDir)),
      ],
      resolve: {
        alias: {
          "@": path.resolve(rootDir, "src"),
          "@assets": path.resolve(rootDir, "..", "..", "attached_assets"),
        },
        dedupe: ["react", "react-dom"],
      },
      root: path.resolve(rootDir),
      build: {
        outDir: path.resolve(rootDir, "dist/public"),
        emptyOutDir: true,
      },
      server: {
        port,
        strictPort: true,
        host: "0.0.0.0",
        allowedHosts: true,
        fs: {
          strict: true,
        },
      },
      preview: {
        port,
        host: "0.0.0.0",
        allowedHosts: true,
      },
    };
  });
}

# [Project name]

_Replace the heading above with the project's name, and this line with one sentence describing what this app does for users._

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

_Populate as you build — non-obvious choices a reader couldn't infer from the code (3-5 bullets)._

## Product

_Describe the high-level user-facing capabilities of this app once they exist._

## User preferences

- **Everything is real, no exceptions.** No mock data, no placeholder buttons, no dead ends, no disabled UI. Every feature shipped must be fully wired and working.
- **Professional README on every project.** Include what the app does, download/install instructions, features, build-from-source steps, and tech stack.
- **Author credit: Joseph Sierengowski** — in the README, package.json, license, and any installer/build config.
- **Real native packaging.** Desktop apps get proper installers (macOS .dmg, Windows .exe, Linux .AppImage) via electron-builder. GitHub Actions workflow included for automated builds on tag push.
- **MIT License** on every project, credited to Joseph Sierengowski.
- **One-liner install scripts** for CLI/desktop tools where applicable.
- **Settings pages must be functional** — every option saves and takes effect, About section shows real version/platform info.

## Gotchas

_Populate as you build — sharp edges, "always run X before Y" rules._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details

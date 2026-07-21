# GowskiNet Security Lab (GSL)

A personal cybersecurity training lab web app for the GowskiNet home network (192.168.0.x). Real tool execution with live WebSocket streaming, 83 tools across 20 categories, SQLite history, notes, and a live network dashboard.

> For local (off-Replit) setup, run steps, and the authentication model, see `README.md`.

## Run & Operate

- Frontend (Vite): managed by workflow `artifacts/gsl: web` (port 19670, path `/`)
- Python backend: managed by workflow `artifacts/gsl: python-api` (port 8000, paths `/api` and `/ws`)
- Node.js API server (unused by GSL): `artifacts/api-server: API Server` (port 8080, path `/api-server`)

**Start the Python backend manually (path-relative, runs anywhere):**
```bash
bash gsl-backend/start.sh
```

**Typecheck frontend:**
```bash
pnpm --filter @workspace/gsl run typecheck
```

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- Frontend: React + Vite (port 19670, path `/`)
- Backend: Python 3.12 + FastAPI + uvicorn (port 8000)
- DB: SQLite via aiosqlite (`gsl-backend/gsl.db`)
- WebSocket: `/ws/run/{run_id}` — client sends `{command}`, receives streamed lines + done event
- Build: esbuild (Node.js API server, unused by GSL)

## Where things live

- `artifacts/gsl/src/` — React frontend (pages, components, lib)
  - `pages/Dashboard.tsx` — live stats + network devices + recent runs
  - `pages/Tools.tsx` — category sidebar, tool grid, right-panel config + terminal
  - `pages/History.tsx` — run history with flag/delete, expandable output
  - `pages/Notes.tsx` — CRUD research notes
  - `components/Terminal.tsx` — WebSocket streaming terminal
  - `components/ToolCard.tsx` — tool card with difficulty badge + favorite star
  - `lib/api.ts` — base fetch helper + wsUrl helper
- `gsl-backend/` — Python FastAPI backend (standalone, NOT part of Node.js monorepo)
  - `main.py` — FastAPI app entry point (CORS + all routers)
  - `app/tools_data.py` — 83 tool definitions across 20 categories with commandTemplates
  - `app/database.py` — SQLite init + aiosqlite connection
  - `app/routers/tools.py` — GET/POST tools, favorites, preview-command
  - `app/routers/runs.py` — run history CRUD + flag
  - `app/routers/notes.py` — notes CRUD
  - `app/routers/dashboard.py` — summary, recent runs, network device scan
  - `app/routers/execute.py` — POST /api/execute + WebSocket /ws/run/{id}
  - `start.sh` — start script (uses absolute paths for workflow runner)

## Architecture decisions

- Python FastAPI chosen over Node.js for backend: subprocess execution, WebSocket streaming, and Kali/security tool integration are more natural in Python
- Backend is standalone (not a pnpm workspace package) — lives at `gsl-backend/` outside the monorepo
- The Node.js API server (`artifacts/api-server`) originally claimed `/api` path; moved to `/api-server` so Python backend owns `/api` and `/ws`
- WebSocket protocol: client connects → sends `{command: "..."}` JSON → server streams `{type, line}` → final `{type: "done", exitCode}`
- commandTemplate in tools_data.py is server-side only (not exposed via API); resolved via `/api/tools/{id}/preview-command` POST

## Product

- **Dashboard**: live stats (83 tools, 20 categories, runs count, findings, favorites), network device discovery (ARP scan via nmap), recent run history
- **Tools**: 20 category sidebar, 83 tool cards with difficulty/timing badges, right-panel config with dynamic params, command preview, execute confirmation dialog, live terminal with WebSocket streaming
- **Learn**: per-tool study modules wired to the real tool registry (theory, flags, params, base command) plus a searchable index
- **History**: all past runs with status badges, expandable output, flag as finding, delete, CSV export
- **Notes**: create/edit/delete research notes with timestamps

## User preferences

- Only for the GowskiNet home network (192.168.0.x), hosted on nyx-cosmic (192.168.0.172)
- Real commands, real subprocess execution — no mocking
- Dark theme: #0a0a0f background, #7B5EA7 purple accent
- JetBrains Mono for all terminal/code output
- Network: 192.168.0.172 (nyx-cosmic), 192.168.0.125 (pi-zero-honeypot), 192.168.0.80 (pi5-kali)

## Gotchas

- The Python backend workflow (`artifacts/gsl: python-api`) uses an absolute path in start.sh because the workflow runner's CWD is not the workspace root
- The Node.js API server must NOT claim `/api` paths — it now uses `/api-server`
- Python packages are installed in `.pythonlibs/` (managed by uv in the workspace root)
- The `PYTHONPATH` must include `gsl-backend/` for relative imports (`from app.xxx import ...`) — start.sh handles this with `cd`
- `pnpm run typecheck` (not `build`) for checking frontend — `build` needs `PORT` and `BASE_PATH` env vars from the workflow

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
- Python tools are available system-wide (nmap, etc.) only on the actual 192.168.0.172 machine

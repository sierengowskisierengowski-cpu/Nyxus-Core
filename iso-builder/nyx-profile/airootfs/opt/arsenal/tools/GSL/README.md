# GowskiNet Security Lab (GSL)

A self-hostable personal cybersecurity training lab. A **FastAPI** backend runs
real security tools via `subprocess` and streams their stdout live over a
WebSocket; a **React + Vite** SPA provides the dashboard, tool runner, history,
notes, findings, command library, and per-tool learning modules.

> **Scope: local / isolated-lab use only.** The tool runner executes real
> commands. Run it only on a network you own (GowskiNet, `192.168.0.x`) and never
> expose it to untrusted networks. Access is protected by authentication (below).

- **83 tools** across 20 categories (`gsl-backend/app/tools_data.py`)
- Real subprocess execution + live WebSocket streaming
- SQLite persistence (runs, notes, favorites), `psutil` telemetry, `nmap` device discovery
- Token-based authentication gating all data and command endpoints

---

## Requirements

- Python 3.12+ (backend)
- Node.js 20+ and **pnpm** (frontend — this repo is a pnpm workspace)
- Optional: `nmap` and the specific security tools you want to run, on `PATH`

## 1. Configure authentication

```bash
cd gsl-backend
cp .env.example .env
# Generate a password hash and paste the printed line into .env:
python3 hash_password.py
# -> GSL_AUTH_PASSWORD_HASH=pbkdf2_sha256$...
```

Set `GSL_AUTH_USERNAME` in `.env` too (default `admin`). If you skip this step
entirely, the backend generates a **one-time password at startup and prints it to
the console** so the app is still protected — but it changes on every restart, so
setting a hash is recommended.

## 2. Run the backend

```bash
cd gsl-backend
bash start.sh            # listens on 0.0.0.0:8000 (override with GSL_BACKEND_PORT)
```

## 3. Run the frontend

### Option A — Vite dev server (development)

```bash
pnpm install
pnpm --filter @workspace/gsl dev     # http://localhost:19670
```

The dev server proxies `/api` and `/ws` to `http://127.0.0.1:8000`, so the SPA
reaches the backend with same-origin URLs (no CORS needed). Override the backend
location with `GSL_BACKEND_URL` if it runs elsewhere.

### Option B — single-port production build (recommended for self-hosting)

```bash
pnpm install
pnpm --filter @workspace/gsl build   # outputs artifacts/gsl/dist/public
cd gsl-backend && bash start.sh      # FastAPI serves the built SPA + API on :8000
```

Now open `http://localhost:8000`. FastAPI serves the SPA and the API from one
origin — no proxy, no CORS. (The backend auto-serves the build if
`artifacts/gsl/dist/public` exists; override with `GSL_STATIC_DIR`.)

> The pnpm build may need `--config.verify-deps-before-run=false` in some
> environments due to the repo's `preinstall` guard, e.g.
> `pnpm --config.verify-deps-before-run=false --filter @workspace/gsl exec vite build --config vite.config.ts`.

## 4. Log in

Open the app, sign in with the username/password you configured. Powerful
endpoints (`/api/execute`, `/api/runs/{id}/kill`, and the `/ws/run/{id}`
WebSocket) require a valid session token; the WebSocket receives it as a
`?token=` query parameter.

---

## Configuration reference (`gsl-backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `GSL_AUTH_USERNAME` | `admin` | Login username |
| `GSL_AUTH_PASSWORD_HASH` | — | PBKDF2 hash from `hash_password.py` (preferred) |
| `GSL_AUTH_PASSWORD` | — | Plaintext fallback (hashed in memory at startup) |
| `GSL_SESSION_TTL_HOURS` | `12` | Session token lifetime |
| `GSL_HOST` / `GSL_BACKEND_PORT` | `0.0.0.0` / `8000` | Backend bind host/port |
| `GSL_CORS_ORIGINS` | `http://localhost:19670,http://127.0.0.1:19670` | Extra CORS origins (only if frontend is a separate origin) |
| `GSL_STATIC_DIR` | `artifacts/gsl/dist/public` | Built SPA directory to serve |

## Tests

```bash
python3 -m pytest gsl-backend/tests
```

A real smoke test boots the FastAPI app against a temp SQLite DB and verifies
health, the tool registry (83 tools), auth gating (401s), login, and command
preview resolution. No external network or command execution occurs.

## Project layout

- `gsl-backend/` — FastAPI app (`main.py`, `app/`, `tests/`)
  - `app/auth.py` / `app/routers/auth.py` — password hashing, sessions, login
  - `app/config.py` — `.env` loader + settings
  - `app/routers/execute.py` — command exec + auth-gated WebSocket runner
  - `app/tools_data.py` — 83 tool definitions
- `artifacts/gsl/` — React + Vite SPA (pages, components, `lib/api.ts`)

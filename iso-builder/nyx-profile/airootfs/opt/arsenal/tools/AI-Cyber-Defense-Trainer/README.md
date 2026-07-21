# AI Cyber Defense Trainer (GowskiNet REDFORGE)

A local, lab-only adversary-emulation training and observability console: a
React SPA on an Express + PostgreSQL backend, with a **real** live-log
WebSocket feed, a **real** MITRE ATT&CK knowledge base, and a **real** network
asset map.

> Scope: LOCAL LAB USE ONLY. All live data comes from this host's own honeypot
> / journal logs and its own allowlisted lab subnet. Nothing here reaches
> external networks.

## Stack

- pnpm workspaces, Node.js 24+ (runs on 26), TypeScript 5.9
- API: Express 5, PostgreSQL + Drizzle ORM
- Live logs: RFC 6455 WebSocket server (built on Node `http`/`crypto`, no `ws` dep)
- Frontend: React 19 + Vite, TanStack Query, Wouter, shadcn/ui, Tailwind
- Auth: JWT (HS256) + scrypt-hashed passwords

## What's real

| Feature | Source of truth |
|---|---|
| Live training/telemetry feed (`/ws`) | tails real honeypot records (`CommandVault/honeypots`), `journalctl -f` for `jett-daemon`/`bifrost-guardian`, and auditd (if readable) |
| MITRE ATT&CK knowledge base | distilled from the official MITRE ATT&CK Enterprise STIX bundle |
| Network map | `arp-scan`/`nmap` discovery of the allowlisted lab subnet |
| Admin login | created by the seed script from an env password (scrypt hash) |

## Prerequisites

- PostgreSQL running locally
- `pnpm install` (dependencies resolve from the local store; offline-friendly)
- For live sources: read access to the honeypot dir + journal (auditd needs
  root and is skipped otherwise)
- For the network map: `arp-scan` (and optionally `nmap`) installed

## Setup

```bash
cp .env.example .env         # then edit DATABASE_URL, SESSION_SECRET, etc.
pnpm install

# 1. Create the schema on a fresh database
pnpm --filter @workspace/db run push

# 2. Seed the admin operator (password comes from the environment)
SEED_ADMIN_PASSWORD='choose-a-strong-pass' \
  pnpm --filter @workspace/scripts run seed

# 3. (optional) Populate the network map from a REAL scan of the lab subnet
pnpm --filter @workspace/scripts run scan-network
# add SCAN_PORTS=1 to also run a bounded nmap top-50 port scan

# 4. (optional) Regenerate the MITRE dataset from a STIX bundle
MITRE_STIX_PATH=/path/to/enterprise-attack.json \
  pnpm --filter @workspace/scripts run build-mitre
```

## Run (development)

Two processes: the API server (`:8080`, serves `/api` + `/ws`) and the Vite
dev server (`:20508`, serves the SPA and proxies `/api` + `/ws` to the API).

```bash
# Terminal A — API + WebSocket log server
PORT=8080 pnpm --filter @workspace/api-server run dev:api

# Terminal B — SPA dev server
PORT=20508 pnpm --filter @workspace/redforge run dev
```

Open http://localhost:20508 and log in with the seeded operator.

(`pnpm --filter @workspace/api-server run dev` starts both together.)

## Build & test

```bash
pnpm run typecheck                              # all packages
pnpm --filter @workspace/api-server run build   # esbuild bundle
pnpm --filter @workspace/api-server run test    # backend smoke test (healthz + /ws)
```

## Live log sources

The WebSocket server (`artifacts/api-server/src/lib/log-sources.ts`) streams
real events, read-only:

- **Honeypots** — every `*.txt` under `HONEYPOT_LOG_DIR` is tailed for new lines.
- **systemd journal** — `journalctl -f` for each unit in `JOURNAL_UNITS`.
- **auditd** — `AUDITD_LOG_PATH` is tailed only if the server user can read it
  (normally root-only, so it is skipped by default — see the in-code TODO).

No source is ever faked; if one is unavailable it is skipped with a warning.

## Security notes (local lab)

- Passwords are scrypt-hashed; no default/secret password is committed.
- `SESSION_SECRET` has a dev fallback — set a real value in `.env`.
- The generator emits real offensive script text for authorised lab training
  only. Network enumeration is hard-restricted to the allowlisted lab subnet.

# GowskiNet FORGE

> Self-hosted AI-powered cybersecurity threat research platform — generate, analyze, and operationalize novel attack techniques for authorized defensive research.

![Stack](https://img.shields.io/badge/stack-React%20%2B%20Express%20%2B%20PostgreSQL-orange?style=flat-square)
![AI](https://img.shields.io/badge/AI-Local%20Ollama-blueviolet?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue?style=flat-square)

---

## What is FORGE?

FORGE is a dark-lab-aesthetic threat research workstation for security professionals. It uses a **fully local AI** (Ollama — no cloud, no API key, no outbound calls) to generate novel, never-before-seen attack techniques with full technical documentation — then automatically produces detection rules, hardening configs, and test plans so defenders can stay ahead of real-world attackers.

Built for:
- Red team researchers who want AI-assisted technique discovery
- Blue teamers who need detection rules for novel threats
- Security engineers conducting authorized threat modeling
- Researchers coordinating responsible disclosure for unprecedented findings

---

## Features

| Module | Description |
|---|---|
| **Mutation Lab** | Generate novel threats via a local Ollama model with streaming SSE output. Control novelty target (1–10), platform, complexity, and evasion priority. |
| **Input Lab** | Feed raw inputs (commands, scripts, CVEs, honeypot captures) as seeds for threat generation. |
| **Threat Library** | Browse, filter, and manage all generated threats. Grid/list view, multi-select bulk actions. |
| **Threat Analysis** | Full breakdown per threat: code, behavioral IOCs, network IOCs, Sigma/Snort/YARA rules, defensive recommendations, hardening config, test plan. |
| **Detection Rules Lab** | View, edit, and manage auto-generated Sigma, Snort/Suricata, and YARA detection rules per threat. |
| **Research Notes** | Markdown notebook with multiple notebooks, note types, pinning, starring, and autosave. |
| **Knowledge Base** | Curated knowledge store (MITRE, Malware, LOLBAS, GTFOBins, CVE, Cowrie, OWASP, etc.) to inform generation. |
| **REDFORGE** | Export generated threats as portable REDFORGE handoff packages (JSON deployment bundles written to a local export directory). |
| **Meli Honeypot** | Live feed of **real** attacker commands ingested read-only from the local Cowrie honeypot ledger; import them as generation seeds. |
| **Disclosure Helper** | Auto-generates responsible disclosure reports and CVE drafts for unprecedented (9–10 novelty) threats. |
| **AI Chat** | Persistent local-AI sessions for research Q&A and technique deep-dives. |
| **Settings** | Configure AI model, default generation parameters, sandbox limits, and integration URLs. |

---

## Tech Stack

- **Monorepo**: pnpm workspaces, Node.js 24
- **Frontend**: React 18, Vite, TypeScript 5.9, TailwindCSS, shadcn/ui, Wouter, TanStack Query
- **Backend**: Express 5, TypeScript, Zod validation, Server-Sent Events (SSE) for streaming
- **Database**: PostgreSQL + Drizzle ORM
- **AI**: Local Ollama (default model `forge-sec`, configurable via `OLLAMA_MODEL`) — no cloud, no API key
- **API Contracts**: OpenAPI spec → Orval codegen (React Query hooks + Zod schemas)
- **Design**: JetBrains Mono, `#070710` dark background, `#f97316` orange + `#7B5EA7` purple accents

---

## Project Structure

```
forge/
├── artifacts/
│   ├── api-server/          # Express 5 API backend (port 5000)
│   │   └── src/
│   │       ├── routes/      # All API route handlers
│   │       └── index.ts     # Server entrypoint
│   └── forge/               # React + Vite frontend
│       └── src/
│           ├── pages/       # 12 application pages
│           ├── components/  # Layout, UI components
│           └── App.tsx      # Router
├── lib/
│   ├── api-spec/            # OpenAPI specification (source of truth)
│   ├── api-client-react/    # Generated React Query hooks (do not edit)
│   ├── api-zod/             # Generated Zod schemas (do not edit)
│   └── db/                  # Drizzle ORM schema + migrations
└── scripts/                 # Utility scripts
```

---

## Getting Started

### Prerequisites

- Node.js 24+
- pnpm 9+
- PostgreSQL database

### Environment Variables

Copy `.env.example` to `.env` and fill it in. `.env` is gitignored — never commit secrets.

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `PORT` | yes | Port the single-process server listens on (serves both `/api` and the SPA) |
| `BASE_PATH` | yes | SPA base path (usually `/`) |
| `OLLAMA_HOST` | for AI | Local Ollama endpoint (default `http://127.0.0.1:11434`). FORGE's AI runs fully local — no cloud, no API key, no outbound calls. Without Ollama running, non-AI features still work. |
| `OLLAMA_MODEL` | for AI | Ollama model name used for generation/analysis/chat (default `forge-sec`) |
| `FORGE_AUTH_USERNAME` | no | Login username (default `admin`) |
| `FORGE_AUTH_PASSWORD` | one of | Plaintext login password (hashed with scrypt in memory at startup) |
| `FORGE_AUTH_PASSWORD_HASH` | one of | Pre-computed scrypt hash (`pnpm --filter @workspace/scripts run hash-password`) |
| `SESSION_SECRET` | recommended | HMAC key for signing session cookies (`openssl rand -hex 32`). Ephemeral if unset. |
| `FORGE_SESSION_TTL_HOURS` | no | Session lifetime in hours (default 168) |
| `FORGE_COOKIE_SECURE` | no | Set `1` when serving over HTTPS |
| `FORGE_ALLOWED_ORIGINS` | no | Comma-separated CORS allowlist. Omit for same-origin (default, locked down). |
| `FORGE_HONEYPOT_LOG_DIR` | no | Cowrie honeypot ledger directory (default `/home/cosmic/CommandVault/honeypots`) |
| `FORGE_HONEYPOT_POLL_MS` | no | Honeypot re-scan interval in ms (default 60000; `0` disables the timer) |
| `FORGE_REDFORGE_EXPORT_DIR` | no | Where REDFORGE handoff packages are written (default `<repo>/exports/redforge`) |

If neither `FORGE_AUTH_PASSWORD` nor `FORGE_AUTH_PASSWORD_HASH` is set, a random one-time
password is generated and printed to the server logs at startup.

### Install & Run (self-hosted, single process)

```bash
# 1. Install dependencies
pnpm install

# 2. Configure environment
cp .env.example .env   # then edit .env

# 3. Load env vars into your shell (or use `node --env-file=.env`)
set -a && . ./.env && set +a

# 4. Push database schema
pnpm --filter @workspace/db run push

# 5. Build the frontend + API
pnpm --filter @workspace/forge run build
pnpm --filter @workspace/api-server run build

# 6. Start the server — serves the API *and* the built SPA on $PORT
pnpm --filter @workspace/api-server run start
# open http://localhost:$PORT  and log in
```

For frontend development with hot reload, run `pnpm --filter @workspace/forge run dev`
in a second terminal (the API must be running; requests to `/api` are same-origin).

### Backend smoke test

Boots the real server against your local Postgres and exercises auth + the honeypot
feed over HTTP (no AI/model calls, no external network):

```bash
set -a && . ./.env && set +a
pnpm --filter @workspace/api-server run build
pnpm --filter @workspace/api-server run test
```

### Codegen (after changing the OpenAPI spec)

```bash
pnpm --filter @workspace/api-spec run codegen
```

### Typecheck

```bash
pnpm run typecheck
```

---

## API Overview

All routes are prefixed with `/api`:

| Route | Description |
|---|---|
| `GET /api/dashboard/stats` | Dashboard metrics |
| `POST /api/inputs` | Create a research input |
| `POST /api/threats/generate` | Stream threat generation via SSE |
| `GET /api/threats` | List threats with filters |
| `GET /api/threats/:id` | Get threat details |
| `GET /api/detection-rules` | List detection rules |
| `GET /api/notes` | List research notes |
| `GET /api/knowledge` | List knowledge base entries |
| `GET /api/settings` | Get platform settings |
| `POST /api/anthropic/conversations` | Start AI chat session |
| `GET /api/integrations/redforge/status` | REDFORGE connection status |
| `GET /api/integrations/meli/feed` | Meli honeypot feed |

---

## Legal Notice

> **FORGE is built exclusively for authorized defensive security research.**
> All generated content is for educational and defensive purposes only.
> Users must have explicit written authorization before testing techniques against any system.
> The authors are not responsible for misuse. By using this tool you agree to only conduct research on systems you own or have written permission to test.

---

## Architecture Decisions

- **Contract-first API**: OpenAPI spec is the single source of truth; client hooks and Zod schemas are generated — never hand-written.
- **SSE for AI streaming**: Threat generation streams tokens via Server-Sent Events for real-time feedback without WebSocket complexity.
- **Inline styles over Tailwind for theming**: Design-critical colors use inline styles to guarantee no Tailwind purge issues and allow runtime theme consistency.
- **Drizzle ORM**: Type-safe database queries with schema-as-code and lightweight migrations via `drizzle-kit push`.
- **pnpm workspaces**: Strict package isolation — each artifact declares its own dependencies; shared logic lives in `lib/`.

---

## Contributing

PRs welcome. Please open an issue first for major feature changes.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a PR

---

## Author

Built by **GowskiNet** — [github.com/sierengowskisierengowski-cpu](https://github.com/sierengowskisierengowski-cpu)

---

*GowskiNet FORGE — Threat Research Command Center*

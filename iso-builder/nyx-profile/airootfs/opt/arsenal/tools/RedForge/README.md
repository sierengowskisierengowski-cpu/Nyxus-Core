# RedForge

A local, single-operator **defensive-skills training** web app: a React 19 SPA
(~25 pages) backed by an Express 5 + PostgreSQL API. It provides argon2 + TOTP
authentication, DB-backed missions/scoring, a knowledge base, an AI tutor, and a
**real local-network asset-inventory** feature for your own lab.

> **Local use only.** See [`DISCLAIMER.md`](./DISCLAIMER.md). Only scan networks
> you own and are authorized to inspect.

## Stack

- pnpm workspaces, Node.js 24+, TypeScript 5.9
- API: Express 5, Drizzle ORM, argon2, speakeasy (TOTP)
- Frontend: React 19 + Vite 7 + Tailwind, wouter, TanStack Query
- API contract: OpenAPI → Orval-generated client + Zod schemas

## Prerequisites

- Node.js 24+ and `pnpm`
- PostgreSQL (local instance or container)
- `nmap` (recommended) and/or `arp-scan` for the network-scan feature

## Setup

```bash
pnpm install
cp .env.example .env      # then edit DATABASE_URL etc.

# create the schema in your Postgres database
pnpm --filter @workspace/db run push
```

## Run (local, two terminals)

```bash
# Terminal 1 — API server (http://localhost:5000, routes under /api)
PORT=5000 DATABASE_URL=postgres://redforge:redforge@localhost:5432/redforge \
  pnpm --filter @workspace/api-server run dev

# Terminal 2 — frontend dev server (http://localhost:5173)
pnpm --filter @workspace/redforge run dev
```

The Vite dev server proxies `/api` → `http://localhost:5000` (override with
`API_PROXY_TARGET`), so no CORS or cookie-origin juggling is needed. `PORT` and
`BASE_PATH` are optional for the frontend and default to `5173` / `/`.

First launch walks you through creating the operator account (argon2 password +
TOTP enrollment).

## Build / verify

```bash
pnpm run typecheck                      # typecheck all packages
pnpm --filter @workspace/redforge run build
pnpm --filter @workspace/api-server run test   # scanner smoke tests
```

## Network scan (defensive asset inventory)

`POST /api/network/scan` runs a **real** host-discovery scan of your own lab and
stores the results in the `network_devices` table — there is no seeded/fake data.

- Default tool `auto`: `nmap -sn` host discovery, enriched with MAC addresses
  from the kernel ARP/neighbour table (`ip neigh`). Set `REDFORGE_SCAN_TOOL` to
  `nmap` or `arp-scan` to force a tool.
- The scan target is the server-configured **Target Subnet** (Settings page /
  `settings.targetSubnet`) — never an arbitrary request-supplied target.
- Every target must be **RFC1918 private** *and* fully contained within an
  allow-listed CIDR. Public/routable ranges are always refused.
- The allow-list defaults to the host-only lab subnet `192.168.56.0/24` plus this
  machine's own directly-attached private subnets. Extend it with
  `REDFORGE_SCAN_ALLOWED_SUBNETS` (comma-separated CIDRs).

### Privileges

`nmap -sn` and ARP-table enrichment work **unprivileged** (IP + reverse-DNS
hostname + MAC for on-link hosts). Full MAC/vendor resolution from a single tool
requires raw-socket privileges; to enable it either run the API with
`CAP_NET_RAW`/root or use `arp-scan` with appropriate capabilities:

```bash
sudo setcap cap_net_raw+ep "$(command -v arp-scan)"
```

## Configuration

See [`.env.example`](./.env.example) for all environment variables.

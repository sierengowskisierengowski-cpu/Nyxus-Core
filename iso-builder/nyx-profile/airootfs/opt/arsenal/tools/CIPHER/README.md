# GowskiNet CIPHER

An **honest, local** password-security lab. CIPHER does three real things and
nothing fake:

1. **Password strength analysis** — entropy, pattern detection, and crack-time
   estimation (`Strength Analyzer`).
2. **Hash-type identification** — regex-based algorithm fingerprinting.
3. **A real front-end for `hashcat` and John the Ripper** — CIPHER does *not*
   implement any cracking algorithm of its own. It shells out to the standard
   tools already installed on the machine, runs them against hash files and
   wordlists **you load yourself**, parses their real progress output, and
   stores the real results.

There is **no fabricated data anywhere**: system/GPU telemetry comes from
`/proc` and `nvidia-smi`, job progress comes from the real tool's status
stream, and cracked results come from the real potfile/outfile.

> Intended for auditing **your own** test hashes in **your own** lab. Only run
> the tools against hashes you own or are explicitly authorized to test.

## Requirements

- Node.js 24+ and `pnpm`
- PostgreSQL (a `DATABASE_URL`)
- `hashcat` and/or `john` on `PATH` (or configured in Settings)
- Optional: an NVIDIA GPU + `nvidia-smi` for GPU acceleration and telemetry

## Setup

```bash
pnpm install

# 1. Configure environment
cp .env.example .env
# edit .env: set DATABASE_URL and CIPHER_PASSWORD (or CIPHER_PASSWORD_HASH)

# 2. Create the database schema and (optionally) seed honest sample data
export DATABASE_URL='postgresql://<user>@localhost:5432/cipher'
pnpm --filter @workspace/db run push
pnpm --filter @workspace/scripts run seed
```

Generate a pre-hashed password instead of using a plaintext one:

```bash
pnpm --filter @workspace/scripts run hash-password 'your-strong-password'
# copy the printed CIPHER_PASSWORD_HASH into your environment
```

## Run (local)

Two processes. The Vite dev server proxies `/api` to the Express API.

```bash
# Terminal 1 — API server (port 8080)
export DATABASE_URL='postgresql://<user>@localhost:5432/cipher'
export CIPHER_PASSWORD='your-strong-password'
pnpm --filter @workspace/api-server run dev

# Terminal 2 — frontend (port 23051, proxies /api -> :8080)
pnpm --filter @workspace/cipher run dev
```

Then open http://localhost:23051, log in with the owner password, accept the
disclaimer, and use the app.

Tip: Node can load the `.env` for the API server directly:

```bash
node --env-file=.env --enable-source-maps artifacts/api-server/dist/index.mjs
```

## Verify

```bash
pnpm run build                       # typecheck + build all packages
pnpm --filter @workspace/api-server run test   # backend smoke test
```

## How the real orchestration works

- Submit/upload your own hashes (`Hash Submission`) and upload a wordlist
  (`Wordlists`), or use the built-in `common-passwords.txt`.
- In `Attack Engine` pick the engine (hashcat/john), hash type, attack mode
  (dictionary / brute-force / hybrid), wordlist, and optional rule set.
- Launching a job writes the target hashes to an app-owned hash file under
  `CIPHER_WORK_DIR` (default `~/.cipher/work`) and spawns the real binary.
- `Live Monitor` shows real progress (parsed from hashcat `--status-json` /
  `john --status`), the real tool stdout/stderr, and real CPU/GPU telemetry.
- Pause/Resume/Stop map to real `SIGSTOP` / `SIGCONT` / `SIGTERM` on the child
  process.
- Cracked plaintexts are read from the real potfile/outfile and saved to
  `Results`; the corresponding hashes are marked cracked.

All tool inputs are confined to `CIPHER_WORK_DIR` — no arbitrary system paths
are ever passed to the tools.

## Auth

Tool-running and mutating endpoints require the owner token (obtained by
logging in with `CIPHER_PASSWORD` / `CIPHER_PASSWORD_HASH`). Tokens are
HMAC-signed with `CIPHER_AUTH_SECRET` (auto-generated and persisted to the
working dir if unset). No secrets are hardcoded in the source.

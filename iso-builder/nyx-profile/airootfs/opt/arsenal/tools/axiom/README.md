# ⚡ AXIOM — Desktop AI Assistant

> A premium personal AI command center. Lives in your system tray. Runs on your GPU. Knows your system.

**Built by [Joseph Sierengowski](https://github.com/josephsierengowski)**

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey?style=flat-square)
![Electron](https://img.shields.io/badge/Electron-36-47848F?style=flat-square&logo=electron)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## What is AXIOM?

AXIOM is a native desktop AI assistant that lives in your system tray and launches instantly via a global hotkey. It lets you control your computer in plain English — organize files, run scheduled automations, manage a personal knowledge base, and have full AI conversations — all running locally on your own hardware or via a cloud API of your choice.

No subscriptions. No cloud lock-in. Your machine, your data.

---

## Download & Install

### macOS
1. Download `AXIOM-mac-arm64.dmg` (Apple Silicon) or `AXIOM-mac-x64.dmg` (Intel) from [Releases](https://github.com/sierengowskisierengowski-cpu/Desktop-Assistant-AI/releases)
2. Open the `.dmg` and drag **AXIOM** into your Applications folder
3. First launch: right-click → **Open** to bypass macOS Gatekeeper
4. AXIOM appears in your menu bar — press **⌘ Shift Space** to open it from anywhere

### Windows
1. Download `AXIOM-Setup-win-x64.exe` from [Releases](https://github.com/sierengowskisierengowski-cpu/Desktop-Assistant-AI/releases)
2. Run the installer — creates Start Menu and optional desktop shortcuts
3. AXIOM starts in the system tray — press **Ctrl+Shift+Space** to open it anywhere

### Linux — one-liner install
```bash
curl -fsSL https://raw.githubusercontent.com/sierengowskisierengowski-cpu/Desktop-Assistant-AI/main/install.sh | bash
```
That's it. No cloning, no building. The script downloads the latest AppImage, makes it executable, and adds it to your app launcher.

Or manually: download `AXIOM-linux-x86_64.AppImage` from [Releases](https://github.com/sierengowskisierengowski-cpu/Desktop-Assistant-AI/releases), `chmod +x` it, and run it.

---

## First-Time Setup

When you first open AXIOM, the onboarding wizard walks you through four steps:

1. **Choose AI mode** — Local GPU (Ollama) or Cloud (OpenAI / compatible API)
2. **Configure your model** — Pull a model like `llama3` or paste your API key
3. **Set allowed paths** — Tell AXIOM which folders it can read and write (e.g. `~/Downloads`, `~/Documents`)
4. **Set your hotkey** — Default: `⌘ Shift Space` / `Ctrl+Shift+Space`

Done. AXIOM is ready.

---

## Features

| Section | What it does |
|---|---|
| **Chat** | Full AI chat with streaming responses, voice input, session history, and one-click file action cards |
| **Scheduler** | Cron-based recurring tasks — AXIOM runs them automatically and logs every result with undo |
| **Knowledge Base** | Persistent notes injected into every AI request so AXIOM always knows your context |
| **Activity Log** | Full history of every action with undo support for file operations |
| **Quick Actions** | One-click AI command buttons — drag to reorder, six starter presets included |
| **File Operations** | Scan, organize, delete, and move files across approved paths with preview before execution |
| **System Stats** | Live CPU, RAM, and disk usage plus AXIOM usage analytics |
| **Settings** | Global hotkey, allowed paths, AI provider config, notifications, window behavior |

---

## Using Local AI (Ollama)

AXIOM works best with [Ollama](https://ollama.ai) for fully private, offline AI:

```bash
# Install Ollama from https://ollama.ai, then:
ollama serve

# Recommended — works well on most machines (8GB+ RAM):
ollama pull llama3

# Higher quality responses (needs 16GB+ RAM):
ollama pull mistral

# Fast and lightweight (4GB RAM):
ollama pull phi3
```

AXIOM auto-detects Ollama at `http://localhost:11434`. You can override the URL in **Settings → AI Provider**.

---

## Using Cloud AI

1. Go to **Settings → AI Provider → Cloud**
2. Enter your API key (`sk-...` for OpenAI)
3. Optionally set a custom base URL for OpenAI-compatible endpoints (Together, Groq, Mistral, local vLLM, etc.)
4. Select your model from the dropdown

---

## Building from Source

### Step 1 — Install Node.js and pnpm

> **You only need to do this once per machine.**

1. Install [Node.js LTS](https://nodejs.org) (v18 or newer)
2. Install pnpm:

```bash
npm install -g pnpm
```

Verify both are working:

```bash
node --version    # should print v18.x or higher
pnpm --version    # should print 8.x or higher
```

### Step 2 — Clone and install dependencies

```bash
git clone https://github.com/sierengowskisierengowski-cpu/Desktop-Assistant-AI.git
cd axiom
pnpm install
```

### Step 3 — Run in development

```bash
# Terminal 1 — API server (port 8080)
pnpm --filter @workspace/api-server run dev

# Terminal 2 — Web UI (opens at localhost:21098)
pnpm --filter @workspace/desktop run dev

# Or run as a native Electron window:
pnpm --filter @workspace/desktop run electron:dev
```

### Step 4 — Build a distributable installer

> **Important:** Each installer must be built on its target OS.
> Build the `.dmg` on a Mac, the `.exe` on Windows, the `.AppImage` on Linux.

```bash
# macOS — .dmg + .zip (Intel + Apple Silicon)
# Must be run on macOS
pnpm --filter @workspace/desktop run electron:pack:mac

# Windows — NSIS installer .exe
pnpm --filter @workspace/desktop run electron:pack:win

# Linux — AppImage
pnpm --filter @workspace/desktop run electron:pack:linux

# All platforms
pnpm --filter @workspace/desktop run electron:pack
```

Installers are output to `artifacts/desktop/release/`.

---

## Publishing a Release (GitHub Actions)

Once the repo is on GitHub, publishing a new release is a single command — GitHub builds all three platforms automatically:

```bash
git tag v1.0.0
git push origin v1.0.0
```

That's all. GitHub Actions will:
1. Build the `.AppImage` on Linux, `.dmg` on macOS, `.exe` on Windows — all in parallel
2. Create a GitHub Release and attach all three installers
3. The Linux one-liner install script will automatically pull the new version

No local build environment needed. Your machine never has to compile anything.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Desktop shell | [Electron](https://electronjs.org) 36 |
| Frontend | [React](https://react.dev) 19 + [Vite](https://vitejs.dev) 7 + TypeScript |
| Styling | [Tailwind CSS](https://tailwindcss.com) 4 + [shadcn/ui](https://ui.shadcn.com) |
| Animations | [Framer Motion](https://framer.motion.com) |
| API server | [Express](https://expressjs.com) 5 + TypeScript |
| Database | SQLite via [Drizzle ORM](https://orm.drizzle.team) |
| Scheduling | node-cron |
| System stats | systeminformation |
| Package manager | pnpm workspaces (monorepo) |
| Installer | [electron-builder](https://electron.build) |

---

## Project Structure

```
axiom/
├── artifacts/
│   ├── desktop/                  # Electron + React/Vite frontend
│   │   ├── electron/             # Main process (main.ts, preload.ts)
│   │   ├── src/
│   │   │   ├── pages/            # Chat, Scheduler, Knowledge, Stats, etc.
│   │   │   ├── components/       # Shared UI components
│   │   │   └── lib/              # Utilities, API client
│   │   ├── icons/                # App icons (PNG, ICO, ICNS)
│   │   └── electron-builder.config.cjs
│   └── api-server/               # Express API + SQLite database
│       ├── src/
│       │   ├── routes/           # chat, files, scheduler, knowledge, activity...
│       │   └── db/               # Drizzle schema & migrations
│       └── drizzle/              # Migration SQL files
└── packages/
    └── api-client-react/         # Auto-generated typed API hooks (Orval)
```

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat/sessions/:id/messages/stream` | Send a message — SSE streaming response |
| `GET`  | `/api/chat/sessions` | List all chat sessions |
| `POST` | `/api/scheduler/tasks/:id/run` | Run a scheduled task immediately |
| `GET`  | `/api/scheduler/status` | All tasks with next-run times |
| `GET`  | `/api/knowledge/notes` | List knowledge base notes |
| `GET`  | `/api/ai/status` | Ollama connectivity + version |
| `GET`  | `/api/ai/models` | Available models (local + cloud) |
| `POST` | `/api/ai/models/pull` | Pull a new Ollama model |
| `POST` | `/api/files/preview` | Preview affected files before operation |
| `POST` | `/api/files/execute` | Execute a confirmed file operation |
| `GET`  | `/api/stats/system` | Live CPU, RAM, disk metrics |
| `GET`  | `/api/activity/summary` | Usage counts by type |
| `POST` | `/api/activity/:id/undo` | Undo a file operation |

---

## Security

AXIOM is designed to be safe by default:

- **Allowed paths only** — File operations are restricted exclusively to paths you approve in Settings. AXIOM cannot touch anything outside those directories.
- **Confirmation required** — Every destructive operation shows exactly which files will be affected and requires explicit approval before running.
- **Undo support** — Deleted and moved files are staged before removal so they can be restored.
- **Local token auth** — The embedded API server generates a random UUID token each session. The renderer must present this token with every request, so no other process on your machine can call the API.
- **No telemetry** — Nothing leaves your machine unless you explicitly use cloud AI mode.

---

## Cron Reference

AXIOM uses standard 5-field cron syntax for the Task Scheduler:

```
┌──────── minute (0-59)
│ ┌────── hour (0-23)
│ │ ┌──── day of month (1-31)
│ │ │ ┌── month (1-12)
│ │ │ │ ┌ day of week (0=Sun, 6=Sat)
│ │ │ │ │
* * * * *
```

| Expression | Meaning |
|---|---|
| `0 9 * * 1` | Every Monday at 9am |
| `0 8 1 * *` | 1st of every month at 8am |
| `*/30 * * * *` | Every 30 minutes |
| `0 0 * * 0` | Every Sunday at midnight |
| `0 */2 * * *` | Every 2 hours |

---

## License

MIT — see [LICENSE](LICENSE) for full text.

---

## Author

**Joseph Sierengowski**
GitHub: [@josephsierengowski](https://github.com/josephsierengowski)

---

*AXIOM — Your AI, your machine, your rules.*

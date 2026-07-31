# Nyxus-Core

> ## 👉 NEW HERE? READ [`HANDOFF.md`](./HANDOFF.md) FIRST.
> It is the authoritative build-state brief: the one-repo rule, **how the desktop
> is actually delivered** (the thing that caused months of confusion), what the
> build includes (ISO, **Kage-Ryu kernel — the default; `NYX_WITH_KAGE_RYU=0` to opt out**, boot art,
> features), the current state + post-mortems, and the canonical
> **bake → flash → boot** procedure. Do not start work — or a bake — without it.

Canonical source repository for the NYXUS platform and NYX image pipeline.

**Terminology standard**
- **NYX**: the bootable ISO image artifact only.
- **NYXUS**: the operating system, platform services, and application ecosystem delivered by NYX.

---

## What works today

> A quick-scan summary — see [`STATUS.md`](STATUS.md) for the full breakdown.

| Area | Status |
|------|--------|
| `pnpm run typecheck` / `pnpm run build` | ✅ Passes |
| CI pipeline (typecheck + validate + codegen-clean) | ✅ Passes |
| ISO profile lint (`verify-profile.sh` + `iso-build-verify.sh`) | ✅ Passes |
| Shared TypeScript libraries (`lib/`) | ✅ Build cleanly |
| API server + download routes | ✅ Builds and typechecks · ⬜ **no public host** — see note |
| Web surfaces (web, notepad, stickies, sysmon, widgets) | ✅ Vite builds pass |
| archiso profile (`profiledef.sh`, `packages.x86_64`, greetd config) | ✅ Validated |
| ISO bake (`build-iso.sh`) | 🟡 Requires Arch Linux host + root + `mkarchiso` |
| Kage-Ryu kernel (`linux-kage-ryu`, XanMod 7.0.12) | ✅ Prebuilt packages present; baked **by default**; verify live-media FS support on each stick |
| Hyprland desktop + 4 EWW bars + GTK4 app suite | 🟡 Source staged; live-boot required for end-to-end test |
| Calamares disk installer | 🟡 Ships as a **binary package from `[blackarch]`** (pacstrapped, *not* AUR-built); branding present; full install flow not yet verified |
| Automated ISO CI artifact + signed release | ⬜ Not yet implemented |

> ⚠ **The `nyxus-core.replit.app` production host is RETIRED** (noted
> 2026-07-30). The API server still builds and the download routes still exist,
> but nothing is deployed at that hostname. Every remaining reference to it in
> the tree is a **dead fallback**, not a working endpoint. The ISO does not need
> it: the offline cache at `/opt/nyxus-cache` is baked in and first boot works
> with no network. See the "Replit host" note in `HANDOFF.md`.

See [`ROADMAP.md`](ROADMAP.md) for the NYXUS v2 phased plan.

---

## Install (terminal)

Deploy the NYXUS desktop onto an existing Arch + Hyprland system straight from the terminal:

```bash
git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core.git
cd Nyxus-Core && ./install.sh
```

Preview the same full deploy without changing anything:

```bash
./install.sh --check
```

Or the one-liner (once you trust the repo — read scripts you pipe to bash):

```bash
curl -fsSL https://raw.githubusercontent.com/sierengowskisierengowski-cpu/Nyxus-Core/main/install.sh | bash -s -- --check   # preview
```

`install.sh` is the canonical one-command installer. By default it:
- backs up and purges stale NYXUS-managed files from `~/.config/hypr`,
  `~/.config/eww`, `~/.nyxus`, `~/.local/bin/nyxus-*`, and
  `~/.local/share/applications/nyxus-*.desktop`
- preserves user-owned state (`~/.config/nyxus`, `nyxus-monitors.conf`, extra
  wallpapers in `~/.config/hypr/walls/rotation`)
- redeploys the repo-managed configs/apps/desktop entries
- runs the system phase (`scripts/nyxus-install.sh`) to install packages,
  repair greeter/session entries, and set `NYXUS (Hyprland)` as the default session

It is idempotent — re-running it on a clean system converges to zero changes and
creates no new backup directory. Flags: `--check` (preview), `--user-only`
(skip the system phase), `--no-reload`, `--keep-legacy-sessions`.

---

## System Overview

Nyxus-Core contains the end-to-end platform implementation:
- Arch-based image construction for **NYX**
- Core runtime payloads and desktop assets for **NYXUS**
- API and web distribution surfaces
- Shared TypeScript packages and automation scripts

The repository is intentionally organized as a pnpm workspace so application, service, and shared-library changes can be versioned and shipped together.

---

## Architecture at a Glance

NYXUS is delivered through three coordinated layers:

1. **Build-time**
   - Workspace typechecking and package builds (`lib/*`, `artifacts/*`, `scripts`)
   - API server bundling and dist payload generation
2. **Distribution-time**
   - API and web surfaces distribute installers, tarballs, and related assets
   - ISO staging mirrors runtime payloads into the archiso profile
3. **Runtime**
   - NYX boots into NYXUS runtime components: Hyprland + EWW bars + full GTK4 app suite + NYXUS Phantom

See `/docs/architecture/architecture-overview.md` for component relationships and responsibility boundaries.

---

## Repository Map

```text
.
├── artifacts/                  # Deployable apps/services and runtime payload sources
│   ├── api-server/             # API distribution service and nyxus-scripts payload source
│   ├── nyxus-web/              # Main web surface
│   ├── nyxus-notepad/          # Web demo app
│   ├── nyxus-stickies/         # Web demo app
│   ├── nyxus-sysmon/           # Web demo app
│   ├── nyxus-widgets/          # Web demo app
│   └── mockup-sandbox/         # Preview and mockup environment
├── iso-builder/                # Archiso profile and NYX ISO build pipeline
├── lib/                        # Shared TypeScript packages (API spec/client/zod/db/i18n)
├── scripts/                    # Workspace automation scripts
├── docs/                       # Structured project documentation
├── CHANGELOG.md
├── CREDITS.md
├── LICENSE.md
├── SHIPPING.md
└── replit.md                   # Replit-specific development notes
```

---

## Build and Deployment Summary

### Workspace validation
- `pnpm run typecheck`
- `pnpm run build`

### API/Web packaging flow
- API server build produces distribution outputs under `artifacts/api-server/dist/`
- Vite-based web artifacts use environment-based ports/base paths (see deployment docs)

### NYX ISO flow
- Build host requirement: Arch Linux + root + `mkarchiso`
- Entry point: `iso-builder/build-iso.sh`
- Output artifact: `iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso` (~9.5–10 GB, gitignored)
- ISO label: `NYXUS_2026_07` — must match `profiledef.sh` and all five
  `archisolabel` references or the media will not boot
- The **Kage-Ryu** kernel is baked in **by default**; `NYX_WITH_KAGE_RYU=0` opts out

Operational detail: [`iso-builder/README.md`](iso-builder/README.md),
[`SHIPPING.md`](SHIPPING.md) and `/docs/deployment/*`.

---

## Codebase Size Snapshot (Build Footprint)

Snapshot date: **2026-05-16** — ⚠ **STALE, flagged 2026-07-30, not recomputed.**

> A re-measurement on 2026-07-30 over the same file extensions gives ~**181,000**
> lines across 2,659 tracked files, but that raw number is **not** a valid
> replacement for the figure below and was deliberately not substituted:
> `iso-builder/` alone accounts for ~135,000 of it, and most of that is either a
> **staged duplicate** of `artifacts/api-server/nyxus-scripts/` (the bake copies
> the source of truth into `airootfs/`, so the same file is counted twice) or a
> **vendored third-party tree** under `airootfs/opt/arsenal/tools/` (CIPHER,
> Forge, GSL, RedForge, axiom, the Trainer). Since the total below feeds a
> handwritten-authorship declaration, only the owner should decide how staged
> copies and vendored code are counted, and re-stamp it. **Do not treat the
> table below as current.**

This section shows the tracked code size for the NYXUS build as measured on the
snapshot date above.

### Total code lines (tracked source)

- **Total LOC:** **112,905**

### Breakdown by platform area

| Area | LOC |
|---|---:|
| `artifacts/api-server/nyxus-scripts` | 49,492 |
| `artifacts/` (other packages) | 40,129 |
| `iso-builder/` | 20,263 |
| `artifacts/api-server` (service code excluding `nyxus-scripts`) | 1,171 |
| `scripts/` | 1,082 |
| `lib/` | 768 |
| **Total** | **112,905** |

### Breakdown by language

| Language | LOC |
|---|---:|
| Python | 51,279 |
| TypeScript | 41,157 |
| Shell | 11,874 |
| SCSS | 2,639 |
| Eww Yuck | 2,411 |
| CSS | 2,349 |
| QML | 1,196 |
| **Total** | **112,905** |

### Handwritten creator code total

- **Handwritten by Joseph A. Sierengowski (creator declaration):** **112,905 LOC**

### Measurement method

- Count source lines from tracked code files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.sh`, `.yuck`, `.scss`, `.css`, `.qml`).
- Exclude generated/output/vendor paths (for example: `node_modules/`, `dist/`, `build/`, `coverage/`, `attached_assets/`, `iso-builder/out/`).
- Recalculate this snapshot whenever major build content changes.

---

## Documentation Index

**Read in this order.** 1 is mandatory; everything else is reference.

1. **[`HANDOFF.md`](HANDOFF.md)** — the authoritative build state. Non-optional.
2. **[`docs/README.md`](docs/README.md)** — the full documentation map, with a
   freshness column so you can see at a glance which docs are current.
3. **[`docs/KEYBINDS.md`](docs/KEYBINDS.md)** — every active keybind, re-derived
   from the shipped config 2026-07-30.
4. **[`docs/THEME.md`](docs/THEME.md)** + **[`docs/DESIGN_CONTRACT.md`](docs/DESIGN_CONTRACT.md)**
   — the locked ALIEN NEON palette and the banned-hex list. `nyxus_palette.py`
   and `accent.json` are the machine-readable canon.
5. **[`SHIPPING.md`](SHIPPING.md)** — printable bake → flash → boot checklist.
6. **[`iso-builder/README.md`](iso-builder/README.md)** — the ISO profile and
   what the bake actually stages.

Other reference:

- **Project status:** [`STATUS.md`](STATUS.md)
- **Roadmap:** [`ROADMAP.md`](ROADMAP.md)
- **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md)
- System overview: [`docs/overview/system-overview.md`](docs/overview/system-overview.md)
- Creator and authorship: [`docs/overview/creator.md`](docs/overview/creator.md)
- Architecture overview: [`docs/architecture/architecture-overview.md`](docs/architecture/architecture-overview.md)
- Repository structure: [`docs/architecture/repository-structure.md`](docs/architecture/repository-structure.md)
- Live-desktop runtime constraints: [`docs/architecture/live-build-notes.md`](docs/architecture/live-build-notes.md)
- Build pipeline: [`docs/deployment/build-pipeline.md`](docs/deployment/build-pipeline.md)
- ISO build pipeline: [`docs/deployment/iso-build.md`](docs/deployment/iso-build.md)
- Web/API deployment: [`docs/deployment/web-and-api-deployment.md`](docs/deployment/web-and-api-deployment.md)
- Settings surface: [`docs/SETTINGS.md`](docs/SETTINGS.md)
- Master checklist: [`docs/MASTER_CHECKLIST.md`](docs/MASTER_CHECKLIST.md)
- Security inventory: [`docs/SECURITY_INVENTORY_2026-07-27.md`](docs/SECURITY_INVENTORY_2026-07-27.md)
- Project inventory (repos vs. what ships): [`docs/PROJECT_INVENTORY_2026-07-28.md`](docs/PROJECT_INVENTORY_2026-07-28.md)
- Legacy visual history (**describes purged palettes on purpose** — do not "fix"): [`docs/legacy-visuals.md`](docs/legacy-visuals.md)

---

## Created by Joseph A. Sierengowski

Nyxus-Core, NYX, and NYXUS were created, architected, and built by **Joseph A. Sierengowski**.

Joseph serves as the original system designer and primary platform architect, defining the repository's direction across ISO engineering, runtime composition, application integration, and delivery workflow.

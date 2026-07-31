# NYXUS / Nyxus-Core — Status

> **Last updated:** 2026-07-30 (correction pass over the 2026-07-12 snapshot)
>
> This document is a ground-truth snapshot of what is real and verifiable
> in this repository today, what is partially wired, and what remains
> planned. It is intentionally conservative: if something has not been
> confirmed in a live boot or a passing CI run it is marked accordingly.
>
> ⚠ **This file is NOT the live build state.** For where the build actually
> stands — which fixes are on `main`, whether a rebake is required, what is
> still open — read **[`HANDOFF.md`](HANDOFF.md)**. `STATUS.md` describes
> repository/CI reality; `HANDOFF.md` describes stick reality. Do not use this
> file to decide whether to bake.
>
> **2026-07-30 correction pass.** The 2026-07-12 revision had drifted into
> asserting several things that were no longer true, each of which could send an
> agent down a dead end. Corrected in place and marked; the misstatements are
> listed in the "Corrections" section at the bottom.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Works today — confirmed by CI, script run, or direct verification |
| 🟡 | Partially working / in progress — code exists, integration incomplete or untested end-to-end |
| ⬜ | Planned / not yet implemented — tracked but not present or unverified |

---

## Repository & Build Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| pnpm workspace install | ✅ | `pnpm install --no-frozen-lockfile` succeeds |
| TypeScript typecheck | ✅ | `pnpm run typecheck` passes |
| Workspace build | ✅ | `pnpm run build` passes |
| CI pipeline (typecheck + validate) | ✅ | `.github/workflows/ci.yml`, `typecheck.yml`, `validate.yml` pass |
| ISO profile lint (`verify-profile.sh`) | ✅ | `bash iso-builder/verify-profile.sh` passes from repo root |
| ISO build verification (`iso-build-verify.sh`) | ✅ | `bash scripts/iso-build-verify.sh` passes from repo root |
| Release automation script | ✅ | `scripts/iso-release.sh` present and validated |
| OpenAPI codegen clean check | ✅ | CI `openapi-codegen-clean` job passes |
| Shared TypeScript libraries (`lib/`) | ✅ | api-spec, client, zod, db, i18n packages build cleanly |

---

## ISO / Bootable Image Pipeline

| Item | Status | Notes |
|------|--------|-------|
| archiso profile definition (`profiledef.sh`) | ✅ | `iso_name=nyxus`, `iso_label=NYXUS_2026_07`, `bios.syslinux` + `uefi.grub`, squashfs `zstd` (was `xz` until 2026-07-30) |
| Package list (`packages.x86_64`) | ✅ | **408** package lines. `greetd` + `greetd-regreet` + `greetd-tuigreet` + `cage` present; **no `sddm`**, **no `waybar`** (eww replaced it 2026-05-11) |
| Greeter — greetd → regreet (cage), tuigreet fallback | ✅ | `nyxus-greeter` runs regreet under cage and re-pins the urban-alien login art on every start; tuigreet/agreety fall back with `--cmd nyxus-session-start` |
| Hyprland config staging | ✅ | `hyprland.conf` + **17 sourced** `conf.d` shards (only `nyxus-safemode.conf` is deliberately unsourced) |
| File permission locking (`profiledef.sh`) | ✅ | 181 explicit entries; all `nyxus-*` binaries and helpers locked at `0755` |
| ISO bake (`build-iso.sh`) | 🟡 | Requires Arch Linux host + root + `mkarchiso`; not runnable in CI. Output ~9.5–10 GB |
| Kernel — Kage-Ryu (`linux-kage-ryu`, XanMod 7.0.12) | ✅ | Baked **by default** (`NYX_WITH_KAGE_RYU=0` opts out); boot entry #0 with stock `linux` as labelled rescue; bake **hard-fails** if the prebuilt packages are absent |
| Calamares disk installer | 🟡 | **Binary package from `[blackarch]`, listed in `packages.x86_64` and pacstrapped directly.** It is *not* AUR-built in `customize_airootfs.sh` — believing that cost four failed ISOs before 2026-07-28. Branding synced; full install flow still unverified |
| SDDM login theme | 🟡 | QML theme present in `nyxus-scripts` and staged at bake, but **dormant** — the live ISO and the greetd path never use it. SDDM was abandoned for greetd on 2026-07-14 |
| Offline first-boot cache | ✅ | `/opt/nyxus-cache` staged from `artifacts/api-server/nyxus-scripts/`; the bake **hard-fails** rather than ship an online-only ISO |
| Live-session passwordless sudo drop-in | ✅ | `/etc/sudoers.d/10-nyxus-live` staged and permission-locked |

---

## API & Web Distribution

| Item | Status | Notes |
|------|--------|-------|
| API server (`artifacts/api-server`) | ✅ builds / ⬜ **not hosted** | Builds and typechecks; download routes present. **The `nyxus-core.replit.app` production host is RETIRED** — no public deployment exists (noted 2026-07-30) |
| Download API (`/api/download/nyxus/:filename`) | 🟡 | Route + allowlist (scripts, wallpapers, docs) are implemented, but there is nothing serving them. Every `nyxus-core.replit.app` URL left in the tree is a **dead fallback**, not a live endpoint |
| Crash-report upload endpoint | ✅ | `routes/crash-reports.ts` POST `/api/crash-reports` with quota GC |
| Web surfaces (`nyxus-web`, `nyxus-notepad`, `nyxus-stickies`, `nyxus-sysmon`, `nyxus-widgets`) | ✅ | Vite builds pass; runtime requires a deployment target |
| Mockup sandbox (`mockup-sandbox`) | ✅ | Preview environment builds |

---

## Desktop Runtime (requires live ISO boot on real hardware)

| Item | Status | Notes |
|------|--------|-------|
| Hyprland session startup | 🟡 | Config staged and validated; live-boot required for end-to-end test |
| EWW bars (**four**: top, bottom, left rail, right rail) | 🟡 | Yuck/SCSS validated; live-boot required. Relaunch **only** via `nyxus-eww-launch-safe` (one daemon, four bars) |
| EWW station decks (all 10 stations) | 🟡 | Present and wired into `nyxus-home-deck`. **BIFROST (9) has no deck by design** |
| GTK4 Python app suite (13 GUI apps + CLI Doctor) | 🟡 | Source present in `nyxus-scripts`; Python syntax validated; live-boot required for functional test. `nyxus-home` (GTK4) is **deliberately disabled** — the eww `home-deck` replaced it |
| nyxus-bootstrap first-boot flow | 🟡 | Script present and permission-locked; end-to-end test requires live ISO |
| NYXUS Settings (all 8+ pages) | 🟡 | Source complete per `MASTER_CHECKLIST`; live-boot required |
| Notification center (swaync) | 🟡 | Source present; live-boot required |
| Quick Settings / Control Center | 🟡 | Source present; live-boot required |
| Hyprlock lock screen | 🟡 | Config staged; live-boot required |
| Rofi launcher | 🟡 | Config staged; live-boot required |
| Dunst / Mako notifications | 🟡 | Config staged; live-boot required |
| Alacritty terminal config | 🟡 | Config staged; live-boot required |
| Wlogout logout screen | 🟡 | Config staged; live-boot required. Carries the urban-alien hero canvas |
| ~~Waybar~~ | ⬜ **REMOVED** | Dropped from `packages.x86_64` on 2026-05-11 and replaced by EWW. The `WaybarMockup` web route was deleted 2026-07-24. Do not re-add it or write config for it |
| NYXUS icon theme (31 custom SVGs) | 🟡 | Assets present; live-boot required |
| NYXUS cursor theme (Hyprcursor + XCursor) | 🟡 | Assets present; live-boot required |
| Wallpaper pack (92 backgrounds) | 🟡 | Assets present; auto-mirror to SDDM/lockscreen requires live-boot |
| Hot corners | 🟡 | `nyxus_hotcorners.py` present; live-boot required |
| Night light (gammastep) | 🟡 | Wrapper present; live-boot required |
| Dynamic wallpaper rotator | 🟡 | Script present; live-boot required |
| Game Mode / Focus Mode | 🟡 | Source present; live-boot required |

---

## Station Matrix & Desktop Unification (updated 2026-07-30)

| Item | Status | Notes |
|------|--------|-------|
| Station matrix `stations.json` (1–10 + named annexes) | ✅ | Single source of truth: `artifacts/nyxus-config/stations.json`. `stations-hacker.json` must carry **identical station identity** — gate `13w` asserts it across both trees |
| Hyprland persistent stations | ✅ | `nyxus-stations.conf` — OPS/FORGE/GHOST/PULSE/WAVE/CORE/MESH/SCRIBE/**BIFROST**/**ARSENAL**. 9 and 10 were renamed from BLAST/EDGE on **2026-07-27** |
| Named annex stations | ✅ | HOME (`Super+Home`), START (`Super+End`), LAB (`Super+Delete`) — declared in `nyxus-stations-named.conf`, which **no generator rewrites**. `nyxus-stations.conf` *is* regenerated by `nyxus-hacker-mode`, which is why the annexes cannot live there |
| Companion ("half") stations | ✅ | RELAY/ANVIL/TRACE/BEACON/MIXER/VAULT/SCAN/BOARD/SENTRY/RANGE on `Super+Alt+1..0` |
| EWW left rail | ✅ | HOME / START / 1–10, hue-tinted, station **names** (not numbers) since 2026-07-29; `workspaces.sh` polls stations + occupancy |
| HOME command deck | ✅ | The eww **`home-deck`** window on the **HOME** station (`Super+Home`). ⛔ **Not `name:0`** — a numeric `name:0` resolves into Hyprland's hidden SPECIAL range (id `-1337`) and was never visible; renamed 2026-07-26, and gate `13ag` hard-fails any reappearance. The GTK4 `nyxus-home` app is **disabled** (it rendered an empty window) |
| The Hub (`Super+grave` dashboard / hub) | ✅ | `:stacking "fg"` since 2026-07-30 — it was a fullscreen **OVERLAY** surface, which meant any window it launched landed behind it and read as dead. Gate `13ai` |
| DEEP CORE jeTT verdicts + honeypot feed | ✅ | `deepcore.sh` + `deepcore.yuck` — live docker/jett data (`Super+G`) |
| Mission Control | ✅ | `Super+F3` · `Super+Alt+A` → `nyxus-mission-control-toggle` (hyprexpo bind retired) |
| ~~Unified launcher `nyxus-start`~~ | ⬜ **RETIRED** | The `nyxus-start` GTK4 app sat on the OVERLAY layer and could be neither closed nor moved once it lost keyboard focus. Replaced by the eww **START station** (`Super+End`). `Super+Space` is the app launcher. All five buttons that still opened it were repointed on 2026-07-29 — **do not wire anything back to it** |
| Dock daemon | ✅ | Disabled on live + ISO skel (bar-only layout) |
| Dunst notification stack | ✅ | EWW notif flyout uses `dunstctl` (history + DND); `dunstrc` bridges to eww via an absolute `/usr/local/bin` path |
| Accent pipeline | ✅ | `nyxus-apply-accent prism` → `_nyxus_accent.scss` imported by EWW. **`follow_wallpaper` is LOCKED OFF** |
| ALIEN NEON palette lock | ✅ | `accent.json` has exactly one preset (`prism`); eight older presets deleted 2026-07-23. Canon: violet `#7d3dff` · magenta `#ff2dad` · green `#39ff14` · orange `#ff8a1e` + fixed cyan `#2bd2ff` / red `#ff2d55` / yellow `#ffe600` / orchid `#e367ff`. Banned: cream `#f4ead5`, gold `#d4b87a`, old violet `#a06bff` |
| Reactive bus (`nyxus-sense` → mood → threatd) | ✅ | **Nothing launched `nyxus-sense` until 2026-07-29** — the whole reactive mood layer sat on defaults. `nyxus-reactive.conf` now autostarts the chain; gate `13y` asserts every link |
| Live → canonical backport | ✅ | Full EWW/hypr/apps stack in `artifacts/` via `nyxus-backport-live.sh` — commit `471c1c5` |

---

## Planned / Not Yet Implemented

| Item | Status | Notes |
|------|--------|-------|
| Public release of a signed, downloadable NYX ISO | ⬜ | Build requires Arch Linux host; no automated CI ISO artifact yet |
| Automated ISO CI build + artifact upload | ⬜ | `build-iso.yml` workflow exists but requires privileged Arch runner |
| NYXUS Account service (backend) | ⬜ | UI scaffolded; backend service not shipped |
| NYXUS Drop (file sharing) | ⬜ | UI scaffolded; backend service not shipped |
| Multi-language / i18n runtime (beyond scaffold) | ⬜ | `nyxus_i18n.py` shim + PO stubs present; full locale coverage not done |
| Disk installer end-to-end (Calamares + post-install) | ⬜ | Calamares branding staged; full install-to-disk flow not verified |
| Hardware compatibility matrix | ⬜ | Not documented yet |
| OTA / package update channel | ⬜ | Update UI exists; update channel infra not defined |
| AUR package / PKGBUILD for NYXUS | ⬜ | Not created yet |
| Public API/download host | ⬜ | `nyxus-core.replit.app` is retired; no replacement chosen. Owner decision |
| Hyprland Lua config migration | ⬜ **deliberately deferred** | Hyprland 0.57 drops hyprlang. Owner decision 2026-07-28: **do not migrate yet** — pin the version, stabilise the build, migrate on a branch after 0.57 actually ships. Gate `13x` hard-fails a bake if the repos offer ≥ 0.57 |

---

## Corrections made 2026-07-30

The 2026-07-12 revision asserted these; all were false by the time they were
read, and each is the kind of statement that sends an agent in a circle:

| Was documented | Reality |
|---|---|
| "Calamares built from AUR in `customize_airootfs.sh`, not from `packages.x86_64`" | It is a **binary package from `[blackarch]` listed in `packages.x86_64`**. Four ISOs failed because every fix accepted the AUR premise |
| Stations `…/BLAST/EDGE` | Renamed **BIFROST / ARSENAL** on 2026-07-27 |
| "NYXUS Home … Workspace `name:0` · Super+0" | `name:HOME` via `Super+Home`; `name:0` is Hyprland's *hidden* SPECIAL range. The GTK4 app is disabled; the eww `home-deck` replaced it |
| "Unified launcher (`nyxus-start`) ✅ … Super+Space → `nyxus-start`" | `nyxus-start` was **retired for trapping the desktop**. `Super+Space` runs `nyxus_launcher.py` |
| "Waybar 🟡 config staged" | **Removed 2026-05-11**, replaced by EWW |
| "EWW bars (top + bottom)" | **Four** bars: top, bottom, and left/right rails |
| "API server ✅ Operational" / download API ✅ | The Replit production host is **retired**; nothing is deployed |
| "Obsidian prism theme unification ✅" | The OBSIDIAN PRISM / DARK MIRROR brand and palette were **purged** 2026-07-23/24. The row was replaced with the ALIEN NEON lock |
| "GTK4 Python app suite (12 apps)" | 13 GUI apps + the CLI Doctor |
| "nyxus-panel / nyxus-store binds ✅ Super+Alt+P / Super+Alt+S" | **Neither bind does that.** `Super+Alt+P` is the Pulse toggle; `Super+Alt+S` is Wallpaper Studio. Row removed rather than corrected — see [`docs/KEYBINDS.md`](docs/KEYBINDS.md), which is now the only keybind source of truth |
| "Slim quick-control overlay (Super+`)" | `Super+grave` opens the eww **`dashboard`**; the Hub is a separate surface. Folded into the Hub row |

---

© 2026 Joseph A. Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED

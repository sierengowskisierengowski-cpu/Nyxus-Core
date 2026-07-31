# Nyxus-Core Documentation

**Map rebuilt 2026-07-30.** Every `.md` in this tree is now listed with a
freshness marker, because the previous version of this map listed 15 of the 35
docs and silently omitted `THEME.md`, `KEYBINDS.md`, `SETTINGS.md` and every
dated session brief — so the docs that mattered most were the hardest to find.

## ⛔ Start here, in this order

1. **[`../HANDOFF.md`](../HANDOFF.md)** — the authoritative live build state:
   the one-canonical-repo rule, **how the desktop is actually delivered**, what
   is fixed, what is open, the bake→flash→boot procedure, and the
   do-not-repeat gotchas. **Non-optional. Read it before touching anything.**
2. **[`../AGENTS.md`](../AGENTS.md)** — agent-facing toolchain notes for this
   workspace (pnpm, Postgres, what is out of scope headlessly).
3. **[`../README.md`](../README.md)** — project overview + documentation index.

## Freshness legend

| Marker | Meaning |
|---|---|
| ✅ **current** | Verified against the tree on the date shown |
| 🕓 **dated brief** | A point-in-time session record. Still useful; superseded by later entries in `HANDOFF.md` |
| 🧊 **historical** | Describes a superseded state **on purpose**. Do not "correct" these — the purged palettes and old designs in them are the record of what was purged |
| ⚠ **stale** | Known to contain claims that have not been re-verified. Trust `HANDOFF.md` over these |

---

## Reference — the docs you will actually need

| Doc | State | What it is |
|---|---|---|
| [`KEYBINDS.md`](KEYBINDS.md) | ✅ current (2026-07-30) | **Every active keybind**, re-derived mechanically from `hyprland.conf` + all 18 shards. Includes a corrections table for the six things the 07-14 revision got wrong, and flags that Hacker/Ghost/Panic have **no keybind at all** |
| [`THEME.md`](THEME.md) | ✅ current (2026-07-30) | The locked **ALIEN NEON** palette, fonts, effects, mixins, and the shipped signature surfaces. Generated from `nyxus_palette.py` + `accent.json` |
| [`DESIGN_CONTRACT.md`](DESIGN_CONTRACT.md) | ✅ current | The single UI quality bar (layout, typography, colour, motion, states) **plus the banned-hex list**. §13 is a per-component audit trail |
| [`SETTINGS.md`](SETTINGS.md) | ⚠ stale | The Settings surface map. Two binaries it names (`nyxus-cheatsheet`, `nyxus-usb-watch`) do not ship |
| [`../iso-builder/README.md`](../iso-builder/README.md) | ✅ current (2026-07-30) | The archiso profile, what the bake stages, the env vars, and the `packages.x86_64` facts |
| [`../SHIPPING.md`](../SHIPPING.md) | ✅ current (2026-07-30) | Printable bake → flash → boot → smoke-test checklist |
| [`INSTALL.md`](INSTALL.md) | 🕓 dated brief | Installing NYXUS onto an existing Arch + Hyprland system |
| [`REINSTALL_GUIDE.md`](REINSTALL_GUIDE.md) | 🕓 dated brief | Rebuild-the-box guide |
| [`REBOOT_SURVIVAL.md`](REBOOT_SURVIVAL.md) | 🕓 dated brief | What must survive a reboot and how it is guaranteed |
| [`KERNEL_ISO.md`](KERNEL_ISO.md) | 🕓 dated brief | Kage-Ryu kernel ↔ ISO relationship |
| [`MACHINE_PROFILE.md`](MACHINE_PROFILE.md) | 🕓 dated brief | The build host's hardware |
| [`MASTER_CHECKLIST.md`](MASTER_CHECKLIST.md) | ⚠ stale | Platform-wide delivery checklist |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | ⚠ stale | Written for the `nyxus-rc-2026-07-15` release candidate |

## Structural docs

| Doc | State | What it is |
|---|---|---|
| [`overview/system-overview.md`](overview/system-overview.md) | ✅ current (2026-07-30) | What NYXUS is, what NYX is, what the repo contains |
| [`overview/creator.md`](overview/creator.md) | ✅ current | Creator and authorship context |
| [`architecture/architecture-overview.md`](architecture/architecture-overview.md) | ✅ current | Component boundaries and responsibility model |
| [`architecture/repository-structure.md`](architecture/repository-structure.md) | ✅ current | Workspace and directory structure |
| [`architecture/live-build-notes.md`](architecture/live-build-notes.md) | ⚠ stale | Hard-won runtime constraints for the live Hyprland/EWW desktop, consolidated from session memory |
| [`deployment/build-pipeline.md`](deployment/build-pipeline.md) | ⚠ stale | Workspace build/typecheck flow. Its `dist/` expectations no longer match the bake |
| [`deployment/iso-build.md`](deployment/iso-build.md) | ⚠ stale | Superseded by [`../iso-builder/README.md`](../iso-builder/README.md) |
| [`deployment/web-and-api-deployment.md`](deployment/web-and-api-deployment.md) | ⚠ stale | API/web deployment. **The Replit host it targets is retired** |

## Dated session briefs — the record of how we got here

Newest first. These are 🕓 by nature: each was true when written, and later
entries in `HANDOFF.md` supersede them. Read them for *why* a decision was made,
not for current state.

| Brief | Subject |
|---|---|
| [`PICKUP_BRIEF_2026-07-28.md`](PICKUP_BRIEF_2026-07-28.md) | **The installer bug solved** (calamares is a `[blackarch]` binary, not an AUR build — four ISOs failed on the wrong premise), the blind EDR, the traps that cost hours |
| [`PROJECT_INVENTORY_2026-07-28.md`](PROJECT_INVENTORY_2026-07-28.md) | 47 GitHub repos + local checkouts cross-referenced against what ships. Advisory only, nothing deleted |
| [`STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md`](STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md) | Six stations; the vault consoles are real apps; **a real security fix** (six console backends were listening on `0.0.0.0`) |
| [`SECURITY_INVENTORY_2026-07-27.md`](SECURITY_INVENTORY_2026-07-27.md) | Arsenal / modes / GodsApp / Intel / Vault / BlackArch inventory |
| [`HOME_AND_START_STATIONS_BRIEF_2026-07-27.md`](HOME_AND_START_STATIONS_BRIEF_2026-07-27.md) | HOME and START as eww decks on their own stations; the eww traps that cost real time (a window is sized to its **content**; `:focusable true` is a keyboard grab) |
| [`BARS_AND_LOGIN_BRIEF_2026-07-26.md`](BARS_AND_LOGIN_BRIEF_2026-07-26.md) | The "no login screen" bug killed at source; bars redesigned at the owner's request |
| [`EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](EWW_CHROME_REVERT_BRIEF_2026-07-26.md) | 🧊 The chrome night that was **fully reverted**. Do not re-land `ecdcc952` / `c73caae0` / `0bf2d06c` |
| [`LIVE_BOOT_AUDIT_2026-07-25.md`](LIVE_BOOT_AUDIT_2026-07-25.md) | Live-USB report + full sweep |
| [`ALIEN_NEON_SETTINGS_BRIEF.md`](ALIEN_NEON_SETTINGS_BRIEF.md) | **Entry point** for the ALIEN NEON + Settings workstream (phases, stay-as-is list, progress log) |
| [`ALIEN_NEON_SETTINGS_AUDIT.md`](ALIEN_NEON_SETTINGS_AUDIT.md) | 🧊 Counted checklist of unthemed surfaces / thin Settings pages. **Deliberately names purged palettes as history** |
| [`PRE_BAKE_CLEANUP_AND_SETTINGS.md`](PRE_BAKE_CLEANUP_AND_SETTINGS.md) | Pre-bake cleanup roadmap + the **owner-confirm deletion list**. ⛔ Do **not** delete the `nyxus-recovery-*` / `sddm-themes` cluster — it is live via the shipped `pam.d/sddm-recovery-snippet` |
| [`DEEP_BUILD_AUDIT_2026-07-24.md`](DEEP_BUILD_AUDIT_2026-07-24.md) | Deep consistency audit (lockstep, palette, keybinds, profiledef) |
| [`BUILD_DAY_BRIEF_2026-07-24.md`](BUILD_DAY_BRIEF_2026-07-24.md) | The Jul 23–24 build day: story, timeline, done/open |
| [`NYXUS_BUILD_BRIEF.md`](NYXUS_BUILD_BRIEF.md) · [`NYXUS_BUILD.md`](NYXUS_BUILD.md) · [`NYXUS_STATUS.md`](NYXUS_STATUS.md) | 🧊 Earlier build/status narratives |
| [`PHASE7_HUB_SPEC.md`](PHASE7_HUB_SPEC.md) · [`phase3-eww-handoff.md`](phase3-eww-handoff.md) | 🧊 Phase-era specs, kept for design intent |

## Historical reference — do not "fix" these

| Doc | Why it stays wrong on purpose |
|---|---|
| [`legacy-visuals.md`](legacy-visuals.md) | 🧊 The superseded visual specifications. It documents the cream / gold / DARK MIRROR / OBSIDIAN PRISM palettes **as history**. Rewriting it to ALIEN NEON would destroy the only record of what was banned and why |

## The palette, in one place

Canonical **ALIEN NEON**, preset `prism` (`accent.json` — one preset only, eight
older ones deleted 2026-07-23; `follow_wallpaper: false`):

| Slot | Hex |
|---|---|
| primary (violet) | `#7d3dff` |
| secondary (magenta) | `#ff2dad` |
| ok (neon green) | `#39ff14` |
| warn (orange) | `#ff8a1e` |
| fixed cyan / red / yellow / orchid | `#2bd2ff` · `#ff2d55` · `#ffe600` · `#e367ff` |
| text (`WHITE_OFF`) | `#eef2fa` |
| void | `#05060a` |

**Banned:** cream `#f4ead5`, gold `#d4b87a`, old violet `#a06bff`, old cyan
`#3ad8ff`, and the wallpaper-drift set. Machine-readable canon:
`nyxus_palette.py` (`FORBIDDEN` tuple) and `accent.json`. Full list in
[`DESIGN_CONTRACT.md` §4](DESIGN_CONTRACT.md).

## Terminology Contract

- **NYX** = ISO image only
- **NYXUS** = OS/platform/application ecosystem

This naming is enforced throughout repository documentation.

---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

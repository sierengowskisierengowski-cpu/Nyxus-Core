# NyXxOS / Nyxus-Core — Status

> **Last updated:** 2026-06-10
>
> This document is a ground-truth snapshot of what is real and verifiable
> in this repository today, what is partially wired, and what remains
> planned. It is intentionally conservative: if something has not been
> confirmed in a live boot or a passing CI run it is marked accordingly.

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
| archiso profile definition (`profiledef.sh`) | ✅ | Uses modern `bios.syslinux` + `uefi.grub` bootmodes |
| Package list (`packages.x86_64`) | ✅ | greetd, tuigreet present; sddm excluded from ISO packages |
| Display manager — greetd + tuigreet | ✅ | `config.toml` boots `Hyprland` for the `nyx` user |
| Hyprland Lua config staging | ✅ | `/etc/skel/.config/hypr/hyprland.lua` + `conf.d` shards in place |
| File permission locking (`profiledef.sh`) | ✅ | All `nyxus-*` binaries and helpers locked at `0755` |
| ISO bake (`build-iso.sh`) | 🟡 | Requires Arch Linux host + root + `mkarchiso`; not runnable in CI |
| Calamares installer branding | 🟡 | Profile files and settings present; Calamares built from AUR in `customize_airootfs.sh`, not from `packages.x86_64` |
| SDDM login theme | 🟡 | QML theme is present in `nyxus-scripts`; live ISO uses greetd, not SDDM |
| Live-session passwordless sudo drop-in | ✅ | `/etc/sudoers.d/10-nyxus-live` staged and permission-locked |

---

## API & Web Distribution

| Item | Status | Notes |
|------|--------|-------|
| API server (`artifacts/api-server`) | ✅ | Builds and typechecks; download routes present |
| Download API (`/api/download/nyxus/:filename`) | ✅ | Allowlist covers scripts, wallpapers, and docs |
| Crash-report upload endpoint | ✅ | `routes/crash-reports.ts` POST `/api/crash-reports` with quota GC |
| Web surfaces (`nyxus-web`, `nyxus-notepad`, `nyxus-stickies`, `nyxus-sysmon`, `nyxus-widgets`) | ✅ | Vite builds pass; runtime requires a deployment target |
| Mockup sandbox (`mockup-sandbox`) | ✅ | Preview environment builds |

---

## Desktop Runtime (requires live ISO boot on real hardware)

| Item | Status | Notes |
|------|--------|-------|
| Hyprland session startup | 🟡 | Config staged and validated; live-boot required for end-to-end test |
| EWW bars (top + bottom) | 🟡 | Yuck/SCSS validated; live-boot required |
| GTK4 Python app suite (12 apps) | 🟡 | Source present in `nyxus-scripts`; Python syntax validated; live-boot required for functional test |
| nyxus-bootstrap first-boot flow | 🟡 | Script present and permission-locked; end-to-end test requires live ISO |
| NYXUS Settings (all 8+ pages) | 🟡 | Source complete per `MASTER_CHECKLIST`; live-boot required |
| Notification center (swaync) | 🟡 | Source present; live-boot required |
| Quick Settings / Control Center | 🟡 | Source present; live-boot required |
| Hyprlock lock screen | 🟡 | Config staged; live-boot required |
| Rofi launcher | 🟡 | Config staged; live-boot required |
| Dunst / Mako notifications | 🟡 | Config staged; live-boot required |
| Alacritty terminal config | 🟡 | Config staged; live-boot required |
| Wlogout logout screen | 🟡 | Config staged; live-boot required |
| Waybar | 🟡 | Config staged; live-boot required |
| NYXUS icon theme (31 custom SVGs) | 🟡 | Assets present; live-boot required |
| NYXUS cursor theme (Hyprcursor + XCursor) | 🟡 | Assets present; live-boot required |
| Wallpaper pack (92 backgrounds) | 🟡 | Assets present; auto-mirror to SDDM/lockscreen requires live-boot |
| Hot corners | 🟡 | `nyxus_hotcorners.py` present; live-boot required |
| Night light (gammastep) | 🟡 | Wrapper present; live-boot required |
| Dynamic wallpaper rotator | 🟡 | Script present; live-boot required |
| Game Mode / Focus Mode | 🟡 | Source present; live-boot required |

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

---

## Open Pull Requests

| PR | Title | State |
|----|-------|-------|
| [#42](https://github.com/sierengowskisierengowski-cpu/Nyxus-Core/pull/42) | Copilot/resolve merge conflicts config toml packages | Open — merge conflicts resolved by Copilot in commit `4c8b7f4`; ready for owner review and merge |

---

© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED

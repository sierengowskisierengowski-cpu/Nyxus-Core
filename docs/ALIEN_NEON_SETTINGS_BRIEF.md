# ALIEN NEON + Settings — START HERE (next agent)

> **Owner direction locked 2026-07-24.** Read this before touching theme or Settings.
> Master checklist (counts + full lists): [`ALIEN_NEON_SETTINGS_AUDIT.md`](./ALIEN_NEON_SETTINGS_AUDIT.md)
> Also read [`HANDOFF.md`](../HANDOFF.md) § theme/settings workstream.

---

## Where we start (do not skip)

**Phase 1 — Foundation (DONE on branch `cursor/audit-stay-as-is-scope-92cd`):**

1. ~~`nyxus_palette.py` (+ skel / live mirrors)~~ ✅
   - Full ALIEN NEON canon (include **void `#05060a`** + **orchid `#e367ff`**)
   - Brand string **ALIEN NEON** (kill **DARK MIRROR**)
   - Kill gold `#d4b87a`; `_ACCENT_FALLBACK` = prism; HUD void/green aligned
2. ~~`nyxus_settings.py` (repo + skel lockstep)~~ ✅
   - CSS / chrome → ALIEN NEON
   - Theme Packs page → **prism-only**
   - User-visible “DARK MIRROR” strings replaced; APP_REV `2026.07.24-r11`
3. Launcher `/usr/local/bin/nyxus-settings` comment updated (still execs `nyxus_settings.py`)

**Then Phase 2 — Cascade shell GTK apps** (Home, Panel, Start, Terminal, Control, Store, …) ← **START HERE next**.  
**Then Phase 3 — Deepen EMPTY/MINIMAL Settings pages** (`vpn` first).  
**Then Phase 4 — Add Settings sections only for shell must-haves** (live wallpaper, eww, Hyprland, hyprlock, screensaver, Hacker/Ghost/Panic controls).  
**Not a theme phase:** Bifrost / GodsApp / Meli / Arsenal (see below).

---

## ⛔ Stay as-is (do NOT theme, do NOT add Settings sections for)

| Leave alone | Notes |
|---|---|
| Bifrost | Own UI |
| GodsApp | Own UI |
| Meli | Own UI |
| Arsenal / security lab | CIPHER, Forge, RedForge, GSL, Trainer, AXIOM, Ghost-Relay c2, Shield, Security Center |
| Lab tooling | HoneyHive, Grafana, Prometheus, APEX, GowskiNet flip/FORGE helpers, jeTT restyle |

If an audit row lists these under “not ALIEN NEON” or “no Settings section”, that is **informational only** — not a todo.

---

## In scope (shell / system)

Settings hub, Home/Main Page, Panel, Start, Terminal, Stickies, Notes, Notepad, Launcher/Spotlight, Store, Chrome Library, Control, SysMon, Welcome, Wallpaper Studio, Screensaver, Screenshot, Clipboard, Account, Backup, Drop, Toast, Updater, Power/Battery helpers, eww / greeter / hyprlock chrome, Theme Packs → prism-only.

---

## Already done (do not re-diagnose)

| Item | Status |
|---|---|
| ALIEN NEON locked in `accent.json` (prism-only, follow_wallpaper off) | Done on `main` |
| Desktop Hyprland / walls / GRUB dragon → ALIEN NEON | Done in repo; stick needs bake with current `main` |
| PR #71 eww delay / black-box / stamp fixes | On `main` via #72 (`0f866221`) — needs **rebake** |
| W1 `profiledef` file_permissions regen | On `main` (`09fef7bb`) |
| W6 arsenal/reactive bake shard wipe fix | On `main` (`09fef7bb`) |
| Stay-as-is carve-out documented | This brief + audit §0 |
| Full counts checklist | `docs/ALIEN_NEON_SETTINGS_AUDIT.md` |
| **Phase 1** palette + Settings chrome + Theme Packs prism-only | Done on `cursor/audit-stay-as-is-scope-92cd` (merge to main) |
| Kage-Ryu live iso9660 | **Still blocker** until owner `makepkg` finishes + verify + rebake |

---

## Rules so we don’t redo / overlook

1. **Checklist is canonical for this workstream:** update checkboxes in
   `ALIEN_NEON_SETTINGS_AUDIT.md` when an item lands (don’t only claim it in chat).
2. **Keep trees in lockstep:** `artifacts/api-server/nyxus-scripts/` ↔
   `iso-builder/nyx-profile/airootfs/etc/skel/.nyxus/` (and any
   `usr/local/bin` launcher). Bake **wipes** skel hypr from NS — see HANDOFF W6.
3. **Live `~/.nyxus` ≠ always repo.** Owner’s live settings sha differed from repo;
   prefer editing **repo** sources, then sync live only if owner asks.
4. **Don’t bake mid-edit.** Commit idle repo first. Don’t flash the old
   `nyxus-2026.07.24` expecting #71 / theme-app fixes.
5. **Update HANDOFF** the moment status changes (phase done, blocker cleared, scope change).

---

## Progress log (append, don’t rewrite history)

| Date | What | Commit / note |
|---|---|---|
| 2026-07-24 | Audit + stay-as-is carve-out | `docs/ALIEN_NEON_SETTINGS_AUDIT.md`; branch `cursor/audit-stay-as-is-scope-92cd` |
| 2026-07-24 | This brief added — Phase 1 = start | (this file) |
| 2026-07-24 | **Phase 1 DONE** — palette ALIEN NEON + Settings chrome + Theme Packs prism-only; mirrors synced | branch `cursor/audit-stay-as-is-scope-92cd` |
| 2026-07-24 | **Settings polish pass 1** — Welcome rewired (real marker + skip steps); kill Logo source / path dumps on Welcome/Login/Plymouth/Sounds/Language; VPN file-picker import; wizard honors skip prefs | same branch |

*Next: continue Settings page polish (remaining PARTIAL/MINIMAL) + Phase 2 shell GTK cascade. Tick audit rows as you go.*

# Nyxus Build Brief

**Status:** Draft v1 — living document, update as work is completed
**Owner:** you
**Target repo:** `nyxus-core` (single source of truth on GitHub)

---

## 0. Vision

Nyxus is a custom Hyprland desktop build (custom ISO + custom kernel) meant to become your daily driver alongside COSMIC. The build should be:

- **Consolidated** — one repo, one source of truth, nothing scattered across old agent sessions/projects
- **Clean** — no dead files, no duplicate configs, no old/broken themes lying around
- **Stable** — every menu, flyout, and session path actually works
- **Cohesive** — one consistent visual theme across every surface (bars, hub, menus, backgrounds)
- **Premium** — high-polish "eye candy" UI, not stock Hyprland rice
- **Installable** — bootstrap script so it can be installed from a terminal like a real distro/build
- **Version-controlled** — safepoints committed and pushed as work progresses, so nothing is ever lost or unrecoverable

---

## 1. Current State & Known Problems

### 1.1 Session / login issues
- [ ] Login screen currently falls back to an **old, broken Hyprland login screen** instead of the working one
- [ ] Have to TTY in and manually run `Hyprland` to start a session
- [ ] Previously, login went through the **COSMIC greeter**, letting you choose Hyprland or COSMIC — that choice is currently gone/broken
- [ ] **Display manager status:** SDDM is believed to be installed/taking over, but there is **no greeter configured** — this is the likely root cause of the login screen not showing up / falling back to the broken screen
- [ ] Treat this as: **build a fresh, working greeter/login from scratch** for Nyxus rather than trying to patch the old broken one — install and configure a proper SDDM theme (or confirm SDDM vs. an alternative like greetd/ly) with both Hyprland and COSMIC selectable as sessions
- [ ] Remove the old broken Hyprland login theme entirely — it should not exist as a file, an option, or a fallback
- [ ] New login screen should follow the Nyxus theme (§3) once built

> **Note (added 2026-07-14):** A previously-orphaned local checkout of this repo (`GowskiNet-Vault/OS/Nyxus-Core`, since deleted) had an uncommitted **regreet-based greeter variant** (`regreet.toml`, `regreet.css`, `nyxus-eye.png`, custom `greetd/config.toml`) dated 2026-07-09 — an earlier attempt that predates the current SDDM path. It's fully preserved on GitHub at branch **`archive/vault-uncommitted-wip`**. Review it when starting Phase 2 to see if anything from that attempt is worth reusing before committing to SDDM.

### 1.2 File sprawl
- [ ] Build files currently scattered across multiple tools/sessions (Cursor, Claude, Replit) and multiple project folders (`sharkdash`, `bifrost`, others not yet identified)
- [ ] Need a **full audit of the local machine** to find every file that belongs to this build
- [ ] Everything that is actually part of the running build gets moved into `nyxus-core`
- [ ] Everything else (old experiments, superseded themes, dead configs) gets removed — not archived-in-place, not left "just in case" cluttering the system
- [ ] No file should exist outside `nyxus-core` unless it's a system-level file that has to live elsewhere (e.g. `/boot`, `/etc`) — and even those should be referenced/tracked from the repo (symlinked or documented)

### 1.3 ISO & kernel
- [ ] Audit the custom ISO build process — confirm it's current, reproducible, and free of leftover cruft
- [ ] Audit the custom kernel config/build — confirm it's in "best shape possible" (no stale patches, no unused config flags, documented build steps)

### 1.4 Broken UI elements
- [ ] Go through **every** menu, flyout, and settings panel in the current Hyprland session
- [ ] Identify which ones don't open, glitch, or freeze
- [ ] Fix wiring for all of them — nothing ships half-working

---

## 2. Consolidation Plan

1. Inventory pass: find every Nyxus-related file/folder on the machine
2. Classify each: **keep (active)** / **merge (duplicate of something already kept)** / **delete (dead/old)**
3. Move all "keep" items into `nyxus-core` with a sane folder structure (suggest: `hypr/`, `eww/`, `theme/`, `iso/`, `kernel/`, `scripts/`, `docs/`)
4. Delete everything not moved
5. Commit as a safepoint (see §7) once the repo reflects the real, current build

---

## 3. Visual Theme & Design Language

**Reference:** current wallpaper (galaxy/nebula, deep purple-blue with pink/magenta accent text) and current bar styling.

- Base palette: deep space black background, pink/magenta + purple accent (matches current bars/hub)
- The current wallpaper is the **single background reference for the entire build** — not just the desktop, but every Nyxus surface (Hub, menus, login screen, etc.) should draw from it
- Theme must be **consistent across every surface**, explicitly including:
  - the top ticker/stats bar
  - the two side bars ("floating islands")
  - the bottom bar
  - the Hub
  - every menu/settings panel
  - login/lock screen
  - **every custom Nyxus app built inside this build, going forward** — nothing new gets added off-theme
- Additional visual motif to add throughout: a **twinkling starfield effect** (like a Rolls-Royce starlight headliner) — subtle animated stars/twinkle layered into backgrounds of menus, the Hub, settings panels, etc.
- Doesn't have to be literal stars/planets everywhere — the standard is "eye candy and stunning," starfield is one recurring motif, not the only one
- Everything (existing and new) gets re-themed to match going forward — no exceptions, no leftover old-build styling anywhere

---

## 4. EWW Bars (4 bars total)

Current layout is roughly right; keep the structure, upgrade the content:

- [ ] **Fans/system module (left side):** currently plain text (`FAN1 7741 FAN2 8000`) → redesign as a live graph, add **temp** readout, add **CPU** and **GPU** live graphs (matching theme)
- [ ] **Network module (right side):** currently plain text (`ETH ↑222B ↓402B`) → redesign as a live graph in the same style
- [ ] Keep existing top bar system stats (mem, wifi, load, disk, cpu, kernel, uptime, users, procs) but confirm styling matches the new theme once other modules are redone
- [ ] All graphs should feel like one consistent "high-end monitoring" visual language, not mismatched widgets

> **Note (added 2026-07-14):** A previously-orphaned local checkout (`GowskiNet-Vault/OS/Nyxus-Core`, since deleted) had 48 unmerged EWW/HUD redesign commits never pushed to GitHub until now — "gem-vial pill redesign," "Starlight Headliner bars," four-bar cohesion pass, etc. Fully preserved on GitHub at branch **`archive/vault-bars-signature-redesign`**. Review when starting Phase 6 (§ below) to see if any of that redesign work should be cherry-picked or referenced instead of redoing it from scratch.

---

## 5. Center Widget: "Nyxus" Clock/Date → The Hub

### 5.1 Default state
- Center-bottom widget currently shows "NYX…" + time + date, but looks unfinished/low detail
- Redesign to be a polished, high-detail centerpiece: clearly reads "Nyxus," plus time and date, styled to match the rest of the theme (this is meant to be a flagship visual element)

### 5.2 Click behavior → "The Hub"
- Clicking it opens **The Hub** (rename current "Nyxus Main Hub" popup to just **The Hub**)
- Redesign the Hub to high polish — this is called out as one of the signature features of the build, so it should be the most refined surface in the whole UI
- Keep the existing categories (Connect: wifi/bluetooth/alerts/quick settings; Sound: vol/mic; Display: brightness/display settings; System: dashboard, deep clean, mission control, updates, settings, keyboard; Stations shortcuts; Power: lock/logout/power)
- [ ] Add an **app launcher area inside the Hub** — a way to browse/launch apps from within the Hub itself, as an alternative to the keybind launcher
- Add anything else useful/important you'd want at-a-glance access to (open item — flag specific additions as they come up)
- Everything in the Hub must actually function — no dead buttons

### 5.3 Music mode (new feature)
- [ ] When music is playing, the center widget transforms from the Nyxus clock into a **music visualizer/now-playing graph**: track info (who/what's playing), elapsed/duration, live audio graph
- [ ] When music stops, it reverts back to the Nyxus clock/date view
- [ ] **Source:** needs to be source-agnostic — should pick up whatever is currently playing regardless of app (YouTube in browser, Spotify, local downloaded files). This points to building on **MPRIS/`playerctl`**, since browsers (YouTube), Spotify, and most local players (mpd, vlc, etc.) all expose MPRIS — confirm your local player of choice supports it, or pick one that does

---

## 6. Keybinds & Terminal

Leftover conflicts from different build passes need to be found and resolved — same problem as the file sprawl, just in the keybind config.

- [ ] **Duplicate app launcher binds:** `Super+R` and `Super+Spacebar` both currently open an app launcher — leftovers from two different build iterations. Pick **one** and remove the other bind (or repurpose the freed key for something else)
- [ ] **Broken terminal:** the terminal keybind currently opens a "Cosmic Terminal" that an agent built, which doesn't work — and COSMIC terminal doesn't belong in a Hyprland session anyway. Fix: bind to a working terminal (name can stay "Cosmic Terminal" if you like the name, or rename it — either way it must actually work)
- [ ] **Full keybind audit:** go through every keybind in the config and check for duplicates, dead binds, or binds pointing at broken/removed apps — consolidate to one clean, documented keybind set
- [ ] Document the final keybind list somewhere in the repo (e.g. `docs/KEYBINDS.md`) so it's not just tribal knowledge

---

## 7. Installation / Bootstrap

- [ ] Build a bootstrap/install script so Nyxus can be installed from a terminal (clone repo → run installer → get a working system), similar to how dotfile "rices" or minimal distros are usually installed
- [ ] Script should handle dependencies, config placement, and any needed system setup steps
- [ ] Document usage in the repo README

---

## 8. Version Control Workflow

- [ ] Every meaningful change gets committed
- [ ] Establish "safepoints" — stable, working states get tagged or branched (e.g. `git tag safepoint-YYYY-MM-DD` or a `stable` branch) so you can always roll back if something breaks
- [ ] Push regularly so nothing is only local
- [ ] Suggest a lightweight convention: commit early/often on a working branch, tag/merge to `main` only when a change is confirmed stable

---

## 9. Premium / Rich Features (open list)

Placeholder section — add specific ideas here as they come up. Known so far:
- High-end live graphing bars (§4)
- Polished Hub control center (§5.2)
- Music-reactive center widget (§5.3)
- Starfield/eye-candy motif throughout (§3)

### Deferred / out-of-scope cleanup (not part of this build)

- **Other GitHub projects with multiple un-synced local copies** — the 2026-07-14 file-sprawl audit for Nyxus also turned up several *other*, unrelated GitHub projects with multiple out-of-sync local checkouts on this machine (at least `Bifrost`, `GodsApp`, `Meli`, and a few under `GowskiNet-Vault/Security/Cyber/`). These are **not part of the Nyxus build** and were deliberately left untouched. Flagging here as a candidate for a separate future cleanup pass, using the same compare-before-trusting-any-copy approach as §1.1a below.

---

## 10. Open Questions / Decisions Needed

Resolved:
- ~~Display manager~~ → SDDM believed installed, no greeter configured — building fresh (§1.1)
- ~~Music source~~ → source-agnostic via MPRIS/playerctl (§5.3)
- ~~Theme scope~~ → covers ticker, side bars, bottom bar, background, Hub, all custom Nyxus apps (§3)
- ~~App launcher duplication~~ → `Super+R` vs `Super+Space`, pick one (§6)
- ~~Terminal~~ → fix or replace the non-functional Cosmic Terminal bind (§6)

Still open:
1. Any specific apps/shortcuts you want pinned in the Hub beyond what's already there, besides the new app-launcher area?
2. Do you want the ISO/kernel audit done before or in parallel with the UI/theme work?
3. Preferred safepoint convention — tags vs. a dedicated `stable` branch?
4. Which key should keep the app launcher bind — `Super+R` or `Super+Space` — and should the freed key be reused for something else?

---

## 11. Master Build Checklist

**Rules for whoever (or whichever agent) is working from this brief:**
- Work the list **in order, top to bottom.** Don't skip ahead to something more interesting.
- Check off an item only when it's actually done and verified working in the live Hyprland session — not just written.
- New ideas that come up mid-build get added to §9 (Premium Features) or §10 (Open Questions) — they do **not** get inserted into the active work, to avoid scope creep.
- Commit a git safepoint after each numbered phase below, not just at the very end (§8).
- This checklist is the one to keep updated as the single source of truth for progress — update it in place as boxes get checked.

### Phase 1 — Get to one clean, working system
- [x] 1.1 Full file audit — locate every Nyxus-related file/folder on the machine (§1.2)
- [x] 1.1a **Check for multiple local copies of the same project before trusting any single source (including GitHub) as "current."** — Found 4 local copies of `Nyxus-Core` + GitHub. Canonical (`~/Nyxus-Core`) confirmed authoritative (superset of GitHub `main`, most current). Vault copy had real unmerged work (48-commit EWW redesign, 189-commit Replit-era history, uncommitted regreet greeter variant) — all archived to GitHub (`archive/vault-*` branches, see notes under §1.1 and §4) before deletion. Two stale May-23 backup clones confirmed as pure duplicates with zero unique content, deleted. *(Other non-Nyxus GitHub projects with multiple copies — see §9 deferred list.)*
- [x] 1.2 Classify each file: keep / merge / delete (§2)
- [x] 1.2a **Commit everything to git as-is before deleting anything** — pre-cleanup safepoint commit `c1410f4` made and pushed before any deletions.
- [x] 1.2b **Check repo visibility (private/public) before committing anything sensitive.** — Confirmed **`sierengowskisierengowski-cpu/Nyxus-Core` is PUBLIC.** `NYXUS_VEIL_BRAINDUMP.md` (marked EYES ONLY) and any similarly sensitive notes must stay out of this repo entirely.
- [x] 1.3 Move all "keep" files into `nyxus-core` with organized folder structure — the six Claude agent-memory design notes (theme spec, typography, EWW bar constraints, living-wallpaper FX layer, addon status) consolidated into `docs/architecture/live-build-notes.md`.
- [x] 1.4 Delete everything not moved into the repo — content-checked before deletion (per §1.1a discipline): dead GTK theme and an orphaned stale `nyxus_settings.py` deleted; GOLD snapshots, config backups, and dev screenshots deliberately **kept** (real, recent recovery value while the build is mid-repair, not stale cruft); `/opt/nyxus*` reclassified from the original audit's "dead" call to **live** after verification (dock/hotkey/mission-control/quick-settings/snap daemons all exec from there) — only the one broken `/opt/nyxus-cache` symlink is dead, awaiting a manual `sudo rm` (needs root).
- [x] 1.5 Git safepoint: "consolidated build state" — tag `phase-1-complete-2026-07-14`

### Phase 2 — Reliable boot & login
- [ ] 2.1 Confirm/install proper display manager + greeter (§1.1) — *review `archive/vault-uncommitted-wip` regreet variant first, see note under §1.1*
- [ ] 2.2 Build fresh login screen (no old broken Hyprland login left anywhere)
- [ ] 2.3 Confirm both Hyprland and COSMIC are selectable sessions at login
- [ ] 2.4 Verify: reboot and log in normally, no TTY workaround needed
- [ ] 2.5 Git safepoint: "working login"

### Phase 3 — Fix what's broken in the running session
- [ ] 3.1 Go through every menu/flyout/settings panel, list what's broken (§1.4)
- [ ] 3.2 Fix each one, verify it opens/works without freezing
- [ ] 3.3 Resolve keybind duplicates (`Super+R` vs `Super+Space`) (§6)
- [ ] 3.4 Fix or replace the non-working terminal bind (§6)
- [ ] 3.5 Full keybind audit + document final list in `docs/KEYBINDS.md`
- [ ] 3.6 Git safepoint: "stable, de-duplicated session"

### Phase 4 — ISO & kernel audit
- [ ] 4.1 Review custom ISO build process, remove cruft, confirm reproducible
- [ ] 4.2 Review custom kernel config/build, remove stale patches/unused flags
- [ ] 4.3 Git safepoint: "clean ISO/kernel"

### Phase 5 — Theme pass
- [ ] 5.1 Define the shared theme tokens (colors, fonts, effects) in one place in the repo
- [ ] 5.2 Apply to top ticker, side bars, bottom bar (§3)
- [ ] 5.3 Apply to login/lock screen
- [ ] 5.4 Apply to all menus/settings panels
- [ ] 5.5 Add starfield/twinkle motif where it fits
- [ ] 5.6 Git safepoint: "unified theme v1"

### Phase 6 — EWW bars upgrade
- [ ] 6.1 Redesign fan/temp module as live graph, add CPU + GPU graphs — *review `archive/vault-bars-signature-redesign` first, see note under §4*
- [ ] 6.2 Redesign network module as live graph
- [ ] 6.3 Confirm all bar modules match theme from Phase 5
- [ ] 6.4 Git safepoint: "bars v2"

### Phase 7 — Center widget + The Hub
- [ ] 7.1 Redesign the Nyxus clock/date center widget
- [ ] 7.2 Rename popup to "The Hub," redesign to high polish
- [ ] 7.3 Add app-launcher area inside the Hub
- [ ] 7.4 Add any other useful quick-access items decided from §10
- [ ] 7.5 Build music mode (MPRIS-based now-playing view) on the center widget
- [ ] 7.6 Verify every Hub button/section actually works
- [ ] 7.7 Git safepoint: "Hub v1 + music mode"

### Phase 8 — Daily-driver readiness
- [ ] 8.1 Build bootstrap/install script (§7)
- [ ] 8.2 Write README + KEYBINDS.md + any other docs
- [ ] 8.3 Full end-to-end test: fresh boot → login → daily use, no crashes/freezes
- [ ] 8.4 Git safepoint / tag: "Nyxus v1.0 — daily driver ready"

---

## Appendix: Archive branches (GitHub)

Preserved history from a deleted local checkout (`GowskiNet-Vault/OS/Nyxus-Core`) that was never pushed anywhere before 2026-07-14. Kept on GitHub, not merged into `main` — review opportunistically at the phases noted above, don't let them get deleted or forgotten.

| Branch | Content | Relevant phase |
|---|---|---|
| `archive/vault-bars-signature-redesign` | 48 unmerged EWW/HUD redesign commits (gem-vial pills, Starlight Headliner bars, four-bar cohesion) | Phase 6 (§4) |
| `archive/vault-uncommitted-wip` | Uncommitted working-tree state incl. regreet-based greeter variant (`regreet.toml`/`.css`, custom `greetd/config.toml`) | Phase 2 (§1.1) |
| `archive/vault-main-replit-history` | Separate 189-commit Replit-agent development history, never merged to canonical `main` | Unscoped — historical reference only |
| `archive/vault-replit-agent` | Replit-agent branch, login-screen-related commits | Unscoped — historical reference only |
| `archive/vault-subrepl-4p8v69rp` | Pre-rebase snapshot branch from Replit sub-session | Unscoped — historical reference only |

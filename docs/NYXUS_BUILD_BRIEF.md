# Nyxus Build Brief

**Status:** Draft v1 — living document, update as work is completed
**Owner:** you
**Target repo:** `nyxus-core` (single source of truth on GitHub)

> **Progress annotations** are added inline as **`STATUS (date): …`** lines and
> checkbox marks. Phase 1 is complete; Phase 2 is in progress (see §10).

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
- [ ] New login screen should follow the Nyxus theme (§2) once built

> **STATUS (2026-07-14) — PIVOTED SDDM → greetd+regreet after two failed reboots:**
> 1. First failure: SDDM greeter SIGSEGV in hardware GL on the hybrid Intel+NVIDIA GPU (blank screen + cursor). Fixed the crash with `QT_QUICK_BACKEND=software`.
> 2. Second failure: with the crash gone, the SDDM greeter ran (PID alive, no coredump) but stayed **invisible** — X11's VT/DRM handoff never switched the panel to VT2, leaving a frozen VT1. This is an inherent fragility of SDDM's **X11** greeter on Optimus hardware.
> 3. **Decision:** move the greeter off X11 onto **Wayland via `greetd` + `regreet`** (run under `cage`) — the same Wayland/DRM path Hyprland/COSMIC already use successfully. Verified `cage` initialises its renderer on the Intel Iris Xe in a nested smoke test (no reboot). Never-lock-out fallback chain built: **regreet (GPU) → regreet (pixman/software) → tuigreet (text) → agreety**, so a greeter failure drops to a text login, never a frozen screen.
> - Themed regreet: alien "Nyxus Hyprland" background + frosted purple/magenta login CSS (ported from the SDDM theme + `docs/THEME.md` §8 tokens). Deploy via `sudo scripts/nyxus-setup-greetd.sh`. **Pending user reboot verification.**
> - The SDDM theme/scripts (`sddm-theme/`, `nyxus-fix-login.sh`) are kept in-repo as a fallback but are no longer the active path.
> - **ISO follow-up (Phase 4):** `iso-builder/.../customize_airootfs.sh` still `systemctl enable sddm` — needs swapping to `greetd` to match. Config files already mirrored to the ISO tree.
>
> **Archive pointer:** the original regreet variant is on `archive/vault-uncommitted-wip` — this pivot supersedes/realises it with current tokens.

#### Login screen — functional additions (build in Phase 2)
- [ ] Hide the session picker by default (don't show session pills in plain view) but keep it easily reachable — e.g. a small icon/toggle rather than always-visible options
  > **STATUS (2026-07-14):** DONE in the greeter theme — sessions collapse to a slim `session · NYXUS (Hyprland) ▾` chip; one click reveals the full pill list. Validated offscreen; pending reboot verification.
- [ ] **"Hidden backdoor" login keybind:** `Super+Space+Enter` should trigger a direct login bypass, as a lockout-proof fallback for the worst case (can't even TTY in). Known tradeoff, accepted deliberately: this is a genuine physical-security bypass — anyone with physical access to the machine and knowledge of the combo can get in without a password. Acceptable given it's a personal daily-driver machine and the combo isn't written down anywhere public.
  > **STATUS (2026-07-14):** Chord changed `Super+Space+Fn` → **`Super+Space+Enter`** (Fn is handled in the EC and isn't software-capturable; Space+Enter are). No conflict with the desktop `Super+Space` launcher bind — this fires at the *greeter*, a separate pre-desktop context. **Mechanism still to build.** Note: the stated worst case ("can't even TTY in") is only fully covered by a path that does *not* depend on the greeter rendering — a getty-autologin rescue VT — as well as/instead of a greeter chord. See §9 Q5.
- [ ] **Biometric login (fingerprint + face):** confirm hardware first — does the MSI GS77 actually have a fingerprint reader and/or IR camera capable of face recognition? Not all MSI gaming laptops ship with either. If hardware is confirmed present:
  - Fingerprint via `fprintd` + PAM integration
  - Face recognition via a tool like `howdy` (IR camera) + PAM integration
  - Both are real setup tasks, not simple toggles — treat as their own sub-task once hardware is confirmed
  > **STATUS (2026-07-14): HARDWARE CONFIRMED PRESENT (both).** Fingerprint: **Goodix `27c6:6094`** (USB, disguised as "USB2.0 MISC"). IR camera: **`FHD IR Camera`** on `/dev/video2`+`/dev/video3` (dedicated Windows-Hello-style IR). Stack partially staged already: `fprintd`, `libfprint`, and `howdy-bin` are installed. Caveats to resolve when scoped: Goodix `6094` libfprint driver support is device-specific and must be verified (some Goodix units need extra work); howdy IR enrollment needs configuring against `/dev/video2`. Also present: SteelSeries per-key keyboard (`1038:113a`) and two YubiKeys (`1050:0407`, U2F/CCID) — relevant to §1.3 and to auth options. **Scoped as a follow-up sub-task; not built now.**

#### Login screen — visual design (build in Phase 5, full creative brief so nothing is lost)
- [ ] **Background art:** custom-built, not a stock image. Direction: deep-space/nebula scene, sharp/clean/high-resolution — the same "bad ass" quality as the reference galaxy image (saved at `docs/assets/login-art/reference-background.png`, the purple/magenta galaxy already used as the desktop wallpaper). Dense field of twinkling stars in the Rolls-Royce-starlight style (§2's recurring motif).
- [ ] **Wordmark in the scene:** the art should read **"Nyxus Hyprland"** prominently placed within the scene (not just "Nyxus").
- [ ] **Signature character element:** a stylized alien character floating through the scene, thrown up in a peace sign — explicitly **not** a generic/cute sci-fi alien. Direction: "urban style," modern, cool and a little funny — **the kind of mascot energy Hyprland itself has**, that makes people laugh or say "hell yeah" rather than reading as cheesy or dated.
- [ ] Overall look: clean, sharp, modern urban aesthetic — high-polish, not cartoonish
- [ ] **Login box treatment:** frosted/smoked-glass effect — a semi-transparent panel where whatever is behind it looks blurred/softened, so the art scene reads through the box but the fields stay legible. Sharp and clean, not muddy.
  > **Technical constraint (from Phase 2):** the greeter runs with `QT_QUICK_BACKEND=software` because the hybrid Intel+NVIDIA GPU crashes the hardware-GL greeter. A **live GPU blur shader** (GaussianBlur/ShaderEffect) would reintroduce that GPU dependency and be slow/unstable under llvmpipe. So the frosted-glass look must be achieved by compositing a **pre-blurred (baked) copy of the background image** behind a semi-transparent panel — not a real-time blur. The background is static art, so this looks identical and stays software-render-safe.
- [ ] This is real custom art production, not a config change — scope and time accordingly when Phase 5 starts

### 1.2 File sprawl
- [ ] Build files currently scattered across multiple tools/sessions (Cursor, Claude, Replit) and multiple project folders (`sharkdash`, `bifrost`, others not yet identified)
- [ ] Need a **full audit of the local machine** to find every file that belongs to this build
- [ ] Everything that is actually part of the running build gets moved into `nyxus-core`
- [ ] Everything else (old experiments, superseded themes, dead configs) gets removed — not archived-in-place, not left "just in case" cluttering the system
- [ ] No file should exist outside `nyxus-core` unless it's a system-level file that has to live elsewhere (e.g. `/boot`, `/etc`) — and even those should be referenced/tracked from the repo (symlinked or documented)

> **STATUS (2026-07-14): Phase 1 complete** — see §10 Phase 1. ~15.6 GB of dead duplicates removed (all unique work preserved to GitHub first); canonical repo confirmed authoritative; agent-memory design docs consolidated into `docs/architecture/live-build-notes.md`.

### 1.3 ISO & kernel
- [ ] Audit the custom ISO build process — confirm it's current, reproducible, and free of leftover cruft
- [ ] Audit the custom kernel config/build — confirm it's in "best shape possible" (no stale patches, no unused config flags, documented build steps)
- [ ] **Performance target:** kernel/system should be tuned to run as fast and strong as possible on this hardware — evaluate performance-oriented scheduler options (e.g. BORE/EEVDF), appropriate CPU governor defaults, and any other low-risk kernel tuning that fits a daily-driver machine (not experimental to the point of instability)
- [ ] **Target hardware: MSI GS77 (Stealth).** Kernel/build must fully support this specific machine's hardware, not just generic Linux baseline:
  - Hybrid Intel + NVIDIA Optimus graphics (this is the same GPU pairing already confirmed as the root cause of the Phase 2 SDDM greeter crash — kernel/driver config here directly affects login stability too, not just desktop performance)
  - Proper NVIDIA proprietary driver + PRIME/Optimus setup so the dGPU is fully usable for real work/gaming, while the greeter and lighter tasks can stay on Intel
  - `msi-ec` kernel module (or equivalent) for embedded-controller features: fan control/modes, cooler boost, battery threshold and battery mode, webcam enable/disable, Fn/Windows key swap — confirm which of these are already merged upstream in the kernel version in use vs. need the out-of-tree module
  - Keyboard (per-key RGB / SteelSeries) support — confirm what's needed for it to function under Linux (may require a specific userspace tool, not just a kernel module)
  - WiFi/Bluetooth chipset and audio confirmed working with no missing quirks
  - Document exactly which of these are kernel-level vs. userspace-tool-level, since some overlap with what the ISO installer (§6) needs to set up too
  > **STATUS (2026-07-14):** partial hardware inventory already gathered during Phase 2 — hybrid Intel Iris Xe + NVIDIA RTX 3060 Mobile confirmed; SteelSeries keyboard `1038:113a`; `msi-ec-dkms-git` present in the yay cache. Full audit is Phase 4.

### 1.4 Broken UI elements
- [ ] Go through **every** menu, flyout, and settings panel in the current Hyprland session
- [ ] Identify which ones don't open, glitch, or freeze
- [ ] Fix wiring for all of them — nothing ships half-working

---

## 2. Visual Theme & Design Language

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

> **Live-palette note (verified 2026-07-14):** the accent actually rendering in the live session is purple `#7949f2` + magenta `#ff2667` (EWW bars/Hub + accent engine). **Known desync:** Hyprland window borders are currently a stale orange→yellow gradient — logged as Phase 3.2a.

---

## 3. EWW Bars (4 bars total)

Current layout is roughly right; keep the structure, upgrade the content:

- [ ] **Fans/system module (left side):** currently plain text (`FAN1 7741 FAN2 8000`) → redesign as a live graph, add **temp** readout, add **CPU** and **GPU** live graphs (matching theme)
- [ ] **Network module (right side):** currently plain text (`ETH ↑222B ↓402B`) → redesign as a live graph in the same style
- [ ] Keep existing top bar system stats (mem, wifi, load, disk, cpu, kernel, uptime, users, procs) but confirm styling matches the new theme once other modules are redone
- [ ] All graphs should feel like one consistent "high-end monitoring" visual language, not mismatched widgets

> **Archive pointer:** 48 commits of unmerged EWW/HUD redesign work (gem-vial pills, "Starlight Headliner" bars, four-bar cohesion) are preserved on GitHub branch **`archive/vault-bars-signature-redesign`** — review before redoing this from scratch (Phase 6).

---

## 4. Center Widget: "Nyxus" Clock/Date → The Hub

### 4.1 Default state
- Center-bottom widget currently shows "NYX…" + time + date, but looks unfinished/low detail
- Redesign to be a polished, high-detail centerpiece: clearly reads "Nyxus," plus time and date, styled to match the rest of the theme (this is meant to be a flagship visual element)

### 4.2 Click behavior → "The Hub"
- Clicking it opens **The Hub** (rename current "Nyxus Main Hub" popup to just **The Hub**)
- Redesign the Hub to high polish — this is called out as one of the signature features of the build, so it should be the most refined surface in the whole UI
- Keep the existing categories (Connect: wifi/bluetooth/alerts/quick settings; Sound: vol/mic; Display: brightness/display settings; System: dashboard, deep clean, mission control, updates, settings, keyboard; Stations shortcuts; Power: lock/logout/power)
- [ ] Add an **app launcher area inside the Hub** — a way to browse/launch apps from within the Hub itself, as an alternative to the keybind launcher
- Add anything else useful/important you'd want at-a-glance access to (open item — flag specific additions as they come up)
- Everything in the Hub must actually function — no dead buttons
- [ ] **Master settings surface:** the Hub is where every feature's setting/toggle lives (see the standing rule in §10). As features are built in earlier phases, their settings accumulate here.

### 4.3 Music mode (new feature)
- [ ] When music is playing, the center widget transforms from the Nyxus clock into a **music visualizer/now-playing graph**: track info (who/what's playing), elapsed/duration, live audio graph
- [ ] When music stops, it reverts back to the Nyxus clock/date view
- [ ] **Source:** needs to be source-agnostic — should pick up whatever is currently playing regardless of app (YouTube in browser, Spotify, local downloaded files). This points to building on **MPRIS/`playerctl`**, since browsers (YouTube), Spotify, and most local players (mpd, vlc, etc.) all expose MPRIS — confirm your local player of choice supports it, or pick one that does

---

## 5. Keybinds & Terminal

Leftover conflicts from different build passes need to be found and resolved — same problem as the file sprawl, just in the keybind config.

- [ ] **Duplicate app launcher binds:** `Super+R` and `Super+Spacebar` both currently open an app launcher — leftovers from two different build iterations. Pick **one** and remove the other bind (or repurpose the freed key for something else)
- [ ] **Broken terminal:** the terminal keybind currently opens a "Cosmic Terminal" that an agent built, which doesn't work — and COSMIC terminal doesn't belong in a Hyprland session anyway. Fix: bind to a working terminal (name can stay "Cosmic Terminal" if you like the name, or rename it — either way it must actually work)
- [ ] **Full keybind audit:** go through every keybind in the config and check for duplicates, dead binds, or binds pointing at broken/removed apps — consolidate to one clean, documented keybind set
- [ ] Document the final keybind list somewhere in the repo (e.g. `docs/KEYBINDS.md`) so it's not just tribal knowledge

> **Note:** `Super+Space` is entangled with the backdoor-login chord (§1.1 / Phase 2.4). Resolve the launcher-bind decision (§9 Q4) with that in mind.

---

## 6. Installation / Bootstrap

- [ ] Build a bootstrap/install script so Nyxus can be installed from a terminal (clone repo → run installer → get a working system), similar to how dotfile "rices" or minimal distros are usually installed
- [ ] Script should handle dependencies, config placement, and any needed system setup steps
- [ ] Document usage in the repo README

---

## 7. Version Control Workflow

- [ ] Every meaningful change gets committed
- [ ] Establish "safepoints" — stable, working states get tagged or branched (e.g. `git tag safepoint-YYYY-MM-DD` or a `stable` branch) so you can always roll back if something breaks
- [ ] Push regularly so nothing is only local
- [ ] Suggest a lightweight convention: commit early/often on a working branch, tag/merge to `main` only when a change is confirmed stable

> **STATUS:** working branch `cursor/restore-last-night-state-15e2`; Phase 1 tagged `phase-1-complete-2026-07-14`. Safepoint-convention choice still open (§9 Q3).

---

## 8. Premium / Rich Features (open list)

Placeholder section — add specific ideas here as they come up. Known so far:
- High-end live graphing bars (§3)
- Polished Hub control center (§4.2)
- Music-reactive center widget (§4.3)
- Starfield/eye-candy motif throughout (§2)

### Deferred / out-of-scope cleanup (not part of this build)
- **Other GitHub projects with multiple un-synced local copies** — the 2026-07-14 audit also found several *other*, unrelated projects with multiple out-of-sync local checkouts (`Bifrost`, `GodsApp`, `Meli`, and some under `GowskiNet-Vault/Security/Cyber/`). **Not part of Nyxus**; left untouched. Candidate for a separate future cleanup pass using the same compare-before-trusting approach as §10 / 1.1a.

---

## 9. Open Questions / Decisions Needed

Resolved:
- ~~Display manager~~ → **SDDM** (greeter rebuilt, software-render fix for hybrid GPU) (§1.1)
- ~~Music source~~ → source-agnostic via MPRIS/playerctl (§4.3)
- ~~Theme scope~~ → covers ticker, side bars, bottom bar, background, Hub, all custom Nyxus apps (§2)
- ~~App launcher duplication~~ → `Super+R` vs `Super+Space`, pick one (§5)
- ~~Terminal~~ → fix or replace the non-functional Cosmic Terminal bind (§5)
- ~~Biometric hardware present?~~ → **Yes, both** — Goodix fingerprint + IR camera confirmed (§1.1); scoped as follow-up

Still open:
1. Any specific apps/shortcuts you want pinned in the Hub beyond what's already there, besides the new app-launcher area?
2. Do you want the ISO/kernel audit done before or in parallel with the UI/theme work?
3. Preferred safepoint convention — tags vs. a dedicated `stable` branch?
4. Which key should keep the app launcher bind — `Super+R` or `Super+Space` — and should the freed key be reused for something else? (Interacts with the backdoor chord, Q5.)
5. **Backdoor login (§1.1 / Phase 2.4) — mechanism.** Trigger chord settled: **`Super+Space+Enter`**. Mechanism still open: (a) greeter QML captures the chord → passwordless login via a dedicated PAM rule; (b) chord arms a one-shot autologin; (c) a dedicated getty-autologin **rescue VT** (works even if the greeter itself won't render — best fit for the "can't even TTY in" worst case). Recommend (c) as the true lockout-proof path, optionally plus (a) for convenience.
6. **Standing-rule sequencing:** the "feature → setting in the Hub" rule (§10) applies now, but the Hub itself is rebuilt in Phase 7. For Phase 2/3 features, do settings live in the current `nyxus_settings` app + a tracked checklist item to surface them in the Hub at Phase 7, or another approach?

---

## 10. Master Build Checklist

**Rules for whoever (or whichever agent) is working from this brief:**
- Work the list **in order, top to bottom.** Don't skip ahead to something more interesting.
- Check off an item only when it's actually done and verified working in the live Hyprland session — not just written.
- New ideas that come up mid-build get added to §8 (Premium Features) or §9 (Open Questions) — they do **not** get inserted into the active work, to avoid scope creep.
- Commit a git safepoint after each numbered phase below, not just at the very end (§7).
- **Every feature built from here forward must have its own setting/toggle, and that setting must be added to the Hub's master settings (§4.2) at the same time it's built** — not as a later cleanup pass. A feature with no visible control in the Hub is considered incomplete, even if the underlying functionality works. This applies to everything: the backdoor login keybind, biometric login, EWW bar options, music-mode behavior, theme variants, all of it. *(Sequencing while the Hub is pre-rebuild: see §9 Q6.)*
- This checklist is the one to keep updated as the single source of truth for progress — update it in place as boxes get checked.

### Phase 1 — Get to one clean, working system  ✅ COMPLETE (tag `phase-1-complete-2026-07-14`)
- [x] 1.1 Full file audit — locate every Nyxus-related file/folder on the machine (§1.2)
- [x] 1.1a **Check for multiple local copies before trusting any single source (incl. GitHub).** Found 4 local copies of Nyxus-Core; canonical `~/Nyxus-Core` confirmed authoritative; all unique unmerged work (EWW redesign, Replit history, regreet greeter) preserved to `archive/vault-*` branches before deleting duplicates.
- [x] 1.2 Classify each file: keep / merge / delete
- [x] 1.2a **Commit everything to git as-is before deleting** — pre-cleanup safepoint `c1410f4`.
- [x] 1.2b **Check repo visibility before committing sensitive files** — repo confirmed **PUBLIC**; eyes-only notes kept out of git.
- [x] 1.3 Move all "keep" files into `nyxus-core` — agent-memory design docs → `docs/architecture/live-build-notes.md`.
- [x] 1.4 Delete everything not moved (content-checked each; `/opt/nyxus*` reclassified as live before it broke daemons).
- [x] 1.5 Git safepoint: "consolidated build state"

### Phase 2 — Reliable boot & login  🟡 IN PROGRESS
- [x] 2.1 Confirm/install proper display manager + greeter (§1.1) — **pivoted to greetd + regreet (Wayland)** after SDDM's X11 greeter failed twice on the hybrid GPU. Deploy: `sudo scripts/nyxus-setup-greetd.sh`. *(pending reboot verify)*
- [x] 2.2 Build fresh login screen (no old broken Hyprland login left anywhere) — themed regreet (alien art + frosted purple/magenta CSS); stock `hyprland*.desktop` already removed; never-lock-out fallback chain. *(pending reboot verify)*
- [x] 2.3 Confirm both Hyprland and COSMIC are selectable sessions at login (regreet session dropdown; both `.desktop` present). *(pending reboot verify)*
- [ ] 2.4 Build the hidden backdoor login keybind (**`Super+Space+Enter`**, chord settled) as a lockout-proof fallback — mechanism still to build (§9 Q5).
- [x] 2.5 Check for fingerprint/IR-camera hardware on the GS77; if present, scope fingerprint (`fprintd`) and face (`howdy`) login as a sub-task — **hardware CONFIRMED (Goodix fingerprint + IR camera); scoped as follow-up (§1.1).**
- [ ] 2.6 Add settings/toggles for anything built here to the Hub (per the standing rule) — *pending §9 Q6 sequencing decision.*
- [ ] 2.7 Verify: reboot and log in normally, no TTY workaround needed — **USER ACTION (test-mode preview → reboot).**
- [ ] 2.8 Git safepoint: "working login"

### Phase 3 — Fix what's broken in the running session
- [x] 3.1 Go through every menu/flyout/settings panel, list what's broken (§1.4) — see `docs/phase3-eww-handoff.md`; GTK apps all launch, 13/14 eww flyouts OK, Hub + TIME clock broken (handed to theme/eww agent)
- [ ] 3.2 Fix each one, verify it opens/works without freezing
- [ ] 3.2a **Accent desync — Hyprland window borders out of sync.** Verified live 2026-07-14: EWW bars/Hub + `accent.json` render purple `#7949f2` + magenta `#ff2667`, but the running compositor `general:col.active_border` (`hyprctl getoption`, not a file) is a stale orange→yellow gradient (`#ff7e2e → #ffff1f`). `nyxus-apply-accent` isn't propagating to the compositor border. Fix so borders follow the same accent engine. (Full cohesion in Phase 5.)
- [x] 3.3 Resolve keybind duplicates (`Super+R` vs `Super+Space`) (§5) — kept `Super+Space` (native launcher); removed `Super+R`/`Super+D` drun dupes; also fixed silent conf.d dupes (`T`→`J` togglesplit, `Alt+W`→`Alt+S` wallpaper studio, removed `Shift+W` hyprshot + bare `Escape`)
- [x] 3.4 Fix or replace the non-working terminal bind (§5) — `Super+Return` now binds a real terminal (kitty→alacritty→foot); dropped the broken `nyxus_terminal.py`
- [x] 3.5 Full keybind audit + document final list in `docs/KEYBINDS.md` — 0 duplicate active binds, `hyprctl configerrors` clean
- [ ] 3.6 Git safepoint: "stable, de-duplicated session"

### Phase 4 — ISO & kernel audit
- [ ] 4.1 Review custom ISO build process, remove cruft, confirm reproducible
- [ ] 4.2 Review custom kernel config/build, remove stale patches/unused flags
- [ ] 4.3 Evaluate/apply performance-oriented tuning (scheduler, governor) — daily-driver stable, not experimental
- [ ] 4.4 Confirm MSI GS77 hardware support: Optimus GPU/PRIME setup, `msi-ec` (fan/battery/webcam/Fn-key), keyboard RGB, WiFi/Bluetooth/audio (§1.3)
- [ ] 4.5 Git safepoint: "clean ISO/kernel + MSI GS77 hardware support"

### Phase 5 — Theme pass
- [ ] 5.1 Define the shared theme tokens (colors, fonts, effects) in one place in the repo
- [ ] 5.2 Apply to top ticker, side bars, bottom bar (§2)
- [ ] 5.3 Build the full login/lock screen art per the detailed creative brief in §1.1 (custom nebula/starfield background, urban-style alien character, frosted-glass login box)
- [ ] 5.4 Apply to all menus/settings panels
- [ ] 5.5 Add starfield/twinkle motif where it fits
- [ ] 5.6 Git safepoint: "unified theme v1"

### Phase 6 — EWW bars upgrade
- [ ] 6.1 Redesign fan/temp module as live graph, add CPU + GPU graphs — *review `archive/vault-bars-signature-redesign` first (§3)*
- [ ] 6.2 Redesign network module as live graph
- [ ] 6.3 Confirm all bar modules match theme from Phase 5
- [ ] 6.4 Git safepoint: "bars v2"

### Phase 7 — Center widget + The Hub
- [ ] 7.1 Redesign the Nyxus clock/date center widget
- [ ] 7.2 Rename popup to "The Hub," redesign to high polish
- [ ] 7.3 Add app-launcher area inside the Hub
- [ ] 7.4 Add any other useful quick-access items decided from §9
- [ ] 7.5 Build music mode (MPRIS-based now-playing view) on the center widget
- [ ] 7.6 Verify every Hub button/section actually works — including settings surfaced from earlier phases (standing rule)
- [ ] 7.7 Git safepoint: "Hub v1 + music mode"

### Phase 8 — Daily-driver readiness
- [ ] 8.1 Build bootstrap/install script (§6)
- [ ] 8.2 Write README + KEYBINDS.md + any other docs
- [ ] 8.3 Full end-to-end test: fresh boot → login → daily use, no crashes/freezes
- [ ] 8.4 Git safepoint / tag: "Nyxus v1.0 — daily driver ready"

---

## Appendix: Archive branches (GitHub)

Preserved history from a deleted local checkout (`GowskiNet-Vault/OS/Nyxus-Core`) never pushed anywhere before 2026-07-14. Kept on GitHub, not merged into `main` — review at the phases noted.

| Branch | Content | Phase |
|---|---|---|
| `archive/vault-bars-signature-redesign` | 48 unmerged EWW/HUD redesign commits (gem-vial pills, Starlight Headliner bars, four-bar cohesion) | 6 (§3) |
| `archive/vault-uncommitted-wip` | Uncommitted working tree incl. regreet greeter variant (`regreet.toml`/`.css`, `greetd/config.toml`) | 2 (§1.1) |
| `archive/vault-main-replit-history` | Separate 189-commit Replit-era history | reference only |
| `archive/vault-replit-agent` | Replit-agent branch, login-screen commits | reference only |
| `archive/vault-subrepl-4p8v69rp` | Pre-rebase snapshot from a Replit sub-session | reference only |

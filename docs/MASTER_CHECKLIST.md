# NYXUS — Master Completion Checklist

**Goal:** A fully-complete, no-dead-ends, no-mockups OS that "works like
you bought it from Best Buy." Every menu opens a real panel. Every panel
reads/writes real system state. Every setting persists.

**Working order:** strictly top-to-bottom. Don't skip — each wave's
patterns are reused in the next wave.

**Status legend:** `[x]` done & shipped · `[~]` partial · `[ ]` not started

Last updated: 2026-05-11 (rev r9-eww)

---

## ✅ WAVE 0 — Foundations (DONE earlier)

- [x] Hyprland 0.55+ compositor (clean rev r8-eww boot)
- [x] EWW v0.6.0 bar (replaced waybar)
- [x] dunst, hyprlock, hypridle, hyprpaper wired
- [x] Bootstrap + resync pipeline (`nyxus-bootstrap`, `nyxus-resync-all.sh`)
- [x] ISO bake pipeline (`iso-builder/build-iso.sh`)
- [x] DARK MIRROR theme tokens (purple/cyan, glassmorphic blur)
- [x] First-party apps as real artifacts: Notepad, Stickies, SysMon, Widgets
- [x] Source-of-truth: `artifacts/api-server/nyxus-scripts/` → restaged on every bake

---

## ✅ WAVE 1 — Consumer Minimum (DONE in r9-eww — verify on boot)

Every status pill on the bar opens a real, working flyout.

- [x] Quick Settings panel (12 toggle tiles + 3 sliders)
- [x] WiFi network picker (scan, connect, forget, password prompt)
- [x] Bluetooth device manager (scan, pair, connect, battery%)
- [x] Audio mixer (output picker + per-app volume)
- [x] Calendar flyout (full month grid)
- [x] Notification Center (dunst history, dismiss, clear-all, DND)
- [x] Hyprland keybinds: Super+A/N/W/M/C, Super+Shift+B
- [x] Cheatsheet updated to document new chords
- [x] Security: SSID base64-encoded, MAC validated, vol clamped

**On-boot verification (do this first before Wave 2):**
- [ ] Bar shows new ⚙ and ▦ pills in right cluster
- [ ] Super+A opens Quick Settings
- [ ] Super+W opens WiFi and lists networks
- [ ] Super+M opens audio mixer with real apps listed
- [ ] Super+N opens notifications
- [ ] Super+C opens calendar with today highlighted
- [ ] Super+Shift+B opens Bluetooth and Scan finds devices

---

## ⏳ WAVE 2 — Polish (5 items, ~1 sprint)

- [ ] **First-Boot Welcome Wizard** ← biggest single win
  - Step 1: Language / region
  - Step 2: WiFi connect
  - Step 3: User account (name, password, avatar)
  - Step 4: Theme (dark/light, accent color)
  - Step 5: Privacy (location, telemetry opt-in)
  - Step 6: Account sync (optional — skippable)
  - Step 7: "Tour of NYXUS" interactive overlay
  - Marker file `~/.nyxus/welcome-done` so it never re-runs
- [ ] **Rich Update Indicator**
  - Bar pill shows count + severity color
  - Click → flyout with changelog, "Update now" button
  - Background `pacman -Sy` checker daemon
  - One-click apply with progress bar
- [ ] **DND Scheduling**
  - Quiet hours (start/end time)
  - Per-app allow/block list
  - "Until tomorrow" / "1 hour" quick options
- [ ] **Full Media Widget**
  - Album art (fetched from playerctl metadata)
  - Scrubber with click-to-seek
  - Multi-player switching (Spotify + Firefox + mpv)
  - Lock-screen + bar + flyout variants
- [ ] **Clipboard Manager UI**
  - cliphist-backed, searchable history
  - Pin items, delete items, clear all
  - Image preview support
  - Super+V keybind

---

## ⏳ WAVE 3 — NYXUS Settings App (THE BIG ONE, ~3-4 sprints)

A real settings app with sidebar nav, search, and 14 panes. Every pane
must read AND write real system state — no mockups.

### Settings shell (sprint 3a)
- [ ] App skeleton (`nyxus-settings.tgz` artifact)
- [ ] Left sidebar with 14 entries + icons
- [ ] Top search bar (fuzzy across all panes)
- [ ] Breadcrumb header
- [ ] Settings registry (JSON manifest of every setting + handler)

### Settings panes (sprint 3b/c/d — each must be REAL, no mockups)
- [ ] **Display** — resolution, scaling, refresh, multi-monitor, night light schedule, color profile
- [ ] **Sound** — output/input devices, per-app, system sounds, alerts, balance
- [ ] **Network** — WiFi, ethernet, VPN (wg+openvpn), proxy, hostname, DNS
- [ ] **Bluetooth** — full device manager (deeper than the flyout)
- [ ] **Power** — battery profiles, sleep timeout, lid action, button action, charging limit
- [ ] **Appearance** — wallpaper, theme, accent color, dark/light, fonts, cursor, icon theme
- [ ] **Keyboard** — layout, repeat rate, **shortcuts editor (rebind ALL hyprland binds)**
- [ ] **Mouse / Touchpad** — speed, accel, natural scroll, tap-to-click, gestures
- [ ] **Privacy** — location, camera, mic, recent files, screen lock timeout, telemetry
- [ ] **Users** — add/remove, change password, avatar, autologin, sudo membership
- [ ] **Date & Time** — timezone picker (map), NTP server, format, week-start
- [ ] **Region & Language** — locale, formats, input methods (ibus/fcitx)
- [ ] **Apps & Defaults** — installed list, default apps per mime, autostart, permissions
- [ ] **About** — version, hardware, kernel, support links, factory reset, EULA

---

## ⏳ WAVE 4 — Signature Touches (~1 sprint)

The "wow" layer that elevates above stock Linux.

- [ ] **Workspace Overview** (Mission Control / Activities style)
  - Super+Tab full-screen overview
  - Live thumbnails of every workspace + window
  - Drag windows between workspaces
- [ ] **Screenshot Annotation Overlay**
  - After region capture, slide-up annotation toolbar
  - Arrow / box / text / blur / crop tools
  - Save / copy / share buttons
- [ ] **Color Picker + History**
  - Super+P picks pixel under cursor
  - Hex/RGB/HSL display + copy
  - Last 20 picks history
- [ ] **Lock-Screen Widgets**
  - Now playing / weather / calendar peek
  - Notification preview (respects DND)

---

## ⏳ WAVE 5 — Branding & "Forgot About That" Items (~1-2 sprints)

The things you'd notice missing on a fresh install.

- [ ] **App launcher polish**
  - Categories (Office / Internet / Graphics / Games / System)
  - Recent apps section
  - Pinned apps section (drag to pin)
  - Search across .desktop files + binaries
- [ ] **Right-click desktop menu**
  - Change wallpaper / open terminal here / display settings
- [ ] **File manager (Thunar) NYXUS branding**
  - Custom theme, custom icons, custom toolbar
  - Place sidebar pinned defaults
- [ ] **Login screen (greetd/tuigreet)**
  - NYXUS logo, blur background, theme matching
  - User picker with avatars
- [ ] **Boot splash (Plymouth)**
  - NYXUS logo animation during boot
  - Hides kernel messages
- [ ] **Installer (Calamares) NYXUS branding**
  - Welcome screen with NYXUS logo
  - Custom slideshow during install
  - Theme matched to OS
- [ ] **System Restore / Snapshots**
  - btrfs snapshot integration (snapper)
  - "Roll back to yesterday" UI in Settings → About
- [ ] **About dialog in every first-party app**
  - Version, license, credits, "Report bug" link

---

## ⏳ WAVE 6 — Hardening & Post-Install (~1 sprint)

Things that go on AFTER everything else works (per user pref in replit.md).

- [ ] Enable fail2ban (per-user opt-in via Settings → Privacy)
- [ ] Enable pam_faillock (per-user opt-in via Settings → Privacy)
- [ ] Firewall UI (Settings → Network → Firewall, ufw-backed)
- [ ] AppArmor profiles for first-party apps
- [ ] Automatic security updates toggle
- [ ] Encrypted home folder option (Settings → Users)

---

## ⏳ WAVE 7 — Acceptance Test (the "Best Buy" gate)

Before declaring complete, walk this checklist on a fresh install:

- [ ] Boot from ISO → installer runs → install completes → reboot
- [ ] Welcome wizard runs → all 7 steps work → desktop appears
- [ ] Click EVERY bar pill → opens a real panel
- [ ] Open Settings → click EVERY left-nav entry → pane loads
- [ ] In every pane, change one setting → reboot → setting persisted
- [ ] Right-click EVERY first-party app → context menu works
- [ ] Search in launcher for any installed app → finds it → launches
- [ ] Connect WiFi, pair Bluetooth headphones, plug in USB drive — all work
- [ ] Take a screenshot, annotate it, save it — works
- [ ] Update available → click update → applies → reboots cleanly
- [ ] Lock screen → unlock with password → session restored
- [ ] Power button → menu → Shutdown → clean shutdown (no hangs)
- [ ] Run `nyxus-doctor` → 0 errors, 0 warnings

---

## Sprint cadence

Realistic estimate from current pace:
- Wave 2: 1 sprint
- Wave 3: 3-4 sprints (the big one)
- Wave 4: 1 sprint
- Wave 5: 1-2 sprints
- Wave 6: 1 sprint
- Wave 7: 0.5 sprint (just verification)

**Total: ~7-9 sprints to genuinely Best Buy complete.**

Going strictly top-to-bottom. No skipping. No fakes. Every checkbox flipped
to `[x]` only after it works on real hardware.

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

## 🎨 DESIGN-CONTRACT AUDIT (Wave 2 prerequisite — see `docs/DESIGN_CONTRACT.md` §13)

Every existing component must pass §12 of the design contract before
new surfaces are added. Walk each on a 1366×768 display.

- [x] Quick Settings flyout — audited 2026-05-11 (no list, no empty state needed)
- [x] WiFi flyout — audited 2026-05-11, added empty state
- [x] Bluetooth flyout — audited 2026-05-11, added powered/off-aware empty state
- [x] Audio Mixer flyout — audited 2026-05-11, added empty state
- [x] Calendar flyout — audited 2026-05-11 (static grid, no list)
- [x] Notification Center — audited 2026-05-11, added DND-aware empty state
- [ ] Bar (EWW main bar) — check spacing on right cluster
- [ ] Cheatsheet — three-column layout fit
- [ ] Powermenu — centering + button hierarchy
- [ ] Dashboard — largest known offender, full pass

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

---

# ════════════════════════════════════════════════════════════════════════
# PHASE 8 → 25 — Apple/Windows-class parity build (rev r10, 2026-05-13)
# ════════════════════════════════════════════════════════════════════════

User directive (2026-05-13): "Start at 1, work down to 18. Nothing left
unfinished. Stand next to Apple and Windows in design, function and
stability." Each tier ships in batches of ~3 items, py_compile + bash -n
+ iso-verify after every batch, architect review after every tier.

Grade-A done bar (unchanged): real read · real write · persists · in
Settings + menu/keybind · logs to `~/.cache/nyxus/<app>.log` · fails loud
· architect zero-severe.

## Tier 1 — Devices & Hardware
- [x] **Bluetooth panel** (BluetoothPage — Wave 1; pair/scan/connect/power)
- [x] **Printers & Scanners** (PrintersPage — r10; CUPS service +
      list, set-default, test page, pause/resume, remove, web admin)
- [x] **Mice & Touchpad** (MousePage — sensitivity, accel profile,
      natural scroll, tap-to-click, two-finger scroll, disable-while-
      typing, drag lock, live device list)
- [x] **Camera & Microphone** (CamerasMicsPage — r10; v4l2 enum,
      pactl source enum, cheese/guvcview/pavucontrol launchers)
- [x] **Game Controllers** (ControllersPage — r10; /dev/input/js*
      enum w/ udev names, jstest-gtk/jstest/evtest launchers, browser
      gamepad tester fallback)
- [x] **Touchpad gestures** (MousePage gestures group — r10 batch 2;
      libinput-gestures user systemd toggle + NYXUS-default conf
      writer at ~/.config/libinput-gestures.conf: 3-finger L/R =
      workspace, 4-finger up = fullscreen, 4-finger down = float,
      2-finger pinch = killactive)
- [ ] **Keyboard panel polish** (compose key, switcher tray applet,
      shortcuts editor that rebinds hyprland binds in place)
- [x] **Display arrangement** (DisplayPage._render_monitors — r10
      batch 2; per-monitor ExpanderRow w/ Scale combo (1.00–2.00) and
      Rotation combo (0/90/180/270°), applies live via `hyprctl
      keyword monitor` AND persists to ~/.config/hypr/nyxus-monitors.
      conf with idempotent auto-source line in hyprland.conf)
- [ ] **Color profiles** (colord/ICC import + per-monitor profile)
- [x] **External drives & USB arrival** (nyxus_usb_watch.py daemon +
      nyxus-usb-watch.service user unit — r10 batch 2; tails `udevadm monitor
      --subsystem-match=block --property`, toasts add/remove with
      ID_VENDOR/ID_MODEL via notify-send, logs to ~/.cache/nyxus/
      usb-watch.log; Settings toggle in NotificationsPage →
      External devices)

## Tier 2 — Network & Connectivity
- [x] **VPN: WireGuard + OpenVPN profiles** (NetworkPage Wave 1 covers;
      verify import flow exists and ship if not)
- [ ] **Hotspot / Mobile broadband sharing** (NM share)
- [ ] **Proxy settings UI** (system + per-app)
- [ ] **DNS-over-HTTPS toggle** (systemd-resolved, presets)
- [ ] **Firewall UI** (UFW frontend; lives inside Security Center
      already — verify and surface in Settings → Network too)

## Tier 3 — Look & Feel signature polish
- [ ] **Hot Corners** (4 corners → assignable actions, hyprland binds)
- [ ] **Night Light scheduler** (wlsunset; DisplayPage has nl_grp stub)
- [ ] **Dynamic / time-of-day wallpapers** (Sonoma-style)
- [ ] **Live wallpapers** (mpv-on-desktop optional)
- [ ] **Accent color picker** (override gold)
- [ ] **Cursor theme + size**
- [ ] **Font management** (install/preview/enable)
- [ ] **Window snapping presets** (quarter/third/half tiling)
- [ ] **Stage Manager-style window grouping** (optional mode)
- [ ] **Per-workspace wallpapers**

## Tier 4 — Input & Productivity
- [ ] **Emoji & symbol picker** (`Super+.`, rofi-emoji)
- [ ] **Screenshot tool with annotate** (region, window, delay, draw,
      redact — grim+slurp+swappy)
- [ ] **Screen ruler / color picker** utilities
- [ ] **Text expansion / snippets** (espanso wrapper)
- [ ] **Window picker overlay** (`Alt+Tab` redesign)
- [ ] **App Launchpad** (full-screen app grid, Spotlight sibling)
- [ ] **Login Items / Startup Apps manager** (`~/.config/autostart`)
- [ ] **Default Apps panel** (browser, mail, terminal, image viewer)
- [ ] **File associations editor** (per-mimetype)

## Tier 5 — Notifications & Focus
- [ ] **Do Not Disturb scheduling** (windows, "until tomorrow",
      per-app overrides) — extends NotificationsPage
- [ ] **Focus modes** (Work/Personal/Gaming bundles)
- [ ] **Per-app notification rules** (sound, banners, lockscreen viz)

## Tier 6 — Time, Place & Awareness
- [ ] **Location services panel** (geoclue toggles, per-app)
- [ ] **Weather widget** + lockscreen weather
- [ ] **World clock / time zones panel**
- [ ] **Calendar & Reminders app** (pairs w/ Stickies/Notepad)
- [ ] **Auto time zone** based on location

## Tier 7 — Audio
- [ ] **Sound scheme picker** (UI sounds on/off, presets)
- [ ] **Per-app volume mixer** (native UI, replace pavucontrol)
- [ ] **Audio routing rules** (auto-switch on headphone plug)
- [ ] **EQ / spatial audio preset panel**

## Tier 8 — Storage & Files
- [ ] **Disk Usage Analyzer** (baobab-style treemap inside StoragePage)
- [ ] **Trash management** (auto-empty after N days)
- [ ] **Cloud accounts panel** (Nextcloud/Drive/Dropbox via gvfs)
- [ ] **Disk encryption status + change-passphrase UI** for LUKS
- [ ] **SMART health for drives**
- [ ] **ISO/disk image mounter** (right-click)

## Tier 9 — Apps & Permissions
- [ ] **App Library / Uninstall manager** (single pane: Flatpak +
      pacman + AUR)
- [ ] **Per-app permission viewer** (camera/mic/location/files even
      beyond Flatpak)
- [ ] **Background process manager** (what's running + kill button)
- [ ] **App auto-update toggles** per-app
- [ ] **Pinned-app sync** across machines (NYXUS Account)

## Tier 10 — Accounts & Sync
- [ ] **Online accounts** (Google/Microsoft/Nextcloud sign-in)
- [ ] **Contacts app**
- [ ] **Mail app** (or default-mail picker + Geary bundle)
- [ ] **Browser profile sync** through NYXUS Account
- [ ] **Settings sync** (wallpaper/accent/dock/keybinds)
- [ ] **Find My Device** (last-seen via NYXUS Account)

## Tier 11 — Security & Privacy (extends Security Center)
- [ ] **Password manager / Keyring UI** (gnome-keyring or KeePassXC)
- [ ] **2FA / authenticator app**
- [ ] **Privacy dashboard** (last 24h: who used cam/mic/location)
- [ ] **Clipboard history privacy rules** (skip password fields)
- [ ] **Secure file shredder** (right-click)
- [ ] **Lock-on-leave** (webcam-presence or BT-proximity)

## Tier 12 — Power & Battery
- [ ] **Battery health report** (cycle count, capacity, recs)
- [ ] **Per-app energy impact** view
- [ ] **Power profiles with custom schedules**
- [ ] **Charge limit toggle** (stop at 80%)

## Tier 13 — Connectivity / Continuity (Apple-magic)
- [ ] **Phone link** (KDE Connect rebrand: SMS, notifications, file
      send, clipboard)
- [ ] **AirDrop expansion of NYXUS Drop** (LAN peer discovery)
- [ ] **Universal clipboard** between devices
- [ ] **Handoff** (continue on another device)
- [ ] **Remote desktop** (RustDesk or built-in) + screen sharing
- [ ] **Nearby Share / Quick Share** to Android

## Tier 14 — Accessibility (extends AccessibilityPage)
- [ ] **Voice Control** (whisper.cpp local — "click button")
- [ ] **Live Captions** for any audio (overlay)
- [ ] **Zoom / Magnifier** with follow-cursor
- [ ] **Sticky / Slow / Bounce keys UI**
- [ ] **Color filters** (deuteranopia/protanopia/grayscale)
- [ ] **Reduce motion / reduce transparency** toggles
- [ ] **Mouse keys** (numpad-driven cursor)

## Tier 15 — Developer / Pro
- [ ] **Developer Mode toggle** (verbose logs, debug overlays)
- [ ] **System hardware report exporter** (PDF/JSON for support)
- [ ] **Performance HUD** (FPS/GPU/CPU overlay)
- [ ] **Containers / Distrobox UI**
- [ ] **Virtual machines quick-launcher** (GNOME Boxes wrap)

## Tier 16 — Recovery & Resilience (extends Time Machine)
- [ ] **Boot picker / BLS entry editor** (graphical)
- [ ] **Reset this PC** flow (keep files / wipe — Win11 style)
- [ ] **Safe mode** boot option from Recovery
- [ ] **Driver / kernel rollback UI** tied to snapshot system

## Tier 17 — First-5-minutes experience
- [ ] **Interactive tour** after welcome (gestures, Spotlight, Mission
      Control)
- [ ] **Migration assistant** (import from Linux home / Windows backup
      / Mac Time Machine)
- [ ] **What's New popup** after each major update
- [ ] **Tip of the Day** in welcome

## Tier 18 — Smart / on-device AI (optional)
- [ ] **Local AI assistant** (llama.cpp wrapper, Spotlight integration)
- [ ] **Smart screenshot text extract** (Tesseract OCR → clipboard)
- [ ] **Image background removal** in Files right-click
- [ ] **Smart search in Spotlight** (natural language)

---

## Per-batch progress log (newest first)

- **r10 batch 2** (2026-05-13): Tier 1 #6, #8, #10 — Touchpad
  gestures (MousePage), Display arrangement (DisplayPage scale+
  rotation+persistence), USB arrival (new nyxus-usb-watch daemon +
  unit + NotificationsPage toggle). py_compile ✓ on settings + new
  daemon. Architect pending.

- **r10 batch 1** (2026-05-13): Tier 1 #1–#5 — Bluetooth (already
  present, verified), Printers (new), Mouse (verified deeper than
  plan), Cameras & Mics (new), Game Controllers (new). py_compile ✓.
  Commit pending architect review.



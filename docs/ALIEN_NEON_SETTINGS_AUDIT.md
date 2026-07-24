# NYXUS — ALIEN NEON + Settings Completeness Audit

> Generated: **2026-07-24 09:01 **  
> Live tree: `~/.nyxus` + desktop entries  
> Settings source: `/home/cosmic/.nyxus/nyxus_settings.py` (sha `6d49911d067a`)  
> Repo settings sha: `ba39feefff9e` (not byte-identical to live)  
> **Use this as the master checklist.** Check items off as they land on `main` + verify in bake.

## Canon (done = this)

| Role | Hex |
|---|---|
| violet | `#7d3dff` |
| magenta | `#ff2dad` |
| green | `#39ff14` |
| orange | `#ff8a1e` |
| cyan | `#2bd2ff` |
| red | `#ff2d55` |
| yellow | `#ffe600` |
| orchid | `#e367ff` |
| void | `#05060a` |
| text | `#eef2fa` |

- Brand string: **ALIEN NEON** (not DARK MIRROR)
- `accent.json`: `active=prism`, `follow_wallpaper=false`, **prism-only** presets
- Banned leftovers include cream `#f4ead5`, old violet `#a06bff`, gold `#d4b87a`, etc.

---

## SCOREBOARD

| Bucket | Count |
|---|---:|
| Settings sidebar sections | 48 |
| Settings pages EMPTY | 1 |
| Settings pages MINIMAL (1–4 controls) | 15 |
| Settings pages PARTIAL (5–14) | 23 |
| Settings pages SUBSTANTIVE (15+) | 9 |
| Settings pages with stub/TODO text | 5 |
| Python/GTK surfaces **not** ALIEN NEON | 44 |
| Desktop product apps with **no** Settings section | 58 |
| Session/features with no dedicated Settings section | 15 |
| Theme Pack presets that are **not** ALIEN NEON prism-only | 5 total listed |

---

## 1) NOT ALIEN NEON — Python/GTK surfaces

**Count: 44**

| # | Path | DARK MIRROR | ALIEN brand | Banned hex | Notes |
|---:|---|---:|---:|---|---|
| 1 | `.nyxus/nyxus-home/style.py` | 1 | 0 | — | DARK_MIRROR×1; no_ALIEN_NEON_brand |
| 2 | `.nyxus/nyxus-panel/settings.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 3 | `.nyxus/nyxus-start/main.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 4 | `.nyxus/nyxus_account.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 5 | `.nyxus/nyxus_backup.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 6 | `.nyxus/nyxus_chrome.py` | 6 | 0 | — | DARK_MIRROR×6; no_ALIEN_NEON_brand |
| 7 | `.nyxus/nyxus_clipboard.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 8 | `.nyxus/nyxus_control.py` | 2 | 0 | — | DARK_MIRROR×2; no_ALIEN_NEON_brand |
| 9 | `.nyxus/nyxus_cosmic_bg.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_magenta,void,text |
| 10 | `.nyxus/nyxus_crashd.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 11 | `.nyxus/nyxus_demon_wake.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 12 | `.nyxus/nyxus_doctor.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 13 | `.nyxus/nyxus_drop.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 14 | `.nyxus/nyxus_error.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 15 | `.nyxus/nyxus_files.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 16 | `.nyxus/nyxus_gen_icons.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 17 | `.nyxus/nyxus_hotcorners.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 18 | `.nyxus/nyxus_i18n.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 19 | `.nyxus/nyxus_launcher.py` | 2 | 0 | — | DARK_MIRROR×2; no_ALIEN_NEON_brand |
| 20 | `.nyxus/nyxus_motd.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 21 | `.nyxus/nyxus_notepad.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 22 | `.nyxus/nyxus_notes.py` | 3 | 0 | — | DARK_MIRROR×3; no_ALIEN_NEON_brand |
| 23 | `.nyxus/nyxus_palette.py` | 1 | 0 | — | DARK_MIRROR×1; no_ALIEN_NEON_brand |
| 24 | `.nyxus/nyxus_parental.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 25 | `.nyxus/nyxus_powermenu.py` | 1 | 0 | — | DARK_MIRROR×1; no_ALIEN_NEON_brand |
| 26 | `.nyxus/nyxus_preboot.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 27 | `.nyxus/nyxus_screensaver.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 28 | `.nyxus/nyxus_screenshot.py` | 1 | 0 | — | DARK_MIRROR×1; no_ALIEN_NEON_brand |
| 29 | `.nyxus/nyxus_security.py` | 3 | 0 | `#d4b87a` | DARK_MIRROR×3; no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void |
| 30 | `.nyxus/nyxus_settings.py` | 18 | 0 | `#d4b87a` | DARK_MIRROR×18; no_ALIEN_NEON_brand; banned=#d4b87a |
| 31 | `.nyxus/nyxus_settings_accessibility.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 32 | `.nyxus/nyxus_settings_notifications.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 33 | `.nyxus/nyxus_settings_sandbox.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 34 | `.nyxus/nyxus_settings_snapshots.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 35 | `.nyxus/nyxus_splash.py` | 0 | 0 | — | no_ALIEN_NEON_brand |
| 36 | `.nyxus/nyxus_stickies.py` | 2 | 0 | — | DARK_MIRROR×2; no_ALIEN_NEON_brand |
| 37 | `.nyxus/nyxus_store.py` | 2 | 0 | — | DARK_MIRROR×2; no_ALIEN_NEON_brand; missing_violet,magenta,void |
| 38 | `.nyxus/nyxus_sysmon_gtk.py` | 1 | 0 | — | DARK_MIRROR×1; no_ALIEN_NEON_brand |
| 39 | `.nyxus/nyxus_terminal.py` | 5 | 0 | — | DARK_MIRROR×5; no_ALIEN_NEON_brand |
| 40 | `.nyxus/nyxus_toast.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 41 | `.nyxus/nyxus_updater.py` | 0 | 0 | `#d4b87a` | no_ALIEN_NEON_brand; banned=#d4b87a; missing_violet,magenta,void,text |
| 42 | `.nyxus/nyxus_usb_watch.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 43 | `.nyxus/nyxus_wallpaper_studio.py` | 0 | 0 | — | no_ALIEN_NEON_brand; missing_violet,magenta,void,text |
| 44 | `.nyxus/nyxus_welcome.py` | 2 | 0 | — | DARK_MIRROR×2; no_ALIEN_NEON_brand |

### Shared palette module gaps

- Still brands DARK MIRROR: **1** hit(s)
- ALIEN NEON brand string: **0**
- Canon present: violet, magenta, green, orange, cyan, red, yellow, text
- Canon missing: orchid, void

### Theme Packs page still offers non-locked packs

- `dark_mirror` — DARK MIRROR (default) (`#7d3dff` / `#2bd2ff`) ❌ default is DARK MIRROR — must become ALIEN NEON / prism-only
- `inferno` — INFERNO (`#ff3a5c` / `#ffae3a`) ❌ remove/lock
- `oceanic` — OCEANIC (`#3a7dff` / `#3affd8`) ❌ remove/lock
- `forest` — FOREST (`#3aff7d` / `#a0ff3a`) ❌ remove/lock
- `monochrome` — MONOCHROME (`#cccccc` / `#888888`) ❌ remove/lock

### Also out of scope of the Python scan but NOT ALIEN NEON yet (track separately)

1. Bifrost (Tauri) desktop UI
2. nyxus-app-shell + Arsenal web UIs (CIPHER/Forge/GSL/RedForge/Trainer/AXIOM)
3. Ghost-Relay c2 TUI (kitty) — terminal palette only
4. Meli
5. EWW bar CSS/SCSS (desktop chrome — partial via accent apply, verify)
6. greetd greeter / hyprlock full visual QA
7. Plymouth splash (art exists; settings page separate)
8. GRUB dragon theme (already ALIEN NEON in repo — verify on stick)

---

## 2) SETTINGS PAGES — empty / minimal / incomplete

All **48** nav entries have a `PAGE_CLASSES` mapping (none missing a class).
Incomplete = thin UI, not “unwired class”.

### EMPTY — 1

- [ ] `vpn` — **VPN** (controls=0)

### MINIMAL — 15

- [ ] `app_perms` — **App Permissions** (controls=1, groups=2)
- [ ] `cameras_mics` — **Camera & Microphone** (controls=2, groups=3)
- [ ] `color` — **Color profiles** (controls=3, groups=3)
- [ ] `containers` — **Containers** (controls=2, groups=4)
- [ ] `controllers` — **Game Controllers** (controls=1, groups=2)
- [ ] `doh` — **DNS-over-HTTPS** (controls=3, groups=3)
- [ ] `drop` — **NYXUS Drop** (controls=2, groups=4)
- [ ] `editors` — **Editors** (controls=1, groups=2)
- [ ] `gaming` — **Gaming** (controls=2, groups=3)
- [ ] `kernel` — **Kernel** (controls=1, groups=2)
- [ ] `mac_random` — **MAC Randomization** (controls=3, groups=4 · stub text)
- [ ] `secboot` — **Secure Boot · TPM** (controls=1, groups=3)
- [ ] `sync` — **NYXUS Account** (controls=4, groups=3)
- [ ] `usb_firewall` — **USB Firewall** (controls=4, groups=5)
- [ ] `virt` — **Virtualization** (controls=1, groups=3)

### PARTIAL — 23 (exists but not “complete master” depth)

- [ ] `about` — **About** (controls=6)
- [ ] `accessibility` — **Accessibility** (controls=7)
- [ ] `assistant` — **NYXUS Assistant** (controls=6)
- [ ] `backup` — **Backup** (controls=6)
- [ ] `bluetooth` — **Bluetooth** (controls=14)
- [ ] `clipboard` — **Clipboard** (controls=11)
- [ ] `datetime` — **Date & Time** (controls=5)
- [ ] `dock` — **Dock** (controls=9)
- [ ] `keyboard` — **Keyboard** (controls=11)
- [ ] `language` — **Language & Region** (controls=5)
- [ ] `mouse` — **Mouse & Touchpad** (controls=8)
- [ ] `notifications` — **Notifications** (controls=10)
- [ ] `parental` — **Parental Controls** (controls=12 · stub text)
- [ ] `plymouth` — **Boot Splash** (controls=14)
- [ ] `printers` — **Printers & Scanners** (controls=7)
- [ ] `record` — **Screen Recorder** (controls=8)
- [ ] `security` — **Security** (controls=7)
- [ ] `sound` — **Sound** (controls=8)
- [ ] `sounds` — **Sound Pack** (controls=14)
- [ ] `storage` — **Storage** (controls=9)
- [ ] `themepacks` — **Theme Packs** (controls=5)
- [ ] `wallpaper` — **Wallpaper Studio** (controls=9)
- [ ] `welcome` — **Welcome** (controls=11)

### SUBSTANTIVE — 9 (keep; still need ALIEN NEON reskin)

- [ ] `appearance` — **Appearance** (controls=26 · stub text)
- [ ] `apps` — **Apps & Defaults** (controls=17 · stub text)
- [ ] `display` — **Display** (controls=20)
- [ ] `loginscreen` — **Login Screen** (controls=15)
- [ ] `network` — **Network** (controls=42)
- [ ] `power` — **Power** (controls=24 · stub text)
- [ ] `privacy` — **Privacy & Security** (controls=24)
- [ ] `updates` — **Updates** (controls=23)
- [ ] `users` — **Users** (controls=24)

---

## 3) PRODUCT APPS / DESKTOP ENTRIES WITH NO SETTINGS SECTION

**Count: 58** (NYXUS-related visible `.desktop` entries with no owned section)

| # | App | Exec (short) |
|---:|---|---|
| 1 | AI Cyber Defense Trainer | `/home/cosmic/.local/bin/trainer-app` |
| 2 | APEX Rig (Qtile) | `/home/cosmic/Scripts/utilities/gowskinet-flip.sh` |
| 3 | Arsenal | `kitty --override background_opacity=1.0 --override initial_window_width=1200 --override initial_wind` |
| 4 | AXIOM | `nyxus-app-shell axiom` |
| 5 | Bifrost | `env BIFROST_GUARDIAN=/home/cosmic/Projects/bifrost/bifrost/guardian.py /usr/bin/bifrost` |
| 6 | Bifrost Dashboard | `/home/cosmic/.local/bin/bifrost-app` |
| 7 | CIPHER | `/home/cosmic/.local/bin/cipher-app` |
| 8 | Forge | `nyxus-app-shell forge` |
| 9 | Ghost-Relay (c2) | `kitty --class nyxus-c2 --title "Ghost-Relay · c2" -e nyxus-c2` |
| 10 | GodsApp | `/usr/local/bin/godsapp %U` |
| 11 | GowskiNet Flip Desktop | `/home/cosmic/Scripts/utilities/gowskinet-flip.sh` |
| 12 | GowskiNet FORGE | `/home/cosmic/.local/bin/forge-app` |
| 13 | GowskiNet HoneyHive 🦈 | `/usr/bin/chromium --profile-directory=Default --app-id=afpppjliigpcejdmogakhknfdanjbbon` |
| 14 | GowskiNet Maze - Live Game Show Camera | `/usr/bin/chromium --profile-directory=Default --app-id=mikckfdehiffimpfniolgkcmfpfnkjgo` |
| 15 | Grafana | `/home/cosmic/.local/bin/grafana-app` |
| 16 | GSL | `/home/cosmic/.local/bin/gsl-app` |
| 17 | HoneyHive Map | `/home/cosmic/.local/bin/honeyhive-app` |
| 18 | Install NYXUS | `pkexec calamares` |
| 19 | Main Page | `/home/cosmic/.local/bin/nyxus-home` |
| 20 | Meli | `meli` |
| 21 | NYXUS (Hyprland) | `nyxus-session-start` |
| 22 | NYXUS App Store | `/home/cosmic/.local/bin/nyxus-store` |
| 23 | NYXUS Chrome Library | `/usr/local/bin/nyxus chrome` |
| 24 | NYXUS Control | `python3 /home/cosmic/.nyxus/nyxus_control.py` |
| 25 | NYXUS Control Center | `/usr/local/bin/nyxus control` |
| 26 | NYXUS Crash Reporter | `/usr/local/bin/nyxus crashd` |
| 27 | NYXUS Doctor | `alacritty -e python3 /home/cosmic/.nyxus/nyxus_doctor.py` |
| 28 | NYXUS Error Reporter | `/usr/local/bin/nyxus error` |
| 29 | NYXUS Files | `/usr/local/bin/nyxus files` |
| 30 | NYXUS GodsApp | `python3 /opt/nyxus-godsapp/main.py` |
| 31 | NYXUS Hot Corners | `/usr/local/bin/nyxus hotcorners` |
| 32 | NYXUS Icon Studio | `/usr/local/bin/nyxus gen-icons` |
| 33 | NYXUS Intel | `/usr/local/bin/nyxus-intel` |
| 34 | NYXUS Launcher | `python3 /home/cosmic/.nyxus/nyxus_launcher.py` |
| 35 | NYXUS Message of the Day | `/usr/local/bin/nyxus motd` |
| 36 | NYXUS Notepad | `/usr/local/bin/nyxus notepad` |
| 37 | NYXUS Notes | `/usr/local/bin/nyxus-notes` |
| 38 | NYXUS Panel | `python3 /home/cosmic/.nyxus/nyxus-panel/main.py` |
| 39 | NYXUS Passwords | `/usr/local/bin/nyxus-passwords` |
| 40 | NYXUS Preboot | `/usr/local/bin/nyxus preboot` |
| 41 | NYXUS SAGE | `nyxus-sage` |
| 42 | NYXUS Screensaver | `/usr/local/bin/nyxus screensaver` |
| 43 | NYXUS Screenshot | `python3 /home/cosmic/.nyxus/nyxus_screenshot.py` |
| 44 | NYXUS Shield | `python3 /opt/nyxus-shield/main.py` |
| 45 | NYXUS Spotlight | `/usr/local/bin/nyxus launcher` |
| 46 | NYXUS Start | `/home/cosmic/.local/bin/nyxus-start` |
| 47 | NYXUS Stickies | `python3 /home/cosmic/.nyxus/nyxus_stickies.py` |
| 48 | NYXUS Store | `/usr/local/bin/nyxus store` |
| 49 | NYXUS Studio | `nyxus-studio` |
| 50 | NYXUS SysMon | `python3 /home/cosmic/.nyxus/nyxus_sysmon_gtk.py` |
| 51 | NYXUS System Monitor | `/usr/local/bin/nyxus sysmon-gtk` |
| 52 | NYXUS Terminal | `python3 /home/cosmic/.nyxus/nyxus_terminal.py` |
| 53 | NYXUS Tour | `nyxus-tour` |
| 54 | NYXUS USB Watch | `/usr/local/bin/nyxus usb-watch` |
| 55 | NYXUS Wake Console | `/usr/local/bin/nyxus demon-wake` |
| 56 | NYXUS Weather | `/usr/local/bin/nyxus-weather` |
| 57 | Prometheus | `/home/cosmic/.local/bin/prometheus-app` |
| 58 | RedForge | `/home/cosmic/.local/bin/redforge-app` |

### Apps that already map to a Settings section (still need theme if listed in §1)

- NYXUS Account → `sync`
- NYXUS Backup → `backup`
- NYXUS Battery Health → `power`
- NYXUS Clipboard → `clipboard`
- NYXUS Drop → `drop`
- NYXUS Language → `language`
- NYXUS Network Usage → `network`
- NYXUS Palette → `themepacks`
- NYXUS Power → `power`
- NYXUS Security Center → `security`
- NYXUS Splash → `plymouth`
- NYXUS Toast → `notifications`
- NYXUS Updater → `updates`
- NYXUS Wallpaper Studio → `wallpaper`
- NYXUS Welcome → `welcome`

---

## 4) SESSION / SYSTEM FEATURES WITH NO DEDICATED SETTINGS SECTION

**Count: 15**

1. [ ] **Hacker Mode** — hypr/station feature
2. [ ] **Ghost mode** — hypr/station feature
3. [ ] **Panic** — security panic path
4. [ ] **Live wallpaper / mpvpaper** — nyxus-live-wallpaper
5. [ ] **EWW bars** — bar suite config
6. [ ] **Hyprland window rules / compositor** — conf.d suite
7. [ ] **jeTT daemon** — security daemon
8. [ ] **Audio reactive / cava / mood / beat / tint** — reactive suite
9. [ ] **Companion / saucer** — separate companion project + desktop mascot
10. [ ] **Hyprlock** — lock screen — only greeter/login has a page
11. [ ] **Screensaver / idle** — nyxus-screensaver
12. [ ] **firewalld (system firewall)** — not USB Firewall page
13. [ ] **Arsenal suite (as settings area)** — apps launch but no Arsenal settings root
14. [ ] **Mission Control** — Super+F3 / missiond
15. [ ] **Notification UFO popup** — dunst + eww
16. [ ] **Build stamp / about bake info** — partial via `about` — partial via About page

---

## 5) SUGGESTED WORK ORDER (to actually finish)

1. **Foundation:** `nyxus_palette.py` → full canon + ALIEN NEON brand; kill DARK MIRROR/gold.
2. **Master hub chrome:** `nyxus_settings.py` CSS + strings + Theme Packs → prism-only.
3. **Cascade GTK apps** from §1 list (Home, Control, Chrome, Terminal, Store, …).
4. **Deepen EMPTY/MINIMAL settings pages** from §2 (vpn first, then kernel/virt/gaming/…).
5. **Add missing Settings sections** for §3/§4 must-haves (live wallpaper, eww/bars, Hyprland, Arsenal, Hacker/Ghost/Panic, hyprlock, screensaver).
6. **Tauri/web:** Bifrost + app-shell Arsenal UIs.
7. **Verify on stick** after bake (`/etc/nyxus-build` commit + visual QA).

---

## 6) TOTALS TO TRACK

| Workstream | Items |
|---|---:|
| Theme: Python/GTK not ALIEN NEON | 44 |
| Theme: non-Python surfaces to track | 8 |
| Theme combined trackable | 52 |
| Settings EMPTY+MINIMAL to build out | 16 |
| Settings PARTIAL to deepen | 23 |
| Settings SUBSTANTIVE (theme only) | 9 |
| No Settings section (apps) | 58 |
| No Settings section (session features) | 15 |
| **Missing section trackable** | **73** |

*End of audit.*

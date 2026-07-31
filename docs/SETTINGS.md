# NYXUS Settings — Page / Section Map

Reference for the master Settings app (`~/.nyxus/nyxus_settings.py`, GTK4 +
libadwaita, `io.nyxus.settings`). Canonical mirror lives at
`artifacts/api-server/nyxus-scripts/nyxus_settings.py`.

Last audited: 2026‑07‑14 (Settings‑wiring pass). All 48 sections build and
open live without crashing; every page reads real system state and writes
back through the proper tool.

---

## Architecture

- **Section registry** — `SECTIONS: Tuple[SectionDef, ...]` is the single
  source of truth for the sidebar (order, title, subtitle, glyph, search
  keywords, category). `SECTIONS_BY_KEY` maps `key → SectionDef`.
- **Page factory** — `PAGE_CLASSES` maps `key → SectionPage subclass`.
  `SettingsWindow._show_section()` lazily instantiates `cls(win, section)`
  the first time a section is opened and caches it.
- **Base page** — every page subclasses `SectionPage(Adw.Bin)`. `build()`
  is wrapped in try/except so a single page failure degrades to an in‑page
  "Error" group instead of taking down the app. `__init__` auto‑appends the
  mandatory **Keybinds + Reset + Advanced** footer trio; "golden rule"
  pages additionally get General/Appearance/Behavior headings enforced.
- **Navigation** — `Adw.NavigationSplitView` (categorised sidebar + content
  stack), live search box, `Ctrl+K` command palette (`CommandPalette`), and
  deep‑linking: `nyxus-settings <key>` (e.g. `nyxus-settings security`);
  `nyxus-settings --list` prints all keys.
- **Backends** — all shell‑outs go through `sh()` / `sh_async()` (timeout‑
  bounded, logged, off the GTK main thread). Prefs persist to
  `~/.config/nyxus/settings.json`; logs to `~/.cache/nyxus/settings.log`.

---

## Section map (48 sections)

Status legend: **OK** = present, builds, reads+writes real state.

### Personal
| key | Title | Backend / reads → writes | Status |
|-----|-------|--------------------------|--------|
| `welcome` | Welcome | onboarding markers → launches `nyxus-welcome` | OK |
| `loginscreen` | Login Screen | greeter theme/autologin/numlock (login stack owned by login agent) | OK |
| `plymouth` | Boot Splash | plymouth themes → `nyxus-plymouth` | OK |
| `sounds` | Sound Pack | freedesktop/canberra sound theme, per‑event toggles → `nyxus-sound` | OK |
| `appearance` | Appearance | wallpaper, accent (`nyxus-apply-accent`), font scale, **Hot Corners**, **Dynamic Wallpaper** (self‑healing systemd --user units) | OK |
| `accessibility` | Accessibility | `hyprctl` cursor size / animations, text scale, assistive‑tool launch + XDG autostart (magnus/wvkbd/orca) | OK |
| `notifications` | Notifications | detects mako/dunst/swaync, DND toggle, USB‑arrival toasts (`nyxus-usb-watch`) | ⚠ **`nyxus-usb-watch` does not ship** — absent from `/usr/local/bin` and from `nyxus-scripts` (verified 2026-07-30). The USB‑arrival row has no backing binary |
| `language` | Language & Region | `nyxus_i18n` + `/etc/locale.conf` (pkexec) + `~/.config/nyxus/locale.conf` | **OK (fixed)** |
| `editors` | Editors | curated editor bundle, `xdg-mime` default text‑editor | OK |
| `dock` | Dock | pinned apps / position / autohide → `nyxus-dock` config | OK |
| `wallpaper` | Wallpaper Studio | browse/apply NYXUS walls → `nyxus_wallpaper_studio.py` | OK |
| `themepacks` | Theme Packs | ALIEN NEON accent (`prism` is the only preset) → `nyxus-apply-accent` | OK |
| `clipboard` | Clipboard | `cliphist` history size / persistence / secrets filter | OK |
| `assistant` | NYXUS Assistant | NORA prefs (wake/model/hotkey), `ollama` detection | OK |

### Devices
| key | Title | Backend / reads → writes | Status |
|-----|-------|--------------------------|--------|
| `display` | Display | `hyprctl monitors`, `brightnessctl`, **Night Light** (wlsunset/hyprsunset, self‑healing unit) | OK |
| `sound` | Sound | `wpctl`/`pactl` output/input/per‑app, pavucontrol/easyeffects | OK |
| `keyboard` | Keyboard | `hyprctl` xkb layout / repeat, cheatsheet overlay (`eww`) | OK |
| `mouse` | Mouse & Touchpad | `hyprctl` accel / natural‑scroll / tap, libinput‑gestures | OK |
| `bluetooth` | Bluetooth | `bluetoothctl` pair / connect / trust | OK |
| `printers` | Printers & Scanners | CUPS `lpstat`/`lpadmin`, test page | OK |
| `cameras_mics` | Camera & Microphone | v4l2 / `pactl` device probe, cheese/arecord test | OK |
| `controllers` | Game Controllers | `evtest`/`jstest` axis+button test | OK |
| `color` | Color profiles | `colord`/`colormgr` ICC per display | OK |
| `network` | Network | `nmcli` / NetworkManager (wifi/eth/vpn/dns/hotspot) | OK |
| `gaming` | Gaming | Steam, Proton‑GE (`nyxus-protonup`), GameMode, MangoHud | OK |
| `record` | Screen Recorder | wf‑recorder defaults → `nyxus-record` (guarded) | OK |

### System
| key | Title | Backend / reads → writes | Status |
|-----|-------|--------------------------|--------|
| `power` | Power | power‑profiles‑daemon/tlp, logind lid/sleep | OK |
| `datetime` | Date & Time | `timedatectl` tz / NTP / format | OK |
| `privacy` | Privacy & Security | location/mic/camera/screen permission surface | OK |
| `apps` | Apps & Defaults | installed index, default browser/terminal, autostart, mime | OK |
| `storage` | Storage | `lsblk`/`df`/`smartctl`, ncdu/baobab cleanup | OK |
| `updates` | Updates | `checkupdates`/pacman + paru/yay, reflector, systemd timer → `nyxus-updater` | OK |
| `app_perms` | App Permissions | `flatpak override --user` per‑app toggles | OK |
| `security` | Security | ufw/clamav/bootctl/TPM/LUKS/journalctl posture → `nyxus-security` | **OK (fixed)** |
| `virt` | Virtualization | QEMU/KVM/libvirt/virt‑manager → `nyxus-virt-setup` | OK |
| `containers` | Containers | podman/distrobox → `nyxus-distrobox-helper` | OK |
| `kernel` | Kernel | default boot kernel switch → `nyxus-kernel-switch` | OK |
| `usb_firewall` | USB Firewall | `usbguard` → `nyxus-usbguard-helper` | OK |
| `secboot` | Secure Boot · TPM | `sbctl` + `tpm2-tools` status → `nyxus-secboot` | OK |
| `vpn` | VPN | WireGuard/OpenVPN via `nmcli` → `nyxus-vpn` | OK |
| `doh` | DNS‑over‑HTTPS | `dnscrypt-proxy` off/Cloudflare/Quad9 → `nyxus-doh` | OK |
| `mac_random` | MAC Randomization | NM `wifi.cloned-mac-address` → `nyxus-mac-randomize` | OK |

### Account
| key | Title | Backend / reads → writes | Status |
|-----|-------|--------------------------|--------|
| `users` | Users | `passwd`/`chsh`/groups/id | OK |
| `sync` | NYXUS Account | opt‑in bundle sync → `nyxus-account` | OK |
| `backup` | Backup | Timeshift snapshots (pkexec), scrubber restore/delete → `nyxus-backup` | OK |
| `drop` | NYXUS Drop | `kdeconnect-cli` devices/refresh → `nyxus-drop` | OK |
| `about` | About | system/kernel/hardware/version report | OK |
| `parental` | Parental Controls | bedtime + web blocklist (nudge‑only) → `nyxus_parental.py` | OK |

---

## Standalone subpage modules (superseded — reachable in‑app)

The four standalone GTK panels are **legacy prototypes**. The master
reimplemented each one richer and Hyprland‑native as a first‑class in‑app
page, so their functionality is reachable via the sidebar nav entry (not
"just a separate script"). Nothing imports the standalone `.py` files; they
are kept only as canonical mirrors.

| Standalone module | In‑app replacement (nav key) | Notes |
|-------------------|------------------------------|-------|
| `nyxus_settings_accessibility.py` (`A11yPanel`) | **Accessibility** (`accessibility`) | In‑app adds cursor size, animation toggle, assistive‑tool launch + autostart. The standalone's gsettings high‑contrast toggle intentionally omitted (the ALIEN NEON palette lock owns the theme). |
| `nyxus_settings_notifications.py` | **Notifications** (`notifications`) | In‑app detects mako/dunst/swaync, DND, USB‑arrival toasts. |
| `nyxus_settings_sandbox.py` (`SandboxPanel`) | **App Permissions** (`app_perms`) | In‑app lists installed Flatpaks with per‑app camera/mic/network/fs toggles via `flatpak override --user`. |
| `nyxus_settings_snapshots.py` | **Backup** (`backup`) | In‑app Time‑Machine snapshot scrubber (Timeshift restore/delete via pkexec). |

---

## Companion apps launched from Settings

Thin wrappers in `~/.local/bin` over GTK apps in `~/.nyxus`. All are now
generated/deployed by `nyxus_install.sh` and guarded at the call site by
`SectionPage.launch_app()` (toasts "<app> is not installed" instead of a
dead button):

| Launcher | Impl | Launched from |
|----------|------|---------------|
| `nyxus-backup` | `~/.nyxus/nyxus_backup.py` | Backup |
| `nyxus-updater` | `~/.nyxus/nyxus_updater.py` | Updates |
| `nyxus-drop` | `~/.nyxus/nyxus_drop.py` | NYXUS Drop |
| `nyxus-record` | `~/.local/bin/nyxus-record` (bash) | Screen Recorder |
| `nyxus_hotcorners.py` | `~/.local/bin/nyxus_hotcorners.py` | Appearance → Hot Corners (systemd --user unit) |
| `nyxus-account` / `nyxus-security` | (already deployed) | NYXUS Account / Security |

---

## Fixed in the 2026‑07‑14 wiring pass

1. **Security page** crashed on build — `threading` used but never imported.
   Added module‑level `import threading`.
2. **Language page** crashed — called undefined `empty_group()` on the
   missing‑i18n fallback, and `nyxus_i18n.py` was never deployed to
   `~/.nyxus`. Added a real `empty_group()` helper and deployed the module.
3. **Pango markup** — escaped unescaped `&` and `<…>` in Adw
   subtitles/descriptions across Sound, Keyboard, Mouse, Updates, App
   Permissions, Sync, Drop, Welcome, Language (were rendering blank).
4. **GTK css assertion** — `action_row()` now skips `add_css_class("")`, so
   inactive DoH/MAC/USB rows stop tripping the assertion.
5. **No dead buttons** — added `SectionPage.launch_app()` guard; deployed
   the missing companion apps (backup/updater/drop/record) + Hot Corners
   daemon; repointed the removed `nyxus-cheatsheet` button to the canonical
   `eww open --toggle cheatsheet` overlay. All wired into `nyxus_install.sh`.

   > ⚠ **Note added 2026-07-30:** `nyxus-cheatsheet` does not ship (correct — it
   > was removed). But the `cheatsheet` eww window is itself **superseded by
   > `hotkey-cheatsheet`**, which is what the `Super+/` and `Super+Shift+/` binds
   > actually open. Nothing else opens plain `cheatsheet`. If this Settings button
   > is meant to match the keybind, it should target `hotkey-cheatsheet`.

## Known limitations / decisions for the coordinator

- **ufw** posture reads log `needs root` (INFO) until the polkit path is
  wired — cosmetic; Security page still renders every other subsystem live.
- `nyxus_welcome.py` (onboarding wizard, a separate app — not a Settings
  module) has the same unescaped‑`&` markup bug in two feature‑bundle rows.
  Out of Settings scope; flagged for the owning agent.
- Login Screen page is intentionally read‑mostly; the SDDM/greetd stack is
  owned by the login agent.

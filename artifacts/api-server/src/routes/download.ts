import { Router, type IRouter } from "express";
import path from "path";
import fs from "fs";
import crypto from "crypto";

const router: IRouter = Router();

const SCRIPTS_DIR = path.resolve(__dirname, "nyxus-scripts");

// ── SHA256 manifest cache ────────────────────────────────────────────────
// Hashes every served file at request time, but only re-hashes when the
// file's mtime changes — so steady-state cost is a single fs.statSync
// per file per request (cheap), not a full SHA recompute.
type CacheEntry = { mtimeMs: number; size: number; sha256: string };
const _shaCache = new Map<string, CacheEntry>();

function _sha256OfFile(p: string): string {
  const h = crypto.createHash("sha256");
  h.update(fs.readFileSync(p));
  return h.digest("hex");
}

function _hashOrCached(name: string, p: string): CacheEntry | null {
  let st: fs.Stats;
  try {
    st = fs.statSync(p);
  } catch {
    return null;
  }
  const cached = _shaCache.get(name);
  if (cached && cached.mtimeMs === st.mtimeMs && cached.size === st.size) {
    return cached;
  }
  const entry: CacheEntry = {
    mtimeMs: st.mtimeMs,
    size: st.size,
    sha256: _sha256OfFile(p),
  };
  _shaCache.set(name, entry);
  return entry;
}

// ═══════════════════════════════════════════════════════════════════════════
//   ALLOWED FILES — grouped by purpose so apps are easy to find.
//   When you add a new GTK4 app, add it to "GTK4 USER APPS" only.
// ═══════════════════════════════════════════════════════════════════════════
const ALLOWED_FILES: Record<string, string> = {
  // ── ★ MASTER PALETTE — single source of truth (rev r13) ─────────────────
  "nyxus_palette.py":       "nyxus_palette.py",        //  Python palette constants
  "nyxus-palette.css":      "nyxus-palette.css",       //  CSS @define-color palette
  // ── ★ THE NYXUS GTK4 USER APPS ───────────────────────────────────────────
  // 1. Home (workspace dashboard) — see TGZ section below
  // rev r6-eww (2026-05-11): nyxus_quicksettings / _clock / _calendar /
  // _cheatsheet REMOVED — replaced by native EWW windows. Standalone
  // nyxus_powermenu.py later returned for launcher/menu invocation.
  "nyxus_notes.py":         "nyxus_notes.py",          //  2. Notes (Tesla-min)
  "nyxus_notepad.py":       "nyxus_notepad.py",        //  3. Notepad
  "nyxus_stickies.py":      "nyxus_stickies.py",       //  4. Stickies
  "nyxus_terminal.py":      "nyxus_terminal.py",       //  6. Terminal
  "nyxus_settings.py":      "nyxus_settings.py",       //  7. Settings
  "nyxus_wallpaper_studio.py": "nyxus_wallpaper_studio.py", //  Wallpaper Studio
  "nyxus_sysmon_gtk.py":    "nyxus_sysmon_gtk.py",     //  8. Sysmon (GTK)
  "nyxus_control.py":       "nyxus_control.py",        //  9. Control
  "nyxus_launcher.py":      "nyxus_launcher.py",       // 10. Launcher (Spotlight)
  "nyxus_screenshot.py":    "nyxus_screenshot.py",     // 12. Screenshot
  "nyxus_store.py":         "nyxus_store.py",          // 13. App Store
  "nyxus_powermenu.py":     "nyxus_powermenu.py",      // 14. Power Menu

  // ── ★ EWW SHELL (rev r6-eww, 2026-05-11 — replaces waybar + 5 py apps) ──
  // 4 bars + dashboard + powermenu + cheatsheet + 3 OSDs. All real backends.
  "nyxus-eww-launch":           "nyxus-eww-launch",
  "nyxus-mission-control-toggle":"nyxus-mission-control-toggle",
  "nyxus-eww.service":          "nyxus-eww.service",
  "nyxus-crashd.service":       "nyxus-crashd.service",
  // USB plug-in / removal toast notifier (Tier 1 batch 2, r10).
  // Daemon = nyxus_usb_watch.py (under GTK4 USER APPS-style nyxus_*.py
  // glob); user systemd unit lives at /usr/lib/systemd/user/ on the
  // ISO and is downloaded to ~/.config/systemd/user/ at runtime.
  "nyxus_usb_watch.py":         "nyxus_usb_watch.py",
  "nyxus-usb-watch.service":    "nyxus-usb-watch.service",
  // r10 batch 5 (2026-05-13) — Tier 3 #15/#16/#17 helpers
  "nyxus_hotcorners.py":               "nyxus_hotcorners.py",
  "nyxus-hotcorners.service":          "nyxus-hotcorners.service",
  "nyxus-nightlight.sh":               "nyxus-nightlight.sh",
  "nyxus-nightlight.service":          "nyxus-nightlight.service",
  "nyxus-dynamic-wallpaper.sh":        "nyxus-dynamic-wallpaper.sh",
  "nyxus-dynamic-wallpaper.service":   "nyxus-dynamic-wallpaper.service",
  "nyxus-dynamic-wallpaper.timer":     "nyxus-dynamic-wallpaper.timer",
  // r10 batch 6 (2026-05-13) — Phase 6.26 Calamares + 6.27 snapshot scrubber
  "nyxus-postinstall.sh":                       "nyxus-postinstall.sh",
  "calamares/settings.conf":                    "calamares/settings.conf",
  "calamares/modules/shellprocess_nyxus.conf":  "calamares/modules/shellprocess_nyxus.conf",
  "calamares/shellprocess_nyxus.conf":          "calamares/modules/shellprocess_nyxus.conf",
  "calamares/branding/nyxus/branding.desc":     "calamares/branding/nyxus/branding.desc",
  "calamares/branding/nyxus/show.qml":          "calamares/branding/nyxus/show.qml",
  "calamares/branding/nyxus/stylesheet.qss":    "calamares/branding/nyxus/stylesheet.qss",
  // r10 batch 7 (2026-05-13) — Phase 6.31 i18n scaffold + 7.34 swaync
  "nyxus_i18n.py":                              "nyxus_i18n.py",
  "nyxus_account.py":                           "nyxus_account.py",
  "nyxus_backup.py":                            "nyxus_backup.py",
  "nyxus_parental.py":                          "nyxus_parental.py",
  "nyxus_settings_accessibility.py":            "nyxus_settings_accessibility.py",
  "nyxus_settings_notifications.py":            "nyxus_settings_notifications.py",
  "nyxus_settings_sandbox.py":                  "nyxus_settings_sandbox.py",
  "nyxus_settings_snapshots.py":                "nyxus_settings_snapshots.py",
  "nyxus-crash-report.py":                      "nyxus-crash-report.py",
  "locale/nyxus.pot":                           "locale/nyxus.pot",
  "locale/extract.sh":                          "locale/extract.sh",
  "locale/compile.sh":                          "locale/compile.sh",
  "locale/Makefile":                            "locale/Makefile",
  "locale/en/LC_MESSAGES/nyxus.po":             "locale/en/LC_MESSAGES/nyxus.po",
  "locale/es/LC_MESSAGES/nyxus.po":             "locale/es/LC_MESSAGES/nyxus.po",
  "locale/fr/LC_MESSAGES/nyxus.po":             "locale/fr/LC_MESSAGES/nyxus.po",
  "eww/eww.yuck":               "eww/eww.yuck",
  "eww/eww.scss":               "eww/eww.scss",
  "eww/nyxus.conf":             "eww/nyxus.conf",
  "eww/README.md":              "eww/README.md",
  "eww/scripts/audio.sh":         "eww/scripts/audio.sh",
  "eww/scripts/battery.sh":       "eww/scripts/battery.sh",
  "eww/scripts/bluetooth.sh":     "eww/scripts/bluetooth.sh",
  "eww/scripts/brightness.sh":    "eww/scripts/brightness.sh",
  "eww/scripts/calendar.sh":      "eww/scripts/calendar.sh",
  "eww/scripts/cpu-bars.sh":      "eww/scripts/cpu-bars.sh",
  "eww/scripts/mic.sh":           "eww/scripts/mic.sh",
  "eww/scripts/network.sh":       "eww/scripts/network.sh",
  "eww/scripts/notifications.sh": "eww/scripts/notifications.sh",
  "eww/scripts/osd-show.sh":      "eww/scripts/osd-show.sh",
  "eww/scripts/player.sh":        "eww/scripts/player.sh",
  "eww/scripts/power-profile.sh": "eww/scripts/power-profile.sh",
  "eww/scripts/sys-pulse.sh":     "eww/scripts/sys-pulse.sh",
  "eww/scripts/ticker.sh":        "eww/scripts/ticker.sh",
  "eww/scripts/updates.sh":       "eww/scripts/updates.sh",
  "eww/scripts/weather.sh":       "eww/scripts/weather.sh",
  "eww/scripts/workspaces.sh":    "eww/scripts/workspaces.sh",
  // ── Sprint 1 (rev r9-eww, 2026-05-11) — 6 flyouts: QS / WiFi / BT / Mix / Cal / Notif
  "eww/scripts/quicksettings.sh": "eww/scripts/quicksettings.sh",
  "eww/scripts/qs-toggle.sh":     "eww/scripts/qs-toggle.sh",
  "eww/scripts/wifi-list.sh":     "eww/scripts/wifi-list.sh",
  "eww/scripts/wifi-action.sh":   "eww/scripts/wifi-action.sh",
  "eww/scripts/bt-list.sh":       "eww/scripts/bt-list.sh",
  "eww/scripts/bt-action.sh":     "eww/scripts/bt-action.sh",
  "eww/scripts/audio-sinks.sh":   "eww/scripts/audio-sinks.sh",
  "eww/scripts/audio-action.sh":  "eww/scripts/audio-action.sh",
  "eww/scripts/calendar-month.sh":"eww/scripts/calendar-month.sh",
  "eww/scripts/notif-history.sh": "eww/scripts/notif-history.sh",
  "eww/scripts/notif-action.sh":  "eww/scripts/notif-action.sh",
  // ── Wave 2 / Sprint 2a · Welcome Wizard (rev r9-eww, 2026-05-11) ───────
  "nyxus_welcome.py":             "nyxus_welcome.py",
  "nyxus-welcome":                "nyxus-welcome",
  "nyxus-welcome-helper":         "nyxus-welcome-helper",
  "nyxus-welcome.policy":         "nyxus-welcome.policy",
  "nyxus-account-helper":         "nyxus-account-helper",
  "nyxus-backup-helper":          "nyxus-backup-helper",
  "nyxus-doctor-helper":          "nyxus-doctor-helper",
  "nyxus-usbwatch-helper":        "nyxus-usbwatch-helper",
  "nyxus-parental-helper":        "nyxus-parental-helper",
  "polkit-policies/com.nyxus.account.policy":  "polkit-policies/com.nyxus.account.policy",
  "polkit-policies/com.nyxus.backup.policy":   "polkit-policies/com.nyxus.backup.policy",
  "polkit-policies/com.nyxus.doctor.policy":   "polkit-policies/com.nyxus.doctor.policy",
  "polkit-policies/com.nyxus.firewall.policy": "polkit-policies/com.nyxus.firewall.policy",
  "polkit-policies/com.nyxus.parental.policy": "polkit-policies/com.nyxus.parental.policy",
  "polkit-policies/com.nyxus.updater.policy":  "polkit-policies/com.nyxus.updater.policy",
  "polkit-policies/com.nyxus.usbwatch.policy": "polkit-policies/com.nyxus.usbwatch.policy",
  "desktop-entries/nyxus-account.desktop":      "desktop-entries/nyxus-account.desktop",
  "desktop-entries/nyxus-backup.desktop":       "desktop-entries/nyxus-backup.desktop",
  "desktop-entries/nyxus-chrome.desktop":       "desktop-entries/nyxus-chrome.desktop",
  "desktop-entries/nyxus-clipboard.desktop":    "desktop-entries/nyxus-clipboard.desktop",
  "desktop-entries/nyxus-control.desktop":      "desktop-entries/nyxus-control.desktop",
  "desktop-entries/nyxus-crashd.desktop":       "desktop-entries/nyxus-crashd.desktop",
  "desktop-entries/nyxus-demon-wake.desktop":   "desktop-entries/nyxus-demon-wake.desktop",
  "desktop-entries/nyxus-doctor.desktop":       "desktop-entries/nyxus-doctor.desktop",
  "desktop-entries/nyxus-drop.desktop":         "desktop-entries/nyxus-drop.desktop",
  "desktop-entries/nyxus-error.desktop":        "desktop-entries/nyxus-error.desktop",
  "desktop-entries/nyxus-files.desktop":        "desktop-entries/nyxus-files.desktop",
  "desktop-entries/nyxus-gen-icons.desktop":    "desktop-entries/nyxus-gen-icons.desktop",
  "desktop-entries/nyxus-hotcorners.desktop":   "desktop-entries/nyxus-hotcorners.desktop",
  "desktop-entries/nyxus-i18n.desktop":         "desktop-entries/nyxus-i18n.desktop",
  "desktop-entries/nyxus-launcher.desktop":     "desktop-entries/nyxus-launcher.desktop",
  "desktop-entries/nyxus-motd.desktop":         "desktop-entries/nyxus-motd.desktop",
  "desktop-entries/nyxus-notepad.desktop":      "desktop-entries/nyxus-notepad.desktop",
  "desktop-entries/nyxus-notes.desktop":        "desktop-entries/nyxus-notes.desktop",
  "desktop-entries/nyxus-palette.desktop":      "desktop-entries/nyxus-palette.desktop",
  "desktop-entries/nyxus-powermenu.desktop":    "desktop-entries/nyxus-powermenu.desktop",
  "desktop-entries/nyxus-preboot.desktop":      "desktop-entries/nyxus-preboot.desktop",
  "desktop-entries/nyxus-screensaver.desktop":  "desktop-entries/nyxus-screensaver.desktop",
  "desktop-entries/nyxus-screenshot.desktop":   "desktop-entries/nyxus-screenshot.desktop",
  "desktop-entries/nyxus-security.desktop":     "desktop-entries/nyxus-security.desktop",
  "desktop-entries/nyxus-settings.desktop":     "desktop-entries/nyxus-settings.desktop",
  "desktop-entries/nyxus-wallpaper-studio.desktop": "desktop-entries/nyxus-wallpaper-studio.desktop",
  "desktop-entries/nyxus-splash.desktop":       "desktop-entries/nyxus-splash.desktop",
  "desktop-entries/nyxus-stickies.desktop":     "desktop-entries/nyxus-stickies.desktop",
  "desktop-entries/nyxus-store.desktop":        "desktop-entries/nyxus-store.desktop",
  "desktop-entries/nyxus-sysmon-gtk.desktop":   "desktop-entries/nyxus-sysmon-gtk.desktop",
  "desktop-entries/nyxus-terminal.desktop":     "desktop-entries/nyxus-terminal.desktop",
  "desktop-entries/nyxus-toast.desktop":        "desktop-entries/nyxus-toast.desktop",
  "desktop-entries/nyxus-updater.desktop":      "desktop-entries/nyxus-updater.desktop",
  "desktop-entries/nyxus-usb-watch.desktop":    "desktop-entries/nyxus-usb-watch.desktop",
  "desktop-entries/nyxus-welcome.desktop":      "desktop-entries/nyxus-welcome.desktop",
  "com.nyxus.parental.policy":    "com.nyxus.parental.policy",

  // ── ★ TGZ APP PACKAGES (heavyweight multi-module apps) ───────────────────
  "nyxus-home.tgz":      "nyxus-home.tgz",       // Home (workspace 0)
  "nyxus-start.tgz":     "nyxus-start.tgz",      // Flyout: Start menu / app drawer
  "nyxus-godsapp.tgz":   "nyxus-godsapp.tgz",    // GodsApp (security suite)
  "nyxus-studio.tgz":    "nyxus-studio.tgz",     // Studio (creative suite)
  "nyxus-sage.tgz":      "nyxus-sage.tgz",       // Sage
  "nyxus-shield.tgz":    "nyxus-shield.tgz",     // Shield
  "nyxus-intel.tgz":     "nyxus-intel.tgz",      // Intel
  "nyxus-panel.tgz":     "nyxus-panel.tgz",      // Panel (top bar)
  "nyxus-weather.tgz":   "nyxus-weather.tgz",    // Weather (rich variant)
  "nyxus-notepad.tgz":   "nyxus-notepad.tgz",    // Notepad (rich variant)
  "nyxus-passwords.tgz": "nyxus-passwords.tgz",  // Passwords vault
  "nyxus-phantom.tgz":   "nyxus-phantom.tgz",    // Phantom

  // ── ★ TGZ INSTALLERS (one-shot scripts that unpack each tgz) ─────────────
  "nyxus_home_install.sh":      "nyxus_home_install.sh",
  "nyxus_start_install.sh":     "nyxus_start_install.sh",
  "nyxus_godsapp_install.sh":   "nyxus_godsapp_install.sh",
  "nyxus_studio_install.sh":    "nyxus_studio_install.sh",
  "nyxus_sage_install.sh":      "nyxus_sage_install.sh",
  "nyxus_security_install.sh":  "nyxus_security_install.sh",
  "nyxus_intel_install.sh":     "nyxus_intel_install.sh",
  "nyxus_panel_install.sh":     "nyxus_panel_install.sh",
  "nyxus_weather_install.sh":   "nyxus_weather_install.sh",
  "nyxus_notepad_install.sh":   "nyxus_notepad_install.sh",
  "nyxus_passwords_install.sh": "nyxus_passwords_install.sh",

  // ── ★ SHARED CHROME / RUNTIME (loaded by every GTK4 app) ─────────────────
  "nyxus_chrome.py":       "nyxus_chrome.py",        // Unified visual chrome
  "nyxus_screensaver.py":  "nyxus_screensaver.py",
  "nyxus_demon_wake.py":   "nyxus_demon_wake.py",
  "nyxus_gen_icons.py":    "nyxus_gen_icons.py",

  // ── ★ BOOT / SYSTEM SCRIPTS (run pre-login or at startup) ────────────────
  "nyxus_motd.py":     "nyxus_motd.py",
  "nyxus_error.py":    "nyxus_error.py",
  "nyxus_preboot.py":  "nyxus_preboot.py",
  "nyxus_splash.py":   "nyxus_splash.py",
  "nyxus_doctor.py":   "nyxus_doctor.py",
  "nyxus_verify.sh":   "nyxus_verify.sh",

  // ── ★ INSTALLERS / RESYNC ────────────────────────────────────────────────
  "nyxus_install.sh":    "nyxus_install.sh",
  "nyxus-resync-all.sh": "nyxus-resync-all.sh",
  "nyxus-bootstrap":      "nyxus-bootstrap",       // first-boot wrapper (Hyprland exec-once)
  "nyxus-wait-bootstrap": "nyxus-wait-bootstrap",  // gates dependent autostarts on bootstrap completion
  "nyxus-build-iso.sh":  "nyxus-build-iso.sh",
  "hypr-doctor.sh":      "hypr-doctor.sh",

  // ── ★ HYPRLAND CONFIGS ───────────────────────────────────────────────────
  "hyprland.conf":               "hyprland.conf",
  "hyprlock.conf":               "hyprlock.conf",
  // A6 (2026-05-12): nyxus-hyprlock.conf was merged INTO hyprlock.conf
  // (one canonical filename, branded variant with login-stars wallpaper).
  // Allowlist entry removed — file no longer exists in nyxus-scripts/.
  "hypridle.conf":               "hypridle.conf",
  "nyxus-hyprland-rules.conf":   "nyxus-hyprland-rules.conf",
  "nyxus-hyprland-blur.conf":    "nyxus-hyprland-blur.conf",
  "nyxus-hyprland-fog.conf":     "nyxus-hyprland-fog.conf",
  "nyxus-hyprland-opacity.conf":   "nyxus-hyprland-opacity.conf",
  "nyxus-hyprland-general.conf":   "nyxus-hyprland-general.conf",
  "nyxus-hyprland-layerblur.conf": "nyxus-hyprland-layerblur.conf",
  "nyxus-hyprland-mission.conf":   "nyxus-hyprland-mission.conf",

  // ── ★ DESKTOP UI CONFIGS (rofi, alacritty, dunst, wlogout) ───────────────
  // rev r6-eww (2026-05-11): waybar-config.json / waybar-style.css /
  // waybar-ticker.sh / waybar-stats.sh / nyxus-sys-pulse.sh REMOVED — EWW
  // shell now drives the bars (ticker/sys-pulse live in eww/scripts/).
  "nyxus-notif-status.sh": "nyxus-notif-status.sh",
  "alacritty.toml":        "alacritty.toml",
  "rofi-config.rasi":      "rofi-config.rasi",
  "rofi-nyxus.rasi":       "rofi-nyxus.rasi",
  "rofi-startmenu.rasi":   "rofi-startmenu.rasi",
  "nyxus-dunstrc":         "nyxus-dunstrc",
  "wlogout-style.css":     "wlogout-style.css",
  "wlogout-layout":        "wlogout-layout",

  // ── ★ THEMES / TARBALLS ──────────────────────────────────────────────────
  "nyxus-sddm-theme.tar.gz":  "nyxus-sddm-theme.tar.gz",
  "nyxus-void-splash.tar.gz": "nyxus-void-splash.tar.gz",
  "nyxus-wlogout.tar.gz":     "nyxus-wlogout.tar.gz",
  "nyxus-ui-configs.tar.gz":  "nyxus-ui-configs.tar.gz",
  "nyxus-greetd.toml":        "nyxus-greetd.toml",

  // ── ★ FROST WALLPAPER ────────────────────────────────────────────────────
  "nyxus-frost-sierengowski.png": "nyxus-frost-sierengowski.png",
  "nyxus-fog.py":                 "nyxus-fog.py",
  "nyxus-set-frost-wallpaper.sh": "nyxus-set-frost-wallpaper.sh",
  "wallpaper-rotate.sh":          "wallpaper-rotate.sh",
  "nyxus-ink-swirl.png":          "nyxus-ink-swirl.png",

  // ── ★ FROST TILE TEXTURES (repeating cream tessellations) ───────────────
  // tile-grid (triangle tessellation) repeats inside cards & headerbars.
  // tile-glyphs (runic wall) repeats vertically inside the right-bar column.
  "nyxus-frost-tile-grid.png":    "nyxus-frost-tile-grid.png",
  "nyxus-frost-tile-glyphs.png":  "nyxus-frost-tile-glyphs.png",

  // ── ★ BRAND ASSETS (logos, taskbar bgs, demon) ───────────────────────────
  "nyxus-sierengowski-clean.png": "nyxus-sierengowski-clean.png",
  "nyxus-taskbar-bg.png":         "nyxus-taskbar-bg.png",
  "nyxus-rightbar-bg.png":        "nyxus-rightbar-bg.png",
  "nyxus-starlight.png":          "nyxus-starlight.png",
  "nyxus-void-wallpaper.mp4":     "nyxus-void-wallpaper.mp4",
  "nyxus-login-stars.png":        "nyxus-login-stars.png",
  "nyxus-monogram-mist.png":      "nyxus-monogram-mist.png",
  "nyxus-topbar-mist.png":        "nyxus-topbar-mist.png",
  "nyxus-hyprlock-eye.png":       "nyxus-hyprlock-eye.png",
  "nyxus-bar-stone.png":          "nyxus-bar-stone.png",
  "nyxus-starfield-wall.png":     "nyxus-starfield-wall.png",
  "nyxus-drifter-wall.png":       "nyxus-drifter-wall.png",
  "nyxus-void-vortex.png":        "nyxus-void-vortex.png",  // EWW-era default wallpaper (rev r6-eww)
  "nyxus-demon.png":              "nyxus-demon.png",

  // ── ★ WALLPAPERS (15 backgrounds) ────────────────────────────────────────
  "nyxus-bg-01.png": "nyxus-bg-01.png",
  "nyxus-bg-02.png": "nyxus-bg-02.png",
  "nyxus-bg-03.png": "nyxus-bg-03.png",
  "nyxus-bg-04.png": "nyxus-bg-04.png",
  "nyxus-bg-05.png": "nyxus-bg-05.png",
  "nyxus-bg-06.png": "nyxus-bg-06.png",
  "nyxus-bg-07.png": "nyxus-bg-07.png",
  "nyxus-bg-08.png": "nyxus-bg-08.png",
  "nyxus-bg-09.png": "nyxus-bg-09.png",
  "nyxus-bg-10.png": "nyxus-bg-10.png",
  "nyxus-bg-11.png": "nyxus-bg-11.png",
  "nyxus-bg-12.png": "nyxus-bg-12.png",
  "nyxus-bg-13.png": "nyxus-bg-13.png",
  "nyxus-bg-14.png": "nyxus-bg-14.png",
  "nyxus-bg-15.png": "nyxus-bg-15.png",
  "nyxus-bg-16.png": "nyxus-bg-16.png",

  // ── ★ GRAFFITI ASSETS (24 chrome backgrounds) ────────────────────────────
  "nyxus-graffiti-01.png": "nyxus-graffiti-01.png",
  "nyxus-graffiti-02.png": "nyxus-graffiti-02.png",
  "nyxus-graffiti-03.png": "nyxus-graffiti-03.png",
  "nyxus-graffiti-04.png": "nyxus-graffiti-04.png",
  "nyxus-graffiti-05.png": "nyxus-graffiti-05.png",
  "nyxus-graffiti-06.png": "nyxus-graffiti-06.png",
  "nyxus-graffiti-07.png": "nyxus-graffiti-07.png",
  "nyxus-graffiti-08.png": "nyxus-graffiti-08.png",
  "nyxus-graffiti-09.png": "nyxus-graffiti-09.png",
  "nyxus-graffiti-10.png": "nyxus-graffiti-10.png",
  "nyxus-graffiti-11.png": "nyxus-graffiti-11.png",
  "nyxus-graffiti-12.png": "nyxus-graffiti-12.png",
  "nyxus-graffiti-13.png": "nyxus-graffiti-13.png",
  "nyxus-graffiti-14.png": "nyxus-graffiti-14.png",
  "nyxus-graffiti-15.png": "nyxus-graffiti-15.png",
  "nyxus-graffiti-16.png": "nyxus-graffiti-16.png",
  "nyxus-graffiti-17.png": "nyxus-graffiti-17.png",
  "nyxus-graffiti-18.png": "nyxus-graffiti-18.png",
  "nyxus-graffiti-19.png": "nyxus-graffiti-19.png",
  "nyxus-graffiti-20.png": "nyxus-graffiti-20.png",
  "nyxus-graffiti-21.png": "nyxus-graffiti-21.png",
  "nyxus-graffiti-22.png": "nyxus-graffiti-22.png",
  "nyxus-graffiti-23.png": "nyxus-graffiti-23.png",
  "nyxus-graffiti-24.png": "nyxus-graffiti-24.png",

  // ── ★ DOCUMENTATION ──────────────────────────────────────────────────────
  "README.md":    "README.md",
  "LICENSE.md":   "LICENSE.md",
  "CHANGELOG.md": "CHANGELOG.md",
  "CREDITS.md":   "CREDITS.md",
};

// ── SHA256 manifest ─────────────────────────────────────────────────────
// Returns { version, generated_at, files: { name: { sha256, size_bytes } } }
// Clients (nyxus_verify.sh / NYXUS App Store) hit this endpoint, then
// SHA-verify each subsequently-downloaded file. Defends against single-file
// transit corruption and single-file server tampering.
router.get("/download/nyxus/manifest.json", (_req, res) => {
  const files: Record<string, { sha256: string; size_bytes: number }> = {};
  for (const name of Object.keys(ALLOWED_FILES)) {
    const p = path.join(SCRIPTS_DIR, ALLOWED_FILES[name]);
    const entry = _hashOrCached(name, p);
    if (entry) {
      files[name] = { sha256: entry.sha256, size_bytes: entry.size };
    }
  }
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.json({
    version: 1,
    generated_at: new Date().toISOString(),
    file_count: Object.keys(files).length,
    files,
  });
});

// Plain-text manifest in `sha256sum -c` format. Useful from shell scripts:
//   curl -fsSL .../manifest.txt > /tmp/m && sha256sum -c /tmp/m
router.get("/download/nyxus/manifest.txt", (_req, res) => {
  const lines: string[] = [];
  for (const name of Object.keys(ALLOWED_FILES)) {
    const p = path.join(SCRIPTS_DIR, ALLOWED_FILES[name]);
    const entry = _hashOrCached(name, p);
    if (entry) lines.push(`${entry.sha256}  ${name}`);
  }
  res.setHeader("Content-Type", "text/plain");
  res.setHeader("Cache-Control", "no-store");
  res.send(lines.join("\n") + "\n");
});

// Express 5 wildcard splat — matches nested paths like `eww/scripts/audio.sh`.
// req.params.splat is an array of path segments; join with "/" to recover the
// original key shape used in ALLOWED_FILES (e.g. "eww/scripts/audio.sh").
// Strict allowlist lookup below means the splat cannot be used for traversal.
router.get("/download/nyxus/{*splat}", (req, res) => {
  const splat = req.params.splat;
  const filename = Array.isArray(splat) ? splat.join("/") : String(splat ?? "");

  if (!ALLOWED_FILES[filename]) {
    res.status(404).json({ error: "File not found" });
    return;
  }

  const filePath = path.join(SCRIPTS_DIR, ALLOWED_FILES[filename]);

  if (!fs.existsSync(filePath)) {
    res.status(404).json({ error: "Script not found on disk" });
    return;
  }

  const contentType =
    filename.endsWith(".sh")     ? "text/x-sh" :
    filename.endsWith(".py")     ? "text/x-python" :
    filename.endsWith(".json")   ? "application/json" :
    filename.endsWith(".css")    ? "text/css" :
    filename.endsWith(".conf")   ? "text/plain" :
    filename.endsWith(".toml")   ? "text/plain" :
    filename.endsWith(".png")    ? "image/png" :
    filename.endsWith(".tar.gz") ? "application/gzip" :
    filename.endsWith(".tgz")    ? "application/gzip" :
    "text/plain";

  // ── ★ ANTI-STALE GUARANTEE ──────────────────────────────────────────────
  // Defeats every cache layer (browser, CDN, corporate proxy, Replit edge):
  //   * Cache-Control: no-store + no-cache + must-revalidate + max-age=0
  //   * Pragma: no-cache              (HTTP/1.0 backward compat)
  //   * Expires: 0                    (HTTP/1.0 backward compat)
  // After this, every GET hits this server fresh — there is no way for any
  // intermediary to serve an older copy of a NYXUS file. Pairs with the
  // X-File-SHA256 header so curl can verify the bytes after download:
  //     curl -fsSL .../nyxus-hyprland-blur.conf -D /tmp/h
  //     grep -i x-file-sha256 /tmp/h
  // and matches the value in /api/download/nyxus/manifest.json.
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  const entry = _hashOrCached(filename, filePath);
  if (entry) {
    res.setHeader("X-File-SHA256", entry.sha256);
    res.setHeader("X-File-Size", String(entry.size));
    res.setHeader("X-File-MTime", String(Math.floor(entry.mtimeMs)));
  }
  res.setHeader("Content-Type", contentType);
  res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);

  // Disable Express's automatic ETag + Last-Modified on sendFile so no
  // intermediary can issue a conditional GET and receive 304. Always 200,
  // always full body, always the freshest bytes on disk.
  res.sendFile(filePath, { etag: false, lastModified: false, cacheControl: false });
});

router.get("/download/nyxus", (_req, res) => {
  const available = Object.keys(ALLOWED_FILES).map((name) => ({
    name,
    url: `/api/download/nyxus/${name}`,
  }));
  res.json({ scripts: available });
});

export default router;

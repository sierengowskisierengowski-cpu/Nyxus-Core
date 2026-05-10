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
  // ── ★ THE 12 NYXUS GTK4 USER APPS (the "11 + flyout") ────────────────────
  // 1. Home (workspace dashboard) — see TGZ section below
  "nyxus_notes.py":         "nyxus_notes.py",          //  2. Notes (Tesla-min)
  "nyxus_stickies.py":      "nyxus_stickies.py",       //  4. Stickies
  "nyxus_terminal.py":      "nyxus_terminal.py",       //  6. Terminal
  "nyxus_settings.py":      "nyxus_settings.py",       //  7. Settings
  "nyxus_sysmon_gtk.py":    "nyxus_sysmon_gtk.py",     //  8. Sysmon (GTK)
  "nyxus_control.py":       "nyxus_control.py",        //  9. Control
  "nyxus_launcher.py":      "nyxus_launcher.py",       // 10. Launcher (Spotlight)
  "nyxus_powermenu.py":     "nyxus_powermenu.py",      // 11. Powermenu
  "nyxus_screenshot.py":    "nyxus_screenshot.py",     // 12. Screenshot
  "nyxus_quicksettings.py": "nyxus_quicksettings.py",  // Flyout: Quicksettings
  "nyxus_calendar.py":      "nyxus_calendar.py",       // 13. Calendar (month view + per-day notes)
  "nyxus_clock.py":         "nyxus_clock.py",          // 14. Clock (digital + world + stopwatch)
  "nyxus_cheatsheet.py":    "nyxus_cheatsheet.py",     // 15. Cheatsheet (live keybinds parser, Super+/)

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
  "hypridle.conf":               "hypridle.conf",
  "nyxus-hyprlock.conf":         "nyxus-hyprlock.conf",
  "nyxus-hyprland-rules.conf":   "nyxus-hyprland-rules.conf",
  "nyxus-hyprland-blur.conf":    "nyxus-hyprland-blur.conf",
  "nyxus-hyprland-fog.conf":     "nyxus-hyprland-fog.conf",
  "nyxus-hyprland-opacity.conf":   "nyxus-hyprland-opacity.conf",
  "nyxus-hyprland-general.conf":   "nyxus-hyprland-general.conf",
  "nyxus-hyprland-layerblur.conf": "nyxus-hyprland-layerblur.conf",

  // ── ★ DESKTOP UI CONFIGS (waybar, rofi, alacritty, dunst, wlogout) ───────
  "waybar-config.json":    "waybar-config.json",
  "waybar-style.css":      "waybar-style.css",
  "waybar-ticker.sh":      "waybar-ticker.sh",
  "nyxus-notif-status.sh": "nyxus-notif-status.sh",
  "waybar-stats.sh":       "waybar-stats.sh",
  "nyxus-sys-pulse.sh":    "nyxus-sys-pulse.sh",
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
  "nyxus-waybar-stars.png":       "nyxus-waybar-stars.png",
  "nyxus-monogram-mist.png":      "nyxus-monogram-mist.png",
  "nyxus-topbar-mist.png":        "nyxus-topbar-mist.png",
  "nyxus-hyprlock-eye.png":       "nyxus-hyprlock-eye.png",
  "nyxus-bar-stone.png":          "nyxus-bar-stone.png",
  "nyxus-starfield-wall.png":     "nyxus-starfield-wall.png",
  "nyxus-drifter-wall.png":       "nyxus-drifter-wall.png",
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

router.get("/download/nyxus/:filename", (req, res) => {
  const { filename } = req.params;

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

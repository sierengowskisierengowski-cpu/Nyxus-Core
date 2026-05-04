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

const ALLOWED_FILES: Record<string, string> = {
  "nyxus_motd.py":        "nyxus_motd.py",
  "nyxus_error.py":       "nyxus_error.py",
  "nyxus_preboot.py":     "nyxus_preboot.py",
  "nyxus_splash.py":      "nyxus_splash.py",
  "nyxus_install.sh":     "nyxus_install.sh",
  "nyxus-resync-all.sh":  "nyxus-resync-all.sh",
  "nyxus-hyprland-rules.conf": "nyxus-hyprland-rules.conf",
  "hyprland.conf":        "hyprland.conf",
  "waybar-config.json":   "waybar-config.json",
  "waybar-style.css":     "waybar-style.css",
  "alacritty.toml":       "alacritty.toml",
  "nyxus-sddm-theme.tar.gz":  "nyxus-sddm-theme.tar.gz",
  "hyprlock.conf":            "hyprlock.conf",
  "nyxus-wlogout.tar.gz":    "nyxus-wlogout.tar.gz",
  "wlogout-style.css":       "wlogout-style.css",
  "wlogout-layout":          "wlogout-layout",
  "nyxus_terminal.py":       "nyxus_terminal.py",
  "nyxus-ui-configs.tar.gz": "nyxus-ui-configs.tar.gz",
  "hypridle.conf":           "hypridle.conf",
  "rofi-config.rasi":        "rofi-config.rasi",
  "rofi-nyxus.rasi":         "rofi-nyxus.rasi",
  "waybar-ticker.sh":             "waybar-ticker.sh",
  "waybar-stats.sh":              "waybar-stats.sh",
  "nyxus_quicksettings.py":       "nyxus_quicksettings.py",
  "rofi-startmenu.rasi":          "rofi-startmenu.rasi",
  "nyxus-sierengowski-clean.png": "nyxus-sierengowski-clean.png",
  "nyxus-taskbar-bg.png":         "nyxus-taskbar-bg.png",
  "nyxus-taskbar-bg2.png":        "nyxus-taskbar-bg2.png",
  "nyxus-rightbar-bg.png":        "nyxus-rightbar-bg.png",
  "nyxus_sysmon.py":              "nyxus_sysmon.py",
  "nyxus_sysmon_gtk.py":          "nyxus_sysmon_gtk.py",
  "nyxus_stickies.py":            "nyxus_stickies.py",
  "nyxus_weather.py":             "nyxus_weather.py",
  "nyxus_notepad.py":             "nyxus_notepad.py",
  "nyxus_gen_icons.py":           "nyxus_gen_icons.py",
  "nyxus_control.py":             "nyxus_control.py",
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
  "nyxus-waybar-right.png": "nyxus-waybar-right.png",
  "nyxus-dunstrc":          "nyxus-dunstrc",
  "nyxus_doctor.py":        "nyxus_doctor.py",
  "nyxus_launcher.py":      "nyxus_launcher.py",
  "nyxus_powermenu.py":     "nyxus_powermenu.py",
  "nyxus_screenshot.py":    "nyxus_screenshot.py",
  "nyxus-hyprlock.conf":    "nyxus-hyprlock.conf",
  "nyxus-greetd.toml":      "nyxus-greetd.toml",
  "nyxus_settings.py":     "nyxus_settings.py",
  "nyxus_chrome.py":       "nyxus_chrome.py",
  "nyxus_screensaver.py":  "nyxus_screensaver.py",
  "nyxus_demon_wake.py":   "nyxus_demon_wake.py",
  "nyxus-demon.png":       "nyxus-demon.png",
  "nyxus_verify.sh":       "nyxus_verify.sh",
  "nyxus-phantom.tgz":          "nyxus-phantom.tgz",
  "nyxus-shield.tgz":           "nyxus-shield.tgz",
  "nyxus-godsapp.tgz":          "nyxus-godsapp.tgz",
  "nyxus_security_install.sh":  "nyxus_security_install.sh",
  "nyxus-studio.tgz":           "nyxus-studio.tgz",
  "nyxus_studio_install.sh":    "nyxus_studio_install.sh",
  "nyxus-sage.tgz":             "nyxus-sage.tgz",
  "nyxus_sage_install.sh":      "nyxus_sage_install.sh",
  "nyxus-panel.tgz":            "nyxus-panel.tgz",
  "nyxus_panel_install.sh":     "nyxus_panel_install.sh",
  "nyxus_godsapp_install.sh":   "nyxus_godsapp_install.sh",
  "nyxus-start.tgz":            "nyxus-start.tgz",
  "nyxus_start_install.sh":     "nyxus_start_install.sh",
  "nyxus-intel.tgz":            "nyxus-intel.tgz",
  "nyxus_intel_install.sh":     "nyxus_intel_install.sh",
  "nyxus-home.tgz":             "nyxus-home.tgz",
  "nyxus_home_install.sh":      "nyxus_home_install.sh",
  "nyxus-weather.tgz":            "nyxus-weather.tgz",
  "nyxus_weather_install.sh":     "nyxus_weather_install.sh",
  "nyxus-notepad.tgz":            "nyxus-notepad.tgz",
  "nyxus_notepad_install.sh":     "nyxus_notepad_install.sh",
  "nyxus-passwords.tgz":          "nyxus-passwords.tgz",
  "nyxus_passwords_install.sh":   "nyxus_passwords_install.sh",
  "wallpaper-rotate.sh":          "wallpaper-rotate.sh",
  "README.md":                    "README.md",
  "LICENSE.md":                   "LICENSE.md",
  "CHANGELOG.md":                 "CHANGELOG.md",
  "CREDITS.md":                   "CREDITS.md",
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
  res.setHeader("Content-Type", contentType);
  res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
  res.sendFile(filePath);
});

router.get("/download/nyxus", (_req, res) => {
  const available = Object.keys(ALLOWED_FILES).map((name) => ({
    name,
    url: `/api/download/nyxus/${name}`,
  }));
  res.json({ scripts: available });
});

export default router;

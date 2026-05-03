import { Router, type IRouter } from "express";
import path from "path";
import fs from "fs";

const router: IRouter = Router();

const SCRIPTS_DIR = path.resolve(__dirname, "nyxus-scripts");

const ALLOWED_FILES: Record<string, string> = {
  "nyxus_motd.py":        "nyxus_motd.py",
  "nyxus_error.py":       "nyxus_error.py",
  "nyxus_preboot.py":     "nyxus_preboot.py",
  "nyxus_splash.py":      "nyxus_splash.py",
  "nyxus_install.sh":     "nyxus_install.sh",
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
  "mako-config":              "mako-config",
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
  "nyxus_settings.py":     "nyxus_settings.py",
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

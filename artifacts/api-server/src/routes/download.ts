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
  "nyxus-wallpaper.png":    "nyxus-wallpaper.png",
  "nyxus-wallpaper-v2.png": "nyxus-wallpaper-v2.png",
  "nyxus-wallpaper-v3.png": "nyxus-wallpaper-v3.png",
  "nyxus-wallpaper-v4.png": "nyxus-wallpaper-v4.png",
  "nyxus-sddm-theme.tar.gz":  "nyxus-sddm-theme.tar.gz",
  "hyprlock.conf":            "hyprlock.conf",
  "nyxus-wlogout.tar.gz":    "nyxus-wlogout.tar.gz",
  "mako-config":              "mako-config",
  "nyxus-ui-configs.tar.gz": "nyxus-ui-configs.tar.gz",
  "hypridle.conf":           "hypridle.conf",
  "rofi-config.rasi":        "rofi-config.rasi",
  "rofi-nyxus.rasi":         "rofi-nyxus.rasi",
  "waybar-ticker.sh":        "waybar-ticker.sh",
  "waybar-stats.sh":         "waybar-stats.sh",
  "wallpaper-rotate.sh":     "wallpaper-rotate.sh",
  "nyxus-wall-01.png":       "nyxus-wall-01.png",
  "nyxus-wall-02.png":       "nyxus-wall-02.png",
  "nyxus-wall-03.png":       "nyxus-wall-03.png",
  "nyxus-wall-04.png":       "nyxus-wall-04.png",
  "nyxus-wall-05.png":       "nyxus-wall-05.png",
  "nyxus-wall-06.png":       "nyxus-wall-06.png",
  "nyxus-wall-07.png":       "nyxus-wall-07.png",
  "nyxus-wall-08.png":       "nyxus-wall-08.png",
  "nyxus-wall-09.png":       "nyxus-wall-09.png",
  "nyxus-wall-10.png":       "nyxus-wall-10.png",
  "nyxus-wall-11.png":       "nyxus-wall-11.png",
  "nyxus-wall-12.png":       "nyxus-wall-12.png",
  "nyxus-wall-13.png":       "nyxus-wall-13.png",
  "nyxus-wall-14.png":       "nyxus-wall-14.png",
  "nyxus-wall-15.png":       "nyxus-wall-15.png",
  "nyxus-wall-16.png":       "nyxus-wall-16.png",
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

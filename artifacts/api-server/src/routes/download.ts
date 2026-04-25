import { Router, type IRouter } from "express";
import path from "path";
import fs from "fs";

const router: IRouter = Router();

const SCRIPTS_DIR = path.resolve(__dirname, "../nyxus-scripts");

const ALLOWED_FILES: Record<string, string> = {
  "nyxus_motd.py":     "nyxus_motd.py",
  "nyxus_error.py":    "nyxus_error.py",
  "nyxus_preboot.py":  "nyxus_preboot.py",
  "nyxus_splash.py":   "nyxus_splash.py",
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

  res.setHeader("Content-Type", "text/x-python");
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

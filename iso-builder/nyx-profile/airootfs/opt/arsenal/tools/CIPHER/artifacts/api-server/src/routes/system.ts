import { Router } from "express";
import { getSystemStats } from "../lib/system-stats";
import { requireAuth } from "../lib/auth";

const router = Router();

router.get("/system/stats", requireAuth, async (req, res) => {
  try {
    const stats = await getSystemStats();
    res.json(stats);
  } catch (err) {
    req.log.error(err, "Failed to get system stats");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

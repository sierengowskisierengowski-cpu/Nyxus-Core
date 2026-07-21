import { Router } from "express";
import si from "systeminformation";

const router = Router();

// GET /stats/system
router.get("/stats/system", async (_req, res) => {
  const [cpuLoad, mem, disks] = await Promise.all([
    si.currentLoad(),
    si.mem(),
    si.fsSize(),
  ]);

  const diskInfo = disks.slice(0, 5).map(d => ({
    mount: d.mount,
    total: d.size,
    used: d.used,
    free: d.available,
    percent: d.size > 0 ? Math.round((d.used / d.size) * 100) : 0,
  }));

  res.json({
    cpu: Math.round(cpuLoad.currentLoad),
    memory: {
      total: mem.total,
      used: mem.used,
      free: mem.available,
      percent: Math.round((mem.used / mem.total) * 100),
    },
    disk: diskInfo,
    uptime: Math.floor(process.uptime()),
  });
});

export default router;

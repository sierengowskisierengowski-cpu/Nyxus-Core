import { Router } from "express";
import { db, networkDevicesTable } from "@workspace/db";
import { asc } from "drizzle-orm";

const router = Router();

router.get("/network/devices", async (_req, res) => {
  try {
    const devices = await db.select().from(networkDevicesTable).orderBy(asc(networkDevicesTable.ip));
    res.json(
      devices.map((d) => ({
        ip: d.ip,
        hostname: d.hostname,
        mac: d.mac,
        vendor: d.vendor,
        status: d.status,
        isTarget: d.isTarget,
        openPorts: JSON.parse(d.openPorts || "[]") as number[],
        lastSeen: d.lastSeen?.toISOString() ?? null,
      }))
    );
  } catch (err) {
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

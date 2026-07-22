import { Router, type IRouter } from "express";
import { desc, sql } from "drizzle-orm";
import { db, networkDevices, settings as settingsTable } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { logger } from "../lib/logger";
import {
  loadScanConfig,
  validateScanTarget,
  runNetworkScan,
  type DiscoveredDevice,
} from "../lib/networkScan";

const router: IRouter = Router();

router.get("/network/devices", requireAuth, async (_req, res) => {
  const rows = await db.select().from(networkDevices).orderBy(desc(networkDevices.lastSeen));
  res.json(rows.map(toDevice));
});

router.post("/network/scan", requireAuth, async (_req, res) => {
  const config = loadScanConfig();

  // The scan target is the server-configured subnet — never an arbitrary,
  // request-supplied target. It is still validated against the allow-list.
  const [settingsRow] = await db.select().from(settingsTable).limit(1);
  const target = settingsRow?.targetSubnet?.trim() || "";
  if (!target) {
    res.status(400).json({
      error: "No target subnet configured. Set one in Settings first.",
    });
    return;
  }

  const validation = validateScanTarget(target, config);
  if (!validation.ok) {
    res.status(400).json({
      error: `Refusing to scan: ${validation.reason}`,
      target,
      allowedSubnets: validation.allowedSubnets,
    });
    return;
  }

  let discovered: DiscoveredDevice[];
  try {
    discovered = await runNetworkScan(target, config);
  } catch (err) {
    logger.error({ err, target }, "network-scan failed");
    res.status(500).json({
      error: "Network scan failed. Ensure nmap (or arp-scan) is installed.",
      detail: err instanceof Error ? err.message : String(err),
    });
    return;
  }

  const excluded = new Set(settingsRow?.excludedDevices ?? []);
  const now = new Date();

  for (const d of discovered) {
    await db
      .insert(networkDevices)
      .values({
        ip: d.ip,
        hostname: d.hostname,
        mac: d.mac,
        vendor: d.vendor,
        excluded: excluded.has(d.ip),
        lastSeen: now,
      })
      .onConflictDoUpdate({
        target: networkDevices.ip,
        set: {
          // Keep a previously-known value when this scan couldn't resolve one
          // (e.g. an unprivileged nmap sweep returns no MAC/vendor).
          hostname: sql`coalesce(nullif(excluded.hostname, ''), ${networkDevices.hostname})`,
          mac: sql`coalesce(nullif(excluded.mac, ''), ${networkDevices.mac})`,
          vendor: sql`coalesce(nullif(excluded.vendor, ''), ${networkDevices.vendor})`,
          excluded: excluded.has(d.ip),
          lastSeen: now,
        },
      });
  }

  const rows = await db.select().from(networkDevices).orderBy(desc(networkDevices.lastSeen));
  res.json(rows.map(toDevice));
});

function toDevice(d: typeof networkDevices.$inferSelect) {
  return {
    ip: d.ip,
    hostname: d.hostname,
    mac: d.mac,
    vendor: d.vendor,
    excluded: d.excluded,
    lastSeen: d.lastSeen.toISOString(),
  };
}

export default router;

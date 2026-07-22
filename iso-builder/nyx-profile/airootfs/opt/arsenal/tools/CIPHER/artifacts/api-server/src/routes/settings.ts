import { Router } from "express";
import { db } from "@workspace/db";
import { settingsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { getGpus } from "../lib/system-stats";

const router = Router();

async function getOrCreateSettings() {
  const existing = await db.select().from(settingsTable).limit(1);
  if (existing.length > 0) return existing[0];
  const [created] = await db.insert(settingsTable).values({}).returning();
  return created;
}

function formatSettings(s: typeof settingsTable.$inferSelect) {
  return {
    ...s,
    disclaimerAcceptedAt: s.disclaimerAcceptedAt?.toISOString() ?? null,
    createdAt: undefined,
    updatedAt: undefined,
  };
}

router.get("/settings", async (req, res) => {
  try {
    const settings = await getOrCreateSettings();
    res.json(formatSettings(settings));
  } catch (err) {
    req.log.error(err, "Failed to get settings");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/settings", async (req, res) => {
  try {
    const settings = await getOrCreateSettings();
    const allowed = ["claudeModel", "hashcatPath", "johnPath", "gpuEnabled", "gpuDevice", "gpuMemoryLimit", "gpuTempLimit", "cpuThreads", "defaultAttackMode", "meliEndpoint", "ntfyTopic", "notificationsEnabled", "dataRetentionDays"];
    const updates: Record<string, unknown> = {};

    const fieldMap: Record<string, string> = {
      claudeModel: "claudeModel", hashcatPath: "hashcatPath", johnPath: "johnPath",
      gpuEnabled: "gpuEnabled", gpuDevice: "gpuDevice", gpuMemoryLimit: "gpuMemoryLimit",
      gpuTempLimit: "gpuTempLimit", cpuThreads: "cpuThreads", defaultAttackMode: "defaultAttackMode",
      meliEndpoint: "meliEndpoint", ntfyTopic: "ntfyTopic", notificationsEnabled: "notificationsEnabled",
      dataRetentionDays: "dataRetentionDays",
    };

    for (const key of allowed) {
      if (req.body[key] !== undefined) updates[fieldMap[key]] = req.body[key];
    }

    const [updated] = await db.update(settingsTable).set(updates).where(eq(settingsTable.id, settings.id)).returning();
    res.json(formatSettings(updated));
  } catch (err) {
    req.log.error(err, "Failed to update settings");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/settings/gpu-status", async (req, res) => {
  try {
    // Real telemetry from nvidia-smi. No GPU / no driver => available: false.
    const gpus = await getGpus();
    const gpu = gpus[0];
    if (!gpu) {
      res.json({
        available: false,
        name: "No NVIDIA GPU detected",
        utilizationPercent: 0,
        temperatureCelsius: 0,
        vramUsedMb: 0,
        vramTotalMb: 0,
        powerDrawWatts: 0,
        cudaVersion: null,
      });
      return;
    }
    res.json({
      available: true,
      name: gpu.name,
      utilizationPercent: gpu.utilizationPercent ?? 0,
      temperatureCelsius: gpu.temperatureCelsius ?? 0,
      vramUsedMb: gpu.memUsedMb ?? 0,
      vramTotalMb: gpu.memTotalMb ?? 0,
      powerDrawWatts: gpu.powerWatts ?? 0,
      cudaVersion: null,
    });
  } catch (err) {
    req.log.error(err, "Failed to get GPU status");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/settings/disclaimer-accepted", async (req, res) => {
  try {
    const settings = await getOrCreateSettings();
    const [updated] = await db.update(settingsTable).set({
      disclaimerAccepted: true,
      disclaimerAcceptedAt: new Date(),
    }).where(eq(settingsTable.id, settings.id)).returning();
    res.json({ accepted: true, acceptedAt: updated.disclaimerAcceptedAt?.toISOString() ?? null });
  } catch (err) {
    req.log.error(err, "Failed to accept disclaimer");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/settings/disclaimer-status", async (req, res) => {
  try {
    const settings = await getOrCreateSettings();
    res.json({ accepted: settings.disclaimerAccepted, acceptedAt: settings.disclaimerAcceptedAt?.toISOString() ?? null });
  } catch (err) {
    req.log.error(err, "Failed to get disclaimer status");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

import { Router } from "express";
import { db } from "@workspace/db";
import { jobsTable } from "@workspace/db";
import { eq, desc } from "drizzle-orm";
import { requireAuth } from "../lib/auth";
import {
  startJob,
  controlJob,
  getJobLog,
  isJobRunning,
  CrackerError,
  supportedHashTypes,
} from "../lib/cracker";

const router = Router();

// All job endpoints are tool-running / owner-only.
router.use(requireAuth);

function parseJsonField(value: string | null, fallback: unknown[] = []): unknown[] {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function formatJob(job: typeof jobsTable.$inferSelect) {
  return {
    ...job,
    hashIds: parseJsonField(job.hashIds as string),
    wordlistIds: parseJsonField(job.wordlistIds as string),
    ruleIds: parseJsonField(job.ruleIds as string),
    startedAt: job.startedAt?.toISOString() ?? null,
    completedAt: job.completedAt?.toISOString() ?? null,
    createdAt: job.createdAt.toISOString(),
  };
}

const ACTIVE_STATUSES = new Set(["queued", "running", "paused"]);

router.get("/jobs", async (req, res) => {
  try {
    const statusFilter = req.query.status as string;
    const jobs = await db.select().from(jobsTable).orderBy(desc(jobsTable.createdAt));
    const filtered =
      !statusFilter || statusFilter === "all"
        ? jobs
        : statusFilter === "active"
          ? jobs.filter((j) => ACTIVE_STATUSES.has(j.status))
          : jobs.filter((j) => j.status === statusFilter);
    res.json(filtered.map(formatJob));
  } catch (err) {
    req.log.error(err, "Failed to list jobs");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/jobs", async (req, res) => {
  try {
    const {
      name,
      engine,
      attackMode,
      hashIds,
      hashType,
      wordlistId,
      ruleId,
      mask,
      useGpu,
    } = req.body ?? {};

    if (!name || !attackMode || !hashType || !Array.isArray(hashIds) || hashIds.length === 0) {
      return res
        .status(400)
        .json({ error: "name, attackMode, hashType and at least one hashId are required" });
    }

    const chosenEngine = engine === "john" ? "john" : "hashcat";
    if (!supportedHashTypes(chosenEngine).includes(String(hashType).toLowerCase())) {
      return res.status(400).json({
        error: `Hash type "${hashType}" is not supported by ${chosenEngine}. Supported: ${supportedHashTypes(chosenEngine).join(", ")}`,
      });
    }

    const [job] = await db
      .insert(jobsTable)
      .values({
        name,
        status: "queued",
        engine: chosenEngine,
        attackMode,
        hashIds: JSON.stringify(hashIds),
        hashType: String(hashType).toLowerCase(),
        wordlistIds: JSON.stringify(wordlistId ? [wordlistId] : []),
        ruleIds: JSON.stringify(ruleId ? [ruleId] : []),
        mask: mask || null,
        useGpu: useGpu !== false,
        progress: 0,
        cracksFound: 0,
        timeElapsedSeconds: 0,
        speedUnit: "H/s",
      })
      .returning();

    try {
      await startJob(job.id);
    } catch (err) {
      // Roll back the queued row on validation errors so no junk jobs linger.
      await db.delete(jobsTable).where(eq(jobsTable.id, job.id));
      if (err instanceof CrackerError) {
        return res.status(400).json({ error: err.message });
      }
      throw err;
    }

    const [started] = await db.select().from(jobsTable).where(eq(jobsTable.id, job.id)).limit(1);
    res.status(201).json(formatJob(started ?? job));
  } catch (err) {
    req.log.error(err, "Failed to create job");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/jobs/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [job] = await db.select().from(jobsTable).where(eq(jobsTable.id, id)).limit(1);
    if (!job) return res.status(404).json({ error: "Job not found" });
    res.json(formatJob(job));
  } catch (err) {
    req.log.error(err, "Failed to get job");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/jobs/:id/log", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [job] = await db.select().from(jobsTable).where(eq(jobsTable.id, id)).limit(1);
    if (!job) return res.status(404).json({ error: "Job not found" });
    const log = await getJobLog(id);
    res.json({ jobId: id, running: isJobRunning(id), log });
  } catch (err) {
    req.log.error(err, "Failed to get job log");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/jobs/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    if (isJobRunning(id)) await controlJob(id, "stop");
    await db.delete(jobsTable).where(eq(jobsTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error(err, "Failed to delete job");
    res.status(500).json({ error: "Internal server error" });
  }
});

async function handleControl(action: "pause" | "resume" | "stop", id: number) {
  const ok = await controlJob(id, action);
  if (!ok && action === "stop") {
    // Not actively running (queued/interrupted): mark stopped for consistency.
    await db.update(jobsTable).set({ status: "stopped", completedAt: new Date() }).where(eq(jobsTable.id, id));
    return true;
  }
  return ok;
}

for (const action of ["pause", "resume", "stop"] as const) {
  router.post(`/jobs/:id/${action}`, async (req, res) => {
    try {
      const id = parseInt(req.params.id);
      const [existing] = await db.select().from(jobsTable).where(eq(jobsTable.id, id)).limit(1);
      if (!existing) return res.status(404).json({ error: "Job not found" });

      const ok = await handleControl(action, id);
      if (!ok) {
        return res.status(409).json({ error: `Job is not running; cannot ${action}` });
      }
      const [job] = await db.select().from(jobsTable).where(eq(jobsTable.id, id)).limit(1);
      res.json(formatJob(job));
    } catch (err) {
      req.log.error(err, `Failed to ${action} job`);
      res.status(500).json({ error: "Internal server error" });
    }
  });
}

export default router;

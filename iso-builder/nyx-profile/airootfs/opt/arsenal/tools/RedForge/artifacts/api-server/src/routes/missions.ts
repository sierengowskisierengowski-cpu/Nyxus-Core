import { Router, type IRouter } from "express";
import { eq, desc, and, ne } from "drizzle-orm";
import { db, missions, skillStats } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { SCENARIOS } from "../lib/scenarios";
import { TECHNIQUES } from "../lib/mitre";
import { scoreMission } from "../lib/scoring";
import { UpdateInvestigationBody, SubmitMissionBody } from "@workspace/api-zod";
import { missionRow } from "./scenarios";

const router: IRouter = Router();

function missionSummary(m: typeof missions.$inferSelect) {
  return {
    id: m.id,
    scenarioId: m.scenarioId,
    scenarioName: m.scenarioName,
    category: m.category,
    difficulty: m.difficulty,
    status: m.status,
    startedAt: m.startedAt.toISOString(),
    completedAt: m.completedAt?.toISOString() ?? null,
    score: m.score,
    mastered: m.mastered,
  };
}

function buildDebrief(m: typeof missions.$inferSelect) {
  const s = SCENARIOS.find((x) => x.id === m.scenarioId);
  if (!s) return null;
  const related = TECHNIQUES.filter((t) =>
    s.mitreTechniques.some((mt) => mt.split(/[ -]/)[0] === t.id || mt.startsWith(t.id)),
  )
    .slice(0, 6)
    .map((t) => ({
      id: t.id,
      name: t.name,
      description: t.description,
      tactics: t.tactics,
      platforms: t.platforms,
    }));
  const perf = (m.performance as ReturnType<typeof scoreMission> | null) ?? {
    overall: 0,
    detectionTime: 0,
    identification: 0,
    evidenceQuality: 0,
    containment: 0,
    feedback: "Mission incomplete.",
  };
  return {
    mission: missionRow(m),
    reveal: s.reveal,
    artifacts: [
      { kind: "code", label: "Attacker payload", content: s.reveal.sourceCode },
      { kind: "narrative", label: "Backstory", content: s.backstory },
      { kind: "telemetry", label: "What you should have seen", content: s.reveal.whatYouShouldHaveSeen },
    ],
    performance: perf,
    relatedTechniques: related,
  };
}

router.get("/missions", requireAuth, async (req, res) => {
  const status = typeof req.query.status === "string" ? req.query.status : undefined;
  const list = status
    ? await db.select().from(missions).where(eq(missions.status, status)).orderBy(desc(missions.startedAt))
    : await db.select().from(missions).orderBy(desc(missions.startedAt));
  res.json(list.map(missionSummary));
});

router.get("/missions/active", requireAuth, async (_req, res) => {
  const [row] = await db
    .select()
    .from(missions)
    .where(eq(missions.status, "active"))
    .orderBy(desc(missions.startedAt))
    .limit(1);
  res.json({ mission: row ? missionRow(row) : null });
});

router.get("/missions/:id", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [m] = await db.select().from(missions).where(eq(missions.id, id)).limit(1);
  if (!m) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const s = SCENARIOS.find((x) => x.id === m.scenarioId);
  res.json({
    ...missionRow(m),
    scenario: s
      ? {
          id: s.id,
          name: s.name,
          category: s.category,
          difficulty: s.difficulty,
          description: s.description,
          mitreTechniques: s.mitreTechniques,
          platforms: s.platforms,
          timeLimitMinutes: s.timeLimitMinutes,
          atomicTestId: s.atomicTestId,
          backstory: s.backstory,
          tags: s.tags,
        }
      : undefined,
    debrief: m.status !== "active" ? buildDebrief(m) : null,
  });
});

router.delete("/missions/:id", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  await db.delete(missions).where(eq(missions.id, id));
  res.status(204).end();
});

router.patch("/missions/:id/investigation", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const parsed = UpdateInvestigationBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const patch: Partial<typeof missions.$inferInsert> = {};
  if (parsed.data.notes !== undefined) patch.notes = parsed.data.notes;
  if (parsed.data.hypothesis !== undefined) patch.hypothesis = parsed.data.hypothesis;
  if (parsed.data.evidence !== undefined) patch.evidence = parsed.data.evidence;
  const [row] = await db.update(missions).set(patch).where(eq(missions.id, id)).returning();
  if (!row) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(missionRow(row));
});

router.post("/missions/:id/hint", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [m] = await db.select().from(missions).where(eq(missions.id, id)).limit(1);
  if (!m) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const s = SCENARIOS.find((x) => x.id === m.scenarioId);
  const idx = m.hintsUsed;
  const hint = s?.hints[idx] ?? "No more hints available. Check the debrief if you give up.";
  const [row] = await db.update(missions).set({ hintsUsed: idx + 1 }).where(eq(missions.id, id)).returning();
  res.json({ hint, hintsUsed: row.hintsUsed });
});

router.post("/missions/:id/submit", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const parsed = SubmitMissionBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const [m] = await db.select().from(missions).where(eq(missions.id, id)).limit(1);
  if (!m) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const s = SCENARIOS.find((x) => x.id === m.scenarioId);
  if (!s) {
    res.status(404).json({ error: "Scenario not found" });
    return;
  }
  const durationSeconds = Math.round((Date.now() - m.startedAt.getTime()) / 1000);
  const perf = scoreMission({
    correctTechnique: s.reveal.mitreTechniques[0] ?? s.mitreTechniques[0] ?? "",
    correctCategory: s.category,
    identifiedTechnique: parsed.data.identifiedTechnique,
    identifiedCategory: parsed.data.identifiedCategory ?? undefined,
    confidence: parsed.data.confidence ?? undefined,
    hintsUsed: m.hintsUsed,
    notes: parsed.data.finalNotes ?? m.notes,
    evidence: m.evidence,
    durationSeconds,
    timeLimitMinutes: m.timeLimitMinutes ?? s.timeLimitMinutes,
  });
  const [updated] = await db
    .update(missions)
    .set({
      status: "completed",
      identifiedTechnique: parsed.data.identifiedTechnique,
      identifiedCategory: parsed.data.identifiedCategory ?? null,
      confidence: parsed.data.confidence ?? null,
      score: perf.overall,
      performance: perf,
      completedAt: new Date(),
      notes: parsed.data.finalNotes ?? m.notes,
    })
    .where(eq(missions.id, id))
    .returning();
  await bumpSkill(updated.category, perf.overall);
  res.json(buildDebrief(updated));
});

router.post("/missions/:id/giveup", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [m] = await db.select().from(missions).where(eq(missions.id, id)).limit(1);
  if (!m) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const perf = { overall: 0, detectionTime: 0, identification: 0, evidenceQuality: 0, containment: 0, feedback: "Mission abandoned. Study the reveal carefully." };
  const [updated] = await db
    .update(missions)
    .set({ status: "abandoned", score: 0, performance: perf, completedAt: new Date() })
    .where(eq(missions.id, id))
    .returning();
  res.json(buildDebrief(updated));
});

router.get("/missions/:id/debrief", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [m] = await db.select().from(missions).where(eq(missions.id, id)).limit(1);
  if (!m) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  const debrief = buildDebrief(m);
  if (!debrief) {
    res.status(404).json({ error: "No debrief available" });
    return;
  }
  res.json(debrief);
});

router.post("/missions/:id/master", requireAuth, async (req, res) => {
  const id = Number(req.params.id);
  const [row] = await db
    .update(missions)
    .set({ mastered: true })
    .where(and(eq(missions.id, id), ne(missions.status, "active")))
    .returning();
  if (!row) {
    res.status(404).json({ error: "Mission not found or still active" });
    return;
  }
  res.json(missionSummary(row));
});

async function bumpSkill(category: string, score: number) {
  const [existing] = await db.select().from(skillStats).where(eq(skillStats.category, category)).limit(1);
  if (existing) {
    await db
      .update(skillStats)
      .set({
        totalScore: existing.totalScore + score,
        missionCount: existing.missionCount + 1,
        updatedAt: new Date(),
      })
      .where(eq(skillStats.id, existing.id));
  } else {
    await db.insert(skillStats).values({ category, totalScore: score, missionCount: 1 });
  }
}

export default router;

import { Router, type IRouter } from "express";
import { db, missions, settings as settingsTable } from "@workspace/db";
import { requireAuth } from "../middlewares/requireAuth";
import { SCENARIOS } from "../lib/scenarios";
import { DeployScenarioBody, DeployRandomScenarioBody } from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/scenarios", requireAuth, (req, res) => {
  const category = typeof req.query.category === "string" ? req.query.category : undefined;
  const difficulty = typeof req.query.difficulty === "string" ? req.query.difficulty : undefined;
  const search = typeof req.query.search === "string" ? req.query.search : undefined;
  let list = SCENARIOS.slice();
  if (category) list = list.filter((s) => s.category.toLowerCase() === category.toLowerCase());
  if (difficulty) list = list.filter((s) => s.difficulty === difficulty);
  if (search) {
    const q = search.toLowerCase();
    list = list.filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q) || s.tags.some((t) => t.includes(q)),
    );
  }
  res.json(
    list.map((s) => ({
      id: s.id,
      name: s.name,
      category: s.category,
      difficulty: s.difficulty,
      description: s.description,
      mitreTechniques: s.mitreTechniques,
      platforms: s.platforms,
      timeLimitMinutes: s.timeLimitMinutes,
    })),
  );
});

router.get("/scenarios/:id", requireAuth, (req, res) => {
  const s = SCENARIOS.find((x) => x.id === req.params.id);
  if (!s) {
    res.status(404).json({ error: "Scenario not found" });
    return;
  }
  res.json({
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
  });
});

router.post("/scenarios/random", requireAuth, async (req, res) => {
  const parsed = DeployRandomScenarioBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const { difficulty, categories, timeLimitMinutes } = parsed.data;
  let pool = SCENARIOS.filter((s) => s.difficulty === difficulty);
  if (categories?.length) pool = pool.filter((s) => categories.includes(s.category));
  if (pool.length === 0) pool = SCENARIOS;
  const chosen = pool[Math.floor(Math.random() * pool.length)];
  const mission = await deployMission(chosen.id, "blind", timeLimitMinutes);
  if (!mission) {
    res.status(404).json({ error: "No scenarios available" });
    return;
  }
  res.status(201).json(mission);
});

router.post("/scenarios/:id/deploy", requireAuth, async (req, res) => {
  const parsed = DeployScenarioBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const mission = await deployMission(String(req.params.id), parsed.data.mode, parsed.data.timeLimitMinutes);
  if (!mission) {
    res.status(404).json({ error: "Scenario not found" });
    return;
  }
  res.status(201).json(mission);
});

async function deployMission(scenarioId: string, mode: string, timeLimitMinutes?: number) {
  const s = SCENARIOS.find((x) => x.id === scenarioId);
  if (!s) return null;
  const [config] = await db.select().from(settingsTable).limit(1);
  const limit = timeLimitMinutes ?? s.timeLimitMinutes ?? config?.defaultTimerMinutes ?? 30;
  const [row] = await db
    .insert(missions)
    .values({
      scenarioId: s.id,
      scenarioName: s.name,
      category: s.category,
      difficulty: s.difficulty,
      status: "active",
      mode,
      timeLimitMinutes: limit,
    })
    .returning();
  return missionRow(row);
}

export function missionRow(m: typeof missions.$inferSelect) {
  return {
    id: m.id,
    scenarioId: m.scenarioId,
    scenarioName: m.scenarioName,
    category: m.category,
    difficulty: m.difficulty,
    status: m.status,
    mode: m.mode,
    startedAt: m.startedAt.toISOString(),
    completedAt: m.completedAt?.toISOString() ?? null,
    timeLimitMinutes: m.timeLimitMinutes,
    notes: m.notes,
    hypothesis: m.hypothesis,
    evidence: m.evidence,
    hintsUsed: m.hintsUsed,
    score: m.score,
  };
}

export default router;

import { Router } from "express";
import { db, missionsTable } from "@workspace/db";
import { eq, desc, and } from "drizzle-orm";
import { generateTemplateAttack, generateClaudeAttack, generateHybridAttack } from "../lib/attack-engine";
import type { AttackCategory, AttackDifficulty, GenerationMode } from "../lib/attack-engine";
import { ListMissionsQueryParams, GenerateMissionBody, UpdateMissionStatusBody, ScoreMissionBody, GetMissionParams, DeleteMissionParams, RevealMissionParams, UpdateMissionStatusParams, ScoreMissionParams } from "@workspace/api-zod";
import { logger } from "../lib/logger";

const router = Router();

router.get("/missions", async (req, res) => {
  try {
    const parsed = ListMissionsQueryParams.safeParse(req.query);
    const limit = parsed.success ? (parsed.data.limit ?? 20) : 20;
    const status = parsed.success ? parsed.data.status : undefined;
    const category = parsed.success ? parsed.data.category : undefined;

    let query = db.select().from(missionsTable).orderBy(desc(missionsTable.createdAt)).$dynamic();

    const conditions = [];
    if (status) conditions.push(eq(missionsTable.status, status));
    if (category) conditions.push(eq(missionsTable.category, category));
    if (conditions.length > 0) query = query.where(and(...conditions));

    const missions = await query.limit(limit);
    res.json(missions.map(formatMission));
  } catch (err) {
    req.log.error({ err }, "List missions error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/missions/recent", async (req, res) => {
  try {
    const missions = await db.select().from(missionsTable).orderBy(desc(missionsTable.createdAt)).limit(10);
    res.json(missions.map(formatMission));
  } catch (err) {
    req.log.error({ err }, "Recent missions error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/missions/:id", async (req, res) => {
  try {
    const { id } = GetMissionParams.parse({ id: Number(req.params.id) });
    const [mission] = await db.select().from(missionsTable).where(eq(missionsTable.id, id));
    if (!mission) {
      res.status(404).json({ error: "Mission not found" });
      return;
    }
    res.json(formatMission(mission));
  } catch (err) {
    req.log.error({ err }, "Get mission error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/missions", async (req, res) => {
  try {
    const body = GenerateMissionBody.parse(req.body);
    const mode = (body.mode ?? "hybrid") as GenerationMode;
    const difficulty = (body.difficulty ?? "Unknown") as AttackDifficulty;
    const category = (body.category ?? randomCategory()) as AttackCategory;
    const targetIp = body.targetIp ?? randomTarget();
    const prompt = body.prompt ?? "";
    const blind = body.blind ?? false;

    let attack;
    if (mode === "template") {
      attack = generateTemplateAttack(category, difficulty, targetIp);
    } else if (mode === "claude") {
      attack = await generateClaudeAttack(prompt, category, difficulty, targetIp);
    } else {
      attack = await generateHybridAttack(prompt, category, difficulty, targetIp);
    }

    const [mission] = await db
      .insert(missionsTable)
      .values({
        title: attack.title,
        description: attack.description,
        category: attack.category,
        difficulty: attack.difficulty,
        mode,
        status: "active",
        targetIp: attack.targetIp,
        revealed: !blind,
        blind,
        generatedCode: attack.generatedCode,
        mitreIds: attack.mitreIds,
        primitives: attack.primitives,
        startedAt: new Date(),
      })
      .returning();

    res.status(201).json(formatMission(mission));
  } catch (err) {
    req.log.error({ err }, "Generate mission error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/missions/:id", async (req, res) => {
  try {
    const { id } = DeleteMissionParams.parse({ id: Number(req.params.id) });
    await db.delete(missionsTable).where(eq(missionsTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error({ err }, "Delete mission error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/missions/:id/reveal", async (req, res) => {
  try {
    const { id } = RevealMissionParams.parse({ id: Number(req.params.id) });
    const [mission] = await db
      .update(missionsTable)
      .set({ revealed: true })
      .where(eq(missionsTable.id, id))
      .returning();
    if (!mission) {
      res.status(404).json({ error: "Mission not found" });
      return;
    }
    const primitives = tryParseJson<string[]>(mission.primitives) ?? [];
    const mitreMapping = mission.mitreIds ? mission.mitreIds.split(",").map((s) => s.trim()) : [];
    res.json({ mission: formatMission(mission), primitives, mitreMapping });
  } catch (err) {
    req.log.error({ err }, "Reveal mission error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/missions/:id/status", async (req, res) => {
  try {
    const { id } = UpdateMissionStatusParams.parse({ id: Number(req.params.id) });
    const body = UpdateMissionStatusBody.parse(req.body);
    const updateData: Record<string, unknown> = { status: body.status };
    if (body.status === "active") updateData.startedAt = new Date();
    if (body.status === "completed" || body.status === "failed") updateData.completedAt = new Date();
    const [mission] = await db.update(missionsTable).set(updateData).where(eq(missionsTable.id, id)).returning();
    if (!mission) {
      res.status(404).json({ error: "Mission not found" });
      return;
    }
    res.json(formatMission(mission));
  } catch (err) {
    req.log.error({ err }, "Update mission status error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/missions/:id/score", async (req, res) => {
  try {
    const { id } = ScoreMissionParams.parse({ id: Number(req.params.id) });
    const body = ScoreMissionBody.parse(req.body);
    const [mission] = await db.update(missionsTable).set(body).where(eq(missionsTable.id, id)).returning();
    if (!mission) {
      res.status(404).json({ error: "Mission not found" });
      return;
    }
    res.json(formatMission(mission));
  } catch (err) {
    req.log.error({ err }, "Score mission error");
    res.status(500).json({ error: "Internal server error" });
  }
});

function formatMission(m: typeof missionsTable.$inferSelect) {
  return {
    id: m.id,
    title: m.title,
    description: m.description,
    category: m.category,
    difficulty: m.difficulty,
    mode: m.mode,
    status: m.status,
    targetIp: m.targetIp,
    revealed: m.revealed,
    detectionScore: m.detectionScore,
    responseScore: m.responseScore,
    generatedCode: m.revealed ? m.generatedCode : null,
    mitreIds: m.revealed ? m.mitreIds : null,
    startedAt: m.startedAt?.toISOString() ?? null,
    completedAt: m.completedAt?.toISOString() ?? null,
    createdAt: m.createdAt.toISOString(),
  };
}

function randomCategory(): AttackCategory {
  const cats: AttackCategory[] = ["WiFi", "Web", "Network", "Malware", "Social", "Physical", "Mixed"];
  return cats[Math.floor(Math.random() * cats.length)];
}

function randomTarget(): string {
  return `192.168.0.${Math.floor(Math.random() * 253) + 1}`;
}

function tryParseJson<T>(s: string | null | undefined): T | null {
  if (!s) return null;
  try { return JSON.parse(s) as T; } catch (_e) { return null; }
}

export default router;

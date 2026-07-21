import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { threatsTable, threatInputsTable, detectionRulesTable, redforgeHistoryTable } from "@workspace/db";
import { eq, and, gte, lte, like, desc, or } from "drizzle-orm";
import { anthropic, extractJson } from "@workspace/integrations-anthropic-ai";
import { exportThreatToRedforge } from "../lib/redforge-export";

// JSON Schema handed to Ollama's structured-output mode so the local model is
// constrained to emit valid, correctly-shaped JSON. Small local models are far
// more reliable with this than when merely asked to "respond in JSON".
const THREAT_JSON_SCHEMA: Record<string, unknown> = {
  type: "object",
  properties: {
    name: { type: "string" },
    noveltyScore: { type: "integer", minimum: 1, maximum: 10 },
    estimatedDetectionRate: { type: "integer", minimum: 0, maximum: 100 },
    platform: { type: "string" },
    category: { type: "string" },
    description: { type: "string" },
    code: { type: "string" },
    technicalBreakdown: { type: "string" },
    mitreIds: { type: "array", items: { type: "string" } },
    realWorldFeasibility: { type: "string" },
    sigmaRule: { type: "string" },
    snortRule: { type: "string" },
    yaraRule: { type: "string" },
    behavioralIndicators: { type: "array", items: { type: "string" } },
    networkIndicators: { type: "array", items: { type: "string" } },
    defensiveRecommendations: { type: "string" },
    hardeningConfig: { type: "string" },
    testPlan: { type: "string" },
  },
  required: [
    "name", "noveltyScore", "estimatedDetectionRate", "platform", "category",
    "description", "code", "technicalBreakdown", "mitreIds", "realWorldFeasibility",
    "defensiveRecommendations", "hardeningConfig", "testPlan",
  ],
};
import {
  GetThreatParams,
  UpdateThreatParams,
  UpdateThreatBody,
  DeleteThreatParams,
  SendThreatToRedforgeParams,
  ListThreatsQueryParams,
  GenerateThreatsBody,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/threats", async (req, res): Promise<void> => {
  const params = ListThreatsQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { noveltyMin, noveltyMax, platform, mastered, sentToRedforge, search, limit = 50, offset = 0 } = params.data;

  let query = db.select().from(threatsTable);
  const conditions = [];
  if (noveltyMin !== undefined) conditions.push(gte(threatsTable.noveltyScore, noveltyMin));
  if (noveltyMax !== undefined) conditions.push(lte(threatsTable.noveltyScore, noveltyMax));
  if (platform) conditions.push(eq(threatsTable.platform, platform));
  if (mastered !== undefined) conditions.push(eq(threatsTable.mastered, mastered));
  if (sentToRedforge !== undefined) conditions.push(eq(threatsTable.sentToRedforge, sentToRedforge));
  if (search) conditions.push(or(
    like(threatsTable.name, `%${search}%`),
    like(threatsTable.description, `%${search}%`),
  ));

  const threats = conditions.length > 0
    ? await db.select().from(threatsTable).where(and(...conditions)).orderBy(desc(threatsTable.createdAt)).limit(limit).offset(offset)
    : await db.select().from(threatsTable).orderBy(desc(threatsTable.createdAt)).limit(limit).offset(offset);

  const [totalRow] = conditions.length > 0
    ? await db.select({ count: db.$count(threatsTable, and(...conditions)) }).from(threatsTable)
    : await db.select({ count: db.$count(threatsTable) }).from(threatsTable);

  res.json({ threats, total: totalRow?.count ?? threats.length });
});

router.get("/threats/recent", async (_req, res): Promise<void> => {
  const threats = await db.select().from(threatsTable).orderBy(desc(threatsTable.createdAt)).limit(10);
  res.json(threats);
});

router.get("/threats/top", async (_req, res): Promise<void> => {
  const threats = await db.select().from(threatsTable).orderBy(desc(threatsTable.noveltyScore)).limit(10);
  res.json(threats);
});

router.post("/threats/generate", async (req, res): Promise<void> => {
  const parsed = GenerateThreatsBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");

  const send = (data: object) => res.write(`data: ${JSON.stringify(data)}\n\n`);

  try {
    const { inputIds, engines, noveltyTarget = 7, complexityTarget = "moderate", platform = "linux", evasionPriority = 3, stealthLevel = "balanced", attackGoal = "access" } = parsed.data;

    // Fetch inputs
    const inputs = inputIds.length > 0
      ? await db.select().from(threatInputsTable).where(or(...inputIds.map(id => eq(threatInputsTable.id, id))))
      : await db.select().from(threatInputsTable).limit(5);

    const inputContent = inputs.map(i => `[${i.inputType.toUpperCase()}]\n${i.content}`).join("\n\n---\n\n");

    send({ type: "status", message: "Initializing mutation engines..." });

    const engineNames: Record<string, string> = {
      codeSplicing: "Code Splicing",
      logicMutation: "Logic Mutation",
      crossDomainFusion: "Cross Domain Fusion",
      evasionEvolution: "Evasion Evolution",
      protocolAbuse: "Protocol Abuse",
      lolExpansion: "LOLBAS Expansion",
      payloadPolymorphism: "Payload Polymorphism",
    };

    for (const engine of (engines.length > 0 ? engines : Object.keys(engineNames))) {
      send({ type: "engine_start", engine, name: engineNames[engine] ?? engine });
      await new Promise(r => setTimeout(r, 200));
    }

    send({ type: "status", message: "Running local AI evaluation (Ollama)..." });

    const prompt = `You are an elite cybersecurity threat researcher operating GowskiNet FORGE. Generate a novel attack technique based on the following inputs using these mutation engines: ${engines.join(", ")}.

Target platform: ${platform}
Novelty target: ${noveltyTarget}/10
Complexity: ${complexityTarget}
Evasion priority: ${evasionPriority}/5
Stealth level: ${stealthLevel}
Attack goal: ${attackGoal}

Input material:
${inputContent || "Generate a novel technique from first principles based on current threat landscape."}

Generate a complete threat research package as a JSON object with these exact fields:
{
  "name": "unique descriptive threat name",
  "noveltyScore": 1-10,
  "estimatedDetectionRate": 0-100,
  "platform": "${platform}",
  "category": "category name",
  "description": "one-line description",
  "code": "complete working code with comment header '// Generated by GowskiNet FORGE — authorized defensive research only'",
  "technicalBreakdown": "detailed technical explanation of how and why it works",
  "mitreIds": ["T1059.001", "..."],
  "realWorldFeasibility": "assessment of real-world applicability",
  "sigmaRule": "complete Sigma SIEM detection rule",
  "snortRule": "complete Snort/Suricata IDS rule",
  "yaraRule": "complete YARA malware scanner rule",
  "behavioralIndicators": ["indicator1", "indicator2"],
  "networkIndicators": ["ioc1", "ioc2"],
  "defensiveRecommendations": "specific hardening and defensive steps",
  "hardeningConfig": "exact configuration changes to block this technique",
  "testPlan": "safe testing procedure for your lab",
  "mutationEnginesUsed": ${JSON.stringify(engines)}
}`;

    let fullResponse = "";
    const stream = anthropic.messages.stream({
      model: "forge-sec",
      max_tokens: 8192,
      temperature: 0.9,
      format: THREAT_JSON_SCHEMA,
      messages: [{ role: "user", content: prompt }],
    });

    let tokenCount = 0;
    for await (const event of stream) {
      if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
        fullResponse += event.delta.text;
        tokenCount += event.delta.text.length;
        if (tokenCount % 500 < 50) {
          send({ type: "progress", tokens: tokenCount });
        }
      }
    }

    send({ type: "status", message: "Parsing generated threat..." });

    try {
      const threatData = extractJson<Record<string, any>>(fullResponse);
      if (!threatData) throw new Error("No parseable JSON in model output");

      const [savedThreat] = await db.insert(threatsTable).values({
        name: threatData.name ?? "Novel Threat",
        noveltyScore: Math.min(10, Math.max(1, threatData.noveltyScore ?? noveltyTarget)),
        estimatedDetectionRate: Math.min(100, Math.max(0, threatData.estimatedDetectionRate ?? 50)),
        platform: threatData.platform ?? platform,
        category: threatData.category ?? "Unknown",
        description: threatData.description ?? "",
        code: threatData.code ?? "// Code generation failed",
        technicalBreakdown: threatData.technicalBreakdown ?? "",
        mitreIds: threatData.mitreIds ?? [],
        realWorldFeasibility: threatData.realWorldFeasibility ?? "",
        sigmaRule: threatData.sigmaRule ?? null,
        snortRule: threatData.snortRule ?? null,
        yaraRule: threatData.yaraRule ?? null,
        behavioralIndicators: threatData.behavioralIndicators ?? [],
        networkIndicators: threatData.networkIndicators ?? [],
        defensiveRecommendations: threatData.defensiveRecommendations ?? "",
        hardeningConfig: threatData.hardeningConfig ?? "",
        testPlan: threatData.testPlan ?? "",
        mutationEnginesUsed: engines,
        parentInputIds: inputIds,
        mastered: false,
        sentToRedforge: false,
      }).returning();

      // Auto-save detection rules
      if (threatData.sigmaRule) {
        await db.insert(detectionRulesTable).values({
          ruleType: "sigma",
          name: `${savedThreat.name} — Sigma`,
          content: threatData.sigmaRule,
          threatId: savedThreat.id,
          mitreIds: threatData.mitreIds ?? [],
          tested: false,
        });
      }
      if (threatData.snortRule) {
        await db.insert(detectionRulesTable).values({
          ruleType: "snort",
          name: `${savedThreat.name} — Snort`,
          content: threatData.snortRule,
          threatId: savedThreat.id,
          mitreIds: threatData.mitreIds ?? [],
          tested: false,
        });
      }
      if (threatData.yaraRule) {
        await db.insert(detectionRulesTable).values({
          ruleType: "yara",
          name: `${savedThreat.name} — YARA`,
          content: threatData.yaraRule,
          threatId: savedThreat.id,
          mitreIds: threatData.mitreIds ?? [],
          tested: false,
        });
      }

      send({ type: "threat_generated", threat: savedThreat });
    } catch (parseErr) {
      send({ type: "error", message: "Failed to parse AI output" });
    }

    send({ type: "done" });
    res.end();
  } catch (err) {
    send({ type: "error", message: "Generation failed" });
    res.end();
  }
});

router.get("/threats/:id", async (req, res): Promise<void> => {
  const params = GetThreatParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [threat] = await db.select().from(threatsTable).where(eq(threatsTable.id, params.data.id));
  if (!threat) {
    res.status(404).json({ error: "Threat not found" });
    return;
  }
  res.json(threat);
});

router.patch("/threats/:id", async (req, res): Promise<void> => {
  const params = UpdateThreatParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const body = UpdateThreatBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }
  const [threat] = await db.update(threatsTable).set(body.data).where(eq(threatsTable.id, params.data.id)).returning();
  if (!threat) {
    res.status(404).json({ error: "Threat not found" });
    return;
  }
  res.json(threat);
});

router.delete("/threats/:id", async (req, res): Promise<void> => {
  const params = DeleteThreatParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [deleted] = await db.delete(threatsTable).where(eq(threatsTable.id, params.data.id)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Threat not found" });
    return;
  }
  res.sendStatus(204);
});

router.post("/threats/:id/send-to-redforge", async (req, res): Promise<void> => {
  const params = SendThreatToRedforgeParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [threat] = await db.select().from(threatsTable).where(eq(threatsTable.id, params.data.id));
  if (!threat) {
    res.status(404).json({ error: "Threat not found" });
    return;
  }

  // Real, honest handoff: write a portable REDFORGE deployment package to the
  // local export directory (bundling the threat and its detection rules), then
  // record the export in redforge_history with the real artifact path. We do
  // NOT fabricate a live "deployed" mission/score.
  const rules = await db
    .select()
    .from(detectionRulesTable)
    .where(eq(detectionRulesTable.threatId, threat.id));

  let exportResult;
  try {
    exportResult = await exportThreatToRedforge(threat, rules);
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err instanceof Error ? err.message : "Failed to write REDFORGE export package",
    });
    return;
  }

  await db
    .update(threatsTable)
    .set({ sentToRedforge: true, sentToRedforgeAt: new Date() })
    .where(eq(threatsTable.id, threat.id));

  await db.insert(redforgeHistoryTable).values({
    threatId: threat.id,
    threatName: threat.name,
    missionId: exportResult.fileName,
    outcome: `Exported handoff package (${exportResult.bytes} bytes) → ${exportResult.filePath}`,
    score: null,
    // TODO: when a live REDFORGE instance exposes a documented import API, POST
    // the package to settings.redforgeUrl and capture the real missionId/score
    // here instead of only writing the local handoff file.
  });

  res.json({
    success: true,
    message: `Threat exported to REDFORGE handoff package: ${exportResult.fileName}`,
    exportPath: exportResult.filePath,
    missionId: exportResult.fileName,
  });
});

export default router;

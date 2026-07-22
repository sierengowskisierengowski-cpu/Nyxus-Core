import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { threatInputsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import { anthropic, extractJson } from "@workspace/integrations-anthropic-ai";
import {
  CreateInputBody,
  DeleteInputParams,
  AnalyzeInputsBody,
} from "@workspace/api-zod";

const ANALYSIS_JSON_SCHEMA: Record<string, unknown> = {
  type: "object",
  properties: {
    techniques: { type: "array", items: { type: "string" } },
    mitreIds: { type: "array", items: { type: "string" } },
    patterns: { type: "array", items: { type: "string" } },
    sophisticationScore: { type: "integer", minimum: 1, maximum: 10 },
    gaps: { type: "array", items: { type: "string" } },
    summary: { type: "string" },
  },
  required: ["techniques", "mitreIds", "patterns", "sophisticationScore", "gaps", "summary"],
};

const router: IRouter = Router();

router.get("/inputs", async (_req, res): Promise<void> => {
  const inputs = await db.select().from(threatInputsTable).orderBy(threatInputsTable.createdAt);
  res.json(inputs);
});

router.post("/inputs", async (req, res): Promise<void> => {
  const parsed = CreateInputBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [input] = await db.insert(threatInputsTable).values(parsed.data).returning();
  res.status(201).json(input);
});

router.delete("/inputs/:id", async (req, res): Promise<void> => {
  const params = DeleteInputParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [deleted] = await db.delete(threatInputsTable).where(eq(threatInputsTable.id, params.data.id)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Input not found" });
    return;
  }
  res.sendStatus(204);
});

router.post("/inputs/analyze", async (req, res): Promise<void> => {
  const parsed = AnalyzeInputsBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }

  const inputs = await db.select().from(threatInputsTable);
  const selectedInputs = parsed.data.inputIds.length > 0
    ? inputs.filter(i => parsed.data.inputIds.includes(i.id))
    : inputs;

  if (selectedInputs.length === 0) {
    res.status(400).json({ error: "No inputs found" });
    return;
  }

  const combinedContent = selectedInputs.map(i => `[${i.inputType.toUpperCase()}]\n${i.content}`).join("\n\n---\n\n");

  const message = await anthropic.messages.create({
    model: "forge-sec",
    max_tokens: 8192,
    format: ANALYSIS_JSON_SCHEMA,
    messages: [
      {
        role: "user",
        content: `You are a cybersecurity threat analyst. Analyze the following input material and extract attack techniques, MITRE ATT&CK mappings, behavioral patterns, and sophistication assessment.

Return a JSON object with these exact fields:
{
  "techniques": ["string array of attack primitive names"],
  "mitreIds": ["array of MITRE ATT&CK technique IDs like T1059.001"],
  "patterns": ["array of identified patterns: timing, encoding, protocol, evasion methods"],
  "sophisticationScore": 1-10,
  "gaps": ["array of underdeveloped areas or extensions"],
  "summary": "one paragraph technical summary"
}

INPUT MATERIAL:
${combinedContent}`,
      },
    ],
  });

  const content = message.content[0];
  if (content.type !== "text") {
    res.status(500).json({ error: "AI analysis failed" });
    return;
  }

  try {
    const analysis = extractJson(content.text) ?? { techniques: [], mitreIds: [], patterns: [], sophisticationScore: 5, gaps: [], summary: content.text };
    
    // Mark inputs as analyzed
    for (const input of selectedInputs) {
      await db.update(threatInputsTable).set({ analyzed: true }).where(eq(threatInputsTable.id, input.id));
    }

    res.json(analysis);
  } catch {
    res.status(500).json({ error: "Failed to parse analysis" });
  }
});

export default router;

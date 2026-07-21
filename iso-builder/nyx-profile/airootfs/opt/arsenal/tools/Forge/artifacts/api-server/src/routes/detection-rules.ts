import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { detectionRulesTable } from "@workspace/db";
import { eq, like, and } from "drizzle-orm";
import {
  CreateDetectionRuleBody,
  GetDetectionRuleParams,
  UpdateDetectionRuleParams,
  UpdateDetectionRuleBody,
  DeleteDetectionRuleParams,
  ListDetectionRulesQueryParams,
} from "@workspace/api-zod";

const router: IRouter = Router();

router.get("/detection-rules", async (req, res): Promise<void> => {
  const params = ListDetectionRulesQueryParams.safeParse(req.query);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const { ruleType, threatId, search } = params.data;
  const conditions = [];
  if (ruleType) conditions.push(eq(detectionRulesTable.ruleType, ruleType));
  if (threatId !== undefined) conditions.push(eq(detectionRulesTable.threatId, threatId));
  if (search) conditions.push(like(detectionRulesTable.name, `%${search}%`));

  const rules = conditions.length > 0
    ? await db.select().from(detectionRulesTable).where(and(...conditions))
    : await db.select().from(detectionRulesTable);
  res.json(rules);
});

router.post("/detection-rules", async (req, res): Promise<void> => {
  const parsed = CreateDetectionRuleBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: parsed.error.message });
    return;
  }
  const [rule] = await db.insert(detectionRulesTable).values({
    ...parsed.data,
    mitreIds: parsed.data.mitreIds ?? [],
  }).returning();
  res.status(201).json(rule);
});

router.get("/detection-rules/:id", async (req, res): Promise<void> => {
  const params = GetDetectionRuleParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [rule] = await db.select().from(detectionRulesTable).where(eq(detectionRulesTable.id, params.data.id));
  if (!rule) {
    res.status(404).json({ error: "Rule not found" });
    return;
  }
  res.json(rule);
});

router.patch("/detection-rules/:id", async (req, res): Promise<void> => {
  const params = UpdateDetectionRuleParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const body = UpdateDetectionRuleBody.safeParse(req.body);
  if (!body.success) {
    res.status(400).json({ error: body.error.message });
    return;
  }
  const [rule] = await db.update(detectionRulesTable).set(body.data).where(eq(detectionRulesTable.id, params.data.id)).returning();
  if (!rule) {
    res.status(404).json({ error: "Rule not found" });
    return;
  }
  res.json(rule);
});

router.delete("/detection-rules/:id", async (req, res): Promise<void> => {
  const params = DeleteDetectionRuleParams.safeParse(req.params);
  if (!params.success) {
    res.status(400).json({ error: params.error.message });
    return;
  }
  const [deleted] = await db.delete(detectionRulesTable).where(eq(detectionRulesTable.id, params.data.id)).returning();
  if (!deleted) {
    res.status(404).json({ error: "Rule not found" });
    return;
  }
  res.sendStatus(204);
});

export default router;

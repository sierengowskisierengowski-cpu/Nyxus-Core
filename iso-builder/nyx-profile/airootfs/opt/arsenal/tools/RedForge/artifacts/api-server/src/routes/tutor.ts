import { Router, type IRouter } from "express";
import { requireAuth } from "../middlewares/requireAuth";
import { TutorExplainBody, TutorQuizBody } from "@workspace/api-zod";
import { streamTutor, generateQuiz } from "../lib/claude";
import { db, settings as settingsTable } from "@workspace/db";
import { logger } from "../lib/logger";

const router: IRouter = Router();

async function currentModel(): Promise<string> {
  const [s] = await db.select().from(settingsTable).limit(1);
  return s?.claudeModel ?? "claude-sonnet-4-5";
}

router.post("/tutor/explain", requireAuth, async (req, res) => {
  const parsed = TutorExplainBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("X-Accel-Buffering", "no");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();

  try {
    const model = await currentModel();
    await streamTutor(parsed.data.prompt, parsed.data.context, parsed.data.kind, model, (delta) => {
      res.write(`data: ${JSON.stringify({ content: delta })}\n\n`);
    });
    res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    logger.error({ err: msg }, "tutor.explain failed");
    res.write(`data: ${JSON.stringify({ error: msg })}\n\n`);
  }
  res.end();
});

router.post("/tutor/quiz", requireAuth, async (req, res) => {
  const parsed = TutorQuizBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  try {
    const model = await currentModel();
    const questions = await generateQuiz(
      parsed.data.topic,
      parsed.data.techniqueId,
      parsed.data.count ?? 5,
      model,
    );
    res.json({ questions });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    logger.error({ err: msg }, "tutor.quiz failed");
    res.status(500).json({ error: msg, questions: [] });
  }
});

export default router;

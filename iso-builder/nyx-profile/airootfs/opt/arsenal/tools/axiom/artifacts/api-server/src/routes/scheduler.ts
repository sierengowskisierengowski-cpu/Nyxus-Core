import { Router } from "express";
import { db } from "@workspace/db";
import { scheduledTasksTable, settingsTable, knowledgeNotesTable, activityLogTable } from "@workspace/db";
import { eq, desc, and, like } from "drizzle-orm";
import cron, { type ScheduledTask } from "node-cron";
import { CronExpressionParser } from "cron-parser";
import OpenAI from "openai";
import {
  CreateScheduledTaskBody,
  UpdateScheduledTaskBody,
} from "@workspace/api-zod";
import { isPathAllowed, executeFileOperation } from "../lib/file-executor";

const router = Router();

const activeCrons = new Map<number, ScheduledTask>();

function calcNextRun(schedule: string): string | null {
  try {
    const expr = CronExpressionParser.parse(schedule);
    return expr.next().toDate().toISOString();
  } catch {
    return null;
  }
}

export async function initScheduler() {
  const tasks = await db.select().from(scheduledTasksTable).where(eq(scheduledTasksTable.enabled, true));
  for (const task of tasks) {
    scheduleTask(task);
  }
}

export function scheduleTask(task: { id: number; schedule: string; command: string; name: string }) {
  if (activeCrons.has(task.id)) {
    activeCrons.get(task.id)?.stop();
  }
  if (!cron.validate(task.schedule)) return;
  const job = cron.schedule(task.schedule, async () => {
    await runTask(task.id);
  });
  activeCrons.set(task.id, job);
}

export function stopTask(id: number) {
  activeCrons.get(id)?.stop();
  activeCrons.delete(id);
}

interface AiTaskAction {
  action: "file_op" | "report" | "none";
  operation?: "delete" | "organize" | "dedup" | "rename" | "move";
  path?: string;
  criteria?: string;
  destination?: string;
  summary: string;
}

async function runTask(id: number): Promise<{ success: boolean; output: string }> {
  const [task] = await db.select().from(scheduledTasksTable).where(eq(scheduledTasksTable.id, id));
  if (!task) return { success: false, output: "Task not found" };

  const [settings] = await db.select().from(settingsTable).limit(1);
  const notes = await db.select().from(knowledgeNotesTable);
  const knowledgeCtx = notes.length
    ? "\n\n## User Knowledge Base\n" + notes.map(n => `### ${n.title}\n${n.content}`).join("\n\n")
    : "";

  let output = `Task recorded: ${task.command}`;
  let success = true;
  let filesProcessed = 0;

  try {
    const client = settings?.aiMode === "local"
      ? new OpenAI({ baseURL: `${settings.ollamaBaseUrl}/v1`, apiKey: "ollama" })
      : new OpenAI({
          apiKey: settings?.cloudApiKey || process.env.OPENAI_API_KEY || "",
          baseURL: settings?.cloudBaseUrl || undefined,
        });

    const systemPrompt = `You are AXIOM, a scheduled task runner. Analyze the task description and respond with a JSON object ONLY (no markdown, no explanation).

Schema:
{
  "action": "file_op" | "report" | "none",
  "operation": "delete" | "organize" | "dedup" | "rename" | "move",
  "path": "/absolute/path/to/directory",
  "criteria": "optional filter string (e.g. 'older than 14 days', '.tmp files')",
  "destination": "/destination/path (only for move)",
  "summary": "plain-English description of what was done or would be done"
}

Rules:
- Use "file_op" action only if the task clearly involves file system operations AND a real path can be derived from the knowledge base.
- Use "report" if the task is informational only.
- Use "none" if the task cannot be interpreted.
- The path MUST be an absolute path from the user's knowledge base. If no valid path is available, use "report" or "none".${knowledgeCtx}`;

    const completion = await client.chat.completions.create({
      model: settings?.aiModel || "gpt-4o-mini",
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: task.command },
      ],
      max_tokens: 512,
      response_format: { type: "json_object" },
    });

    const raw = completion.choices[0]?.message?.content || "{}";
    const parsed = JSON.parse(raw) as AiTaskAction;

    if (
      parsed.action === "file_op" &&
      parsed.operation &&
      parsed.path &&
      await isPathAllowed(parsed.path)
    ) {
      const result = await executeFileOperation({
        operation: parsed.operation,
        path: parsed.path,
        criteria: parsed.criteria,
        destination: parsed.destination,
        skipActivityLog: true,
      });
      filesProcessed = result.filesProcessed;
      output = parsed.summary || result.summary;
      success = result.success;

      await db.insert(activityLogTable).values({
        type: "scheduled",
        description: `Scheduled[${task.id}]: ${task.name}`,
        detail: `${output} — ${result.details.slice(0, 3).join(", ")}`,
        filesAffected: JSON.stringify(result.details.slice(0, 10)),
        undoable: result.undoKey !== null,
        undoData: result.undoKey,
      });
    } else {
      output = parsed.summary || `Task completed: ${task.command}`;
      await db.insert(activityLogTable).values({
        type: "scheduled",
        description: `Scheduled[${task.id}]: ${task.name}`,
        detail: output.slice(0, 500),
        filesAffected: "[]",
        undoable: false,
      });
    }
  } catch (err) {
    output = `AI provider unavailable — task recorded: ${task.command}`;
    success = false;
    await db.insert(activityLogTable).values({
      type: "scheduled",
      description: `Scheduled[${id}]: ${task.name}`,
      detail: output,
      filesAffected: "[]",
      undoable: false,
    });
  }

  await db.update(scheduledTasksTable).set({
    lastRunAt: new Date().toISOString(),
    lastRunStatus: success ? "success" : "error",
    nextRunAt: calcNextRun(task.schedule),
  }).where(eq(scheduledTasksTable.id, id));

  void filesProcessed;
  return { success, output };
}

// GET /scheduler/tasks
router.get("/scheduler/tasks", async (_req, res) => {
  const tasks = await db.select().from(scheduledTasksTable).orderBy(desc(scheduledTasksTable.createdAt));
  res.json(tasks);
});

// POST /scheduler/tasks
router.post("/scheduler/tasks", async (req, res) => {
  const body = CreateScheduledTaskBody.parse(req.body);
  const [task] = await db.insert(scheduledTasksTable).values({
    name: body.name,
    command: body.command,
    schedule: body.schedule,
    scheduleLabel: body.scheduleLabel,
    enabled: body.enabled !== false,
    nextRunAt: calcNextRun(body.schedule),
  }).returning();
  if (task.enabled) scheduleTask(task);
  res.status(201).json(task);
});

// GET /scheduler/tasks/:id
router.get("/scheduler/tasks/:id", async (req, res) => {
  const [task] = await db.select().from(scheduledTasksTable).where(eq(scheduledTasksTable.id, parseInt(req.params.id)));
  if (!task) return res.status(404).json({ error: "Not found" });
  res.json(task);
});

// GET /scheduler/tasks/:id/logs
router.get("/scheduler/tasks/:id/logs", async (req, res) => {
  const id = parseInt(req.params.id);
  const logs = await db
    .select()
    .from(activityLogTable)
    .where(
      and(
        eq(activityLogTable.type, "scheduled"),
        like(activityLogTable.description, `Scheduled[${id}]:%`)
      )
    )
    .orderBy(desc(activityLogTable.createdAt))
    .limit(20);
  res.json(logs);
});

// PATCH /scheduler/tasks/:id
router.patch("/scheduler/tasks/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  const body = UpdateScheduledTaskBody.parse(req.body);
  const updateData: Record<string, unknown> = { ...body };
  if (body.schedule) updateData.nextRunAt = calcNextRun(body.schedule);
  const [task] = await db.update(scheduledTasksTable).set(updateData).where(eq(scheduledTasksTable.id, id)).returning();
  if (!task) return res.status(404).json({ error: "Not found" });
  if (task.enabled) scheduleTask(task);
  else stopTask(id);
  res.json(task);
});

// DELETE /scheduler/tasks/:id
router.delete("/scheduler/tasks/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  stopTask(id);
  await db.delete(scheduledTasksTable).where(eq(scheduledTasksTable.id, id));
  res.status(204).send();
});

// POST /scheduler/tasks/:id/run
router.post("/scheduler/tasks/:id/run", async (req, res) => {
  const id = parseInt(req.params.id);
  const result = await runTask(id);
  res.json({ ...result, ranAt: new Date().toISOString() });
});

// POST /scheduler/tasks/:id/toggle
router.post("/scheduler/tasks/:id/toggle", async (req, res) => {
  const id = parseInt(req.params.id);
  const [existing] = await db.select().from(scheduledTasksTable).where(eq(scheduledTasksTable.id, id));
  if (!existing) return res.status(404).json({ error: "Not found" });
  const [task] = await db.update(scheduledTasksTable).set({ enabled: !existing.enabled }).where(eq(scheduledTasksTable.id, id)).returning();
  if (task.enabled) scheduleTask(task);
  else stopTask(id);
  res.json(task);
});

// GET /scheduler/status
router.get("/scheduler/status", async (_req, res) => {
  const tasks = await db.select().from(scheduledTasksTable);
  const now = Date.now();
  const statusTasks = tasks.map(t => ({
    id: t.id,
    name: t.name,
    enabled: t.enabled,
    nextRunAt: t.nextRunAt || null,
    secondsUntilRun: t.nextRunAt ? Math.max(0, Math.floor((new Date(t.nextRunAt).getTime() - now) / 1000)) : null,
  }));
  res.json({
    tasks: statusTasks,
    totalEnabled: tasks.filter(t => t.enabled).length,
    totalDisabled: tasks.filter(t => !t.enabled).length,
  });
});

export { runTask };
export default router;

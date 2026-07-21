import { Router } from "express";
import { db } from "@workspace/db";
import { settingsTable } from "@workspace/db";
import OpenAI from "openai";
import { PullAiModelBody } from "@workspace/api-zod";

const router = Router();

const CLOUD_MODELS = [
  { name: "gpt-4o", type: "cloud" as const, size: null, contextLength: 128000, description: "Most capable OpenAI model" },
  { name: "gpt-4o-mini", type: "cloud" as const, size: null, contextLength: 128000, description: "Fast and cost-efficient" },
  { name: "gpt-4-turbo", type: "cloud" as const, size: null, contextLength: 128000, description: "GPT-4 with vision" },
  { name: "gpt-3.5-turbo", type: "cloud" as const, size: null, contextLength: 16385, description: "Legacy fast model" },
];

interface PullProgress {
  status: "pulling" | "complete" | "error";
  progress: number;
  total: number;
  completed: number;
  startedAt: Date;
  completedAt: Date | null;
  error: string | null;
}

const pullProgressMap = new Map<string, PullProgress>();

async function checkOllama(baseUrl: string): Promise<{ available: boolean; version: string | null; models: Array<{ name: string; size: string }> }> {
  try {
    const res = await fetch(`${baseUrl}/api/tags`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return { available: false, version: null, models: [] };
    const data = await res.json() as { models?: Array<{ name: string; size: number }> };
    const vRes = await fetch(`${baseUrl}/api/version`, { signal: AbortSignal.timeout(2000) }).catch(() => null);
    let version: string | null = null;
    if (vRes?.ok) {
      const vData = await vRes.json() as { version?: string };
      version = vData.version || null;
    }
    const models = (data.models || []).map(m => ({
      name: m.name,
      size: m.size ? `${(m.size / 1e9).toFixed(1)} GB` : "unknown",
    }));
    return { available: true, version, models };
  } catch {
    return { available: false, version: null, models: [] };
  }
}

async function streamOllamaPull(ollamaUrl: string, modelName: string) {
  const progress: PullProgress = {
    status: "pulling",
    progress: 0,
    total: 0,
    completed: 0,
    startedAt: new Date(),
    completedAt: null,
    error: null,
  };
  pullProgressMap.set(modelName, progress);

  try {
    const res = await fetch(`${ollamaUrl}/api/pull`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: modelName, stream: true }),
      signal: AbortSignal.timeout(300000),
    });

    if (!res.ok || !res.body) {
      progress.status = "error";
      progress.error = `Ollama returned ${res.status}`;
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line) as { status?: string; total?: number; completed?: number };
          if (evt.total) progress.total = evt.total;
          if (evt.completed) {
            progress.completed = evt.completed;
            progress.progress = progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0;
          }
          if (evt.status === "success") {
            progress.status = "complete";
            progress.progress = 100;
            progress.completedAt = new Date();
          }
        } catch {}
      }
    }

    if (progress.status === "pulling") {
      progress.status = "complete";
      progress.progress = 100;
      progress.completedAt = new Date();
    }
  } catch (err) {
    progress.status = "error";
    progress.error = err instanceof Error ? err.message : "Unknown error";
  }
}

// GET /ai/status
router.get("/ai/status", async (_req, res) => {
  const [settings] = await db.select().from(settingsTable).limit(1);
  const ollamaUrl = settings?.ollamaBaseUrl || "http://localhost:11434";
  const { available, version } = await checkOllama(ollamaUrl);
  res.json({
    mode: settings?.aiMode || "cloud",
    ollamaAvailable: available,
    ollamaVersion: version,
    activeModel: settings?.aiModel || "gpt-4o-mini",
    cloudConfigured: !!(settings?.cloudApiKey || process.env.OPENAI_API_KEY),
  });
});

// GET /ai/models
router.get("/ai/models", async (_req, res) => {
  const [settings] = await db.select().from(settingsTable).limit(1);
  const ollamaUrl = settings?.ollamaBaseUrl || "http://localhost:11434";
  const { available, models: localModels } = await checkOllama(ollamaUrl);
  const local = available ? localModels.map(m => ({
    name: m.name,
    type: "local" as const,
    size: m.size,
    contextLength: null,
    description: "Local Ollama model",
  })) : [];
  res.json([...local, ...CLOUD_MODELS]);
});

// POST /ai/models/pull — starts async Ollama pull; poll /ai/models/pull/status/:name for progress
router.post("/ai/models/pull", async (req, res) => {
  const body = PullAiModelBody.parse(req.body);
  const [settings] = await db.select().from(settingsTable).limit(1);
  const ollamaUrl = settings?.ollamaBaseUrl || "http://localhost:11434";

  const existing = pullProgressMap.get(body.name);
  if (existing && existing.status === "pulling") {
    return res.json({ name: body.name, status: "pulling", progress: existing.progress, total: existing.total, completed: existing.completed });
  }

  const { available } = await checkOllama(ollamaUrl);
  if (!available) {
    return res.status(503).json({ error: "Ollama is not running. Start Ollama on localhost:11434 first." });
  }

  streamOllamaPull(ollamaUrl, body.name);
  res.json({ name: body.name, status: "pulling", progress: 0, total: 0, completed: 0 });
});

// GET /ai/models/pull/status/:name — real-time pull progress
router.get("/ai/models/pull/status/:name", (req, res) => {
  const name = decodeURIComponent(req.params.name);
  const progress = pullProgressMap.get(name);
  if (!progress) {
    return res.json({ name, status: "unknown", progress: 0 });
  }
  res.json({
    name,
    status: progress.status,
    progress: progress.progress,
    total: progress.total,
    completed: progress.completed,
    startedAt: progress.startedAt,
    completedAt: progress.completedAt,
    error: progress.error,
  });
});

// DELETE /ai/models/:name
router.delete("/ai/models/:name", async (req, res) => {
  const [settings] = await db.select().from(settingsTable).limit(1);
  const ollamaUrl = settings?.ollamaBaseUrl || "http://localhost:11434";
  try {
    await fetch(`${ollamaUrl}/api/delete`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: req.params.name }),
    });
  } catch {}
  res.status(204).send();
});

export default router;

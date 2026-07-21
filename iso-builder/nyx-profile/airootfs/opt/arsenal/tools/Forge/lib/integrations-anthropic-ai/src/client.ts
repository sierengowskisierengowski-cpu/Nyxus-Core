// GowskiNet FORGE runs entirely on local hardware — no cloud AI vendor, no
// API key, no outbound network dependency. This module talks to a local
// Ollama instance (http://127.0.0.1:11434 by default) instead of Anthropic's
// cloud API.
//
// The exported shape — `anthropic.messages.stream({ model, max_tokens, system,
// messages })` returning an async-iterable of Claude-style
// `content_block_delta` / `text_delta` events — is kept identical to the
// original Anthropic SDK surface this package used to wrap, so every call
// site (routes/threats.ts, routes/anthropic/index.ts) works unmodified.

const OLLAMA_HOST = (process.env.OLLAMA_HOST ?? "http://127.0.0.1:11434").replace(/\/+$/, "");
const DEFAULT_MODEL = process.env.OLLAMA_MODEL ?? "forge-sec";
const DEFAULT_TEMPERATURE = 0.7;

export type ChatRole = "user" | "assistant" | "system";
export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface MessagesStreamParams {
  /** Ignored value from Claude-model-name call sites; local model is chosen via OLLAMA_MODEL / options.model. */
  model?: string;
  max_tokens?: number;
  system?: string;
  messages: ChatMessage[];
  temperature?: number;
  /**
   * Ollama structured-output control. Either the string "json" (constrain to
   * any valid JSON) or a JSON Schema object (constrain to a specific shape).
   * Small local models are far more reliable at emitting parseable JSON when
   * this is set than when merely asked to "respond in JSON".
   */
  format?: "json" | Record<string, unknown>;
}

export type TextDeltaEvent = {
  type: "content_block_delta";
  delta: { type: "text_delta"; text: string };
};
export type MessageStopEvent = { type: "message_stop" };
export type StreamEvent = TextDeltaEvent | MessageStopEvent;

interface OllamaChatChunk {
  message?: { role: string; content: string };
  done: boolean;
  done_reason?: string;
}

async function* streamOllamaChat(params: MessagesStreamParams): AsyncGenerator<StreamEvent> {
  const messages: ChatMessage[] = params.system
    ? [{ role: "system", content: params.system }, ...params.messages]
    : params.messages;

  const res = await fetch(`${OLLAMA_HOST}/api/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      model: process.env.OLLAMA_MODEL ?? DEFAULT_MODEL,
      messages,
      stream: true,
      ...(params.format ? { format: params.format } : {}),
      options: {
        temperature: params.temperature ?? DEFAULT_TEMPERATURE,
        num_predict: params.max_tokens ?? 4096,
      },
    }),
  });

  if (!res.ok || !res.body) {
    const body = await res.text().catch(() => "");
    throw new Error(`Ollama chat request failed: HTTP ${res.status} ${res.statusText} ${body}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let newlineIdx: number;
      while ((newlineIdx = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newlineIdx).trim();
        buffer = buffer.slice(newlineIdx + 1);
        if (!line) continue;

        const chunk = JSON.parse(line) as OllamaChatChunk;
        if (chunk.message?.content) {
          yield {
            type: "content_block_delta",
            delta: { type: "text_delta", text: chunk.message.content },
          };
        }
        if (chunk.done) {
          yield { type: "message_stop" };
          return;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export interface TextContentBlock {
  type: "text";
  text: string;
}
export interface CreateMessageResult {
  content: TextContentBlock[];
}

async function createOllamaChat(params: MessagesStreamParams): Promise<CreateMessageResult> {
  let text = "";
  for await (const event of streamOllamaChat(params)) {
    if (event.type === "content_block_delta") text += event.delta.text;
  }
  return { content: [{ type: "text", text }] };
}

/** No API key is required for local Ollama inference; kept for call-site compatibility. */
export function isAnthropicConfigured(): boolean {
  return true;
}

/**
 * Best-effort JSON extraction for LLM output. Handles the common ways a local
 * model deviates from clean JSON:
 *   - markdown code fences (```json … ```)
 *   - prose before/after the object
 *   - trailing commas
 * Returns the parsed object, or null if nothing parseable is found.
 */
export function extractJson<T = unknown>(raw: string): T | null {
  if (!raw) return null;
  let text = raw.trim();

  // Strip a leading/trailing markdown code fence if present.
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) text = fence[1].trim();

  // Narrow to the outermost {...} span.
  const first = text.indexOf("{");
  const last = text.lastIndexOf("}");
  if (first !== -1 && last > first) text = text.slice(first, last + 1);

  const attempts = [
    text,
    // Remove trailing commas before } or ].
    text.replace(/,(\s*[}\]])/g, "$1"),
  ];
  for (const candidate of attempts) {
    try {
      return JSON.parse(candidate) as T;
    } catch {
      // try next
    }
  }
  return null;
}

export const anthropic = {
  messages: {
    stream(params: MessagesStreamParams): AsyncIterable<StreamEvent> {
      return { [Symbol.asyncIterator]: () => streamOllamaChat(params) };
    },
    create(params: MessagesStreamParams): Promise<CreateMessageResult> {
      return createOllamaChat(params);
    },
  },
};

/** Quick reachability + model-presence check, used by /api/health. */
export async function checkLocalAiHealth(): Promise<{ ok: boolean; model: string; detail: string }> {
  const model = process.env.OLLAMA_MODEL ?? DEFAULT_MODEL;
  try {
    const res = await fetch(`${OLLAMA_HOST}/api/tags`, { signal: AbortSignal.timeout(3000) });
    if (!res.ok) return { ok: false, model, detail: `Ollama HTTP ${res.status}` };
    const data = (await res.json()) as { models?: { name: string }[] };
    const present = data.models?.some((m) => m.name === model || m.name.startsWith(`${model}:`));
    return present
      ? { ok: true, model, detail: "Local model loaded and reachable." }
      : { ok: false, model, detail: `Ollama is up but model "${model}" is not pulled.` };
  } catch (err) {
    return { ok: false, model, detail: err instanceof Error ? err.message : "Ollama unreachable" };
  }
}

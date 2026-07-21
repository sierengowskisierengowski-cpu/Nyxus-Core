import { anthropic } from "@workspace/integrations-anthropic-ai";

const DEFAULT_MODEL = "claude-sonnet-4-5";

export async function getClaudeStatus(): Promise<"ready" | "missing-key" | "error"> {
  if (!process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY && !process.env.ANTHROPIC_API_KEY) {
    return "missing-key";
  }
  return "ready";
}

const TUTOR_SYSTEM = `You are the REDFORGE Tutor — a senior cybersecurity defender mentoring a junior SOC analyst.

Your role:
- Explain attack techniques, log artifacts, code snippets, and detection logic CLEARLY and TACTICALLY.
- Frame everything from the DEFENDER perspective: what to look for, how to detect, how to harden.
- Reference MITRE ATT&CK technique IDs (e.g. T1059.001) when relevant.
- Suggest concrete telemetry sources (Sysmon Event IDs, auditd rules, Suricata signatures, EDR signals).
- Never write novel malware or weaponized exploit code. You can explain existing public techniques and show defensive code.
- Be concise, dense, terminal-friendly. Use markdown headings, bullets, fenced code blocks for commands and detection rules.

If asked to do something offensive that crosses into weaponization or unauthorized targeting, refuse politely and steer the user back to defense.`;

const QUIZ_SYSTEM = `You are the REDFORGE Quiz Generator. Output ONLY valid JSON matching this exact shape:
{"questions":[{"question":"...","answer":"...","difficulty":"easy|medium|hard"}]}

Generate study questions about the requested topic for a SOC analyst studying detection engineering. Each answer should be 1-3 sentences, accurate, and reference MITRE/data sources where relevant. No markdown, no preamble, no trailing text — JSON only.`;

export async function streamTutor(
  prompt: string,
  context: string | undefined,
  kind: string | undefined,
  model: string,
  onDelta: (text: string) => void,
): Promise<void> {
  const userMessage = context
    ? `Context (${kind ?? "general"}):\n\`\`\`\n${context}\n\`\`\`\n\nQuestion: ${prompt}`
    : prompt;

  const stream = await anthropic.messages.stream({
    model: model || DEFAULT_MODEL,
    max_tokens: 2048,
    system: TUTOR_SYSTEM,
    messages: [{ role: "user", content: userMessage }],
  });

  for await (const event of stream) {
    if (event.type === "content_block_delta" && event.delta.type === "text_delta") {
      onDelta(event.delta.text);
    }
  }
}

export interface QuizQuestion {
  question: string;
  answer: string;
  difficulty?: string;
}

export async function generateQuiz(
  topic: string,
  techniqueId: string | undefined,
  count: number,
  model: string,
): Promise<QuizQuestion[]> {
  const prompt = `Generate ${count} study questions about: ${topic}${
    techniqueId ? ` (MITRE technique ${techniqueId})` : ""
  }. Mix difficulties. Cover detection, telemetry, attacker behavior, and mitigation.`;

  const response = await anthropic.messages.create({
    model: model || DEFAULT_MODEL,
    max_tokens: 2048,
    system: QUIZ_SYSTEM,
    messages: [{ role: "user", content: prompt }],
  });

  const text = response.content
    .filter((b): b is { type: "text"; text: string } & typeof b => b.type === "text")
    .map((b) => b.text)
    .join("");

  const jsonStart = text.indexOf("{");
  const jsonEnd = text.lastIndexOf("}");
  if (jsonStart === -1 || jsonEnd === -1) return [];
  try {
    const parsed = JSON.parse(text.slice(jsonStart, jsonEnd + 1));
    if (Array.isArray(parsed.questions)) return parsed.questions as QuizQuestion[];
  } catch {
    // fall through
  }
  return [];
}

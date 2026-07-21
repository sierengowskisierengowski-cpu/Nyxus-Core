import { Router } from "express";
import { db } from "@workspace/db";
import { chatSessionsTable, chatMessagesTable } from "@workspace/db";
import { knowledgeNotesTable, settingsTable } from "@workspace/db";
import { activityLogTable } from "@workspace/db";
import { eq, desc, count, sql } from "drizzle-orm";
import OpenAI from "openai";
import {
  CreateChatSessionBody,
  SendChatMessageBody,
} from "@workspace/api-zod";

const router = Router();

function getOpenAIClient(settings: { cloudApiKey: string | null; cloudBaseUrl: string | null; ollamaBaseUrl: string; aiMode: string }) {
  if (settings.aiMode === "local") {
    return new OpenAI({
      baseURL: `${settings.ollamaBaseUrl}/v1`,
      apiKey: "ollama",
    });
  }
  return new OpenAI({
    apiKey: settings.cloudApiKey || process.env.OPENAI_API_KEY || "",
    baseURL: settings.cloudBaseUrl || undefined,
  });
}

async function getKnowledgeContext(): Promise<string> {
  const notes = await db.select().from(knowledgeNotesTable).orderBy(desc(knowledgeNotesTable.pinned));
  if (!notes.length) return "";
  return "\n\n## User Knowledge Base\n" + notes.map(n => `### ${n.title}\n${n.content}`).join("\n\n");
}

function buildSystemPrompt(knowledgeCtx: string): string {
  return `You are AXIOM, a premium desktop AI assistant. You help the user manage their computer — organizing files, running scheduled tasks, answering questions about their system, and executing file operations.

When the user asks you to perform a file operation (delete, move, organize, rename, find duplicates), respond with a JSON action block at the end of your message in this format:
<action>{"type":"file_op","operation":"delete|move|organize|rename|dedup","path":"/path/to/dir","criteria":"optional criteria","destination":"optional dest","requiresConfirmation":true,"description":"human readable description of what will happen"}</action>

For informational requests, just respond naturally. Keep responses concise and direct. You are speaking to a power user.${knowledgeCtx}`;
}

// GET /chat/sessions
router.get("/chat/sessions", async (_req, res) => {
  const sessions = await db
    .select({
      id: chatSessionsTable.id,
      title: chatSessionsTable.title,
      createdAt: chatSessionsTable.createdAt,
      updatedAt: chatSessionsTable.updatedAt,
      messageCount: sql<number>`(SELECT COUNT(*) FROM chat_messages WHERE session_id = ${chatSessionsTable.id})`.mapWith(Number),
    })
    .from(chatSessionsTable)
    .orderBy(desc(chatSessionsTable.updatedAt));
  res.json(sessions);
});

// POST /chat/sessions
router.post("/chat/sessions", async (req, res) => {
  const body = CreateChatSessionBody.parse(req.body);
  const [session] = await db.insert(chatSessionsTable).values({
    title: body.title || "New Chat",
  }).returning();
  res.status(201).json({ ...session, messageCount: 0 });
});

// GET /chat/sessions/:id
router.get("/chat/sessions/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  const [session] = await db.select().from(chatSessionsTable).where(eq(chatSessionsTable.id, id));
  if (!session) return res.status(404).json({ error: "Not found" });
  const messages = await db.select().from(chatMessagesTable).where(eq(chatMessagesTable.sessionId, id)).orderBy(chatMessagesTable.createdAt);
  res.json({ ...session, messages });
});

// DELETE /chat/sessions/:id
router.delete("/chat/sessions/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  await db.delete(chatSessionsTable).where(eq(chatSessionsTable.id, id));
  res.status(204).send();
});

// POST /chat/sessions/:id/messages/stream  — SSE streaming endpoint
router.post("/chat/sessions/:id/messages/stream", async (req, res) => {
  const sessionId = parseInt(req.params.id);
  const body = SendChatMessageBody.parse(req.body);

  const [session] = await db.select().from(chatSessionsTable).where(eq(chatSessionsTable.id, sessionId));
  if (!session) return res.status(404).json({ error: "Not found" });

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  const sendEvent = (event: string, data: unknown) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  const [userMessage] = await db.insert(chatMessagesTable).values({
    sessionId,
    role: "user",
    content: body.content,
  }).returning();
  sendEvent("user_message", { id: userMessage.id });

  const [settingsRow] = await db.select().from(settingsTable).limit(1);
  const knowledgeCtx = await getKnowledgeContext();
  const systemPrompt = buildSystemPrompt(knowledgeCtx);

  const previousMessages = await db.select().from(chatMessagesTable)
    .where(eq(chatMessagesTable.sessionId, sessionId))
    .orderBy(chatMessagesTable.createdAt)
    .limit(20);

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt },
    ...previousMessages.slice(0, -1).map(m => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
    { role: "user", content: body.content },
  ];

  let aiContent = "";
  let actionType: string | null = null;
  let actionData: string | null = null;
  let action = null;

  try {
    const client = getOpenAIClient(settingsRow || {
      cloudApiKey: null, cloudBaseUrl: null,
      ollamaBaseUrl: "http://localhost:11434", aiMode: "cloud",
    });

    const stream = await client.chat.completions.create({
      model: settingsRow?.aiModel || "gpt-4o-mini",
      messages,
      max_tokens: 1024,
      stream: true,
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) {
        aiContent += delta;
        sendEvent("chunk", { content: delta });
      }
    }

    if (!aiContent) {
      aiContent = "I understand your request. Let me help you with that.";
    }

    const actionMatch = aiContent.match(/<action>(.*?)<\/action>/s);
    if (actionMatch) {
      try {
        const parsed = JSON.parse(actionMatch[1]);
        actionType = parsed.type || "file_op";
        actionData = actionMatch[1];
        action = {
          type: parsed.type || "file_op",
          description: parsed.description || "File operation pending",
          payload: actionMatch[1],
          requiresConfirmation: parsed.requiresConfirmation !== false,
        };
        aiContent = aiContent.replace(/<action>.*?<\/action>/s, "").trim();
      } catch {}
    }
  } catch {
    aiContent = "I'm having trouble connecting to the AI provider. Please check your settings — make sure your API key is configured or Ollama is running locally.";
    sendEvent("chunk", { content: aiContent });
  }

  const [assistantMessage] = await db.insert(chatMessagesTable).values({
    sessionId,
    role: "assistant",
    content: aiContent,
    actionType,
    actionData,
  }).returning();

  await db.update(chatSessionsTable).set({ updatedAt: new Date().toISOString() }).where(eq(chatSessionsTable.id, sessionId));

  if (session.title === "New Chat" && body.content.length > 0) {
    const newTitle = body.content.slice(0, 60) + (body.content.length > 60 ? "..." : "");
    await db.update(chatSessionsTable).set({ title: newTitle, updatedAt: new Date().toISOString() }).where(eq(chatSessionsTable.id, sessionId));
  }

  await db.insert(activityLogTable).values({
    type: "chat",
    description: `Chat: ${body.content.slice(0, 80)}`,
    detail: aiContent.slice(0, 200),
    filesAffected: "[]",
    undoable: false,
  });

  sendEvent("done", { messageId: assistantMessage.id, action });
  res.end();
});

// POST /chat/sessions/:id/messages  — non-streaming fallback
router.post("/chat/sessions/:id/messages", async (req, res) => {
  const sessionId = parseInt(req.params.id);
  const body = SendChatMessageBody.parse(req.body);

  const [session] = await db.select().from(chatSessionsTable).where(eq(chatSessionsTable.id, sessionId));
  if (!session) return res.status(404).json({ error: "Not found" });

  const [userMessage] = await db.insert(chatMessagesTable).values({
    sessionId,
    role: "user",
    content: body.content,
  }).returning();

  const [settingsRow] = await db.select().from(settingsTable).limit(1);
  const knowledgeCtx = await getKnowledgeContext();
  const systemPrompt = buildSystemPrompt(knowledgeCtx);

  const previousMessages = await db.select().from(chatMessagesTable)
    .where(eq(chatMessagesTable.sessionId, sessionId))
    .orderBy(chatMessagesTable.createdAt)
    .limit(20);

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt },
    ...previousMessages.slice(0, -1).map(m => ({
      role: m.role as "user" | "assistant",
      content: m.content,
    })),
    { role: "user", content: body.content },
  ];

  let aiContent = "I understand your request. Let me help you with that.";
  let actionType: string | null = null;
  let actionData: string | null = null;
  let action = null;

  try {
    const client = getOpenAIClient(settingsRow || {
      cloudApiKey: null, cloudBaseUrl: null,
      ollamaBaseUrl: "http://localhost:11434", aiMode: "cloud",
    });
    const completion = await client.chat.completions.create({
      model: settingsRow?.aiModel || "gpt-4o-mini",
      messages,
      max_tokens: 1024,
    });
    aiContent = completion.choices[0]?.message?.content || aiContent;

    const actionMatch = aiContent.match(/<action>(.*?)<\/action>/s);
    if (actionMatch) {
      try {
        const parsed = JSON.parse(actionMatch[1]);
        actionType = parsed.type || "file_op";
        actionData = actionMatch[1];
        action = {
          type: parsed.type || "file_op",
          description: parsed.description || "File operation pending",
          payload: actionMatch[1],
          requiresConfirmation: parsed.requiresConfirmation !== false,
        };
        aiContent = aiContent.replace(/<action>.*?<\/action>/s, "").trim();
      } catch {}
    }
  } catch {
    aiContent = "I'm having trouble connecting to the AI provider. Please check your settings — make sure your API key is configured or Ollama is running locally.";
  }

  const [assistantMessage] = await db.insert(chatMessagesTable).values({
    sessionId,
    role: "assistant",
    content: aiContent,
    actionType,
    actionData,
  }).returning();

  await db.update(chatSessionsTable).set({ updatedAt: new Date().toISOString() }).where(eq(chatSessionsTable.id, sessionId));

  if (session.title === "New Chat" && body.content.length > 0) {
    const newTitle = body.content.slice(0, 60) + (body.content.length > 60 ? "..." : "");
    await db.update(chatSessionsTable).set({ title: newTitle, updatedAt: new Date().toISOString() }).where(eq(chatSessionsTable.id, sessionId));
  }

  await db.insert(activityLogTable).values({
    type: "chat",
    description: `Chat: ${body.content.slice(0, 80)}`,
    detail: aiContent.slice(0, 200),
    filesAffected: "[]",
    undoable: false,
  });

  void userMessage;
  res.json({ message: assistantMessage, action });
});

// GET /chat/recent
router.get("/chat/recent", async (_req, res) => {
  const sessions = await db
    .select({
      id: chatSessionsTable.id,
      title: chatSessionsTable.title,
      updatedAt: chatSessionsTable.updatedAt,
    })
    .from(chatSessionsTable)
    .orderBy(desc(chatSessionsTable.updatedAt))
    .limit(10);

  const results = await Promise.all(sessions.map(async (s) => {
    const [lastMsg] = await db.select().from(chatMessagesTable)
      .where(eq(chatMessagesTable.sessionId, s.id))
      .orderBy(desc(chatMessagesTable.createdAt))
      .limit(1);
    const [{ value: msgCount }] = await db.select({ value: count() }).from(chatMessagesTable).where(eq(chatMessagesTable.sessionId, s.id));
    return {
      ...s,
      lastMessage: lastMsg?.content?.slice(0, 100) || null,
      messageCount: Number(msgCount),
    };
  }));

  res.json(results);
});

export default router;

import { Router } from "express";
import fs from "node:fs";
import path from "node:path";
import { db } from "@workspace/db";
import { wordlistsTable } from "@workspace/db";
import { eq, desc } from "drizzle-orm";
import { WORDLISTS_DIR, ensureWorkspace, safeFileName } from "../lib/workspace-paths";

const router = Router();

function formatWordlist(w: typeof wordlistsTable.$inferSelect) {
  return {
    ...w,
    tags: (() => { try { return w.tags ? JSON.parse(w.tags) : []; } catch { return []; } })(),
    createdAt: w.createdAt.toISOString(),
    lastUsed: w.lastUsed?.toISOString() ?? null,
  };
}

router.get("/wordlists", async (req, res) => {
  try {
    const wordlists = await db.select().from(wordlistsTable).orderBy(desc(wordlistsTable.createdAt));
    res.json(wordlists.map(formatWordlist));
  } catch (err) {
    req.log.error(err, "Failed to list wordlists");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/wordlists", async (req, res) => {
  try {
    const { name, description, words, content, tags } = req.body;
    if (!name) return res.status(400).json({ error: "name is required" });

    // Accept either a `words` array or a raw multiline `content` string (upload).
    let wordContent = "";
    if (typeof content === "string") wordContent = content;
    else if (Array.isArray(words)) wordContent = words.join("\n");

    const lines = wordContent.split("\n").filter((l) => l.trim().length > 0);
    const wordCount = lines.length;
    const normalized = lines.join("\n") + (lines.length > 0 ? "\n" : "");
    const sizeBytes = Buffer.byteLength(normalized, "utf8");

    if (wordCount === 0) {
      return res.status(400).json({ error: "wordlist content is empty" });
    }

    // Persist the real file into the app-owned workspace so the tools can use it.
    ensureWorkspace();
    const fileName = `${Date.now()}-${safeFileName(name, "wordlist")}.txt`;
    const filePath = path.join(WORDLISTS_DIR, fileName);
    fs.writeFileSync(filePath, normalized, "utf8");

    const [wordlist] = await db.insert(wordlistsTable).values({
      name,
      description: description || null,
      wordCount,
      sizeBytes,
      source: "custom",
      isBuiltin: false,
      tags: JSON.stringify(tags || []),
      words: normalized,
      filePath,
    }).returning();

    res.status(201).json(formatWordlist(wordlist));
  } catch (err) {
    req.log.error(err, "Failed to create wordlist");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/wordlists/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [wordlist] = await db.select().from(wordlistsTable).where(eq(wordlistsTable.id, id)).limit(1);
    if (!wordlist) return res.status(404).json({ error: "Wordlist not found" });
    res.json(formatWordlist(wordlist));
  } catch (err) {
    req.log.error(err, "Failed to get wordlist");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/wordlists/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [wl] = await db.select().from(wordlistsTable).where(eq(wordlistsTable.id, id)).limit(1);
    if (wl?.filePath) {
      try {
        // Only delete files inside the managed workspace dir.
        if (path.resolve(wl.filePath).startsWith(path.resolve(WORDLISTS_DIR))) {
          fs.rmSync(wl.filePath, { force: true });
        }
      } catch {
        /* best-effort cleanup */
      }
    }
    await db.delete(wordlistsTable).where(eq(wordlistsTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error(err, "Failed to delete wordlist");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

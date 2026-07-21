import { Router } from "express";
import { db } from "@workspace/db";
import { activityLogTable } from "@workspace/db";
import { eq, desc, count, sql } from "drizzle-orm";
import { ListActivityLogQueryParams } from "@workspace/api-zod";
import fs from "fs/promises";
import path from "path";

const router = Router();

// GET /activity
router.get("/activity", async (req, res) => {
  const query = ListActivityLogQueryParams.parse(req.query);
  const limit = query.limit ?? 50;
  let rows;
  if (!query.type || query.type === "all") {
    rows = await db.select().from(activityLogTable)
      .orderBy(desc(activityLogTable.createdAt))
      .limit(limit);
  } else {
    rows = await db.select().from(activityLogTable)
      .where(eq(activityLogTable.type, query.type as "chat" | "file_op" | "scheduled"))
      .orderBy(desc(activityLogTable.createdAt))
      .limit(limit);
  }
  const result = rows.map(r => ({
    ...r,
    filesAffected: JSON.parse(r.filesAffected || "[]"),
  }));
  res.json(result);
});

// POST /activity/:id/undo
router.post("/activity/:id/undo", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) return res.status(400).json({ error: "Invalid id" });

  const [entry] = await db.select().from(activityLogTable).where(eq(activityLogTable.id, id));
  if (!entry) return res.status(404).json({ error: "Not found" });
  if (!entry.undoable) {
    return res.json({ success: false, message: "This action is not undoable", filesRestored: [], errors: [] });
  }
  if (entry.undone) {
    return res.json({ success: false, message: "Already undone", filesRestored: [], errors: [] });
  }

  const filesRestored: string[] = [];
  const undoErrors: Array<{ file: string; error: string }> = [];

  if (entry.undoData) {
    let undoInfo: {
      files?: Array<{ tempPath: string; originalPath: string }>;
      moves?: Array<{ from: string; to: string }>;
    };
    try {
      undoInfo = JSON.parse(entry.undoData);
    } catch {
      return res.status(500).json({ success: false, message: "Corrupt undo data", filesRestored: [], errors: [] });
    }

    // Undo delete/dedup: restore from temp dir back to original path
    for (const f of undoInfo.files || []) {
      try {
        await fs.access(f.tempPath);
        await fs.mkdir(path.dirname(f.originalPath), { recursive: true });
        await fs.rename(f.tempPath, f.originalPath);
        filesRestored.push(f.originalPath);
      } catch (err) {
        undoErrors.push({
          file: f.originalPath,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    // Undo move/organize/rename: reverse each source→dest mapping (in reverse order)
    for (const m of (undoInfo.moves || []).slice().reverse()) {
      try {
        await fs.access(m.to);
        await fs.mkdir(path.dirname(m.from), { recursive: true });
        await fs.rename(m.to, m.from);
        filesRestored.push(m.from);
      } catch (err) {
        undoErrors.push({
          file: m.from,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  }

  // Mark undone only if at least some files were restored (partial success is still marked done)
  if (filesRestored.length > 0 || undoErrors.length === 0) {
    await db.update(activityLogTable).set({ undone: true }).where(eq(activityLogTable.id, id));
  }

  const success = filesRestored.length > 0;
  const message = success
    ? `Restored ${filesRestored.length} file(s)${undoErrors.length > 0 ? ` (${undoErrors.length} failed)` : ""}`
    : undoErrors.length > 0
      ? `Undo failed: ${undoErrors[0].error}`
      : "Nothing to undo";

  res.json({ success, message, filesRestored, errors: undoErrors });
});

// GET /activity/summary
router.get("/activity/summary", async (_req, res) => {
  const [totalRow] = await db.select({ value: count() }).from(activityLogTable);
  const [chatRow] = await db.select({ value: count() }).from(activityLogTable).where(eq(activityLogTable.type, "chat"));
  const [fileRow] = await db.select({ value: count() }).from(activityLogTable).where(eq(activityLogTable.type, "file_op"));
  const [schedRow] = await db.select({ value: count() }).from(activityLogTable).where(eq(activityLogTable.type, "scheduled"));

  const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  const [recentRow] = await db.select({ value: count() }).from(activityLogTable)
    .where(sql`created_at > ${since}`);

  res.json({
    total: Number(totalRow.value),
    byType: {
      chat: Number(chatRow.value),
      file_op: Number(fileRow.value),
      scheduled: Number(schedRow.value),
    },
    recentCount: Number(recentRow.value),
  });
});

export default router;

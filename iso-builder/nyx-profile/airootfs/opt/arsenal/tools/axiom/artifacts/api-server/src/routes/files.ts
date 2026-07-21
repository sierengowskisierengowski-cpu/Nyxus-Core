import { Router } from "express";
import { db } from "@workspace/db";
import { allowedPathsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import fs from "fs/promises";
import {
  ScanFilesBody,
  PreviewFileOpBody,
  ExecuteFileOpBody,
  AddAllowedPathBody,
} from "@workspace/api-zod";
import {
  isPathAllowed,
  scanDirectory,
  applyCriteria,
  executeFileOperation,
  TYPE_MAP,
} from "../lib/file-executor";

const router = Router();

// GET /files/allowed-paths
router.get("/files/allowed-paths", async (_req, res) => {
  const paths = await db.select().from(allowedPathsTable);
  res.json(paths);
});

// POST /files/allowed-paths
router.post("/files/allowed-paths", async (req, res) => {
  const body = AddAllowedPathBody.parse(req.body);
  try {
    await fs.access(body.path);
  } catch {
    return res.status(400).json({ error: "Path does not exist or is not accessible" });
  }
  const [created] = await db.insert(allowedPathsTable).values({
    path: body.path,
    label: body.label,
  }).returning().catch(() => [null]);
  if (!created) return res.status(409).json({ error: "Path already added" });
  res.status(201).json(created);
});

// DELETE /files/allowed-paths/:id
router.delete("/files/allowed-paths/:id", async (req, res) => {
  await db.delete(allowedPathsTable).where(eq(allowedPathsTable.id, parseInt(req.params.id)));
  res.status(204).send();
});

// POST /files/scan
router.post("/files/scan", async (req, res) => {
  const body = ScanFilesBody.parse(req.body);
  if (!await isPathAllowed(body.path)) {
    return res.status(403).json({ error: "Path not in allowed list. Add it in Settings > Allowed Paths first." });
  }
  try {
    const files = await scanDirectory(body.path, body.recursive ?? false, body.maxDepth ?? 2);
    const totalSize = files.filter(f => f.type === "file").reduce((sum, f) => sum + f.size, 0);
    res.json({ path: body.path, files, totalCount: files.length, totalSize });
  } catch {
    res.status(400).json({ error: "Could not scan directory" });
  }
});

// POST /files/preview
router.post("/files/preview", async (req, res) => {
  const body = PreviewFileOpBody.parse(req.body);
  if (!await isPathAllowed(body.path)) {
    return res.status(403).json({ error: "Path not allowed" });
  }

  const files = await scanDirectory(body.path, true, 3);
  let affected = files.filter(f => f.type === "file");
  let summary = "";
  const reversible = true;

  if (body.operation === "delete") {
    affected = applyCriteria(affected, body.criteria);
    summary = `Delete ${affected.length} files (${(affected.reduce((s, f) => s + f.size, 0) / 1e6).toFixed(1)} MB)`;
  } else if (body.operation === "organize") {
    summary = `Organize ${affected.length} files by type into subfolders (${Object.keys(TYPE_MAP).length > 0 ? Object.values(TYPE_MAP).filter((v, i, a) => a.indexOf(v) === i).join(", ") : "Images, Videos, Documents, etc."})`;
  } else if (body.operation === "dedup") {
    const sizeMap = new Map<number, typeof affected>();
    affected.forEach(f => {
      const arr = sizeMap.get(f.size) || [];
      arr.push(f);
      sizeMap.set(f.size, arr);
    });
    affected = [...sizeMap.values()].filter(g => g.length > 1).flatMap(g => g.slice(1));
    summary = `Remove ${affected.length} potential duplicate files (same size)`;
  } else if (body.operation === "rename") {
    const criteria = body.criteria || "";
    const previewCount = Math.min(affected.length, 5);
    summary = `Rename ${affected.length} files — e.g. applying: ${criteria || "custom pattern"} (showing first ${previewCount})`;
    affected = affected.slice(0, 100);
  } else if (body.operation === "move" && body.destination) {
    summary = `Move ${affected.length} files to ${body.destination}`;
  } else {
    summary = `Process ${affected.length} files`;
  }

  res.json({
    operation: body.operation,
    affectedFiles: affected.slice(0, 100),
    summary,
    totalSize: affected.reduce((s, f) => s + f.size, 0),
    reversible,
  });
});

// POST /files/execute
router.post("/files/execute", async (req, res) => {
  const body = ExecuteFileOpBody.parse(req.body);
  if (!await isPathAllowed(body.path)) {
    return res.status(403).json({ error: "Path not allowed" });
  }
  if (!body.confirmed) {
    return res.status(400).json({ error: "Operation not confirmed" });
  }
  if (body.operation === "move" && body.destination && !await isPathAllowed(body.destination)) {
    return res.status(403).json({ error: "Move destination is not in allowed paths" });
  }

  const result = await executeFileOperation({
    operation: body.operation,
    path: body.path,
    criteria: body.criteria,
    destination: body.destination,
  });

  res.json(result);
});

export default router;

import { Router } from "express";
import { getKnowledgeBaseStatus, loadMitreDataset } from "../lib/mitre";

const router = Router();

router.get("/knowledge-base/status", (_req, res) => {
  res.json(getKnowledgeBaseStatus());
});

// Real technique catalog (filterable by tactic shortname / free-text query).
router.get("/knowledge-base/techniques", (req, res) => {
  const ds = loadMitreDataset();
  if (!ds) {
    res.status(503).json({ error: "MITRE dataset not loaded" });
    return;
  }
  const tactic = typeof req.query.tactic === "string" ? req.query.tactic : undefined;
  const q = typeof req.query.q === "string" ? req.query.q.toLowerCase() : undefined;
  const limit = Math.min(Number(req.query.limit) || 100, 1000);

  let techniques = ds.techniques;
  if (tactic) techniques = techniques.filter((t) => t.tactics.includes(tactic));
  if (q) {
    techniques = techniques.filter(
      (t) =>
        t.id.toLowerCase().includes(q) ||
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q),
    );
  }

  res.json({
    total: techniques.length,
    tactics: ds.tactics,
    techniques: techniques.slice(0, limit),
  });
});

export default router;

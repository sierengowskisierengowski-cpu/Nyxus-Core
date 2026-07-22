import { Router, type IRouter } from "express";
import { requireAuth } from "../middlewares/requireAuth";
import { TACTICS, TECHNIQUES } from "../lib/mitre";
import { LOLBAS, GTFOBINS, MALWARE, ATOMIC_TESTS, CVES, type KbEntryData } from "../lib/kb-data";

const router: IRouter = Router();

router.get("/kb/mitre/tactics", requireAuth, (_req, res) => {
  res.json(
    TACTICS.map((t) => ({
      ...t,
      techniqueCount: TECHNIQUES.filter((tech) => tech.tactics.includes(t.name)).length,
    })),
  );
});

router.get("/kb/mitre/techniques", requireAuth, (req, res) => {
  const tactic = qs(req.query.tactic);
  const platform = qs(req.query.platform);
  const search = qs(req.query.search);
  let list = TECHNIQUES.slice();
  if (tactic) list = list.filter((t) => t.tactics.some((x) => x.toLowerCase() === tactic.toLowerCase()));
  if (platform) list = list.filter((t) => t.platforms.some((x) => x.toLowerCase() === platform.toLowerCase()));
  if (search) {
    const q = search.toLowerCase();
    list = list.filter(
      (t) => t.id.toLowerCase().includes(q) || t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q),
    );
  }
  res.json(list.map(({ id, name, description, tactics, platforms }) => ({ id, name, description, tactics, platforms })));
});

router.get("/kb/mitre/techniques/:techniqueId", requireAuth, (req, res) => {
  const t = TECHNIQUES.find((x) => x.id === req.params.techniqueId);
  if (!t) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json({
    id: t.id,
    name: t.name,
    description: t.description,
    tactics: t.tactics,
    platforms: t.platforms,
    detection: t.detection,
    mitigation: t.mitigation,
    dataSources: t.dataSources,
    references: t.references,
    subTechniques: t.subTechniques ?? [],
  });
});

function kbList(data: KbEntryData[]) {
  return (search?: string) => {
    let list = data;
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (e) => e.name.toLowerCase().includes(q) || e.summary.toLowerCase().includes(q) || (e.tags ?? []).some((t) => t.includes(q)),
      );
    }
    return list.map((e) => ({ name: e.name, summary: e.summary, category: e.category, tags: e.tags ?? [] }));
  };
}

function kbDetail(data: KbEntryData[]) {
  return (name: string) => {
    const e = data.find((x) => x.name.toLowerCase() === name.toLowerCase());
    if (!e) return null;
    return {
      name: e.name,
      summary: e.summary,
      category: e.category,
      tags: e.tags ?? [],
      description: e.description,
      examples: e.examples ?? [],
      mitreTechniques: e.mitreTechniques ?? [],
      references: e.references ?? [],
    };
  };
}

const lolbasList = kbList(LOLBAS);
const lolbasDetail = kbDetail(LOLBAS);
const gtfoList = kbList(GTFOBINS);
const gtfoDetail = kbDetail(GTFOBINS);
const malwareDetail = kbDetail(MALWARE);

function qs(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

router.get("/kb/lolbas", requireAuth, (req, res) => res.json(lolbasList(qs(req.query.search))));
router.get("/kb/lolbas/:name", requireAuth, (req, res) => {
  const d = lolbasDetail(String(req.params.name));
  if (!d) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(d);
});

router.get("/kb/gtfobins", requireAuth, (req, res) => res.json(gtfoList(qs(req.query.search))));
router.get("/kb/gtfobins/:name", requireAuth, (req, res) => {
  const d = gtfoDetail(String(req.params.name));
  if (!d) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(d);
});

router.get("/kb/malware", requireAuth, (_req, res) => res.json(kbList(MALWARE)()));
router.get("/kb/malware/:name", requireAuth, (req, res) => {
  const d = malwareDetail(String(req.params.name));
  if (!d) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(d);
});

router.get("/kb/atomic-tests", requireAuth, (req, res) => {
  const technique = qs(req.query.technique);
  const platform = qs(req.query.platform);
  const search = qs(req.query.search);
  let list = ATOMIC_TESTS.slice();
  if (technique) list = list.filter((t) => t.techniqueId.toLowerCase() === technique.toLowerCase());
  if (platform) list = list.filter((t) => t.platforms.includes(platform.toLowerCase()));
  if (search) {
    const q = search.toLowerCase();
    list = list.filter((t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q));
  }
  res.json(
    list.map((t) => ({
      id: t.id,
      name: t.name,
      techniqueId: t.techniqueId,
      techniqueName: t.techniqueName,
      description: t.description,
      platforms: t.platforms,
      executor: t.executor,
    })),
  );
});

router.get("/kb/atomic-tests/:id", requireAuth, (req, res) => {
  const t = ATOMIC_TESTS.find((x) => x.id === req.params.id);
  if (!t) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json(t);
});

router.get("/kb/cves", requireAuth, (req, res) => {
  const search = qs(req.query.search);
  const year = qs(req.query.year);
  const severity = qs(req.query.severity);
  let list = CVES.slice();
  if (year) list = list.filter((c) => c.id.includes(`-${year}-`));
  if (severity) list = list.filter((c) => c.severity === severity);
  if (search) {
    const q = search.toLowerCase();
    list = list.filter(
      (c) => c.id.toLowerCase().includes(q) || c.summary.toLowerCase().includes(q) || c.product.toLowerCase().includes(q),
    );
  }
  res.json(
    list.map((c) => ({
      id: c.id,
      summary: c.summary,
      severity: c.severity,
      cvss: c.cvss ?? null,
      published: c.published ?? null,
      product: c.product,
      vendor: c.vendor,
    })),
  );
});

router.get("/kb/cves/:cveId", requireAuth, (req, res) => {
  const cveId = String(req.params.cveId);
  const c = CVES.find((x) => x.id.toLowerCase() === cveId.toLowerCase());
  if (!c) {
    res.status(404).json({ error: "Not found" });
    return;
  }
  res.json({
    id: c.id,
    summary: c.summary,
    severity: c.severity,
    cvss: c.cvss ?? null,
    published: c.published ?? null,
    product: c.product,
    vendor: c.vendor,
    description: c.description ?? "",
    references: c.references ?? [],
    cwe: c.cwe ?? [],
  });
});

export default router;

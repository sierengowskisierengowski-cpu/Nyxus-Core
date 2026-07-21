export interface PerformanceScore {
  overall: number;
  detectionTime: number;
  identification: number;
  evidenceQuality: number;
  containment: number;
  feedback: string;
}

export function levelFromXp(xp: number): { level: string; xpToNext: number } {
  const tiers = [
    { xp: 0, name: "Recruit" },
    { xp: 250, name: "Initiate" },
    { xp: 750, name: "Analyst I" },
    { xp: 1500, name: "Analyst II" },
    { xp: 3000, name: "Hunter" },
    { xp: 5000, name: "Senior Hunter" },
    { xp: 8000, name: "Detection Engineer" },
    { xp: 12000, name: "Threat Hunter" },
    { xp: 18000, name: "Principal" },
    { xp: 30000, name: "Operator" },
  ];
  let current = tiers[0];
  let next = tiers[1] ?? tiers[0];
  for (let i = 0; i < tiers.length; i++) {
    if (xp >= tiers[i].xp) {
      current = tiers[i];
      next = tiers[i + 1] ?? tiers[i];
    }
  }
  return { level: current.name, xpToNext: Math.max(0, next.xp - xp) };
}

export function scoreMission(opts: {
  correctTechnique: string;
  correctCategory: string;
  identifiedTechnique?: string;
  identifiedCategory?: string;
  confidence?: number;
  hintsUsed: number;
  notes: string;
  evidence: string;
  durationSeconds: number;
  timeLimitMinutes: number;
}): PerformanceScore {
  const techMatch = norm(opts.identifiedTechnique) === norm(opts.correctTechnique);
  const altMatch = norm(opts.identifiedTechnique).includes(norm(opts.correctTechnique).split(" ")[0] ?? "");
  const catMatch = norm(opts.identifiedCategory) === norm(opts.correctCategory);

  const identification = techMatch ? 100 : altMatch ? 60 : catMatch ? 35 : 0;

  const limit = opts.timeLimitMinutes * 60;
  const ratio = limit > 0 ? Math.min(1, opts.durationSeconds / limit) : 1;
  const detectionTime = Math.max(0, Math.round(100 * (1 - ratio * 0.7)));

  const evidenceLen = (opts.evidence?.length ?? 0) + (opts.notes?.length ?? 0);
  const evidenceQuality = Math.min(100, Math.round(evidenceLen / 8));

  const containment = Math.max(0, Math.round(80 - opts.hintsUsed * 15 + (opts.confidence ?? 50) * 0.2));

  const overall = Math.round(
    identification * 0.45 + detectionTime * 0.2 + evidenceQuality * 0.2 + containment * 0.15,
  );

  const feedback = techMatch
    ? "Correct identification. Strong work — refine your evidence narrative for an even cleaner debrief."
    : altMatch
    ? "Right family, wrong sub-technique. Sharpen the specificity of your IOC mapping."
    : catMatch
    ? "Category is correct but the specific technique was missed. Build a mental map of sub-techniques per category."
    : "Identification missed. Re-read the reveal and add a note linking the observed artifacts to the MITRE technique.";

  return { overall, detectionTime, identification, evidenceQuality, containment, feedback };
}

function norm(s?: string): string {
  return (s ?? "").trim().toLowerCase().replace(/\s+/g, " ");
}

export const ACHIEVEMENT_DEFS: { id: string; name: string; description: string; icon: string }[] = [
  { id: "first-blood", name: "First Blood", description: "Complete your first mission.", icon: "target" },
  { id: "perfect-detection", name: "Perfect Detection", description: "Score 100 on any mission.", icon: "crosshair" },
  { id: "no-hints", name: "Unassisted", description: "Solve a mission without using hints.", icon: "shield" },
  { id: "week-streak", name: "Seven-Day Vigil", description: "Train 7 days in a row.", icon: "flame" },
  { id: "ten-missions", name: "Battle-Hardened", description: "Complete 10 missions.", icon: "swords" },
  { id: "fifty-missions", name: "Veteran", description: "Complete 50 missions.", icon: "award" },
  { id: "all-categories", name: "Spectrum Coverage", description: "Complete a mission in every MITRE category.", icon: "grid" },
  { id: "speed-demon", name: "Speed Demon", description: "Solve a mission in under 3 minutes.", icon: "zap" },
  { id: "note-keeper", name: "Note Keeper", description: "Create 25 notes.", icon: "book" },
  { id: "knowledge-seeker", name: "Knowledge Seeker", description: "Open 20 knowledge base entries.", icon: "library" },
];

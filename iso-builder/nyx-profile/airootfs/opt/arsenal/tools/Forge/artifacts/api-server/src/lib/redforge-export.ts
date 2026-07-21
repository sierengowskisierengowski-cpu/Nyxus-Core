import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { DetectionRule, Threat } from "@workspace/db";

// ─── REDFORGE handoff export ──────────────────────────────────────────────────
//
// The original "send to REDFORGE" endpoint only flipped a boolean flag and
// claimed the threat was "deployed" — nothing actually left the app. This module
// performs a real, honest action instead: it serializes the full threat (plus
// its detection rules) into a portable JSON "deployment package" and writes it
// to a local handoff directory. A red-team operator (or a future REDFORGE
// importer) can pick these files up directly. We never claim a live mission ran.
//
// Output dir is configurable via FORGE_REDFORGE_EXPORT_DIR; default is
// `exports/redforge` at the repo root.

export function redforgeExportDir(): string {
  if (process.env.FORGE_REDFORGE_EXPORT_DIR?.trim()) {
    return path.resolve(process.env.FORGE_REDFORGE_EXPORT_DIR.trim());
  }
  // dist file lives at artifacts/api-server/dist/index.mjs → repo root is ../../..
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(here, "../../..", "exports", "redforge");
}

export interface RedforgeExportResult {
  fileName: string;
  filePath: string;
  bytes: number;
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || "threat";
}

export async function exportThreatToRedforge(
  threat: Threat,
  detectionRules: DetectionRule[],
): Promise<RedforgeExportResult> {
  const dir = redforgeExportDir();
  await fs.mkdir(dir, { recursive: true });

  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const fileName = `redforge-threat-${threat.id}-${slugify(threat.name)}-${stamp}.json`;
  const filePath = path.join(dir, fileName);

  const pkg = {
    schema: "gowskinet.forge.redforge-handoff/v1",
    exportedAt: new Date().toISOString(),
    source: "GowskiNet FORGE",
    threat: {
      id: threat.id,
      name: threat.name,
      noveltyScore: threat.noveltyScore,
      estimatedDetectionRate: threat.estimatedDetectionRate,
      platform: threat.platform,
      category: threat.category,
      description: threat.description,
      code: threat.code,
      technicalBreakdown: threat.technicalBreakdown,
      mitreIds: threat.mitreIds,
      realWorldFeasibility: threat.realWorldFeasibility,
      behavioralIndicators: threat.behavioralIndicators,
      networkIndicators: threat.networkIndicators,
      defensiveRecommendations: threat.defensiveRecommendations,
      hardeningConfig: threat.hardeningConfig,
      testPlan: threat.testPlan,
    },
    detectionRules: detectionRules.map((r) => ({
      ruleType: r.ruleType,
      name: r.name,
      content: r.content,
      mitreIds: r.mitreIds,
    })),
  };

  const json = JSON.stringify(pkg, null, 2);
  await fs.writeFile(filePath, json, "utf8");

  return { fileName, filePath, bytes: Buffer.byteLength(json) };
}

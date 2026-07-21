import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { logger } from "./logger";

// Loads the real MITRE ATT&CK dataset shipped in artifacts/api-server/data.
// The dataset is distilled straight from the official MITRE ATT&CK STIX bundle
// (see scripts/src/build-mitre-dataset.ts). No counts or techniques are
// hardcoded — everything below is read from that file.

export interface MitreTactic {
  id: string;
  name: string;
  shortname: string;
  description: string;
}

export interface MitreTechnique {
  id: string;
  name: string;
  tactics: string[];
  isSubtechnique: boolean;
  platforms: string[];
  url: string | null;
  description: string;
}

export interface MitreDataset {
  source: string;
  attackVersion: string | null;
  generatedAt: string;
  tacticCount: number;
  techniqueCount: number;
  categories: Record<string, number>;
  tactics: MitreTactic[];
  techniques: MitreTechnique[];
}

let cached: MitreDataset | null = null;

function resolveDatasetPath(): string | null {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const candidates = [
    process.env.MITRE_DATASET_PATH,
    path.join(here, "..", "data", "mitre-attack-enterprise.json"),
    path.join(here, "data", "mitre-attack-enterprise.json"),
    path.resolve(process.cwd(), "artifacts/api-server/data/mitre-attack-enterprise.json"),
    path.resolve(process.cwd(), "data/mitre-attack-enterprise.json"),
  ].filter((c): c is string => Boolean(c));

  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

export function loadMitreDataset(): MitreDataset | null {
  if (cached) return cached;
  const datasetPath = resolveDatasetPath();
  if (!datasetPath) {
    logger.warn(
      "MITRE ATT&CK dataset not found. Run `pnpm --filter @workspace/scripts run build-mitre` to generate it.",
    );
    return null;
  }
  try {
    cached = JSON.parse(fs.readFileSync(datasetPath, "utf8")) as MitreDataset;
    logger.info(
      { techniques: cached.techniqueCount, tactics: cached.tacticCount },
      "Loaded MITRE ATT&CK dataset",
    );
    return cached;
  } catch (err) {
    logger.error({ err, datasetPath }, "Failed to parse MITRE ATT&CK dataset");
    return null;
  }
}

export interface KnowledgeBaseStatus {
  totalTechniques: number;
  loaded: boolean;
  categories: Record<string, number>;
  lastUpdated: string | null;
}

export function getKnowledgeBaseStatus(): KnowledgeBaseStatus {
  const ds = loadMitreDataset();
  if (!ds) {
    return { totalTechniques: 0, loaded: false, categories: {}, lastUpdated: null };
  }
  return {
    totalTechniques: ds.techniqueCount,
    loaded: true,
    categories: ds.categories,
    lastUpdated: ds.generatedAt,
  };
}

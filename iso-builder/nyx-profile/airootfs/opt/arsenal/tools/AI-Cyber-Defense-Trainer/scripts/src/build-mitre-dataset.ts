#!/usr/bin/env tsx
/**
 * Distils the official MITRE ATT&CK Enterprise STIX 2.x bundle into a compact
 * dataset the API server ships and serves. This is REAL MITRE data — technique
 * IDs, names, tactics and platforms are taken verbatim from the STIX source;
 * nothing is invented.
 *
 * Usage:
 *   MITRE_STIX_PATH=/path/to/enterprise-attack.json pnpm --filter @workspace/scripts run build-mitre
 *
 * The STIX bundle is large and NOT committed; the distilled output IS committed
 * so the app works out-of-the-box without the multi-MB source file.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const DEFAULT_STIX =
  process.env.MITRE_STIX_PATH ??
  "/home/cosmic/Projects/jeTT/knowledge_base/mitre_attack/enterprise-attack.json";

const here = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(
  here,
  "../../artifacts/api-server/data/mitre-attack-enterprise.json",
);

interface StixObject {
  type: string;
  name?: string;
  description?: string;
  revoked?: boolean;
  x_mitre_deprecated?: boolean;
  x_mitre_shortname?: string;
  x_mitre_is_subtechnique?: boolean;
  x_mitre_platforms?: string[];
  x_mitre_version?: string;
  tactic_refs?: string[];
  id?: string;
  external_references?: Array<{
    source_name?: string;
    external_id?: string;
    url?: string;
  }>;
  kill_chain_phases?: Array<{ kill_chain_name?: string; phase_name?: string }>;
}

function attackId(obj: StixObject): string | null {
  const ref = obj.external_references?.find(
    (r) => r.source_name === "mitre-attack" && r.external_id,
  );
  return ref?.external_id ?? null;
}

function attackUrl(obj: StixObject): string | null {
  const ref = obj.external_references?.find(
    (r) => r.source_name === "mitre-attack" && r.url,
  );
  return ref?.url ?? null;
}

function shortDescription(desc: string | undefined): string {
  if (!desc) return "";
  const firstPara = desc.split("\n")[0].trim();
  const oneLine = firstPara.replace(/\(Citation:[^)]*\)/g, "").replace(/\s+/g, " ").trim();
  return oneLine.length > 320 ? `${oneLine.slice(0, 317)}…` : oneLine;
}

function main(): void {
  if (!fs.existsSync(DEFAULT_STIX)) {
    console.error(`STIX bundle not found: ${DEFAULT_STIX}`);
    console.error("Set MITRE_STIX_PATH to a MITRE ATT&CK Enterprise STIX JSON file.");
    process.exit(1);
  }

  console.log(`Reading STIX bundle: ${DEFAULT_STIX}`);
  const bundle = JSON.parse(fs.readFileSync(DEFAULT_STIX, "utf8")) as {
    objects: StixObject[];
  };
  const objects = bundle.objects ?? [];

  // --- tactics (keep matrix order from x-mitre-matrix.tactic_refs) ----------
  const matrix = objects.find((o) => o.type === "x-mitre-matrix");
  const tacticById = new Map<string, StixObject>();
  for (const o of objects) {
    if (o.type === "x-mitre-tactic" && o.id) tacticById.set(o.id, o);
  }
  const orderedTacticRefs = matrix?.tactic_refs ?? [...tacticById.keys()];

  const tactics = orderedTacticRefs
    .map((ref) => tacticById.get(ref))
    .filter((t): t is StixObject => Boolean(t))
    .map((t) => ({
      id: attackId(t) ?? "",
      name: t.name ?? "",
      shortname: t.x_mitre_shortname ?? "",
      description: shortDescription(t.description),
    }));

  const shortnameToName = new Map(tactics.map((t) => [t.shortname, t.name]));

  // --- techniques (attack-pattern) ------------------------------------------
  const techniques = objects
    .filter(
      (o) =>
        o.type === "attack-pattern" &&
        !o.revoked &&
        !o.x_mitre_deprecated &&
        attackId(o),
    )
    .map((o) => {
      const phases = (o.kill_chain_phases ?? [])
        .filter((p) => p.kill_chain_name === "mitre-attack" && p.phase_name)
        .map((p) => p.phase_name as string);
      const id = attackId(o) as string;
      return {
        id,
        name: o.name ?? "",
        tactics: phases,
        isSubtechnique: Boolean(o.x_mitre_is_subtechnique) || id.includes("."),
        platforms: o.x_mitre_platforms ?? [],
        url: attackUrl(o),
        description: shortDescription(o.description),
      };
    })
    .sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));

  // --- per-tactic technique counts (real, computed) -------------------------
  const categories: Record<string, number> = {};
  for (const t of tactics) categories[t.name] = 0;
  for (const tech of techniques) {
    for (const shortname of tech.tactics) {
      const name = shortnameToName.get(shortname);
      if (name) categories[name] = (categories[name] ?? 0) + 1;
    }
  }

  const collection = objects.find((o) => o.type === "x-mitre-collection");
  const version = collection?.x_mitre_version ?? null;

  const output = {
    source: "MITRE ATT&CK for Enterprise",
    format: "distilled from MITRE ATT&CK STIX 2.x",
    attackVersion: version,
    generatedAt: new Date().toISOString(),
    tacticCount: tactics.length,
    techniqueCount: techniques.length,
    categories,
    tactics,
    techniques,
  };

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(output, null, 2));
  console.log(
    `Wrote ${OUT}\n  tactics: ${tactics.length}, techniques: ${techniques.length}, attackVersion: ${version}`,
  );
}

main();

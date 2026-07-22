import { Router } from "express";
import { db } from "@workspace/db";
import { hashesTable, resultsTable } from "@workspace/db";
import { eq, desc, and, like, sql, count } from "drizzle-orm";
import crypto from "crypto";

const router = Router();

const HASH_PATTERNS: Record<string, { pattern: RegExp; algorithm: string; difficulty: string; salted: boolean }> = {
  md5: { pattern: /^[a-f0-9]{32}$/i, algorithm: "MD5", difficulty: "easy", salted: false },
  sha1: { pattern: /^[a-f0-9]{40}$/i, algorithm: "SHA-1", difficulty: "easy", salted: false },
  sha256: { pattern: /^[a-f0-9]{64}$/i, algorithm: "SHA-256", difficulty: "medium", salted: false },
  sha512: { pattern: /^[a-f0-9]{128}$/i, algorithm: "SHA-512", difficulty: "hard", salted: false },
  ntlm: { pattern: /^[a-f0-9]{32}$/i, algorithm: "NTLM", difficulty: "easy", salted: false },
  bcrypt: { pattern: /^\$2[ayb]\$.{56}$/, algorithm: "bcrypt", difficulty: "extreme", salted: true },
  sha256crypt: { pattern: /^\$5\$/, algorithm: "SHA-256-crypt", difficulty: "hard", salted: true },
  sha512crypt: { pattern: /^\$6\$/, algorithm: "SHA-512-crypt", difficulty: "extreme", salted: true },
  argon2: { pattern: /^\$argon2/, algorithm: "Argon2", difficulty: "extreme", salted: true },
  scrypt: { pattern: /^\$scrypt\$/, algorithm: "scrypt", difficulty: "extreme", salted: true },
};

function identifyHashType(hash: string): { hashType: string; algorithm: string; difficulty: string; salted: boolean; confidence: number; weaknesses: string[] } {
  const trimmed = hash.trim();
  const weaknesses: string[] = [];

  if (HASH_PATTERNS.bcrypt.pattern.test(trimmed)) {
    return { hashType: "bcrypt", algorithm: "bcrypt", difficulty: "extreme", salted: true, confidence: 0.99, weaknesses: [] };
  }
  if (HASH_PATTERNS.sha512crypt.pattern.test(trimmed)) {
    return { hashType: "sha512crypt", algorithm: "SHA-512-crypt", difficulty: "extreme", salted: true, confidence: 0.99, weaknesses: [] };
  }
  if (HASH_PATTERNS.sha256crypt.pattern.test(trimmed)) {
    return { hashType: "sha256crypt", algorithm: "SHA-256-crypt", difficulty: "hard", salted: true, confidence: 0.99, weaknesses: [] };
  }
  if (HASH_PATTERNS.argon2.pattern.test(trimmed)) {
    return { hashType: "argon2", algorithm: "Argon2", difficulty: "extreme", salted: true, confidence: 0.99, weaknesses: [] };
  }
  if (trimmed.length === 128 && /^[a-f0-9]+$/i.test(trimmed)) {
    return { hashType: "sha512", algorithm: "SHA-512", difficulty: "hard", salted: false, confidence: 0.9, weaknesses: ["Unsalted hash vulnerable to rainbow table attacks"] };
  }
  if (trimmed.length === 64 && /^[a-f0-9]+$/i.test(trimmed)) {
    return { hashType: "sha256", algorithm: "SHA-256", difficulty: "medium", salted: false, confidence: 0.85, weaknesses: ["Unsalted — vulnerable to dictionary attacks", "No key stretching"] };
  }
  if (trimmed.length === 40 && /^[a-f0-9]+$/i.test(trimmed)) {
    weaknesses.push("SHA-1 is cryptographically broken", "Unsalted hash", "Vulnerable to rainbow tables");
    return { hashType: "sha1", algorithm: "SHA-1", difficulty: "easy", salted: false, confidence: 0.85, weaknesses };
  }
  if (trimmed.length === 32 && /^[a-f0-9]+$/i.test(trimmed)) {
    weaknesses.push("MD5 is cryptographically broken", "Unsalted hash", "Highly vulnerable to rainbow tables", "GPU crack at billions/second");
    return { hashType: "md5", algorithm: "MD5", difficulty: "easy", salted: false, confidence: 0.8, weaknesses };
  }

  return { hashType: "unknown", algorithm: "Unknown", difficulty: "unknown", salted: false, confidence: 0.1, weaknesses: ["Unable to identify hash type"] };
}

function getRecommendedAttack(hashType: string): string {
  const map: Record<string, string> = {
    md5: "Rainbow table attack — instant for common passwords",
    sha1: "Dictionary attack with Best64 rules, then rainbow tables",
    sha256: "Dictionary + Hybrid attack with GowskiNet wordlist",
    sha512: "AI Targeted attack or GowskiNet Intelligence",
    bcrypt: "Dictionary attack only — brute force infeasible",
    sha512crypt: "Dictionary attack with targeted wordlist",
    sha256crypt: "Dictionary attack with GowskiNet wordlist",
    argon2: "Dictionary attack only — GPU acceleration has limited effect",
    scrypt: "Dictionary attack only",
  };
  return map[hashType] || "Dictionary attack with GowskiNet Intelligence";
}

router.get("/hashes", async (req, res) => {
  try {
    const statusFilter = req.query.status as string;
    const hashTypeFilter = req.query.hashType as string;
    const page = parseInt(req.query.page as string) || 1;
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = (page - 1) * limit;

    const conditions = [];
    if (statusFilter && statusFilter !== "all") {
      if (statusFilter === "cracked") conditions.push(eq(hashesTable.status, "cracked"));
      else if (statusFilter === "uncracked") conditions.push(sql`${hashesTable.status} != 'cracked'`);
    }
    if (hashTypeFilter) {
      conditions.push(eq(hashesTable.hashType, hashTypeFilter));
    }

    const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

    const [hashes, totalResult] = await Promise.all([
      db.select().from(hashesTable).where(whereClause).orderBy(desc(hashesTable.submittedAt)).limit(limit).offset(offset),
      db.select({ count: count() }).from(hashesTable).where(whereClause),
    ]);

    res.json({ hashes, total: totalResult[0]?.count || 0, page, limit });
  } catch (err) {
    req.log.error(err, "Failed to list hashes");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/hashes", async (req, res) => {
  try {
    const { hashes, hashType, label, source } = req.body;
    if (!hashes || !Array.isArray(hashes) || hashes.length === 0) {
      return res.status(400).json({ error: "hashes array is required" });
    }

    const inserted = await db.insert(hashesTable).values(
      hashes.map((h: string) => {
        const id_info = identifyHashType(h);
        return {
          value: h.trim(),
          hashType: hashType || id_info.hashType,
          status: "pending" as const,
          label: label || null,
          source: source || null,
          difficulty: id_info.difficulty,
          salted: id_info.salted,
        };
      })
    ).returning();

    res.status(201).json(inserted);
  } catch (err) {
    req.log.error(err, "Failed to submit hashes");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/hashes/identify", async (req, res) => {
  try {
    const { hash } = req.body;
    if (!hash) return res.status(400).json({ error: "hash is required" });

    const info = identifyHashType(hash);
    res.json({
      hashType: info.hashType,
      algorithm: info.algorithm,
      salted: info.salted,
      difficulty: info.difficulty === "unknown" ? "medium" : info.difficulty,
      recommendedAttack: getRecommendedAttack(info.hashType),
      confidence: info.confidence,
      weaknesses: info.weaknesses,
    });
  } catch (err) {
    req.log.error(err, "Failed to identify hash");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/hashes/generate", async (req, res) => {
  try {
    const { plaintext, algorithm } = req.body;
    if (!plaintext || !algorithm) return res.status(400).json({ error: "plaintext and algorithm are required" });

    let hash = "";
    const algoLower = algorithm.toLowerCase().replace(/-/g, "");
    if (algoLower === "md5") {
      hash = crypto.createHash("md5").update(plaintext).digest("hex");
    } else if (algoLower === "sha1") {
      hash = crypto.createHash("sha1").update(plaintext).digest("hex");
    } else if (algoLower === "sha256") {
      hash = crypto.createHash("sha256").update(plaintext).digest("hex");
    } else if (algoLower === "sha512") {
      hash = crypto.createHash("sha512").update(plaintext).digest("hex");
    } else {
      hash = crypto.createHash("sha256").update(plaintext).digest("hex");
    }

    res.json({ plaintext, algorithm, hash });
  } catch (err) {
    req.log.error(err, "Failed to generate hash");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/hashes/stats", async (req, res) => {
  try {
    const [allHashes, crackedHashes, byType, weakHashes] = await Promise.all([
      db.select({ count: count() }).from(hashesTable),
      db.select({ count: count() }).from(hashesTable).where(eq(hashesTable.status, "cracked")),
      db.select({ hashType: hashesTable.hashType, count: count() }).from(hashesTable).groupBy(hashesTable.hashType),
      db.select().from(hashesTable).where(and(eq(hashesTable.salted, false), sql`${hashesTable.hashType} IN ('md5', 'sha1')`)).limit(10),
    ]);

    const total = allHashes[0]?.count || 0;
    const cracked = crackedHashes[0]?.count || 0;
    const crackRate = total > 0 ? (cracked / total) * 100 : 0;

    const typeStats = byType.map(t => ({
      hashType: t.hashType,
      count: t.count,
      cracked: 0,
      crackRate: 0,
      avgCrackTimeSeconds: null,
    }));

    res.json({
      totalSubmitted: total,
      totalCracked: cracked,
      crackRate,
      byType: typeStats,
      avgCrackTime: 0,
      weakHashes,
    });
  } catch (err) {
    req.log.error(err, "Failed to get hash stats");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/hashes/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const hash = await db.select().from(hashesTable).where(eq(hashesTable.id, id)).limit(1);
    if (!hash.length) return res.status(404).json({ error: "Hash not found" });
    res.json(hash[0]);
  } catch (err) {
    req.log.error(err, "Failed to get hash");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/hashes/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    await db.delete(hashesTable).where(eq(hashesTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error(err, "Failed to delete hash");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

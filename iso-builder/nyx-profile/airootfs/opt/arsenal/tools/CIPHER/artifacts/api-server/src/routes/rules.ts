import { Router } from "express";
import { db } from "@workspace/db";
import { rulesTable } from "@workspace/db";
import { eq, desc } from "drizzle-orm";

const router = Router();

function countRules(rulesText: string): number {
  return rulesText.split("\n").filter(l => l.trim() && !l.trim().startsWith("#")).length;
}

function formatRule(r: typeof rulesTable.$inferSelect) {
  return {
    ...r,
    createdAt: r.createdAt.toISOString(),
  };
}

router.get("/rules", async (req, res) => {
  try {
    const rules = await db.select().from(rulesTable).orderBy(desc(rulesTable.createdAt));
    res.json(rules.map(formatRule));
  } catch (err) {
    req.log.error(err, "Failed to list rules");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/rules", async (req, res) => {
  try {
    const { name, description, rules, format } = req.body;
    if (!name || !rules || !format) return res.status(400).json({ error: "name, rules, and format are required" });

    const [ruleset] = await db.insert(rulesTable).values({
      name,
      description: description || null,
      rules,
      ruleCount: countRules(rules),
      format,
      isBuiltin: false,
      cracksProduced: 0,
    }).returning();

    res.status(201).json(formatRule(ruleset));
  } catch (err) {
    req.log.error(err, "Failed to create rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/rules/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const [rule] = await db.select().from(rulesTable).where(eq(rulesTable.id, id)).limit(1);
    if (!rule) return res.status(404).json({ error: "Rule not found" });
    res.json(formatRule(rule));
  } catch (err) {
    req.log.error(err, "Failed to get rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.patch("/rules/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const { name, description, rules } = req.body;
    const updates: Record<string, unknown> = {};
    if (name !== undefined) updates.name = name;
    if (description !== undefined) updates.description = description;
    if (rules !== undefined) { updates.rules = rules; updates.ruleCount = countRules(rules); }

    const [updated] = await db.update(rulesTable).set(updates).where(eq(rulesTable.id, id)).returning();
    if (!updated) return res.status(404).json({ error: "Rule not found" });
    res.json(formatRule(updated));
  } catch (err) {
    req.log.error(err, "Failed to update rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.delete("/rules/:id", async (req, res) => {
  try {
    const id = parseInt(req.params.id);
    await db.delete(rulesTable).where(eq(rulesTable.id, id));
    res.status(204).send();
  } catch (err) {
    req.log.error(err, "Failed to delete rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/rules/test", async (req, res) => {
  try {
    const { rules, sampleWords } = req.body;
    if (!rules || !sampleWords) return res.status(400).json({ error: "rules and sampleWords are required" });

    const ruleLines = (rules as string).split("\n").filter((l: string) => l.trim() && !l.trim().startsWith("#"));
    const output: string[] = [];

    sampleWords.forEach((word: string) => {
      ruleLines.forEach((rule: string) => {
        const r = rule.trim();
        if (r === ":") { output.push(word); return; }
        if (r === "l") { output.push(word.toLowerCase()); return; }
        if (r === "u") { output.push(word.toUpperCase()); return; }
        if (r === "c") { output.push(word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()); return; }
        if (r === "r") { output.push(word.split("").reverse().join("")); return; }
        if (r.startsWith("$")) { output.push(word + r.slice(1)); return; }
        if (r.startsWith("^")) { output.push(r.slice(1) + word); return; }
        if (r.startsWith("sa")) { output.push(word.replace(/a/g, "@")); return; }
        if (r.startsWith("se")) { output.push(word.replace(/e/g, "3")); return; }
        if (r.startsWith("si")) { output.push(word.replace(/i/g, "1")); return; }
        if (r.startsWith("so")) { output.push(word.replace(/o/g, "0")); return; }
        if (r.startsWith("ss")) { output.push(word.replace(/s/g, "$")); return; }
        output.push(word + r.replace(/[^a-zA-Z0-9]/g, ""));
      });
    });

    const unique = [...new Set(output)];
    res.json({ output: unique.slice(0, 1000), inputCount: sampleWords.length, outputCount: unique.length });
  } catch (err) {
    req.log.error(err, "Failed to test rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/rules/generate", async (req, res) => {
  try {
    const { description, format = "hashcat" } = req.body;
    if (!description) return res.status(400).json({ error: "description is required" });

    const desc = (description as string).toLowerCase();
    const rules: string[] = [];

    if (desc.includes("leet") || desc.includes("substitut")) {
      rules.push("# Leet speak substitutions", "sa@", "se3", "si1", "so0", "ss$", "sl!");
    }
    if (desc.includes("append") || desc.includes("suffix") || desc.includes("number")) {
      rules.push("# Number appends", "$1", "$2", "$3", "$123", "$1234", "$12345", "$69", "$!1", "$@1");
    }
    if (desc.includes("capital") || desc.includes("upper")) {
      rules.push("# Capitalization", "c", "u", "C");
    }
    if (desc.includes("reverse")) {
      rules.push("# Reverse", "r");
    }
    if (desc.includes("year")) {
      rules.push("# Year appends", "$2023", "$2024", "$2025", "$1990", "$1985", "$1999");
    }
    if (rules.length === 0) {
      rules.push("# General mutations", ":", "l", "u", "c", "$1", "$!", "sa@", "se3", "$123");
    }

    const rulesText = rules.join("\n");
    res.json({ rules: rulesText, explanation: `Generated ${countRules(rulesText)} rules for: ${description}. These rules cover common mutation patterns relevant to the described use case.` });
  } catch (err) {
    req.log.error(err, "Failed to generate rule");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

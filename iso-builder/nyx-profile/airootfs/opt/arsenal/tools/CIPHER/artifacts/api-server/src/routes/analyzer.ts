import { Router } from "express";
import { db } from "@workspace/db";
import { resultsTable } from "@workspace/db";
import { eq } from "drizzle-orm";
import crypto from "crypto";

const router = Router();

const COMMON_PASSWORDS = new Set(["password", "123456", "12345678", "qwerty", "abc123", "monkey", "1234567", "letmein", "trustno1", "dragon", "baseball", "iloveyou", "master", "sunshine", "ashley", "bailey", "passw0rd", "shadow", "123123", "654321", "superman", "qazwsx", "michael", "football"]);
const DICT_WORDS = new Set(["password", "admin", "login", "user", "root", "hello", "welcome", "test", "master", "dragon", "baseball", "monkey", "football", "soccer", "batman", "superman", "shadow", "sunshine", "princess", "dragon", "letmein", "trustno1"]);

function calculateEntropy(password: string): number {
  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasNumbers = /[0-9]/.test(password);
  const hasSymbols = /[^a-zA-Z0-9]/.test(password);

  let charsetSize = 0;
  if (hasLower) charsetSize += 26;
  if (hasUpper) charsetSize += 26;
  if (hasNumbers) charsetSize += 10;
  if (hasSymbols) charsetSize += 32;

  return Math.log2(Math.pow(charsetSize || 1, password.length));
}

function analyzePassword(password: string) {
  const entropy = calculateEntropy(password);
  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasNumbers = /[0-9]/.test(password);
  const hasSymbols = /[^a-zA-Z0-9]/.test(password);
  const charsetSize = (hasLower ? 26 : 0) + (hasUpper ? 26 : 0) + (hasNumbers ? 10 : 0) + (hasSymbols ? 32 : 0);

  const isCommon = COMMON_PASSWORDS.has(password.toLowerCase());
  const containsDict = [...DICT_WORDS].some(w => password.toLowerCase().includes(w));

  const weaknesses: string[] = [];
  const suggestions: string[] = [];

  if (password.length < 8) weaknesses.push("Too short — minimum 8 characters recommended");
  if (password.length < 12) weaknesses.push("Length below 12 characters reduces security significantly");
  if (!hasUpper) { weaknesses.push("No uppercase letters"); suggestions.push("Add uppercase letters"); }
  if (!hasNumbers) { weaknesses.push("No numbers"); suggestions.push("Add numbers"); }
  if (!hasSymbols) { weaknesses.push("No symbols"); suggestions.push("Add symbols like !@#$%"); }
  if (isCommon) weaknesses.push("This is a commonly used password — in every wordlist");
  if (containsDict) weaknesses.push("Contains a dictionary word as base");
  if (/(.)\1{2,}/.test(password)) weaknesses.push("Contains repeated characters");
  if (/^[a-zA-Z]+$/.test(password)) weaknesses.push("Letters only — no mixed character types");

  if (suggestions.length === 0) suggestions.push("Consider using a passphrase", "Use a password manager for unique passwords per site");

  let strengthScore = 0;
  if (password.length >= 8) strengthScore += 20;
  if (password.length >= 12) strengthScore += 15;
  if (password.length >= 16) strengthScore += 10;
  if (hasLower) strengthScore += 10;
  if (hasUpper) strengthScore += 10;
  if (hasNumbers) strengthScore += 10;
  if (hasSymbols) strengthScore += 15;
  if (!isCommon) strengthScore += 5;
  if (!containsDict) strengthScore += 5;
  if (entropy > 50) strengthScore += 5;

  strengthScore = Math.min(100, strengthScore);

  let strengthLabel: string;
  if (strengthScore < 20) strengthLabel = "very_weak";
  else if (strengthScore < 40) strengthLabel = "weak";
  else if (strengthScore < 60) strengthLabel = "fair";
  else if (strengthScore < 80) strengthLabel = "strong";
  else strengthLabel = "very_strong";

  let patternIdentified: string | null = null;
  if (/^[a-z]+\d+$/.test(password)) patternIdentified = "word+numbers";
  else if (/^[a-z]+\d+[!@#$%]+$/.test(password)) patternIdentified = "word+numbers+symbol";
  else if (/^[A-Z][a-z]+\d+$/.test(password)) patternIdentified = "Capitalized+word+numbers";
  else if (/^\d+$/.test(password)) patternIdentified = "numbers_only";
  else if (/^[a-z]+$/.test(password)) patternIdentified = "lowercase_word_only";

  const crackTimeEstimates = [
    { attackType: "Online (1000 attempts/hour)", hardware: "Web service rate-limited", estimatedTime: entropy < 30 ? "Seconds" : entropy < 50 ? "Minutes" : "Years" },
    { attackType: "MD5 GPU Crack", hardware: "RTX 3060", estimatedTime: entropy < 30 ? "Instant" : entropy < 45 ? "Seconds" : entropy < 60 ? "Hours" : "Centuries" },
    { attackType: "bcrypt GPU Crack", hardware: "RTX 3060", estimatedTime: entropy < 35 ? "Minutes" : entropy < 50 ? "Days" : "Millennia" },
    { attackType: "Dictionary Attack", hardware: "Any", estimatedTime: isCommon ? "Instant" : containsDict ? "Seconds" : "N/A — not in dictionary" },
  ];

  return {
    password: "*".repeat(Math.min(password.length, 4)) + password.slice(-2),
    entropyBits: Math.round(entropy * 10) / 10,
    strengthScore,
    strengthLabel,
    charsetAnalysis: { hasLowercase: hasLower, hasUppercase: hasUpper, hasNumbers, hasSymbols, charsetSize },
    patternDetected: patternIdentified,
    dictionaryWordDetected: containsDict,
    commonPassword: isCommon,
    weaknesses,
    suggestions,
    crackTimeEstimates,
    previouslyInDatabase: false,
  };
}

router.post("/analyzer/analyze", async (req, res) => {
  try {
    const { password } = req.body;
    if (!password) return res.status(400).json({ error: "password is required" });

    const hash = crypto.createHash("sha256").update(password).digest("hex");
    const [existing] = await db.select().from(resultsTable).where(eq(resultsTable.hash, hash)).limit(1);

    const result = analyzePassword(password);
    result.previouslyInDatabase = !!existing;

    res.json(result);
  } catch (err) {
    req.log.error(err, "Failed to analyze password");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/analyzer/bulk", async (req, res) => {
  try {
    const { passwords } = req.body;
    if (!passwords || !Array.isArray(passwords)) return res.status(400).json({ error: "passwords array is required" });

    const results = passwords.slice(0, 1000).map((p: string) => analyzePassword(p));
    res.json(results);
  } catch (err) {
    req.log.error(err, "Failed to bulk analyze");
    res.status(500).json({ error: "Internal server error" });
  }
});

export default router;

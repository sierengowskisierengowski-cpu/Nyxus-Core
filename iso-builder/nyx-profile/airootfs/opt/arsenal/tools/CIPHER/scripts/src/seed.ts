import { db } from "@workspace/db";
import { wordlistsTable, rulesTable, notesTable, hashesTable } from "@workspace/db";

/**
 * Honest seed data. Everything here is real and self-consistent:
 * - A small, genuine common-password wordlist (word count matches the content).
 * - Real hashcat rule sets with accurate rule counts.
 * - Sample hashes whose plaintexts are actually in the seeded wordlist, so a
 *   real dictionary attack against them genuinely cracks them.
 * No fabricated statistics, no fake honeypot credentials, no invented metrics.
 */

const COMMON_PASSWORDS = [
  "password",
  "123456",
  "123456789",
  "12345678",
  "qwerty",
  "abc123",
  "password1",
  "111111",
  "letmein",
  "welcome",
  "admin",
  "monkey",
  "dragon",
  "sunshine",
  "iloveyou",
  "trustno1",
  "master",
  "hello",
  "shadow",
  "superman",
  "qazwsx",
  "football",
  "baseball",
  "starwars",
  "whatever",
  "passw0rd",
  "Password1",
  "P@ssw0rd",
  "changeme",
  "root",
  "toor",
  "guest",
  "test",
  "login",
  "1q2w3e4r",
];

const COMMON_MUTATIONS_RULE = [
  "# Common real hashcat mutation rules",
  ":",
  "l",
  "u",
  "c",
  "r",
  "$1",
  "$2",
  "$3",
  "$123",
  "$!",
  "$@",
  "sa@",
  "se3",
  "si1",
  "so0",
  "ss$",
  "$2024",
  "$2025",
].join("\n");

const LEET_RULE = ["# Leet-speak substitutions", "sa@", "se3", "si1", "so0", "ss$", "sl1", "st7", "sg9"].join("\n");

function ruleCount(text: string): number {
  return text.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#")).length;
}

async function seed() {
  console.log("Seeding built-in wordlist (real common passwords)...");
  const wlContent = COMMON_PASSWORDS.join("\n");
  await db
    .insert(wordlistsTable)
    .values([
      {
        name: "common-passwords.txt",
        description:
          "A small built-in list of widely-known weak passwords for auditing your own test hashes. Not a breach dump — just common defaults.",
        wordCount: COMMON_PASSWORDS.length,
        sizeBytes: Buffer.byteLength(wlContent + "\n", "utf8"),
        source: "builtin",
        isBuiltin: true,
        tags: JSON.stringify(["builtin", "common"]),
        words: wlContent,
      },
    ] as (typeof wordlistsTable.$inferInsert)[])
    .onConflictDoNothing();

  console.log("Seeding built-in rule sets (real hashcat rules)...");
  await db
    .insert(rulesTable)
    .values([
      {
        name: "common-mutations.rule",
        description: "Common real hashcat mutation rules (case, appends, leet).",
        rules: COMMON_MUTATIONS_RULE,
        ruleCount: ruleCount(COMMON_MUTATIONS_RULE),
        format: "hashcat",
        isBuiltin: true,
        cracksProduced: 0,
      },
      {
        name: "leet.rule",
        description: "Leet-speak character substitutions.",
        rules: LEET_RULE,
        ruleCount: ruleCount(LEET_RULE),
        format: "hashcat",
        isBuiltin: true,
        cracksProduced: 0,
      },
    ] as (typeof rulesTable.$inferInsert)[])
    .onConflictDoNothing();

  console.log("Seeding sample hashes (plaintexts are in the built-in wordlist)...");
  await db
    .insert(hashesTable)
    .values([
      // md5("password")
      { value: "5f4dcc3b5aa765d61d8327deb882cf99", hashType: "md5", status: "pending", label: "Sample MD5 (crackable with built-in wordlist)", difficulty: "easy", salted: false },
      // md5("123456")
      { value: "e10adc3949ba59abbe56e057f20f883e", hashType: "md5", status: "pending", label: "Sample MD5", difficulty: "easy", salted: false },
      // sha1("password")
      { value: "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8", hashType: "sha1", status: "pending", label: "Sample SHA-1", difficulty: "easy", salted: false },
      // sha256("hello")
      { value: "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", hashType: "sha256", status: "pending", label: "Sample SHA-256", difficulty: "medium", salted: false },
    ] as (typeof hashesTable.$inferInsert)[])
    .onConflictDoNothing();

  console.log("Seeding a starter research note...");
  await db
    .insert(notesTable)
    .values([
      {
        title: "Getting started with CIPHER",
        content:
          "## CIPHER — honest local password-auditing lab\n\nThis tool runs the real `hashcat` and `john` binaries installed on this machine against hash files you load yourself.\n\n### Workflow\n1. Submit or upload your own test hashes (Hash Submission).\n2. Upload a wordlist, or use the built-in `common-passwords.txt`.\n3. Launch a job in the Attack Engine (pick engine, hash type, wordlist).\n4. Watch real progress in Live Monitor; cracked results appear under Results.\n\nOnly use this against hashes you own or are authorized to test.",
        noteType: "quick_capture",
        notebook: "general",
        tags: JSON.stringify(["getting-started"]),
        isPinned: true,
        isFavorite: false,
        isArchived: false,
      },
    ] as (typeof notesTable.$inferInsert)[])
    .onConflictDoNothing();

  console.log("Seeding complete!");
  process.exit(0);
}

seed().catch((e) => {
  console.error(e);
  process.exit(1);
});

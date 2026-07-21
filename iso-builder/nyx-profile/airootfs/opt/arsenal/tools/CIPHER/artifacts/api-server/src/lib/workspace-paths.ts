import fs from "node:fs";
import path from "node:path";
import os from "node:os";

/**
 * CIPHER only ever reads/writes files inside a single, app-owned working
 * directory. Every hash file, wordlist, rule file, potfile and run log lives
 * here. Nothing in this app is allowed to touch arbitrary system paths — all
 * of the real tool orchestration is scoped to files the user loads through the
 * app into this directory.
 *
 * Override the location with CIPHER_WORK_DIR. Defaults to ~/.cipher/work.
 */
export const WORK_DIR: string =
  process.env["CIPHER_WORK_DIR"] && process.env["CIPHER_WORK_DIR"].trim() !== ""
    ? path.resolve(process.env["CIPHER_WORK_DIR"])
    : path.join(os.homedir(), ".cipher", "work");

export const HASHFILES_DIR = path.join(WORK_DIR, "hashfiles");
export const WORDLISTS_DIR = path.join(WORK_DIR, "wordlists");
export const RULES_DIR = path.join(WORK_DIR, "rules");
export const RUNS_DIR = path.join(WORK_DIR, "runs");
export const POTFILES_DIR = path.join(WORK_DIR, "potfiles");

export function ensureWorkspace(): void {
  for (const dir of [
    WORK_DIR,
    HASHFILES_DIR,
    WORDLISTS_DIR,
    RULES_DIR,
    RUNS_DIR,
    POTFILES_DIR,
  ]) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

/**
 * Strip a caller-supplied name down to a safe basename. Prevents path
 * traversal (e.g. "../../etc/passwd") and shell-hostile characters.
 */
export function safeFileName(name: string, fallback = "file"): string {
  const base = path.basename(String(name ?? ""));
  const cleaned = base.replace(/[^A-Za-z0-9._-]/g, "_").replace(/^\.+/, "");
  return cleaned.length > 0 ? cleaned.slice(0, 128) : fallback;
}

/**
 * Resolve `candidate` and assert it stays inside `baseDir`. Throws otherwise.
 * This is the single choke point that guarantees the tool runner can never be
 * pointed at a file outside the app-owned workspace.
 */
export function resolveWithin(baseDir: string, candidate: string): string {
  const resolvedBase = path.resolve(baseDir);
  const resolved = path.resolve(resolvedBase, candidate);
  const rel = path.relative(resolvedBase, resolved);
  if (rel === "" || rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`Path "${candidate}" escapes the allowed directory`);
  }
  return resolved;
}

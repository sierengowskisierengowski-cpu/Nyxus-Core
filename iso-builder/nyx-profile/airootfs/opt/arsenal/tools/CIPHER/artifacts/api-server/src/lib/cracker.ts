import { spawn, type ChildProcessByStdio } from "node:child_process";
import type { Readable } from "node:stream";
import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { db } from "@workspace/db";
import { jobsTable, hashesTable, wordlistsTable, rulesTable, resultsTable, settingsTable } from "@workspace/db";
import { eq, inArray, sql } from "drizzle-orm";
import { logger } from "./logger";
import {
  HASHFILES_DIR,
  WORDLISTS_DIR,
  RULES_DIR,
  RUNS_DIR,
  POTFILES_DIR,
  ensureWorkspace,
  resolveWithin,
} from "./workspace-paths";

/**
 * Real password-auditing orchestration. CIPHER does NOT implement any cracking
 * algorithm of its own — it shells out to the standard tools already installed
 * on this machine (hashcat / John the Ripper), runs them against hash files and
 * wordlists the owner loads through the app, parses their real progress output,
 * and stores the real results. Everything is scoped to the app-owned working
 * directory; no arbitrary system paths are ever passed to the tools.
 */

type Engine = "hashcat" | "john";
type AttackMode = "dictionary" | "bruteforce" | "hybrid";

// hashcat -m mode numbers keyed by our internal hash type identifiers.
const HASHCAT_MODES: Record<string, number> = {
  md5: 0,
  sha1: 100,
  sha256: 1400,
  sha512: 1700,
  ntlm: 1000,
  md5crypt: 500,
  bcrypt: 3200,
  sha256crypt: 7400,
  sha512crypt: 1800,
};

// John the Ripper --format names keyed by our internal hash type identifiers.
const JOHN_FORMATS: Record<string, string> = {
  md5: "raw-md5",
  sha1: "raw-sha1",
  sha256: "raw-sha256",
  sha512: "raw-sha512",
  ntlm: "nt",
  md5crypt: "md5crypt",
  bcrypt: "bcrypt",
  sha256crypt: "sha256crypt",
  sha512crypt: "sha512crypt",
};

type CrackerChild = ChildProcessByStdio<null, Readable, Readable>;

interface RunningProc {
  child: CrackerChild;
  logPath: string;
  outfilePath: string;
  attackMode: string;
  hashType: string;
  wordlistName: string | null;
  startedAtMs: number;
  stopRequested: boolean;
  johnPoll?: NodeJS.Timeout;
}

const running = new Map<number, RunningProc>();

function hashcatModeFor(hashType: string): number | null {
  const mode = HASHCAT_MODES[hashType?.toLowerCase()];
  return mode === undefined ? null : mode;
}

function johnFormatFor(hashType: string): string | null {
  return JOHN_FORMATS[hashType?.toLowerCase()] ?? null;
}

export function supportedHashTypes(engine: Engine): string[] {
  return Object.keys(engine === "john" ? JOHN_FORMATS : HASHCAT_MODES);
}

function parseJsonField(value: string | null): number[] {
  try {
    const arr = value ? JSON.parse(value) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

async function updateJob(id: number, values: Partial<typeof jobsTable.$inferInsert>): Promise<void> {
  await db.update(jobsTable).set(values).where(eq(jobsTable.id, id));
}

/**
 * Mark any jobs that were "running"/"paused" when the server last stopped as
 * interrupted — their real child processes did not survive the restart, so we
 * never report stale progress as if it were live.
 */
export async function markStaleJobsInterrupted(): Promise<void> {
  try {
    await db
      .update(jobsTable)
      .set({ status: "interrupted", completedAt: new Date() })
      .where(sql`${jobsTable.status} IN ('running', 'paused', 'queued')`);
  } catch (err) {
    logger.error({ err }, "Failed to reset stale jobs on startup");
  }
}

export class CrackerError extends Error {}

/**
 * Prepare inputs and spawn the real tool for a freshly-created job row.
 * Throws CrackerError (caller returns 4xx) on validation problems.
 */
export async function startJob(jobId: number): Promise<void> {
  ensureWorkspace();

  const [job] = await db.select().from(jobsTable).where(eq(jobsTable.id, jobId)).limit(1);
  if (!job) throw new CrackerError("Job not found");

  const engine = (job.engine === "john" ? "john" : "hashcat") as Engine;
  const attackMode = (job.attackMode || "dictionary").toLowerCase() as AttackMode;
  const hashType = (job.hashType || "").toLowerCase();

  const hashIds = parseJsonField(job.hashIds);
  if (hashIds.length === 0) {
    throw new CrackerError("No target hashes selected for this job");
  }

  const hashes = await db.select().from(hashesTable).where(inArray(hashesTable.id, hashIds));
  const targetHashes = hashes.filter((h) => h.status !== "cracked");
  if (targetHashes.length === 0) {
    throw new CrackerError("All selected hashes are already cracked");
  }

  // Write the target hashes to an app-owned hash file (one per line).
  const runDir = path.join(RUNS_DIR, `job-${jobId}`);
  await fsp.mkdir(runDir, { recursive: true });
  const hashfilePath = path.join(HASHFILES_DIR, `job-${jobId}.hash`);
  await fsp.writeFile(hashfilePath, targetHashes.map((h) => h.value).join("\n") + "\n", "utf8");

  const outfilePath = path.join(runDir, "cracked.out");
  const potfilePath = path.join(POTFILES_DIR, `job-${jobId}.pot`);
  const logPath = path.join(runDir, "run.log");
  // Fresh outfile/pot per run so nothing is skipped and no results are stale.
  await fsp.rm(outfilePath, { force: true });
  await fsp.rm(potfilePath, { force: true });

  // Resolve wordlist (dictionary / hybrid).
  let wordlistPath: string | null = null;
  let wordlistName: string | null = null;
  if (attackMode === "dictionary" || attackMode === "hybrid") {
    const wlIds = parseJsonField(job.wordlistIds);
    if (wlIds.length === 0) throw new CrackerError("A wordlist is required for this attack mode");
    const [wl] = await db.select().from(wordlistsTable).where(eq(wordlistsTable.id, wlIds[0])).limit(1);
    if (!wl) throw new CrackerError("Selected wordlist not found");
    wordlistName = wl.name;
    wordlistPath = await materializeWordlist(wl);
  }

  // Resolve optional rule file (hashcat dictionary attacks).
  let rulePath: string | null = null;
  const ruleIds = parseJsonField(job.ruleIds);
  if (ruleIds.length > 0) {
    const [rule] = await db.select().from(rulesTable).where(eq(rulesTable.id, ruleIds[0])).limit(1);
    if (rule && rule.rules && rule.rules.trim() !== "") {
      rulePath = path.join(RULES_DIR, `rule-${rule.id}.rule`);
      await fsp.writeFile(rulePath, rule.rules, "utf8");
    }
  }

  const mask = job.mask && job.mask.trim() !== "" ? job.mask.trim() : "?a?a?a?a?a?a";

  const args =
    engine === "hashcat"
      ? buildHashcatArgs({ job, attackMode, hashType, hashfilePath, wordlistPath, rulePath, mask, outfilePath, potfilePath })
      : buildJohnArgs({ job, attackMode, hashType, hashfilePath, wordlistPath, potfilePath });

  // Resolve the real binary. Prefer the operator-configured path from settings
  // when it exists on disk, else fall back to the command name on PATH.
  const [settings] = await db.select().from(settingsTable).limit(1);
  const configuredPath = engine === "hashcat" ? settings?.hashcatPath : settings?.johnPath;
  const binary =
    configuredPath && fs.existsSync(configuredPath) ? configuredPath : engine === "hashcat" ? "hashcat" : "john";

  const logStream = fs.createWriteStream(logPath, { flags: "a" });
  logStream.write(`$ ${binary} ${args.join(" ")}\n\n`);

  let child: CrackerChild;
  try {
    child = spawn(binary, args, { stdio: ["ignore", "pipe", "pipe"] });
  } catch (err) {
    logStream.end();
    throw new CrackerError(`Failed to start ${binary}: ${(err as Error).message}`);
  }

  const startedAtMs = Date.now();
  const proc: RunningProc = {
    child,
    logPath,
    outfilePath,
    attackMode: job.attackMode,
    hashType,
    wordlistName,
    startedAtMs,
    stopRequested: false,
  };
  running.set(jobId, proc);

  await updateJob(jobId, {
    status: "running",
    startedAt: new Date(),
    logPath,
    errorMessage: null,
    progress: 0,
    cracksFound: 0,
  });

  if (engine === "hashcat") {
    wireHashcat(jobId, proc, logStream);
  } else {
    wireJohn(jobId, proc, logStream, potfilePath, hashfilePath, hashType);
  }

  child.on("error", (err) => {
    logStream.write(`\n[spawn error] ${err.message}\n`);
  });

  child.on("close", (code, signal) => {
    logStream.end();
    if (proc.johnPoll) clearInterval(proc.johnPoll);
    void finalizeJob(jobId, code, signal, proc, potfilePath).catch((err) =>
      logger.error({ err, jobId }, "Failed to finalize job"),
    );
  });
}

function buildHashcatArgs(opts: {
  job: typeof jobsTable.$inferSelect;
  attackMode: AttackMode;
  hashType: string;
  hashfilePath: string;
  wordlistPath: string | null;
  rulePath: string | null;
  mask: string;
  outfilePath: string;
  potfilePath: string;
}): string[] {
  const mode = hashcatModeFor(opts.hashType);
  if (mode === null) {
    throw new CrackerError(
      `hashcat does not have a configured mode for hash type "${opts.hashType}". Supported: ${supportedHashTypes("hashcat").join(", ")}`,
    );
  }

  const attackNum = opts.attackMode === "bruteforce" ? 3 : opts.attackMode === "hybrid" ? 6 : 0;
  const args = [
    "-m",
    String(mode),
    "-a",
    String(attackNum),
    "--status",
    "--status-json",
    "--status-timer=2",
    "--potfile-path",
    opts.potfilePath,
    "--outfile",
    opts.outfilePath,
    "--outfile-format",
    "3",
    "--force",
  ];

  // Device selection: 1 = CPU, 2 = GPU.
  if (opts.job.useGpu === false) args.push("-D", "1");

  args.push(opts.hashfilePath);

  if (opts.attackMode === "bruteforce") {
    args.push(opts.mask);
  } else if (opts.attackMode === "hybrid") {
    if (!opts.wordlistPath) throw new CrackerError("Hybrid attack requires a wordlist");
    args.push(opts.wordlistPath, opts.mask);
  } else {
    if (!opts.wordlistPath) throw new CrackerError("Dictionary attack requires a wordlist");
    args.push(opts.wordlistPath);
    if (opts.rulePath) args.push("-r", opts.rulePath);
  }

  return args;
}

function buildJohnArgs(opts: {
  job: typeof jobsTable.$inferSelect;
  attackMode: AttackMode;
  hashType: string;
  hashfilePath: string;
  wordlistPath: string | null;
  potfilePath: string;
}): string[] {
  const format = johnFormatFor(opts.hashType);
  if (!format) {
    throw new CrackerError(
      `John does not have a configured format for hash type "${opts.hashType}". Supported: ${supportedHashTypes("john").join(", ")}`,
    );
  }

  // Keep John's session (.rec) and log files inside the app-owned run dir so
  // nothing is written into the server's working directory.
  const sessionPath = path.join(RUNS_DIR, `job-${opts.job.id}`, "john");
  const args = [`--format=${format}`, `--pot=${opts.potfilePath}`, `--session=${sessionPath}`];

  if (opts.attackMode === "dictionary" || opts.attackMode === "hybrid") {
    if (!opts.wordlistPath) throw new CrackerError("Dictionary attack requires a wordlist");
    args.push(`--wordlist=${opts.wordlistPath}`);
    const ruleIds = parseJsonField(opts.job.ruleIds);
    if (ruleIds.length > 0) args.push("--rules");
  } else {
    // Real exhaustive search via John's incremental mode.
    args.push("--incremental");
  }

  args.push(opts.hashfilePath);
  return args;
}

/** Materialize a wordlist row into a real on-disk file inside the workspace. */
async function materializeWordlist(wl: typeof wordlistsTable.$inferSelect): Promise<string> {
  // If it already points at a file inside our managed dir, use it.
  if (wl.filePath) {
    const resolved = resolveWithin(WORDLISTS_DIR, path.basename(wl.filePath));
    if (fs.existsSync(resolved)) return resolved;
  }
  const target = path.join(WORDLISTS_DIR, `wordlist-${wl.id}.txt`);
  if (!fs.existsSync(target)) {
    const content = wl.words ?? "";
    await fsp.writeFile(target, content.endsWith("\n") ? content : content + "\n", "utf8");
  }
  // Keep the DB row pointing at the materialized file.
  await db.update(wordlistsTable).set({ filePath: target }).where(eq(wordlistsTable.id, wl.id));
  return target;
}

function wireHashcat(jobId: number, proc: RunningProc, logStream: fs.WriteStream): void {
  let stdoutBuf = "";
  proc.child.stdout.on("data", (chunk: Buffer) => {
    const text = chunk.toString("utf8");
    logStream.write(text);
    stdoutBuf += text;
    const lines = stdoutBuf.split("\n");
    stdoutBuf = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
        void applyHashcatStatus(jobId, proc, trimmed);
      }
    }
  });
  proc.child.stderr.on("data", (chunk: Buffer) => logStream.write(chunk.toString("utf8")));
}

async function applyHashcatStatus(jobId: number, proc: RunningProc, jsonLine: string): Promise<void> {
  try {
    const s = JSON.parse(jsonLine) as {
      progress?: [number, number];
      recovered_hashes?: [number, number];
      devices?: Array<{ speed?: number }>;
      estimated_stop?: number;
    };
    const values: Partial<typeof jobsTable.$inferInsert> = {};
    if (Array.isArray(s.progress) && s.progress[1] > 0) {
      values.progress = Math.min(100, (s.progress[0] / s.progress[1]) * 100);
      values.candidatesTried = Math.round(s.progress[0]);
      values.totalCandidates = Math.round(s.progress[1]);
    }
    if (Array.isArray(s.recovered_hashes)) {
      values.cracksFound = s.recovered_hashes[0];
    }
    if (Array.isArray(s.devices)) {
      const speed = s.devices.reduce((sum, d) => sum + (d.speed ?? 0), 0);
      values.speed = Math.round(speed);
      values.speedUnit = "H/s";
    }
    values.timeElapsedSeconds = Math.round((Date.now() - proc.startedAtMs) / 1000);
    if (typeof s.estimated_stop === "number" && s.estimated_stop > 0) {
      const eta = s.estimated_stop - Math.floor(Date.now() / 1000);
      values.estimatedTimeSeconds = eta > 0 ? eta : 0;
    }
    await updateJob(jobId, values);
  } catch {
    /* ignore malformed status lines */
  }
}

function wireJohn(
  jobId: number,
  proc: RunningProc,
  logStream: fs.WriteStream,
  potfilePath: string,
  hashfilePath: string,
  hashType: string,
): void {
  proc.child.stdout.on("data", (chunk: Buffer) => logStream.write(chunk.toString("utf8")));
  proc.child.stderr.on("data", (chunk: Buffer) => logStream.write(chunk.toString("utf8")));

  // John does not emit machine-readable progress; poll its real status + the
  // growing potfile for genuine recovered-count/elapsed telemetry.
  proc.johnPoll = setInterval(() => {
    void (async () => {
      const values: Partial<typeof jobsTable.$inferInsert> = {
        timeElapsedSeconds: Math.round((Date.now() - proc.startedAtMs) / 1000),
      };
      try {
        const cracked = await parsePotfile(potfilePath, hashfilePath);
        values.cracksFound = cracked.length;
      } catch {
        /* pot not ready yet */
      }
      const status = await readJohnStatus(jobId);
      if (status) {
        if (status.progress !== null) values.progress = status.progress;
        if (status.speed !== null) {
          values.speed = status.speed;
          values.speedUnit = "c/s";
        }
      }
      await updateJob(jobId, values);
    })();
  }, 2500);
}

function readJohnStatus(jobId: number): Promise<{ progress: number | null; speed: number | null } | null> {
  return new Promise((resolve) => {
    const sessionPath = path.join(RUNS_DIR, `job-${jobId}`, "john");
    const child = spawn("john", [`--status=${sessionPath}`], { stdio: ["ignore", "pipe", "pipe"] });
    let out = "";
    child.stdout.on("data", (c: Buffer) => (out += c.toString("utf8")));
    child.stderr.on("data", (c: Buffer) => (out += c.toString("utf8")));
    child.on("error", () => resolve(null));
    child.on("close", () => {
      const pct = out.match(/([\d.]+)%/);
      const speed = out.match(/(\d+(?:\.\d+)?[KMG]?)\s*(?:c\/s|p\/s|C\/s)/i);
      resolve({
        progress: pct ? Math.min(100, Number.parseFloat(pct[1])) : null,
        speed: speed ? scaleSuffix(speed[1]) : null,
      });
    });
  });
}

function scaleSuffix(v: string): number {
  const m = v.match(/^(\d+(?:\.\d+)?)([KMG]?)$/i);
  if (!m) return Number.parseFloat(v) || 0;
  const n = Number.parseFloat(m[1]);
  const mult = m[2].toUpperCase() === "K" ? 1e3 : m[2].toUpperCase() === "M" ? 1e6 : m[2].toUpperCase() === "G" ? 1e9 : 1;
  return Math.round(n * mult);
}

/**
 * Parse a hashcat/john potfile into [{hash, plaintext}]. Matches recovered
 * plaintexts back to the job's real target hashes so we can persist results.
 */
async function parsePotfile(
  potfilePath: string,
  hashfilePath: string,
): Promise<Array<{ hash: string; plaintext: string }>> {
  const [potRaw, hashRaw] = await Promise.all([
    fsp.readFile(potfilePath, "utf8").catch(() => ""),
    fsp.readFile(hashfilePath, "utf8").catch(() => ""),
  ]);
  const targets = hashRaw.split("\n").map((l) => l.trim()).filter(Boolean);
  const results: Array<{ hash: string; plaintext: string }> = [];
  for (const line of potRaw.split("\n")) {
    if (!line.trim()) continue;
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const left = line.slice(0, idx);
    const plaintext = line.slice(idx + 1);
    const match = targets.find((t) => t === left || left.endsWith(t) || left.includes(t));
    if (match) results.push({ hash: match, plaintext });
  }
  return results;
}

async function parseOutfile(outfilePath: string): Promise<Array<{ hash: string; plaintext: string }>> {
  const raw = await fsp.readFile(outfilePath, "utf8").catch(() => "");
  const results: Array<{ hash: string; plaintext: string }> = [];
  for (const line of raw.split("\n")) {
    if (!line.trim()) continue;
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    results.push({ hash: line.slice(0, idx), plaintext: line.slice(idx + 1) });
  }
  return results;
}

async function persistCracks(
  jobId: number,
  cracks: Array<{ hash: string; plaintext: string }>,
  proc: RunningProc,
): Promise<number> {
  let persisted = 0;
  for (const { hash, plaintext } of cracks) {
    // Match against real DB hash rows by exact value or embedded value.
    const rows = await db.select().from(hashesTable);
    const matches = rows.filter(
      (r) => r.status !== "cracked" && (r.value === hash || hash.endsWith(r.value) || hash.includes(r.value)),
    );
    for (const row of matches) {
      await db
        .update(hashesTable)
        .set({ status: "cracked", plaintext, crackedAt: new Date() })
        .where(eq(hashesTable.id, row.id));
      await db.insert(resultsTable).values({
        hashId: row.id,
        jobId,
        hash: row.value,
        plaintext,
        hashType: proc.hashType,
        attackMode: proc.attackMode,
        crackTimeSeconds: Math.round((Date.now() - proc.startedAtMs) / 1000),
        wordlistUsed: proc.wordlistName,
      });
      persisted++;
    }
  }
  return persisted;
}

async function finalizeJob(
  jobId: number,
  code: number | null,
  signal: NodeJS.Signals | null,
  proc: RunningProc,
  potfilePath: string,
): Promise<void> {
  running.delete(jobId);

  // Collect real cracked results from both outfile (hashcat) and potfile (both).
  const [fromOut, fromPot] = await Promise.all([
    parseOutfile(proc.outfilePath),
    parsePotfile(potfilePath, path.join(HASHFILES_DIR, `job-${jobId}.hash`)),
  ]);
  const merged = new Map<string, string>();
  for (const c of [...fromOut, ...fromPot]) merged.set(c.hash, c.plaintext);
  const persisted = await persistCracks(
    jobId,
    [...merged.entries()].map(([hash, plaintext]) => ({ hash, plaintext })),
    proc,
  );

  const timeElapsedSeconds = Math.round((Date.now() - proc.startedAtMs) / 1000);
  const base: Partial<typeof jobsTable.$inferInsert> = {
    completedAt: new Date(),
    timeElapsedSeconds,
    speed: 0,
  };

  let status: string;
  let errorMessage: string | null = null;
  if (proc.stopRequested || signal === "SIGTERM" || signal === "SIGKILL") {
    status = "stopped";
  } else if (code === 0 || code === 1) {
    // hashcat: 0 = cracked, 1 = exhausted. john: 0 = normal completion.
    status = "completed";
    base.progress = 100;
  } else {
    status = "failed";
    errorMessage = await tailLog(proc.logPath, 600);
  }

  const [cur] = await db.select().from(jobsTable).where(eq(jobsTable.id, jobId)).limit(1);
  const finalCracks = Math.max(persisted, cur?.cracksFound ?? 0);

  await updateJob(jobId, { ...base, status, errorMessage, cracksFound: finalCracks });
  logger.info({ jobId, status, code, signal, persisted }, "Crack job finished");
}

async function tailLog(logPath: string, chars: number): Promise<string> {
  try {
    const raw = await fsp.readFile(logPath, "utf8");
    return raw.slice(-chars);
  } catch {
    return "";
  }
}

export async function getJobLog(jobId: number, maxChars = 20000): Promise<string> {
  const [job] = await db.select().from(jobsTable).where(eq(jobsTable.id, jobId)).limit(1);
  if (!job?.logPath) return "";
  return tailLog(job.logPath, maxChars);
}

export function isJobRunning(jobId: number): boolean {
  return running.has(jobId);
}

/** Real process control via POSIX signals + status persistence. */
export async function controlJob(jobId: number, action: "pause" | "resume" | "stop"): Promise<boolean> {
  const proc = running.get(jobId);
  if (!proc) return false;
  const pid = proc.child.pid;
  if (!pid) return false;

  if (action === "pause") {
    process.kill(pid, "SIGSTOP");
    await updateJob(jobId, { status: "paused" });
    return true;
  }
  if (action === "resume") {
    process.kill(pid, "SIGCONT");
    await updateJob(jobId, { status: "running" });
    return true;
  }
  // stop
  proc.stopRequested = true;
  try {
    process.kill(pid, "SIGCONT"); // ensure a paused process can receive TERM
  } catch {
    /* ignore */
  }
  proc.child.kill("SIGTERM");
  setTimeout(() => {
    if (running.has(jobId)) {
      try {
        proc.child.kill("SIGKILL");
      } catch {
        /* already gone */
      }
    }
  }, 4000);
  return true;
}

import fs from "node:fs";
import path from "node:path";
import { logger } from "./logger";

// ─── Cowrie honeypot log parsing ──────────────────────────────────────────────
//
// The live dockerized Cowrie SSH honeypot's events are mirrored (read-only) into
// a per-service ledger under CommandVault. We parse the real attacker command
// executions ("CMD:" lines) out of those logs. Nothing here writes to or
// otherwise disturbs the honeypot — we only read the ledger files.
//
// A Cowrie command line looks like:
//   2026-07-04 14:35:35\t2026-07-04T18:35:35+0000 [SSHChannel session (0) on \
//     SSHService b'ssh-connection' on HoneyPotSSHTransport,568,95.24.35.51] CMD: cd ~; ...
//
// From it we extract: session id, source IP, the full command, and a timestamp.

export interface ParsedHoneypotCommand {
  command: string;
  sourceIp: string;
  session: string;
  capturedAt: Date | null;
}

const CMD_RE =
  /HoneyPotSSHTransport,(\d+),([\d.:a-fA-F]+)\]\s+CMD:\s+(.*)$/;
const ISO_TS_RE = /(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{4})/;
const PLAIN_TS_RE = /^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/;

export function parseCowrieCommands(logText: string): ParsedHoneypotCommand[] {
  const out: ParsedHoneypotCommand[] = [];
  for (const rawLine of logText.split("\n")) {
    const line = rawLine.trimEnd();
    const m = CMD_RE.exec(line);
    if (!m) continue;

    const [, session, sourceIp, commandRaw] = m;
    const command = commandRaw.trim();
    if (!command) continue;

    let capturedAt: Date | null = null;
    const iso = ISO_TS_RE.exec(line);
    if (iso) {
      const d = new Date(iso[1]);
      if (!Number.isNaN(d.getTime())) capturedAt = d;
    }
    if (!capturedAt) {
      const plain = PLAIN_TS_RE.exec(line);
      if (plain) {
        const d = new Date(plain[1].replace(" ", "T"));
        if (!Number.isNaN(d.getTime())) capturedAt = d;
      }
    }

    out.push({ command, sourceIp, session, capturedAt });
  }
  return out;
}

export function keyOf(c: {
  command: string;
  sourceIp: string;
  session: string;
}): string {
  return `${c.command}\u0000${c.sourceIp}\u0000${c.session}`;
}

// Deduplicate parsed commands by (command, sourceIp, session), keeping the
// earliest known timestamp for each.
export function dedupeCommands(commands: ParsedHoneypotCommand[]): ParsedHoneypotCommand[] {
  const byKey = new Map<string, ParsedHoneypotCommand>();
  for (const c of commands) {
    const k = keyOf(c);
    const existing = byKey.get(k);
    if (!existing) {
      byKey.set(k, c);
    } else if (c.capturedAt && (!existing.capturedAt || c.capturedAt < existing.capturedAt)) {
      byKey.set(k, { ...existing, capturedAt: c.capturedAt });
    }
  }
  return [...byKey.values()];
}

export function defaultHoneypotDir(): string {
  return process.env.FORGE_HONEYPOT_LOG_DIR?.trim() || "/home/cosmic/CommandVault/honeypots";
}

// Candidate Cowrie ledger files, in priority order. The `_audit` copy carries
// real timestamps; the top-level ledger is de-duplicated but timestamp-free
// (we fall back to the file's mtime for those entries).
function cowrieSources(dir: string): Array<{ file: string; timestamped: boolean }> {
  return [
    { file: path.join(dir, "_audit", "cowrie.log"), timestamped: true },
    { file: path.join(dir, "cowrie.txt"), timestamped: false },
  ];
}

export interface HoneypotSourceInfo {
  dir: string;
  available: boolean;
  files: string[];
}

export function honeypotSourceInfo(dir = defaultHoneypotDir()): HoneypotSourceInfo {
  const files = cowrieSources(dir)
    .map((s) => s.file)
    .filter((f) => {
      try {
        return fs.statSync(f).isFile();
      } catch {
        return false;
      }
    });
  return { dir, available: files.length > 0, files };
}

// Read + parse every available Cowrie ledger file (read-only) and return a
// de-duplicated list of real attacker commands. Entries missing an in-line
// timestamp inherit the source file's last-modified time.
export function collectHoneypotCommands(dir = defaultHoneypotDir()): ParsedHoneypotCommand[] {
  const collected: ParsedHoneypotCommand[] = [];
  for (const { file } of cowrieSources(dir)) {
    let text: string;
    let mtime: Date | null = null;
    try {
      const stat = fs.statSync(file);
      if (!stat.isFile()) continue;
      mtime = stat.mtime;
      text = fs.readFileSync(file, "utf8");
    } catch (err) {
      logger.debug({ err, file }, "Honeypot source not readable, skipping");
      continue;
    }
    for (const cmd of parseCowrieCommands(text)) {
      collected.push({ ...cmd, capturedAt: cmd.capturedAt ?? mtime });
    }
  }
  return dedupeCommands(collected);
}

import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { logger } from "./logger";

// -----------------------------------------------------------------------------
// Real log event hub
//
// This streams GENUINE log data from live sources on this host. Nothing here is
// synthesised or randomised — every event corresponds to a real line produced
// by one of the configured sources:
//
//   * Honeypot event records  (files under CommandVault/honeypots)
//   * systemd journal units    (jett-daemon, bifrost-guardian, ...)
//   * auditd log               (if readable; requires elevated perms)
//
// All sources are tailed READ-ONLY. If a source is unavailable it is skipped
// with a warning; the hub never fabricates data to fill the gap.
// -----------------------------------------------------------------------------

export interface LogEvent {
  ts: string; // ISO-8601 timestamp of when the event was observed
  source: string; // e.g. "honeypot:cowrie", "journal:jett-daemon", "auditd"
  line: string;
}

type Listener = (evt: LogEvent) => void;

const BACKLOG_MAX = 200;

function envList(name: string, fallback: string[]): string[] {
  const raw = process.env[name];
  if (!raw) return fallback;
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export class LogHub {
  private listeners = new Set<Listener>();
  private backlog: LogEvent[] = [];
  private children: ChildProcess[] = [];
  private watchers: fs.FSWatcher[] = [];
  private pollers: NodeJS.Timeout[] = [];
  private fileOffsets = new Map<string, number>();
  private started = false;

  readonly honeypotDir = process.env.HONEYPOT_LOG_DIR ?? "/home/cosmic/CommandVault/honeypots";
  readonly journalUnits = envList("JOURNAL_UNITS", ["jett-daemon", "bifrost-guardian"]);
  readonly auditdPath = process.env.AUDITD_LOG_PATH ?? "/var/log/audit/audit.log";

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getBacklog(): LogEvent[] {
    return [...this.backlog];
  }

  private emit(source: string, line: string): void {
    const trimmed = line.replace(/\s+$/u, "");
    if (!trimmed) return;
    const evt: LogEvent = { ts: new Date().toISOString(), source, line: trimmed };
    this.backlog.push(evt);
    if (this.backlog.length > BACKLOG_MAX) this.backlog.shift();
    for (const l of this.listeners) {
      try {
        l(evt);
      } catch (err) {
        logger.warn({ err }, "log listener threw");
      }
    }
  }

  start(): void {
    if (this.started) return;
    this.started = true;
    this.startJournal();
    this.startHoneypotTails();
    this.startAuditd();
    logger.info(
      { honeypotDir: this.honeypotDir, journalUnits: this.journalUnits },
      "Log hub started — streaming real log sources",
    );
  }

  stop(): void {
    for (const c of this.children) c.kill("SIGTERM");
    for (const w of this.watchers) w.close();
    for (const p of this.pollers) clearInterval(p);
    this.children = [];
    this.watchers = [];
    this.pollers = [];
    this.started = false;
  }

  // --- systemd journal (real, actively-updating service logs) ----------------
  private startJournal(): void {
    for (const unit of this.journalUnits) {
      try {
        const child = spawn(
          "journalctl",
          ["-f", "-n", "20", "-o", "cat", "--no-pager", "--unit", unit],
          { stdio: ["ignore", "pipe", "pipe"] },
        );

        let buf = "";
        child.stdout?.on("data", (chunk: Buffer) => {
          buf += chunk.toString("utf8");
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";
          for (const line of lines) this.emit(`journal:${unit}`, line);
        });
        child.on("error", (err) => {
          logger.warn({ err, unit }, "journalctl source unavailable — skipping");
        });
        child.on("exit", (code) => {
          if (code && code !== 0) {
            logger.warn({ code, unit }, "journalctl exited (source stopped)");
          }
        });
        this.children.push(child);
      } catch (err) {
        logger.warn({ err, unit }, "failed to spawn journalctl — skipping unit");
      }
    }
  }

  // --- honeypot event records (real captured attacker activity) --------------
  private startHoneypotTails(): void {
    let entries: string[] = [];
    try {
      entries = fs
        .readdirSync(this.honeypotDir)
        .filter((f) => f.endsWith(".txt") && !f.startsWith("_"));
    } catch (err) {
      logger.warn({ err, dir: this.honeypotDir }, "honeypot dir unreadable — skipping");
      return;
    }

    for (const name of entries) {
      const full = path.join(this.honeypotDir, name);
      const source = `honeypot:${name.replace(/\.txt$/u, "")}`;
      // Seed the offset at the current end so we stream only NEW activity live.
      try {
        this.fileOffsets.set(full, fs.statSync(full).size);
      } catch {
        this.fileOffsets.set(full, 0);
      }
      this.readNewLines(full, source); // no-op initially, primes state
    }

    // Poll for growth. Honeypot vaults are rewritten/appended by external
    // collectors on their own cadence; polling handles both append & rotation.
    const poller = setInterval(() => {
      for (const name of entries) {
        const full = path.join(this.honeypotDir, name);
        const source = `honeypot:${name.replace(/\.txt$/u, "")}`;
        this.readNewLines(full, source);
      }
    }, 2000);
    this.pollers.push(poller);
  }

  private readNewLines(file: string, source: string): void {
    let size: number;
    try {
      size = fs.statSync(file).size;
    } catch {
      return;
    }
    const prev = this.fileOffsets.get(file) ?? 0;
    if (size === prev) return;
    // File shrank (rotated/rewritten) — restart from beginning of new content.
    const start = size < prev ? 0 : prev;
    try {
      const fd = fs.openSync(file, "r");
      const length = size - start;
      const buffer = Buffer.alloc(length);
      fs.readSync(fd, buffer, 0, length, start);
      fs.closeSync(fd);
      this.fileOffsets.set(file, size);
      const text = buffer.toString("utf8");
      for (const line of text.split("\n")) {
        if (line.trim()) this.emit(source, line);
      }
    } catch (err) {
      logger.warn({ err, file }, "failed reading honeypot log delta");
    }
  }

  // --- auditd (real, but typically root-only) --------------------------------
  private startAuditd(): void {
    // TODO(auditd): /var/log/audit/audit.log is normally readable only by root.
    // Running the API server as an unprivileged user (the safe default) means
    // this source is skipped. To enable it, grant read access to the audit log
    // (e.g. an ACL for the service user) and it will stream automatically. We
    // deliberately do NOT escalate privileges or fabricate audit events here.
    let fd: number;
    try {
      fd = fs.openSync(this.auditdPath, "r");
    } catch (err) {
      logger.warn(
        { err, path: this.auditdPath },
        "auditd log not readable (needs elevated perms) — source disabled",
      );
      return;
    }
    fs.closeSync(fd);

    try {
      this.fileOffsets.set(this.auditdPath, fs.statSync(this.auditdPath).size);
    } catch {
      this.fileOffsets.set(this.auditdPath, 0);
    }
    const poller = setInterval(() => {
      this.readNewLines(this.auditdPath, "auditd");
    }, 2000);
    this.pollers.push(poller);
    logger.info({ path: this.auditdPath }, "auditd source enabled");
  }
}

/** Formats an event into the single-line string streamed to the UI. */
export function formatEvent(evt: LogEvent): string {
  const time = evt.ts.slice(11, 19); // HH:MM:SS
  return `[${time}] [${evt.source}] ${evt.line}`;
}

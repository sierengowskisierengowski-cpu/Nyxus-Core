import { spawn } from "node:child_process";
import { networkInterfaces } from "node:os";
import { logger } from "./logger";

/**
 * Real local-network asset inventory for the operator's OWN lab.
 *
 * This module shells out to standard, already-installed discovery tools
 * (`nmap` for host discovery, optionally `arp-scan`) and enriches results
 * with the kernel ARP/neighbour table. It NEVER seeds or fabricates devices.
 *
 * Safety model (defensive, own-lab only):
 *   - The scan target always comes from server-side configuration
 *     (the `targetSubnet` setting), never from an arbitrary request field.
 *   - Every target must be RFC1918 private space AND fully contained within
 *     an allow-listed CIDR. Public / routable ranges are always rejected.
 *   - The allow-list defaults to the host-only lab subnet (192.168.56.0/24)
 *     plus the machine's own directly-attached private subnets, and can be
 *     extended via REDFORGE_SCAN_ALLOWED_SUBNETS.
 *   - Tools are invoked via spawn() with an argument array (no shell), so a
 *     validated CIDR string cannot inject additional commands.
 */

export interface DiscoveredDevice {
  ip: string;
  hostname: string;
  mac: string;
  vendor: string;
}

export type ScanTool = "auto" | "nmap" | "arp-scan";

export interface ScanConfig {
  tool: ScanTool;
  /** Explicitly allow-listed CIDRs (from env / defaults). */
  allowedSubnets: string[];
  /** Also allow the machine's own directly-attached private subnets. */
  allowLocalLan: boolean;
  timeoutMs: number;
}

export interface CommandResult {
  stdout: string;
  stderr: string;
  code: number | null;
}

export type CommandRunner = (
  cmd: string,
  args: string[],
  timeoutMs: number,
) => Promise<CommandResult>;

/** The host-only lab subnet used by default when nothing else is configured. */
export const DEFAULT_LAB_SUBNET = "192.168.56.0/24";

// ---------------------------------------------------------------------------
// IPv4 / CIDR helpers (no external dependencies)
// ---------------------------------------------------------------------------

const IPV4_RE = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;

export function ipv4ToInt(ip: string): number | null {
  const m = IPV4_RE.exec(ip.trim());
  if (!m) return null;
  let value = 0;
  for (let i = 1; i <= 4; i++) {
    const octet = Number(m[i]);
    if (!Number.isInteger(octet) || octet < 0 || octet > 255) return null;
    value = value * 256 + octet;
  }
  // Force unsigned 32-bit.
  return value >>> 0;
}

export interface ParsedCidr {
  base: number;
  bits: number;
}

/** Parse a CIDR (or a bare IPv4, treated as /32) into a normalized network. */
export function parseCidr(input: string): ParsedCidr | null {
  const trimmed = input.trim();
  const [addr, bitsRaw] = trimmed.split("/");
  const bits = bitsRaw === undefined ? 32 : Number(bitsRaw);
  if (!Number.isInteger(bits) || bits < 0 || bits > 32) return null;
  const ip = ipv4ToInt(addr);
  if (ip === null) return null;
  const mask = bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
  const base = (ip & mask) >>> 0;
  return { base, bits };
}

/** True when `inner` is entirely contained within `outer`. */
export function cidrContains(outer: ParsedCidr, inner: ParsedCidr): boolean {
  if (inner.bits < outer.bits) return false;
  const mask = outer.bits === 0 ? 0 : (0xffffffff << (32 - outer.bits)) >>> 0;
  return ((inner.base & mask) >>> 0) === outer.base;
}

/** RFC1918 private IPv4 space (10/8, 172.16/12, 192.168/16). */
export function isPrivateIpv4Cidr(cidr: ParsedCidr): boolean {
  const ranges = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"].map(parseCidr);
  return ranges.every((r) => r !== null) && ranges.some((r) => cidrContains(r!, cidr));
}

// ---------------------------------------------------------------------------
// Allow-list resolution
// ---------------------------------------------------------------------------

/** Directly-attached, non-internal private IPv4 subnets of this machine. */
export function detectLocalSubnets(): string[] {
  const out = new Set<string>();
  const ifaces = networkInterfaces();
  for (const addrs of Object.values(ifaces)) {
    for (const a of addrs ?? []) {
      if (a.family !== "IPv4" || a.internal) continue;
      const bits = netmaskToBits(a.netmask);
      if (bits === null) continue;
      const cidr = parseCidr(`${a.address}/${bits}`);
      if (!cidr || !isPrivateIpv4Cidr(cidr)) continue;
      out.add(intToIpv4(cidr.base) + "/" + cidr.bits);
    }
  }
  return [...out];
}

export function resolveAllowedSubnets(config: ScanConfig): string[] {
  const list = new Set<string>(config.allowedSubnets);
  if (config.allowLocalLan) {
    for (const s of detectLocalSubnets()) list.add(s);
  }
  // Keep only well-formed private CIDRs — never allow public space to slip in.
  return [...list].filter((s) => {
    const c = parseCidr(s);
    return c !== null && isPrivateIpv4Cidr(c);
  });
}

export interface TargetValidation {
  ok: boolean;
  reason?: string;
  allowedSubnets: string[];
}

/**
 * Validate a requested scan target against the allow-list.
 * Accepts a CIDR or a bare IPv4 (treated as /32).
 */
export function validateScanTarget(target: string, config: ScanConfig): TargetValidation {
  const allowedSubnets = resolveAllowedSubnets(config);
  const parsed = parseCidr(target);
  if (!parsed) {
    return { ok: false, reason: `"${target}" is not a valid IPv4 address or CIDR.`, allowedSubnets };
  }
  if (!isPrivateIpv4Cidr(parsed)) {
    return {
      ok: false,
      reason: `"${target}" is not an RFC1918 private range. Only private lab ranges may be scanned.`,
      allowedSubnets,
    };
  }
  const allowed = allowedSubnets
    .map(parseCidr)
    .some((c) => c !== null && cidrContains(c, parsed));
  if (!allowed) {
    return {
      ok: false,
      reason: `"${target}" is outside the allow-listed lab ranges.`,
      allowedSubnets,
    };
  }
  return { ok: true, allowedSubnets };
}

// ---------------------------------------------------------------------------
// Output parsers
// ---------------------------------------------------------------------------

const MAC_RE = /([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})/;

/** Parse the normal (human) output of `nmap -sn`. */
export function parseNmapOutput(stdout: string): DiscoveredDevice[] {
  const devices: DiscoveredDevice[] = [];
  let current: DiscoveredDevice | null = null;

  const commit = () => {
    if (current && current.ip) devices.push(current);
    current = null;
  };

  for (const rawLine of stdout.split("\n")) {
    const line = rawLine.trim();
    const report = /^Nmap scan report for (.+)$/.exec(line);
    if (report) {
      commit();
      const token = report[1].trim();
      // Either "hostname (1.2.3.4)" or bare "1.2.3.4".
      const withHost = /^(.*)\s+\(([\d.]+)\)$/.exec(token);
      if (withHost) {
        current = { ip: withHost[2], hostname: withHost[1].trim(), mac: "", vendor: "" };
      } else {
        current = { ip: token, hostname: "", mac: "", vendor: "" };
      }
      continue;
    }
    if (current && line.startsWith("MAC Address:")) {
      const macMatch = MAC_RE.exec(line);
      if (macMatch) current.mac = macMatch[1].toLowerCase();
      const vendorMatch = /\(([^)]*)\)\s*$/.exec(line);
      if (vendorMatch) current.vendor = vendorMatch[1].trim();
    }
  }
  commit();
  return devices.filter((d) => ipv4ToInt(d.ip) !== null);
}

/** Parse `arp-scan --plain` output (IP<tab>MAC<tab>vendor). */
export function parseArpScanOutput(stdout: string): DiscoveredDevice[] {
  const devices: DiscoveredDevice[] = [];
  for (const rawLine of stdout.split("\n")) {
    const line = rawLine.trim();
    const m = /^(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F:]{17})\s*(.*)$/.exec(line);
    if (!m) continue;
    if (ipv4ToInt(m[1]) === null) continue;
    devices.push({ ip: m[1], hostname: "", mac: m[2].toLowerCase(), vendor: m[3].trim() });
  }
  return devices;
}

/** Parse `ip neigh show` into an ip -> mac map (reachable entries only). */
export function parseIpNeigh(stdout: string): Map<string, string> {
  const map = new Map<string, string>();
  for (const rawLine of stdout.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    const ipMatch = /^(\d{1,3}(?:\.\d{1,3}){3})\b/.exec(line);
    const macMatch = /lladdr\s+([0-9a-fA-F:]{17})/.exec(line);
    if (!ipMatch || !macMatch) continue;
    if (/\b(FAILED|INCOMPLETE)\b/.test(line)) continue;
    map.set(ipMatch[1], macMatch[1].toLowerCase());
  }
  return map;
}

// ---------------------------------------------------------------------------
// Command runner
// ---------------------------------------------------------------------------

export const spawnRunner: CommandRunner = (cmd, args, timeoutMs) =>
  new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      child.kill("SIGKILL");
      settled = true;
      reject(new Error(`Command "${cmd}" timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    child.stdout.on("data", (d) => (stdout += d.toString()));
    child.stderr.on("data", (d) => (stderr += d.toString()));
    child.on("error", (err) => {
      if (settled) return;
      clearTimeout(timer);
      settled = true;
      reject(err);
    });
    child.on("close", (code) => {
      if (settled) return;
      clearTimeout(timer);
      settled = true;
      resolve({ stdout, stderr, code });
    });
  });

// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

function mergeArpTable(devices: DiscoveredDevice[], arp: Map<string, string>): DiscoveredDevice[] {
  return devices.map((d) => (d.mac ? d : { ...d, mac: arp.get(d.ip) ?? "" }));
}

/**
 * Run a real discovery scan against a validated target.
 * `runner` is injectable so tests can exercise the parsing/orchestration
 * without spawning real processes; production always uses `spawnRunner`.
 */
export async function runNetworkScan(
  target: string,
  config: ScanConfig,
  runner: CommandRunner = spawnRunner,
): Promise<DiscoveredDevice[]> {
  if (config.tool === "arp-scan") {
    const res = await runner("arp-scan", ["--plain", "--retry=2", target], config.timeoutMs);
    if (res.code !== 0 && !res.stdout.trim()) {
      throw new Error(
        `arp-scan failed (exit ${res.code}). It usually needs CAP_NET_RAW/root. ` +
          `stderr: ${res.stderr.trim().slice(0, 300)}`,
      );
    }
    return parseArpScanOutput(res.stdout);
  }

  // "auto" and "nmap": nmap -sn works unprivileged; enrich MACs from the
  // kernel neighbour table (populated by the sweep) when nmap couldn't get
  // them (nmap only reports MAC/vendor when run with raw-socket privileges).
  const res = await runner("nmap", ["-sn", "-T4", target], config.timeoutMs);
  if (res.code !== 0 && !res.stdout.trim()) {
    throw new Error(
      `nmap failed (exit ${res.code}). stderr: ${res.stderr.trim().slice(0, 300)}`,
    );
  }
  const devices = parseNmapOutput(res.stdout);

  let arp = new Map<string, string>();
  try {
    const neigh = await runner("ip", ["neigh", "show"], Math.min(config.timeoutMs, 10_000));
    arp = parseIpNeigh(neigh.stdout);
  } catch (err) {
    logger.warn({ err }, "network-scan: failed to read ARP neighbour table");
  }
  return mergeArpTable(devices, arp);
}

// ---------------------------------------------------------------------------
// Config from environment
// ---------------------------------------------------------------------------

function parseSubnetList(raw: string | undefined): string[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function loadScanConfig(env: NodeJS.ProcessEnv = process.env): ScanConfig {
  const toolRaw = (env["REDFORGE_SCAN_TOOL"] ?? "auto").toLowerCase();
  const tool: ScanTool =
    toolRaw === "nmap" || toolRaw === "arp-scan" ? toolRaw : "auto";

  const explicit = parseSubnetList(env["REDFORGE_SCAN_ALLOWED_SUBNETS"]);
  const allowedSubnets = explicit.length > 0 ? explicit : [DEFAULT_LAB_SUBNET];

  const allowLocalLan = env["REDFORGE_SCAN_ALLOW_LOCAL_LAN"] !== "false";

  const timeoutRaw = Number(env["REDFORGE_SCAN_TIMEOUT_MS"]);
  const timeoutMs =
    Number.isFinite(timeoutRaw) && timeoutRaw > 0 ? timeoutRaw : 120_000;

  return { tool, allowedSubnets, allowLocalLan, timeoutMs };
}

// ---------------------------------------------------------------------------
// small local helpers
// ---------------------------------------------------------------------------

function intToIpv4(value: number): string {
  return [
    (value >>> 24) & 0xff,
    (value >>> 16) & 0xff,
    (value >>> 8) & 0xff,
    value & 0xff,
  ].join(".");
}

function netmaskToBits(netmask: string): number | null {
  const int = ipv4ToInt(netmask);
  if (int === null) return null;
  // Count contiguous leading 1s.
  let bits = 0;
  let seenZero = false;
  for (let i = 31; i >= 0; i--) {
    const bit = (int >>> i) & 1;
    if (bit === 1) {
      if (seenZero) return null; // non-contiguous mask
      bits++;
    } else {
      seenZero = true;
    }
  }
  return bits;
}

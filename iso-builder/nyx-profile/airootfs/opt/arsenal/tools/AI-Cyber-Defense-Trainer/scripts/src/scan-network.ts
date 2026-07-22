#!/usr/bin/env tsx
/**
 * Real network asset discovery for the Network Map.
 *
 * Runs arp-scan (and optionally nmap) against the owner's own lab subnet and
 * writes the discovered hosts into the `network_devices` table that the SPA's
 * Network Map reads. Everything stored is REAL scan output — no fabricated
 * devices. If nothing is on the subnet (e.g. the lab VM / vboxnet0 is down),
 * nothing is inserted and the map is honestly empty.
 *
 * Safety: host enumeration is restricted to an allowlist. The default (and only
 * built-in) allowed subnet is the VirtualBox host-only lab 192.168.56.0/24.
 * Additional subnets may be opted into by the owner via SCAN_ALLOWLIST.
 *
 *   SCAN_SUBNETS   comma list of CIDRs to scan   (default 192.168.56.0/24)
 *   SCAN_ALLOWLIST comma list of extra allowed CIDRs (owner opt-in)
 *   SCAN_PORTS=1   also run a bounded nmap port scan on discovered hosts
 *   SCAN_TARGETS   comma list of IPs to flag as high-value targets
 */
import { execFile } from "node:child_process";
import os from "node:os";
import dns from "node:dns/promises";
import { promisify } from "node:util";
import { db, networkDevicesTable, closeDb } from "@workspace/db";
import { sql } from "drizzle-orm";

const execFileP = promisify(execFile);

const BUILTIN_ALLOW = ["192.168.56.0/24"];

interface Cidr {
  base: number;
  bits: number;
  raw: string;
}

function ipToInt(ip: string): number {
  const parts = ip.split(".").map(Number);
  if (parts.length !== 4 || parts.some((n) => Number.isNaN(n) || n < 0 || n > 255)) {
    throw new Error(`Invalid IPv4 address: ${ip}`);
  }
  return ((parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0;
}

function parseCidr(cidr: string): Cidr {
  const [ip, bitsStr] = cidr.trim().split("/");
  const bits = bitsStr === undefined ? 32 : Number(bitsStr);
  if (Number.isNaN(bits) || bits < 0 || bits > 32) throw new Error(`Invalid CIDR: ${cidr}`);
  const mask = bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
  return { base: (ipToInt(ip) & mask) >>> 0, bits, raw: cidr.trim() };
}

/** True if `inner` is fully contained by `outer`. */
function cidrContains(outer: Cidr, inner: Cidr): boolean {
  if (inner.bits < outer.bits) return false;
  const mask = outer.bits === 0 ? 0 : (0xffffffff << (32 - outer.bits)) >>> 0;
  return ((inner.base & mask) >>> 0) === outer.base;
}

function envList(name: string): string[] {
  return (process.env[name] ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function assertAllowed(subnets: Cidr[]): void {
  const allow = [...BUILTIN_ALLOW, ...envList("SCAN_ALLOWLIST")].map(parseCidr);
  for (const s of subnets) {
    if (!allow.some((a) => cidrContains(a, s))) {
      throw new Error(
        `Refusing to scan ${s.raw}: not within the allowlist (${allow
          .map((a) => a.raw)
          .join(", ")}). Add it to SCAN_ALLOWLIST to opt in.`,
      );
    }
  }
}

function interfaceForSubnet(subnet: Cidr): string | null {
  const ifaces = os.networkInterfaces();
  for (const [name, addrs] of Object.entries(ifaces)) {
    for (const a of addrs ?? []) {
      if (a.family === "IPv4" && !a.internal) {
        try {
          if ((ipToInt(a.address) & maskOf(subnet.bits)) >>> 0 === subnet.base) return name;
        } catch {
          /* ignore */
        }
      }
    }
  }
  return null;
}

function maskOf(bits: number): number {
  return bits === 0 ? 0 : (0xffffffff << (32 - bits)) >>> 0;
}

interface Discovered {
  ip: string;
  mac: string | null;
  vendor: string | null;
  openPorts: number[];
}

async function arpScan(subnet: Cidr, iface: string | null): Promise<Discovered[]> {
  const args = ["--retry=2", "--timeout=200"];
  if (iface) args.push(`--interface=${iface}`);
  args.push(subnet.raw);
  let stdout = "";
  try {
    ({ stdout } = await execFileP("arp-scan", args, { timeout: 60000 }));
  } catch (err) {
    const e = err as { stdout?: string; stderr?: string; message?: string };
    if (e.stdout) stdout = e.stdout;
    else {
      console.warn(`  arp-scan on ${subnet.raw} (${iface ?? "auto"}) failed: ${e.stderr || e.message}`);
      return [];
    }
  }
  const devices: Discovered[] = [];
  const lineRe = /^(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F:]{17})\s+(.*)$/;
  for (const line of stdout.split("\n")) {
    const m = line.match(lineRe);
    if (!m) continue;
    devices.push({ ip: m[1], mac: m[2].toLowerCase(), vendor: m[3].trim() || null, openPorts: [] });
  }
  return devices;
}

async function portScan(ip: string): Promise<number[]> {
  try {
    const { stdout } = await execFileP(
      "nmap",
      ["-Pn", "-T4", "--top-ports", "50", "-oG", "-", ip],
      { timeout: 120000 },
    );
    const ports: number[] = [];
    const m = stdout.match(/Ports:\s*(.+)/);
    if (m) {
      for (const chunk of m[1].split(",")) {
        const pm = chunk.trim().match(/^(\d+)\/open/);
        if (pm) ports.push(Number(pm[1]));
      }
    }
    return ports;
  } catch {
    return [];
  }
}

async function reverseDns(ip: string): Promise<string | null> {
  try {
    const names = await dns.reverse(ip);
    return names[0] ?? null;
  } catch {
    return null;
  }
}

async function main(): Promise<void> {
  const subnetStrs = envList("SCAN_SUBNETS");
  const subnets = (subnetStrs.length ? subnetStrs : ["192.168.56.0/24"]).map(parseCidr);
  assertAllowed(subnets);

  const doPorts = process.env.SCAN_PORTS === "1";
  const targets = new Set(envList("SCAN_TARGETS"));

  console.log(`Scanning allowlisted subnets: ${subnets.map((s) => s.raw).join(", ")}`);

  const all: Discovered[] = [];
  for (const subnet of subnets) {
    const iface = interfaceForSubnet(subnet);
    console.log(`  ${subnet.raw} via ${iface ?? "arp-scan default interface"}`);
    const found = await arpScan(subnet, iface);
    console.log(`    arp-scan discovered ${found.length} host(s)`);
    all.push(...found);
  }

  // De-dupe by IP.
  const byIp = new Map<string, Discovered>();
  for (const d of all) byIp.set(d.ip, d);
  const devices = [...byIp.values()];

  if (doPorts) {
    for (const d of devices) {
      d.openPorts = await portScan(d.ip);
      console.log(`    ${d.ip}: ports ${d.openPorts.join(", ") || "(none open in top 50)"}`);
    }
  }

  if (devices.length === 0) {
    console.log(
      "No hosts discovered. If your lab subnet is down (e.g. vboxnet0), start the lab VM " +
        "or set SCAN_SUBNETS to an active allowlisted subnet, then re-run.",
    );
    await closeDb();
    return;
  }

  let written = 0;
  for (const d of devices) {
    const hostname = await reverseDns(d.ip);
    await db
      .insert(networkDevicesTable)
      .values({
        ip: d.ip,
        hostname,
        mac: d.mac,
        vendor: d.vendor,
        status: "online",
        isTarget: targets.has(d.ip),
        openPorts: JSON.stringify(d.openPorts),
        lastSeen: new Date(),
      })
      .onConflictDoUpdate({
        target: networkDevicesTable.ip,
        set: {
          hostname,
          mac: d.mac,
          vendor: d.vendor,
          status: "online",
          isTarget: targets.has(d.ip),
          openPorts: JSON.stringify(d.openPorts),
          lastSeen: new Date(),
        },
      });
    written++;
  }
  console.log(`Wrote ${written} real device(s) to network_devices.`);
  await closeDb();
}

main().catch(async (err) => {
  console.error(err instanceof Error ? err.message : err);
  await closeDb().catch(() => {});
  process.exit(1);
});

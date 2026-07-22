import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  parseCidr,
  cidrContains,
  isPrivateIpv4Cidr,
  validateScanTarget,
  parseNmapOutput,
  parseArpScanOutput,
  parseIpNeigh,
  runNetworkScan,
  loadScanConfig,
  spawnRunner,
  type ScanConfig,
  type CommandRunner,
} from "./networkScan";

const baseConfig: ScanConfig = {
  tool: "auto",
  allowedSubnets: ["192.168.56.0/24"],
  allowLocalLan: false,
  timeoutMs: 30_000,
};

test("CIDR containment math", () => {
  const outer = parseCidr("192.168.56.0/24")!;
  assert.ok(cidrContains(outer, parseCidr("192.168.56.10/32")!));
  assert.ok(cidrContains(outer, parseCidr("192.168.56.0/24")!));
  assert.ok(!cidrContains(outer, parseCidr("192.168.57.0/24")!));
  assert.ok(!cidrContains(outer, parseCidr("192.168.56.0/23")!)); // wider is not contained
});

test("private range detection", () => {
  assert.ok(isPrivateIpv4Cidr(parseCidr("10.1.2.0/24")!));
  assert.ok(isPrivateIpv4Cidr(parseCidr("192.168.56.0/24")!));
  assert.ok(isPrivateIpv4Cidr(parseCidr("172.16.5.0/24")!));
  assert.ok(!isPrivateIpv4Cidr(parseCidr("8.8.8.8/32")!));
  assert.ok(!isPrivateIpv4Cidr(parseCidr("172.32.0.0/16")!));
});

test("validateScanTarget accepts allow-listed private targets", () => {
  const v = validateScanTarget("192.168.56.0/24", baseConfig);
  assert.equal(v.ok, true);
});

test("validateScanTarget rejects public / out-of-allowlist targets", () => {
  assert.equal(validateScanTarget("8.8.8.0/24", baseConfig).ok, false);
  assert.equal(validateScanTarget("192.168.99.0/24", baseConfig).ok, false); // private but not allow-listed
  assert.equal(validateScanTarget("not-an-ip", baseConfig).ok, false);
  assert.equal(validateScanTarget("192.168.56.10", baseConfig).ok, true); // bare IP -> /32
});

test("parseNmapOutput extracts ip/hostname/mac/vendor", () => {
  const out = [
    "Starting Nmap 7.99 ( https://nmap.org )",
    "Nmap scan report for gateway.lab (192.168.56.1)",
    "Host is up (0.0021s latency).",
    "MAC Address: AA:BB:CC:DD:EE:01 (Ubiquiti Networks)",
    "Nmap scan report for 192.168.56.20",
    "Host is up.",
    "Nmap done: 256 IP addresses (2 hosts up) scanned in 2.10 seconds",
  ].join("\n");
  const devices = parseNmapOutput(out);
  assert.equal(devices.length, 2);
  assert.deepEqual(devices[0], {
    ip: "192.168.56.1",
    hostname: "gateway.lab",
    mac: "aa:bb:cc:dd:ee:01",
    vendor: "Ubiquiti Networks",
  });
  assert.equal(devices[1].ip, "192.168.56.20");
  assert.equal(devices[1].mac, "");
});

test("parseArpScanOutput parses plain output", () => {
  const out = [
    "192.168.56.1\taa:bb:cc:dd:ee:01\tUbiquiti Networks",
    "192.168.56.20\taa:bb:cc:dd:ee:20\t(Unknown)",
    "garbage line",
  ].join("\n");
  const devices = parseArpScanOutput(out);
  assert.equal(devices.length, 2);
  assert.equal(devices[0].mac, "aa:bb:cc:dd:ee:01");
});

test("parseIpNeigh maps reachable entries", () => {
  const out = [
    "192.168.56.1 dev eth0 lladdr aa:bb:cc:dd:ee:01 REACHABLE",
    "192.168.56.99 dev eth0 FAILED",
    "192.168.56.20 dev eth0 lladdr aa:bb:cc:dd:ee:20 STALE",
  ].join("\n");
  const map = parseIpNeigh(out);
  assert.equal(map.get("192.168.56.1"), "aa:bb:cc:dd:ee:01");
  assert.equal(map.get("192.168.56.20"), "aa:bb:cc:dd:ee:20");
  assert.equal(map.has("192.168.56.99"), false);
});

test("runNetworkScan (auto) merges nmap output with ARP table via mocked subprocess", async () => {
  const nmapOut = [
    "Nmap scan report for 192.168.56.20",
    "Host is up.",
  ].join("\n");
  const neighOut = "192.168.56.20 dev eth0 lladdr aa:bb:cc:dd:ee:20 REACHABLE";

  const mockRunner: CommandRunner = async (cmd) => {
    if (cmd === "nmap") return { stdout: nmapOut, stderr: "", code: 0 };
    if (cmd === "ip") return { stdout: neighOut, stderr: "", code: 0 };
    throw new Error(`unexpected command: ${cmd}`);
  };

  const devices = await runNetworkScan("192.168.56.0/24", baseConfig, mockRunner);
  assert.equal(devices.length, 1);
  assert.equal(devices[0].ip, "192.168.56.20");
  // MAC was empty from nmap but enriched from the ARP neighbour table.
  assert.equal(devices[0].mac, "aa:bb:cc:dd:ee:20");
});

test("loadScanConfig honours env overrides", () => {
  const cfg = loadScanConfig({
    REDFORGE_SCAN_TOOL: "arp-scan",
    REDFORGE_SCAN_ALLOWED_SUBNETS: "10.0.0.0/24, 192.168.56.0/24",
    REDFORGE_SCAN_ALLOW_LOCAL_LAN: "false",
    REDFORGE_SCAN_TIMEOUT_MS: "5000",
  } as NodeJS.ProcessEnv);
  assert.equal(cfg.tool, "arp-scan");
  assert.deepEqual(cfg.allowedSubnets, ["10.0.0.0/24", "192.168.56.0/24"]);
  assert.equal(cfg.allowLocalLan, false);
  assert.equal(cfg.timeoutMs, 5000);
});

// Real-tool smoke: exercises the actual nmap binary through the production
// spawnRunner. Skipped gracefully when nmap is not installed.
const hasNmap = spawnSync("nmap", ["--version"], { stdio: "ignore" }).status === 0;

test("runNetworkScan invokes the real nmap binary against loopback", { skip: !hasNmap }, async () => {
  const devices = await runNetworkScan(
    "127.0.0.1/32",
    { ...baseConfig, timeoutMs: 20_000 },
    spawnRunner,
  );
  assert.ok(Array.isArray(devices));
  assert.ok(
    devices.some((d) => d.ip === "127.0.0.1"),
    `expected loopback in results, got ${JSON.stringify(devices)}`,
  );
});

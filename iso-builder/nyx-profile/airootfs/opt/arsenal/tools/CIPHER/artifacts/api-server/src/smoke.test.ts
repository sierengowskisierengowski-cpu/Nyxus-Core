import { test } from "node:test";
import assert from "node:assert/strict";
import os from "node:os";
import path from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

// Scope the workspace to a temp dir so the test never touches real app data.
process.env["CIPHER_WORK_DIR"] = path.join(os.tmpdir(), `cipher-test-${process.pid}`);
process.env["CIPHER_AUTH_SECRET"] = "test-secret-value-for-smoke-tests";

const { hashPassword, verifyPassword, signToken, verifyToken } = await import("./lib/auth");
const { safeFileName, resolveWithin } = await import("./lib/workspace-paths");
const { getSystemStats } = await import("./lib/system-stats");

test("password hashing round-trips and rejects wrong passwords", () => {
  const hash = hashPassword("labpass123");
  assert.ok(hash.startsWith("scrypt$"));
  assert.equal(verifyPassword("labpass123", hash), true);
  assert.equal(verifyPassword("wrong", hash), false);
});

test("auth tokens sign, verify, and reject tampering", () => {
  const token = signToken("owner");
  const payload = verifyToken(token);
  assert.ok(payload);
  assert.equal(payload?.sub, "owner");
  assert.equal(verifyToken(token + "x"), null);
  assert.equal(verifyToken("garbage"), null);
  assert.equal(verifyToken(undefined), null);
});

test("workspace path helpers prevent traversal", () => {
  assert.equal(safeFileName("../../etc/passwd"), "passwd");
  assert.equal(safeFileName("my list!.txt"), "my_list_.txt");
  const base = "/tmp/base";
  assert.equal(resolveWithin(base, "ok.txt"), path.join(base, "ok.txt"));
  assert.throws(() => resolveWithin(base, "../escape"));
  assert.throws(() => resolveWithin(base, "/etc/passwd"));
});

test("system stats report real host telemetry", async () => {
  const stats = await getSystemStats();
  assert.ok(stats.cpu.cores > 0, "should detect CPU cores");
  assert.ok(typeof stats.cpu.model === "string" && stats.cpu.model.length > 0);
  assert.ok(stats.memory.totalMb > 0, "should read total memory");
  assert.ok(Array.isArray(stats.gpus));
  assert.equal(typeof stats.gpuAvailable, "boolean");
});

// Proves the real endpoints have a real binary to orchestrate. The HTTP
// /jobs endpoint invokes these same binaries (verified interactively); here we
// just confirm the tools are installed and invokable on this host.
test("real hashcat binary is installed and invokable", async () => {
  try {
    const { stdout } = await execFileAsync("hashcat", ["--version"], { timeout: 15000 });
    assert.match(stdout, /v?\d+\.\d+/);
  } catch (err) {
    assert.fail(`hashcat is not invokable: ${(err as Error).message}`);
  }
});

test("real john binary is installed and invokable", async () => {
  try {
    // `john` with no args prints usage/version banner to stdout or stderr.
    const { stdout, stderr } = await execFileAsync("john", [], { timeout: 15000 }).catch((e: { stdout?: string; stderr?: string }) => ({
      stdout: e.stdout ?? "",
      stderr: e.stderr ?? "",
    }));
    assert.match(`${stdout}${stderr}`, /John the Ripper/i);
  } catch (err) {
    assert.fail(`john is not invokable: ${(err as Error).message}`);
  }
});

// Minimal real backend smoke test.
//
// Boots the actual built Express server against the local Postgres DB on an
// ephemeral port and exercises the real auth + honeypot-feed paths over HTTP.
// It never hits the AI/generation endpoints, so no external network access and
// no local model are required (FORGE's AI runs locally via Ollama).
//
// Requires: DATABASE_URL set, Postgres reachable, schema pushed
// (`pnpm --filter @workspace/db run push`).
//
// Run: node ./smoke-test.mjs   (from artifacts/api-server, after `pnpm build`)

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const entry = path.join(here, "dist", "index.mjs");

if (!existsSync(entry)) {
  console.error(`Build output missing at ${entry}. Run \`pnpm build\` first.`);
  process.exit(1);
}

const PORT = 21567; // ephemeral, unlikely to collide
const USERNAME = "smoke-admin";
const PASSWORD = "smoke-password-123";
const BASE = `http://127.0.0.1:${PORT}/api`;

const env = {
  ...process.env,
  NODE_ENV: "production", // avoid pino-pretty worker thread in tests
  PORT: String(PORT),
  BASE_PATH: "/",
  FORGE_AUTH_USERNAME: USERNAME,
  FORGE_AUTH_PASSWORD: PASSWORD,
  SESSION_SECRET: "smoke-test-session-secret-not-for-production",
  FORGE_HONEYPOT_POLL_MS: "0", // no background timer during the test
  // No AI endpoints are exercised, so Ollama need not be running.
};

const failures = [];
function check(name, cond, detail = "") {
  if (cond) {
    console.log(`  ok   ${name}`);
  } else {
    console.error(`  FAIL ${name}${detail ? ` — ${detail}` : ""}`);
    failures.push(name);
  }
}

async function waitForHealth(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${BASE}/healthz`);
      if (res.ok) return true;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

const server = spawn("node", ["--enable-source-maps", entry], { env, stdio: ["ignore", "pipe", "pipe"] });
let serverLog = "";
server.stdout.on("data", (d) => (serverLog += d.toString()));
server.stderr.on("data", (d) => (serverLog += d.toString()));

let exitCode = 0;
try {
  const up = await waitForHealth();
  check("server starts and /healthz responds", up);
  if (!up) throw new Error("server never became healthy:\n" + serverLog);

  // Unauthenticated access is rejected.
  const meAnon = await fetch(`${BASE}/auth/me`);
  check("GET /auth/me is 401 when logged out", meAnon.status === 401, `got ${meAnon.status}`);

  const threatsAnon = await fetch(`${BASE}/threats`);
  check("protected route /threats is 401 when logged out", threatsAnon.status === 401, `got ${threatsAnon.status}`);

  // Bad credentials rejected.
  const badLogin = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username: USERNAME, password: "wrong" }),
  });
  check("login with wrong password is 401", badLogin.status === 401, `got ${badLogin.status}`);

  // Correct credentials succeed and set a session cookie.
  const login = await fetch(`${BASE}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  check("login with correct password is 200", login.status === 200, `got ${login.status}`);
  const setCookie = login.headers.get("set-cookie") ?? "";
  check("login sets forge_session cookie", /forge_session=/.test(setCookie));
  const cookie = setCookie.split(";")[0];

  // Authenticated access works.
  const meAuth = await fetch(`${BASE}/auth/me`, { headers: { cookie } });
  check("GET /auth/me is 200 with session cookie", meAuth.status === 200, `got ${meAuth.status}`);

  const threatsAuth = await fetch(`${BASE}/threats`, { headers: { cookie } });
  check("protected route /threats is 200 with session cookie", threatsAuth.status === 200, `got ${threatsAuth.status}`);

  // Meli feed returns real, ingested honeypot commands (array; typically > 0).
  const feed = await fetch(`${BASE}/integrations/meli/feed`, { headers: { cookie } });
  check("GET /integrations/meli/feed is 200", feed.status === 200, `got ${feed.status}`);
  const feedBody = await feed.json();
  check("meli feed returns an array", Array.isArray(feedBody));
  if (Array.isArray(feedBody)) {
    console.log(`  info meli feed contains ${feedBody.length} real honeypot command(s)`);
    if (feedBody[0]) {
      const row = feedBody[0];
      check(
        "meli feed rows have command/sourceIp fields",
        typeof row.command === "string" && typeof row.sourceIp === "string",
      );
    }
  }

  // REDFORGE status reports handoff readiness (never falsely disabled).
  const rf = await fetch(`${BASE}/integrations/redforge/status`, { headers: { cookie } });
  const rfBody = await rf.json();
  check("REDFORGE status is 200 and ready", rf.status === 200 && rfBody.online === true, JSON.stringify(rfBody));

  const logout = await fetch(`${BASE}/auth/logout`, { method: "POST", headers: { cookie } });
  check("logout is 200", logout.status === 200, `got ${logout.status}`);
} catch (err) {
  console.error("Smoke test error:", err);
  exitCode = 1;
} finally {
  server.kill("SIGTERM");
}

if (failures.length > 0) {
  console.error(`\n${failures.length} check(s) failed: ${failures.join(", ")}`);
  process.exit(1);
}
console.log("\nAll smoke checks passed.");
process.exit(exitCode);

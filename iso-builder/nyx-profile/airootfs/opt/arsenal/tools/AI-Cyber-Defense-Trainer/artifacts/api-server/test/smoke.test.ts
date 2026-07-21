import test from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import app from "../src/app";
import { LogHub } from "../src/lib/log-sources";
import { createLogWsServer } from "../src/lib/ws-server";

// Minimal real backend smoke test: boots the Express app + /ws WebSocket server
// on an ephemeral port and exercises both. No database is required (the health
// check and WebSocket handshake do not touch the DB).

function listen(server: Server): Promise<number> {
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      resolve((server.address() as AddressInfo).port);
    });
  });
}

test("GET /api/healthz returns ok", async () => {
  const server = createServer(app);
  const hub = new LogHub();
  const ws = createLogWsServer(server, hub, "/ws");
  const port = await listen(server);
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/healthz`);
    assert.equal(res.status, 200);
    const body = (await res.json()) as { status?: string };
    assert.equal(body.status, "ok");
  } finally {
    ws.close();
    hub.stop();
    await new Promise((r) => server.close(r));
  }
});

test("/ws upgrades and streams a hello frame", async () => {
  const server = createServer(app);
  const hub = new LogHub();
  const ws = createLogWsServer(server, hub, "/ws");
  const port = await listen(server);
  try {
    const client = new WebSocket(`ws://127.0.0.1:${port}/ws`);
    const first = await new Promise<string>((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("ws message timeout")), 4000);
      client.onmessage = (e) => {
        clearTimeout(timer);
        resolve(String(e.data));
      };
      client.onerror = () => {
        clearTimeout(timer);
        reject(new Error("ws error"));
      };
    });
    assert.match(first, /REDFORGE live log stream/);
    client.close();
  } finally {
    ws.close();
    hub.stop();
    await new Promise((r) => server.close(r));
  }
});

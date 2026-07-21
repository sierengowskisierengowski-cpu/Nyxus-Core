import crypto from "node:crypto";
import type { Server as HttpServer, IncomingMessage } from "node:http";
import type { Duplex } from "node:stream";
import { LogHub, formatEvent } from "./log-sources";
import { logger } from "./logger";

// -----------------------------------------------------------------------------
// Minimal RFC 6455 WebSocket server (server -> client text streaming).
//
// We implement the handshake and framing directly on the raw socket instead of
// pulling in the `ws` package. The live-log feed only needs to PUSH text frames
// to clients, so this stays small: we encode outbound text frames, respond to
// pings, and detect client close frames. No third-party runtime dependency.
// -----------------------------------------------------------------------------

const WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";
const OP_TEXT = 0x1;
const OP_CLOSE = 0x8;
const OP_PING = 0x9;
const OP_PONG = 0xa;

function acceptKey(clientKey: string): string {
  return crypto
    .createHash("sha1")
    .update(clientKey + WS_GUID)
    .digest("base64");
}

/** Encodes an unmasked frame (server -> client). */
function encodeFrame(opcode: number, payload: Buffer): Buffer {
  const len = payload.length;
  let header: Buffer;
  if (len < 126) {
    header = Buffer.alloc(2);
    header[1] = len;
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[1] = 126;
    header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[1] = 127;
    header.writeBigUInt64BE(BigInt(len), 2);
  }
  header[0] = 0x80 | opcode; // FIN + opcode
  return Buffer.concat([header, payload]);
}

function encodeText(text: string): Buffer {
  return encodeFrame(OP_TEXT, Buffer.from(text, "utf8"));
}

class WsClient {
  private inbound = Buffer.alloc(0);
  alive = true;

  constructor(
    private readonly socket: Duplex,
    private readonly onClose: () => void,
  ) {
    socket.on("data", (chunk: Buffer) => this.onData(chunk));
    socket.on("close", () => this.terminate());
    socket.on("error", () => this.terminate());
  }

  send(text: string): void {
    if (!this.alive) return;
    try {
      this.socket.write(encodeText(text));
    } catch {
      this.terminate();
    }
  }

  ping(): void {
    if (!this.alive) return;
    try {
      this.socket.write(encodeFrame(OP_PING, Buffer.alloc(0)));
    } catch {
      this.terminate();
    }
  }

  terminate(): void {
    if (!this.alive) return;
    this.alive = false;
    try {
      this.socket.end();
    } catch {
      /* ignore */
    }
    this.onClose();
  }

  // Parse inbound (masked) frames far enough to honour close/ping control
  // frames. Payload data frames from the client are ignored (feed is push-only).
  private onData(chunk: Buffer): void {
    this.inbound = Buffer.concat([this.inbound, chunk]);
    while (this.inbound.length >= 2) {
      const opcode = this.inbound[0] & 0x0f;
      const masked = (this.inbound[1] & 0x80) !== 0;
      let len = this.inbound[1] & 0x7f;
      let offset = 2;

      if (len === 126) {
        if (this.inbound.length < offset + 2) return;
        len = this.inbound.readUInt16BE(offset);
        offset += 2;
      } else if (len === 127) {
        if (this.inbound.length < offset + 8) return;
        len = Number(this.inbound.readBigUInt64BE(offset));
        offset += 8;
      }

      const maskLen = masked ? 4 : 0;
      if (this.inbound.length < offset + maskLen + len) return; // wait for more

      const maskKey = masked
        ? this.inbound.subarray(offset, offset + 4)
        : Buffer.alloc(0);
      offset += maskLen;
      const payload = this.inbound.subarray(offset, offset + len);
      offset += len;

      if (masked) {
        for (let i = 0; i < payload.length; i++) payload[i] ^= maskKey[i % 4];
      }

      if (opcode === OP_CLOSE) {
        this.terminate();
        return;
      }
      if (opcode === OP_PING) {
        try {
          this.socket.write(encodeFrame(OP_PONG, payload));
        } catch {
          this.terminate();
        }
      }
      // OP_PONG / OP_TEXT from client: ignored.

      this.inbound = this.inbound.subarray(offset);
    }
  }
}

export interface LogWsServer {
  handleUpgrade(req: IncomingMessage, socket: Duplex, head: Buffer): void;
  clientCount(): number;
  close(): void;
}

/**
 * Attaches the live-log WebSocket server to an HTTP server at `pathname`.
 * Returns a handle whose `handleUpgrade` should be invoked for matching
 * upgrade requests (the caller routes non-matching upgrades elsewhere).
 */
export function createLogWsServer(
  server: HttpServer,
  hub: LogHub,
  pathname = "/ws",
): LogWsServer {
  const clients = new Set<WsClient>();

  const unsubscribe = hub.subscribe((evt) => {
    const line = formatEvent(evt);
    for (const c of clients) c.send(line);
  });

  const heartbeat = setInterval(() => {
    for (const c of clients) c.ping();
  }, 30000);

  function handleUpgrade(req: IncomingMessage, socket: Duplex, head: Buffer): void {
    const key = req.headers["sec-websocket-key"];
    if (req.headers.upgrade?.toLowerCase() !== "websocket" || typeof key !== "string") {
      socket.destroy();
      return;
    }

    const responseHeaders = [
      "HTTP/1.1 101 Switching Protocols",
      "Upgrade: websocket",
      "Connection: Upgrade",
      `Sec-WebSocket-Accept: ${acceptKey(key)}`,
      "\r\n",
    ];
    socket.write(responseHeaders.join("\r\n"));

    const client = new WsClient(socket, () => clients.delete(client));
    clients.add(client);
    if (head && head.length) socket.unshift(head);

    // Replay recent real activity so the panel isn't empty on connect.
    client.send("[+] Connected to REDFORGE live log stream (real sources)");
    const backlog = hub.getBacklog();
    for (const evt of backlog.slice(-60)) client.send(formatEvent(evt));
    if (backlog.length === 0) {
      client.send("[*] Awaiting live events from honeypot / journal sources…");
    }
    logger.info({ clients: clients.size }, "WebSocket client connected to /ws");
  }

  const attachedUpgrade = (req: IncomingMessage, socket: Duplex, head: Buffer) => {
    let reqPath = req.url ?? "";
    const q = reqPath.indexOf("?");
    if (q !== -1) reqPath = reqPath.slice(0, q);
    if (reqPath === pathname) handleUpgrade(req, socket, head);
  };
  server.on("upgrade", attachedUpgrade);

  return {
    handleUpgrade,
    clientCount: () => clients.size,
    close: () => {
      clearInterval(heartbeat);
      unsubscribe();
      for (const c of clients) c.terminate();
      server.off("upgrade", attachedUpgrade);
    },
  };
}

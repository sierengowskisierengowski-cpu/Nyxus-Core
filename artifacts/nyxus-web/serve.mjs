import { createServer } from "http";
import { createReadStream, statSync, existsSync } from "fs";
import { join, extname, resolve, sep } from "path";
import { fileURLToPath } from "url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const PORT = parseInt(process.env.PORT ?? "18304", 10);
const DIST = resolve(__dirname, "dist/public");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".txt": "text/plain",
};

// Confine a resolved path to DIST. Rejects `..` traversal that would
// otherwise let a raw request like `GET /../../../etc/passwd` escape the
// web root and read arbitrary files off the host.
function isInsideDist(candidate) {
  const r = resolve(candidate);
  return r === DIST || r.startsWith(DIST + sep);
}

const server = createServer((req, res) => {
  let urlPath = req.url.split("?")[0];

  // Decode percent-encoding so encoded traversal (e.g. %2e%2e%2f) is
  // caught by the containment check below rather than slipping through.
  try {
    urlPath = decodeURIComponent(urlPath);
  } catch {
    res.writeHead(400, { "Content-Type": "text/plain" });
    res.end("Bad request");
    return;
  }

  let filePath = join(DIST, urlPath);

  if (!isInsideDist(filePath)) {
    res.writeHead(403, { "Content-Type": "text/plain" });
    res.end("Forbidden");
    return;
  }

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    const withIndex = join(filePath, "index.html");
    if (existsSync(withIndex)) {
      filePath = withIndex;
    } else {
      filePath = join(DIST, "index.html");
    }
  }

  if (!existsSync(filePath)) {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("Not found");
    return;
  }

  const ext = extname(filePath).toLowerCase();
  const contentType = MIME[ext] ?? "application/octet-stream";

  res.writeHead(200, {
    "Content-Type": contentType,
    "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
  });

  createReadStream(filePath).pipe(res);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`NYXUS web portal serving from ${DIST} on port ${PORT}`);
});

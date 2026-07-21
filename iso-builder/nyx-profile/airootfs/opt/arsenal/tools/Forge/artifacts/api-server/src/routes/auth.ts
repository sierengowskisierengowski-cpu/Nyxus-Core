import { Router, type IRouter } from "express";
import {
  SESSION_COOKIE,
  createSessionToken,
  getAuthConfig,
  verifyCredentials,
  verifySessionToken,
} from "../lib/auth";

const router: IRouter = Router();

function cookieOptions(maxAgeMs: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    // `secure` is intentionally driven by env: local HTTP deployments must not
    // set Secure or the cookie is dropped. Set FORGE_COOKIE_SECURE=1 behind TLS.
    secure: process.env.FORGE_COOKIE_SECURE === "1",
    path: "/",
    maxAge: maxAgeMs,
  };
}

router.post("/auth/login", (req, res): void => {
  const { username, password } = (req.body ?? {}) as {
    username?: unknown;
    password?: unknown;
  };
  if (typeof username !== "string" || typeof password !== "string") {
    res.status(400).json({ error: "username and password are required" });
    return;
  }

  if (!verifyCredentials(username, password)) {
    res.status(401).json({ error: "Invalid credentials" });
    return;
  }

  const cfg = getAuthConfig();
  const token = createSessionToken(username, cfg);
  res.cookie(SESSION_COOKIE, token, cookieOptions(cfg.sessionTtlMs));
  res.json({ username });
});

router.post("/auth/logout", (_req, res): void => {
  res.clearCookie(SESSION_COOKIE, { path: "/" });
  res.json({ success: true });
});

router.get("/auth/me", (req, res): void => {
  const token = req.cookies?.[SESSION_COOKIE] as string | undefined;
  const session = verifySessionToken(token);
  if (!session) {
    res.status(401).json({ error: "Not authenticated" });
    return;
  }
  res.json({ username: session.username });
});

export default router;

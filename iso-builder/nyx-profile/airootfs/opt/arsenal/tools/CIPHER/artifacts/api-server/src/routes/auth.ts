import { Router } from "express";
import {
  getConfiguredPasswordHash,
  isAuthConfigured,
  signToken,
  verifyPassword,
  verifyToken,
  requireAuth,
} from "../lib/auth";

const router = Router();

router.get("/auth/status", (_req, res) => {
  res.json({ configured: isAuthConfigured() });
});

router.post("/auth/login", (req, res) => {
  const passwordHash = getConfiguredPasswordHash();
  if (!passwordHash) {
    res.status(503).json({
      error:
        "Authentication is not configured. Set CIPHER_PASSWORD (or CIPHER_PASSWORD_HASH) in the server environment.",
    });
    return;
  }
  const { password } = req.body ?? {};
  if (typeof password !== "string" || password.length === 0) {
    res.status(400).json({ error: "password is required" });
    return;
  }
  if (!verifyPassword(password, passwordHash)) {
    res.status(401).json({ error: "Invalid password" });
    return;
  }
  const token = signToken("owner");
  res.cookie?.("cipher_token", token, {
    httpOnly: true,
    sameSite: "lax",
    maxAge: 12 * 60 * 60 * 1000,
  });
  res.json({ token });
});

router.post("/auth/logout", (_req, res) => {
  res.clearCookie?.("cipher_token");
  res.json({ ok: true });
});

router.get("/auth/me", requireAuth, (req, res) => {
  const header = req.headers["authorization"];
  const token = typeof header === "string" ? header.slice(7).trim() : undefined;
  const payload = verifyToken(token) ?? { sub: "owner" };
  res.json({ authenticated: true, subject: payload.sub });
});

export default router;

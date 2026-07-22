import { Router, type IRouter } from "express";
import { eq } from "drizzle-orm";
import { db, users, sessions, disclaimerAcceptances } from "@workspace/db";
import { SetupAuthBody, LoginBody } from "@workspace/api-zod";
import {
  hashPassword,
  verifyPassword,
  generateTotpSecret,
  verifyTotp,
  generateRecoveryCodes,
  newSessionId,
} from "../lib/auth";

const router: IRouter = Router();
const SESSION_DAYS = 14;
const COOKIE_NAME = "redforge_sid";

function cookieOpts() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    maxAge: SESSION_DAYS * 24 * 60 * 60 * 1000,
    path: "/",
  };
}

router.get("/auth/status", async (req, res) => {
  const userCount = await db.select().from(users).limit(1);
  const needsSetup = userCount.length === 0;
  let acceptedAt: string | null = null;
  if (req.user) {
    const acc = await db
      .select()
      .from(disclaimerAcceptances)
      .where(eq(disclaimerAcceptances.userId, req.user.id))
      .limit(1);
    acceptedAt = acc[0]?.acceptedAt.toISOString() ?? null;
  }
  res.json({
    needsSetup,
    authenticated: !!req.user,
    username: req.user?.username ?? null,
    disclaimerAcceptedAt: acceptedAt,
  });
});

router.post("/auth/setup", async (req, res) => {
  const parsed = SetupAuthBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input", details: parsed.error.issues });
    return;
  }
  const existing = await db.select().from(users).limit(1);
  if (existing.length > 0) {
    res.status(409).json({ error: "Setup already complete" });
    return;
  }
  const { username, password } = parsed.data;
  const passwordHash = await hashPassword(password);
  const { secret, otpauthUrl } = generateTotpSecret(username);
  const recoveryCodes = generateRecoveryCodes();

  const [user] = await db
    .insert(users)
    .values({ username, passwordHash, totpSecret: secret, recoveryCodes })
    .returning();

  const sid = newSessionId();
  await db
    .insert(sessions)
    .values({ id: sid, userId: user.id, expiresAt: new Date(Date.now() + SESSION_DAYS * 86400_000) });
  res.cookie(COOKIE_NAME, sid, cookieOpts());

  res.json({ totpSecret: secret, otpauthUrl, recoveryCodes });
});

router.post("/auth/login", async (req, res) => {
  const parsed = LoginBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input" });
    return;
  }
  const { username, password, totpCode } = parsed.data;
  const [user] = await db.select().from(users).where(eq(users.username, username)).limit(1);
  if (!user) {
    res.status(401).json({ error: "Invalid credentials" });
    return;
  }
  if (user.failedAttempts >= 10) {
    res.status(429).json({ error: "Too many failed attempts. Restart the server to reset." });
    return;
  }
  const pwOk = await verifyPassword(user.passwordHash, password);
  const totpOk = pwOk && verifyTotp(user.totpSecret, totpCode);
  if (!pwOk || !totpOk) {
    await db.update(users).set({ failedAttempts: user.failedAttempts + 1 }).where(eq(users.id, user.id));
    res.status(401).json({ error: "Invalid credentials" });
    return;
  }
  await db
    .update(users)
    .set({ failedAttempts: 0, lastLoginAt: new Date() })
    .where(eq(users.id, user.id));

  const sid = newSessionId();
  await db
    .insert(sessions)
    .values({ id: sid, userId: user.id, expiresAt: new Date(Date.now() + SESSION_DAYS * 86400_000) });
  res.cookie(COOKIE_NAME, sid, cookieOpts());
  res.json({ username: user.username });
});

router.post("/auth/logout", async (req, res) => {
  if (req.sessionId) {
    await db.delete(sessions).where(eq(sessions.id, req.sessionId));
  }
  res.clearCookie(COOKIE_NAME, { path: "/" });
  res.status(204).end();
});

export default router;

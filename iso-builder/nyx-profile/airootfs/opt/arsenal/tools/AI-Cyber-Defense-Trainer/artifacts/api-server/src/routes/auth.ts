import { Router } from "express";
import { db, usersTable, hashPassword, verifyPassword } from "@workspace/db";
import { eq } from "drizzle-orm";
import jwt from "jsonwebtoken";
import { logger } from "../lib/logger";

const router = Router();

const JWT_SECRET = process.env.SESSION_SECRET ?? "redforge-dev-secret";

router.post("/auth/login", async (req, res) => {
  const { username, password } = req.body as { username?: string; password?: string };
  if (!username || !password) {
    res.status(400).json({ error: "Username and password required" });
    return;
  }

  try {
    const [user] = await db.select().from(usersTable).where(eq(usersTable.username, username));
    if (!user) {
      res.status(401).json({ error: "Invalid credentials" });
      return;
    }
    if (!verifyPassword(password, user.passwordHash)) {
      res.status(401).json({ error: "Invalid credentials" });
      return;
    }
    const token = jwt.sign({ userId: user.id, username: user.username }, JWT_SECRET, { expiresIn: "7d" });
    res.json({ token, username: user.username });
  } catch (err) {
    logger.error({ err }, "Login error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.post("/auth/setup", async (req, res) => {
  const { username, password } = req.body as { username?: string; password?: string };
  if (!username || !password) {
    res.status(400).json({ error: "Username and password required" });
    return;
  }

  try {
    const existing = await db.select().from(usersTable);
    if (existing.length > 0) {
      res.status(403).json({ error: "Setup already completed" });
      return;
    }
    const passwordHash = hashPassword(password);
    const [user] = await db.insert(usersTable).values({ username, passwordHash }).returning();
    const token = jwt.sign({ userId: user.id, username: user.username }, JWT_SECRET, { expiresIn: "7d" });
    res.status(201).json({ token, username: user.username });
  } catch (err) {
    logger.error({ err }, "Setup error");
    res.status(500).json({ error: "Internal server error" });
  }
});

router.get("/auth/me", async (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith("Bearer ")) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }
  const token = authHeader.slice(7);
  try {
    const payload = jwt.verify(token, JWT_SECRET) as { userId: number; username: string };
    res.json({ userId: payload.userId, username: payload.username });
  } catch {
    res.status(401).json({ error: "Invalid token" });
  }
});

router.get("/auth/status", async (_req, res) => {
  const users = await db.select().from(usersTable);
  res.json({ setupRequired: users.length === 0 });
});

export default router;

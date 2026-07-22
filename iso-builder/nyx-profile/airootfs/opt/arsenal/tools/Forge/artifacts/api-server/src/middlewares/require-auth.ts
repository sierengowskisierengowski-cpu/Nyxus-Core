import type { RequestHandler } from "express";
import { SESSION_COOKIE, verifySessionToken } from "../lib/auth";

// Gate every mutation/data route behind a valid session cookie. The auth
// routes themselves and the health check are mounted before this middleware
// so they stay reachable while logged out.
export const requireAuth: RequestHandler = (req, res, next) => {
  const token = req.cookies?.[SESSION_COOKIE] as string | undefined;
  const session = verifySessionToken(token);
  if (!session) {
    res.status(401).json({ error: "Authentication required" });
    return;
  }
  (req as typeof req & { user?: { username: string } }).user = {
    username: session.username,
  };
  next();
};

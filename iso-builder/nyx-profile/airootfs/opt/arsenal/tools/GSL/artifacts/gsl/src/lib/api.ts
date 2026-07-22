const BASE = "";
const TOKEN_KEY = "gsl_token";

// ── Token storage ─────────────────────────────────────────────────────────────
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

/** Fired when the backend rejects our token so the app can return to login. */
export class UnauthorizedError extends Error {
  constructor() {
    super("Unauthorized");
    this.name = "UnauthorizedError";
  }
}

function notifyUnauthorized() {
  clearToken();
  window.dispatchEvent(new Event("gsl:unauthorized"));
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
    ...options,
  });

  if (res.status === 401) {
    notifyUnauthorized();
    throw new UnauthorizedError();
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text}`);
  }
  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Build a WebSocket URL, appending the session token as a query param
 *  (browsers can't set Authorization headers on WS handshakes). */
export function wsUrl(path: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const token = getToken();
  const sep = path.includes("?") ? "&" : "?";
  const auth = token ? `${sep}token=${encodeURIComponent(token)}` : "";
  return `${protocol}//${window.location.host}${path}${auth}`;
}

// ── Auth API ──────────────────────────────────────────────────────────────────
export interface LoginResult {
  token: string;
  username: string;
  expiresAt: number;
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (res.status === 401) {
    throw new Error("Invalid username or password");
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "Login failed");
    throw new Error(`Login failed (${res.status}): ${text}`);
  }
  const data: LoginResult = await res.json();
  setToken(data.token);
  return data;
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/api/auth/logout", { method: "POST" });
  } catch {
    // best-effort; clear locally regardless
  }
  clearToken();
}

export async function checkAuth(): Promise<boolean> {
  if (!getToken()) return false;
  try {
    await apiFetch("/api/auth/status");
    return true;
  } catch {
    return false;
  }
}

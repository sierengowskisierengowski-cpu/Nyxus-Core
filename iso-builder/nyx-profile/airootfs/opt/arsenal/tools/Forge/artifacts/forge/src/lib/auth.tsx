import React from "react";

// Auth is intentionally hand-written (not generated from the OpenAPI spec)
// because it is cross-cutting infrastructure. It talks to the same-origin
// Express API, so the httpOnly session cookie is sent automatically.

export interface AuthUser {
  username: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

async function fetchMe(): Promise<AuthUser | null> {
  const res = await fetch("/api/auth/me", { credentials: "same-origin" });
  if (!res.ok) return null;
  return (await res.json()) as AuthUser;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [loading, setLoading] = React.useState(true);

  const refresh = React.useCallback(async () => {
    try {
      setUser(await fetchMe());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = React.useCallback(async (username: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const data = (await res.json().catch(() => null)) as { error?: string } | null;
      throw new Error(data?.error ?? "Login failed");
    }
    setUser((await res.json()) as AuthUser);
  }, []);

  const logout = React.useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
    setUser(null);
  }, []);

  const value = React.useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

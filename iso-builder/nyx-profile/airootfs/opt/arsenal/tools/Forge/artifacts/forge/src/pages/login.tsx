import React from "react";
import { useAuth } from "@/lib/auth";
import { Flame, Loader2 } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="flex h-screen w-full items-center justify-center"
      style={{ background: "#070710" }}
    >
      <div
        className="w-full max-w-sm rounded-xl p-8"
        style={{
          background: "linear-gradient(135deg, #0e0e18 0%, #090910 100%)",
          border: "1px solid #14141f",
          boxShadow: "0 0 40px rgba(249,115,22,0.06)",
        }}
      >
        <div className="flex items-center gap-2 mb-1">
          <div
            className="w-1.5 h-6 rounded-full"
            style={{ background: "#f97316", boxShadow: "0 0 8px rgba(249,115,22,0.6)" }}
          />
          <Flame className="w-5 h-5" style={{ color: "#f97316" }} />
          <span
            className="font-black tracking-widest uppercase text-xl"
            style={{ color: "#f97316", letterSpacing: "0.12em" }}
          >
            FORGE
          </span>
        </div>
        <p
          className="text-[10px] tracking-[0.3em] uppercase font-mono mb-7 ml-4"
          style={{ color: "#3a3a52" }}
        >
          Threat Research Command Center
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label
              className="block text-[10px] tracking-[0.2em] uppercase font-bold font-mono mb-1.5"
              style={{ color: "#64748b" }}
            >
              Username
            </label>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg text-sm font-mono outline-none"
              style={{ background: "#04040a", border: "1px solid #14141f", color: "#e2e8f0" }}
              autoFocus
            />
          </div>
          <div>
            <label
              className="block text-[10px] tracking-[0.2em] uppercase font-bold font-mono mb-1.5"
              style={{ color: "#64748b" }}
            >
              Password
            </label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg text-sm font-mono outline-none"
              style={{ background: "#04040a", border: "1px solid #14141f", color: "#e2e8f0" }}
            />
          </div>

          {error && (
            <div
              className="text-[11px] font-mono px-3 py-2 rounded-lg"
              style={{
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.25)",
                color: "#f87171",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting || !username || !password}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-[12px] font-black tracking-widest uppercase font-mono transition-all disabled:opacity-40"
            style={{ background: "#f97316", color: "white", border: "none" }}
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {submitting ? "Authenticating" : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}

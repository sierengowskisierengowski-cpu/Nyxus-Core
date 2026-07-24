import { useState } from "react";
import { Terminal, Lock, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/api";

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      onSuccess();
    } catch (err: any) {
      setError(err?.message ?? "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center bg-background text-foreground dark bg-grid px-4"
      style={{ background: "hsl(237 38% 3.5%)" }}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg p-8"
        style={{
          background: "hsl(235 30% 5.5%)",
          border: "1px solid hsl(263 55% 62% / 0.2)",
          boxShadow: "0 0 40px hsl(263 55% 62% / 0.08), 0 25px 60px rgba(0,0,0,0.8)",
        }}
      >
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-10 h-10 rounded flex items-center justify-center flex-shrink-0"
            style={{
              background: "linear-gradient(135deg, hsl(263 55% 62% / 0.2), hsl(192 100% 50% / 0.1))",
              border: "1px solid hsl(263 55% 62% / 0.3)",
              boxShadow: "0 0 12px hsl(263 55% 62% / 0.15)",
            }}
          >
            <Terminal className="h-5 w-5" style={{ color: "hsl(263 55% 72%)" }} />
          </div>
          <div>
            <div
              className="text-sm font-bold font-mono tracking-widest"
              style={{ color: "hsl(220 20% 95%)", letterSpacing: "0.15em" }}
            >
              GSL
            </div>
            <div className="text-[10px] font-mono opacity-40 tracking-wider">
              GOWSKINET SECURITY LAB
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="username" className="text-xs">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-xs">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              autoFocus
              className="font-mono text-sm"
            />
          </div>

          {error && (
            <div
              className="flex items-center gap-2 text-xs rounded-md px-3 py-2"
              style={{
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.2)",
                color: "#f87171",
              }}
            >
              <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
              {error}
            </div>
          )}

          <Button type="submit" className="w-full h-10 font-bold" disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <Lock className="mr-2 h-4 w-4" />
                Sign in
              </>
            )}
          </Button>
        </div>

        <p className="text-[10px] font-mono text-muted-foreground/60 mt-6 text-center leading-relaxed">
          Local / isolated-lab access only.
          <br />
          Credentials are configured in gsl-backend/.env
        </p>
      </form>
    </div>
  );
}

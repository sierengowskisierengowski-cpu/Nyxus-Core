import { useState } from "react";
import { Terminal, Lock, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin, useGetAuthStatus } from "@workspace/api-client-react";
import { setToken } from "@/lib/auth";

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const loginMutation = useLogin();
  const { data: status } = useGetAuthStatus({ query: { queryKey: ["getAuthStatus"] } });

  const configured = status?.configured !== false;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    loginMutation.mutate(
      { data: { password } },
      {
        onSuccess: (data) => {
          setToken(data.token);
          onSuccess();
        },
        onError: (err: unknown) => {
          const msg = err instanceof Error ? err.message : "Login failed";
          setError(msg.includes("401") ? "Invalid password" : msg);
        },
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background p-4">
      <div className="max-w-md w-full bg-card border border-border p-8 rounded-md shadow-2xl">
        <div className="flex items-center gap-2 mb-8 justify-center">
          <Terminal className="text-primary" size={28} />
          <span className="font-mono font-bold text-2xl text-primary">CIPHER</span>
        </div>

        {!configured ? (
          <div className="text-sm text-muted-foreground font-mono space-y-3 leading-relaxed">
            <p className="text-destructive font-semibold">Authentication is not configured.</p>
            <p>
              Set an owner password in the server environment before using CIPHER:
            </p>
            <pre className="bg-background border border-border/50 rounded p-3 text-xs overflow-x-auto">
              export CIPHER_PASSWORD='your-strong-password'
            </pre>
            <p>Then restart the API server and reload this page.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label className="font-mono text-xs text-muted-foreground uppercase flex items-center gap-2">
                <Lock className="w-3 h-3" /> Owner Password
              </Label>
              <Input
                type="password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-background/50 font-mono"
                placeholder="Enter password"
              />
            </div>
            {error && <div className="text-destructive text-xs font-mono">{error}</div>}
            <Button
              type="submit"
              disabled={!password || loginMutation.isPending}
              className="w-full font-mono uppercase tracking-widest gap-2"
            >
              {loginMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Unlock CIPHER
            </Button>
          </form>
        )}
        <div className="text-[10px] text-muted-foreground text-center mt-8 uppercase tracking-widest">
          Authorized Local Use Only
        </div>
      </div>
    </div>
  );
}

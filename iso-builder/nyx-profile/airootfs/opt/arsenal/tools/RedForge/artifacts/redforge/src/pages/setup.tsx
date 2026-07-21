import { useState } from "react";
import { useSetupAuth } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Terminal } from "lucide-react";

export default function Setup() {
  useDocumentTitle("System Initialization");
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const setupMutation = useSetupAuth();
  
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [result, setResult] = useState<{ totpSecret: string; otpauthUrl: string; recoveryCodes?: string[] } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setupMutation.mutate({ data: { username, password } }, {
      onSuccess: (data) => {
        setResult(data);
        toast({ title: "Setup initialized", description: "Save your TOTP details." });
      },
      onError: (err: any) => {
        toast({ title: "Setup failed", description: err.message || "Unknown error", variant: "destructive" });
      }
    });
  };

  const handleComplete = () => {
    setLocation("/login");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 relative">
      <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      
      <div className="w-full max-w-md border border-border bg-card p-6 shadow-2xl relative">
        <div className="flex items-center gap-2 mb-8 border-b border-border pb-4">
          <Terminal className="w-5 h-5 text-primary" />
          <h1 className="font-bold tracking-widest text-primary">REDFORGE_INIT</h1>
        </div>

        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Admin Username</Label>
              <Input 
                id="username" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                required 
                className="font-mono bg-background"
                autoFocus
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Master Password</Label>
              <Input 
                id="password" 
                type="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
                minLength={8}
                className="font-mono bg-background"
              />
            </div>

            <Button type="submit" disabled={setupMutation.isPending} className="w-full font-mono uppercase tracking-widest">
              {setupMutation.isPending ? "Initializing..." : "Initialize System"}
            </Button>
          </form>
        ) : (
          <div className="space-y-6">
            <div className="p-4 border border-secondary/30 bg-secondary/5 rounded-md space-y-4">
              <h2 className="text-sm font-bold text-secondary uppercase tracking-widest">MFA Enrollment Required</h2>
              
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">TOTP Secret</Label>
                <code className="block p-2 bg-background border border-border text-xs break-all text-secondary">
                  {result.totpSecret}
                </code>
              </div>

              {result.recoveryCodes && (
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">Recovery Codes</Label>
                  <div className="p-2 bg-background border border-border text-xs font-mono grid grid-cols-2 gap-2 text-destructive">
                    {result.recoveryCodes.map((code, i) => (
                      <span key={i}>{code}</span>
                    ))}
                  </div>
                  <p className="text-[10px] text-destructive mt-1">Save these securely. They will not be shown again.</p>
                </div>
              )}
            </div>

            <Button onClick={handleComplete} className="w-full font-mono uppercase tracking-widest bg-secondary text-secondary-foreground hover:bg-secondary/90">
              Proceed to Login
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

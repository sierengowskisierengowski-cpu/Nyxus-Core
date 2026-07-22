import { useState } from "react";
import { useLogin } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Terminal, ShieldAlert } from "lucide-react";

export default function Login() {
  useDocumentTitle("Authentication");
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const loginMutation = useLogin();
  
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ data: { username, password, totpCode } }, {
      onSuccess: () => {
        toast({ title: "Access granted", description: "Welcome to REDFORGE." });
        setLocation("/"); // auth gate will route to disclaimer if needed
      },
      onError: (err: any) => {
        toast({ title: "Access denied", description: "Invalid credentials.", variant: "destructive" });
      }
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 relative">
      <div className="absolute inset-0 pointer-events-none opacity-5 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
      
      <div className="w-full max-w-sm border border-border bg-card p-6 shadow-2xl relative">
        <div className="flex flex-col items-center gap-4 mb-8 pb-6 border-b border-border text-center">
          <div className="w-12 h-12 bg-primary/10 border border-primary flex items-center justify-center rounded-sm">
            <ShieldAlert className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="font-bold tracking-widest text-primary text-xl">REDFORGE</h1>
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground mt-1">Authorized Access Only</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Operator ID</Label>
            <Input 
              id="username" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
              className="font-mono bg-background border-border h-9 rounded-sm"
              autoFocus
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password" className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Passphrase</Label>
            <Input 
              id="password" 
              type="password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
              className="font-mono bg-background border-border h-9 rounded-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="totpCode" className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Authenticator Code</Label>
            <Input 
              id="totpCode" 
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={6}
              value={totpCode} 
              onChange={(e) => setTotpCode(e.target.value)} 
              required 
              className="font-mono bg-background border-border h-9 rounded-sm tracking-[0.5em] text-center"
              placeholder="------"
            />
          </div>

          <Button type="submit" disabled={loginMutation.isPending} className="w-full font-mono uppercase tracking-widest h-10 mt-6 rounded-sm">
            {loginMutation.isPending ? "Authenticating..." : "Establish Connection"}
          </Button>
        </form>
      </div>
    </div>
  );
}

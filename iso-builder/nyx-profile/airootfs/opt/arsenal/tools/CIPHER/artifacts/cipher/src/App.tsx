import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout } from "@/components/layout";
import { useEffect, useState } from "react";
import { useAcceptDisclaimer } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

import NotFound from "@/pages/not-found";
import Login from "@/pages/login";
import { getToken } from "@/lib/auth";

import Dashboard from "@/pages/dashboard";
import Hashes from "@/pages/hashes";
import Attack from "@/pages/attack";
import Monitor from "@/pages/monitor";
import Results from "@/pages/results";
import Wordlists from "@/pages/wordlists";
import Rules from "@/pages/rules";
import Database from "@/pages/database";
import Analyzer from "@/pages/analyzer";
import Notes from "@/pages/notes";
import Settings from "@/pages/settings";

const queryClient = new QueryClient();

function DisclaimerModal({ onAccept }: { onAccept: () => void }) {
  const [checked, setChecked] = useState(false);
  const acceptMutation = useAcceptDisclaimer();

  const handleAccept = () => {
    acceptMutation.mutate(undefined, {
      onSuccess: () => {
        localStorage.setItem("cipher_disclaimer_accepted", "true");
        onAccept();
      }
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/95 backdrop-blur-md p-4">
      <div className="max-w-2xl w-full bg-card border border-border p-8 rounded-md shadow-2xl">
        <h2 className="text-2xl font-bold text-destructive mb-6 flex items-center gap-2">
          <span className="bg-destructive/20 text-destructive p-1 rounded font-mono">LEGAL DISCLAIMER</span>
        </h2>
        <div className="space-y-4 text-foreground/80 mb-8 leading-relaxed text-sm">
          <p>
            GowskiNet CIPHER is a personal password security research and analysis tool intended exclusively for authorized security testing, password policy research, and defensive security education on systems and accounts you own or have explicit written authorization to test.
          </p>
          <p>
            Using password cracking tools against accounts, systems, or hashes you do not own or are not explicitly authorized to test is illegal under the Computer Fraud and Abuse Act, the Stored Communications Act, and equivalent laws worldwide. You are solely responsible for ensuring all use is lawful and authorized.
          </p>
          <p className="font-semibold text-foreground">
            By using CIPHER you confirm that all hashes and credentials submitted are from systems you own or are explicitly authorized to test.
          </p>
        </div>
        
        <div className="flex items-start space-x-3 mb-8 bg-background p-4 rounded-sm border border-border">
          <Checkbox 
            id="terms" 
            checked={checked} 
            onCheckedChange={(c) => setChecked(c as boolean)} 
            className="mt-1 border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground"
          />
          <label htmlFor="terms" className="text-sm font-medium leading-none cursor-pointer text-muted-foreground select-none">
            I confirm all hashes submitted are from systems I own or am explicitly authorized to test
          </label>
        </div>

        <div className="flex justify-end">
          <Button 
            disabled={!checked || acceptMutation.isPending} 
            onClick={handleAccept}
            className="w-full sm:w-auto font-mono uppercase tracking-wider"
          >
            Access CIPHER
          </Button>
        </div>
      </div>
    </div>
  );
}

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/hashes" component={Hashes} />
        <Route path="/attack" component={Attack} />
        <Route path="/monitor" component={Monitor} />
        <Route path="/results" component={Results} />
        <Route path="/wordlists" component={Wordlists} />
        <Route path="/rules" component={Rules} />
        <Route path="/database" component={Database} />
        <Route path="/analyzer" component={Analyzer} />
        <Route path="/notes" component={Notes} />
        <Route path="/settings" component={Settings} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  const [authed, setAuthed] = useState<boolean>(() => !!getToken());
  const [disclaimerAccepted, setDisclaimerAccepted] = useState<boolean | null>(null);

  useEffect(() => {
    document.documentElement.classList.add("dark");
    const isAccepted = localStorage.getItem("cipher_disclaimer_accepted") === "true";
    setDisclaimerAccepted(isAccepted);
  }, []);

  if (disclaimerAccepted === null) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        {!authed ? (
          <Login onSuccess={() => setAuthed(true)} />
        ) : !disclaimerAccepted ? (
          <DisclaimerModal onAccept={() => setDisclaimerAccepted(true)} />
        ) : (
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
            <Router />
          </WouterRouter>
        )}
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

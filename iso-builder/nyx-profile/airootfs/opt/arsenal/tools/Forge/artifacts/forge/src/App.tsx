import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { Layout } from "@/components/layout";
import { AuthProvider, useAuth } from "@/lib/auth";
import Login from "@/pages/login";

import Dashboard from "@/pages/dashboard";
import InputLab from "@/pages/input-lab";
import MutationLab from "@/pages/mutation-lab";
import ThreatAnalysis from "@/pages/threat-analysis";
import ThreatLibrary from "@/pages/threat-library";
import DetectionRules from "@/pages/detection-rules";
import Notes from "@/pages/notes";
import KnowledgeBase from "@/pages/knowledge-base";
import Redforge from "@/pages/redforge";
import Meli from "@/pages/meli";
import Disclosure from "@/pages/disclosure";
import Settings from "@/pages/settings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/input-lab" component={InputLab} />
        <Route path="/mutation-lab" component={MutationLab} />
        <Route path="/threat-analysis/:id" component={ThreatAnalysis} />
        <Route path="/threat-library" component={ThreatLibrary} />
        <Route path="/detection-rules" component={DetectionRules} />
        <Route path="/notes" component={Notes} />
        <Route path="/knowledge-base" component={KnowledgeBase} />
        <Route path="/redforge" component={Redforge} />
        <Route path="/meli" component={Meli} />
        <Route path="/disclosure" component={Disclosure} />
        <Route path="/settings" component={Settings} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function Gate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center" style={{ background: "#070710" }}>
        <span className="text-[11px] tracking-[0.3em] uppercase font-mono" style={{ color: "#3a3a52" }}>
          Loading…
        </span>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
      <Router />
    </WouterRouter>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AuthProvider>
          <Gate />
        </AuthProvider>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

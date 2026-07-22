import { useEffect, useState } from "react";
import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import { Layout } from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Tools from "@/pages/Tools";
import History from "@/pages/History";
import Notes from "@/pages/Notes";
import Learn from "@/pages/Learn";
import Findings from "@/pages/Findings";
import Library from "@/pages/Library";
import Login from "@/pages/Login";
import { checkAuth } from "@/lib/api";

const queryClient = new QueryClient();

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/tools" component={Tools} />
        <Route path="/history" component={History} />
        <Route path="/notes" component={Notes} />
        <Route path="/findings" component={Findings} />
        <Route path="/library" component={Library} />
        <Route path="/learn" component={Learn} />
        <Route path="/learn/:toolId" component={Learn} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

type AuthState = "loading" | "authed" | "anon";

function App() {
  const [auth, setAuth] = useState<AuthState>("loading");

  useEffect(() => {
    let active = true;
    checkAuth().then((ok) => {
      if (active) setAuth(ok ? "authed" : "anon");
    });
    const onUnauthorized = () => setAuth("anon");
    window.addEventListener("gsl:unauthorized", onUnauthorized);
    return () => {
      active = false;
      window.removeEventListener("gsl:unauthorized", onUnauthorized);
    };
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        {auth === "loading" ? (
          <div className="min-h-screen flex items-center justify-center bg-background text-foreground dark">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : auth === "anon" ? (
          <Login onSuccess={() => setAuth("authed")} />
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

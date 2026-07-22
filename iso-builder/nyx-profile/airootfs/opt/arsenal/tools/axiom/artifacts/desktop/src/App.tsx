import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/layout/AppLayout";
import NotFound from "@/pages/not-found";
import Chat from "@/pages/chat";
import Scheduler from "@/pages/scheduler";
import Knowledge from "@/pages/knowledge";
import Activity from "@/pages/activity";
import QuickActions from "@/pages/quick-actions";
import Files from "@/pages/files";
import Settings from "@/pages/settings";
import Stats from "@/pages/stats";
import Onboarding from "@/pages/onboarding";
import { useGetSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";
import { useEffect } from "react";
import { electron } from "@/lib/electron-api";

const queryClient = new QueryClient();

function RouteGuard() {
  const [location, setLocation] = useLocation();
  const { data: settings, isLoading } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });

  // Handle navigation events dispatched from Electron tray context menu
  useEffect(() => {
    const unsub = electron.onNavigate((path) => {
      setLocation(path);
    });
    return unsub;
  }, [setLocation]);

  useEffect(() => {
    if (!isLoading && settings && !settings.onboardingCompleted && location !== "/onboarding") {
      setLocation("/onboarding");
    } else if (!isLoading && settings && settings.onboardingCompleted && location === "/onboarding") {
      setLocation("/chat");
    } else if (location === "/") {
      setLocation("/chat");
    }
  }, [location, setLocation, settings, isLoading]);

  if (isLoading) {
    return <div className="flex h-full items-center justify-center text-primary animate-pulse">Loading System...</div>;
  }

  return (
    <Switch>
      <Route path="/onboarding" component={Onboarding} />
      <Route path="/chat" component={Chat} />
      <Route path="/scheduler" component={Scheduler} />
      <Route path="/knowledge" component={Knowledge} />
      <Route path="/activity" component={Activity} />
      <Route path="/quick-actions" component={QuickActions} />
      <Route path="/files" component={Files} />
      <Route path="/settings" component={Settings} />
      <Route path="/stats" component={Stats} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <AppLayout>
            <RouteGuard />
          </AppLayout>
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Layout } from "@/components/layout";
import { AuthGate } from "@/components/auth-gate";

import Setup from "@/pages/setup";
import Login from "@/pages/login";
import Disclaimer from "@/pages/disclaimer";
import Dashboard from "@/pages/dashboard";
import Network from "@/pages/network";
import Settings from "@/pages/settings";
import Scenarios from "@/pages/scenarios";
import ScenarioDetail from "@/pages/scenario-detail";
import Missions from "@/pages/missions";
import MissionWorkspace from "@/pages/mission-workspace";
import Notes from "@/pages/notes";
import Notebooks from "@/pages/notebooks";
import Scoreboard from "@/pages/scoreboard";

import KbIndex from "@/pages/kb/index";
import MitreTechniques from "@/pages/kb/mitre";
import MitreTechniqueDetail from "@/pages/kb/mitre-detail";
import LolbasList from "@/pages/kb/lolbas";
import LolbasDetail from "@/pages/kb/lolbas-detail";
import GtfobinsList from "@/pages/kb/gtfobins";
import GtfobinsDetail from "@/pages/kb/gtfobins-detail";
import AtomicTestsList from "@/pages/kb/atomic";
import AtomicTestDetail from "@/pages/kb/atomic-detail";
import CvesList from "@/pages/kb/cves";
import CveDetail from "@/pages/kb/cve-detail";
import MalwareList from "@/pages/kb/malware";
import MalwareDetail from "@/pages/kb/malware-detail";

import NotFound from "@/pages/not-found";

const queryClient = new QueryClient();

function Router() {
  return (
    <Switch>
      <Route path="/setup" component={Setup} />
      <Route path="/login" component={Login} />
      <Route path="/disclaimer" component={Disclaimer} />
      
      <Route path="/">
        <Layout><Dashboard /></Layout>
      </Route>
      
      <Route path="/scenarios">
        <Layout><Scenarios /></Layout>
      </Route>
      <Route path="/scenarios/:id">
        <Layout><ScenarioDetail /></Layout>
      </Route>
      
      <Route path="/missions">
        <Layout><Missions /></Layout>
      </Route>
      <Route path="/missions/:id">
        <Layout><MissionWorkspace /></Layout>
      </Route>
      
      <Route path="/notes">
        <Layout><Notes /></Layout>
      </Route>
      <Route path="/notebooks">
        <Layout><Notebooks /></Layout>
      </Route>
      
      <Route path="/kb">
        <Layout><KbIndex /></Layout>
      </Route>
      <Route path="/kb/mitre">
        <Layout><MitreTechniques /></Layout>
      </Route>
      <Route path="/kb/mitre/:id">
        <Layout><MitreTechniqueDetail /></Layout>
      </Route>
      <Route path="/kb/lolbas">
        <Layout><LolbasList /></Layout>
      </Route>
      <Route path="/kb/lolbas/:name">
        <Layout><LolbasDetail /></Layout>
      </Route>
      <Route path="/kb/gtfobins">
        <Layout><GtfobinsList /></Layout>
      </Route>
      <Route path="/kb/gtfobins/:name">
        <Layout><GtfobinsDetail /></Layout>
      </Route>
      <Route path="/kb/atomic">
        <Layout><AtomicTestsList /></Layout>
      </Route>
      <Route path="/kb/atomic/:id">
        <Layout><AtomicTestDetail /></Layout>
      </Route>
      <Route path="/kb/cves">
        <Layout><CvesList /></Layout>
      </Route>
      <Route path="/kb/cves/:id">
        <Layout><CveDetail /></Layout>
      </Route>
      <Route path="/kb/malware">
        <Layout><MalwareList /></Layout>
      </Route>
      <Route path="/kb/malware/:name">
        <Layout><MalwareDetail /></Layout>
      </Route>
      
      <Route path="/scoreboard">
        <Layout><Scoreboard /></Layout>
      </Route>
      <Route path="/network">
        <Layout><Network /></Layout>
      </Route>
      <Route path="/settings">
        <Layout><Settings /></Layout>
      </Route>

      <Route>
        <Layout><NotFound /></Layout>
      </Route>
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Settings as SettingsIcon, Cpu, Cloud, Keyboard, FolderOpen, Bell, Monitor, Loader2, CheckCircle2, AlertTriangle, Trash2, Plus, Shield, Info, Zap } from "lucide-react";
import { electron, isElectron } from "@/lib/electron-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import {
  useGetSettings, getGetSettingsQueryKey,
  useUpdateSettings,
  useGetAiStatus, getGetAiStatusQueryKey,
  useListAiModels, getListAiModelsQueryKey,
  usePullAiModel, useDeleteAiModel,
  useGetModelPullStatus, getGetModelPullStatusQueryKey,
  useGetAllowedPaths, getGetAllowedPathsQueryKey,
  useAddAllowedPath, useRemoveAllowedPath,
} from "@workspace/api-client-react";
import type { AppSettingsUpdate } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";

const SECTION_COLORS: Record<string, string> = {
  ai:         "text-indigo-400",
  paths:      "text-orange-400",
  hotkey:     "text-violet-400",
  appearance: "text-sky-400",
  window:     "text-cyan-400",
  notifs:     "text-emerald-400",
  about:      "text-zinc-400",
};

function Section({ id, title, icon: Icon, children }: {
  id: string;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-xl p-5 border border-white/[0.06] space-y-4"
    >
      <div className="flex items-center gap-2">
        <Icon className={cn("w-4 h-4", SECTION_COLORS[id] ?? "text-muted-foreground")} />
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      <Separator className="bg-white/[0.07]" />
      <div className="space-y-4">{children}</div>
    </motion.div>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground/90">{label}</p>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export default function Settings() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [, setLocation] = useLocation();
  const [pullModelName, setPullModelName] = useState("");
  const [activePulling, setActivePulling] = useState<string | null>(null);
  const [newPathInput, setNewPathInput] = useState("");

  const { data: settings, isLoading } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });
  const { data: aiStatus } = useGetAiStatus({ query: { queryKey: getGetAiStatusQueryKey(), refetchInterval: 10000 } });
  const { data: models = [] } = useListAiModels({ query: { queryKey: getListAiModelsQueryKey() } });

  const { data: pullStatus } = useGetModelPullStatus(activePulling ?? "", {
    query: {
      queryKey: getGetModelPullStatusQueryKey(activePulling ?? ""),
      enabled: !!activePulling,
      refetchInterval: (query) => {
        const data = query.state.data;
        if (!data) return 1500;
        if (data.status === "pulling") return 1500;
        return false;
      },
    },
  });

  useEffect(() => {
    if (!pullStatus || !activePulling) return;
    if (pullStatus.status === "complete") {
      toast({ title: `Model "${activePulling}" ready`, description: "Model downloaded successfully" });
      setActivePulling(null);
      queryClient.invalidateQueries({ queryKey: getListAiModelsQueryKey() });
    } else if (pullStatus.status === "error") {
      toast({ title: "Pull failed", description: pullStatus.error || "Unknown error", variant: "destructive" });
      setActivePulling(null);
    }
  }, [pullStatus, activePulling, toast, queryClient]);

  const updateSettings = useUpdateSettings();
  const pullModel = usePullAiModel();
  const deleteModel = useDeleteAiModel();

  const update = useCallback((patch: AppSettingsUpdate) => {
    updateSettings.mutate({ data: patch }, {
      onSuccess: async () => {
        queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
        if (isElectron) {
          if (patch.hotkey !== undefined) {
            const result = await electron.updateHotkey(patch.hotkey);
            if (!result.success) toast({ title: "Hotkey could not be registered", description: "Try a different key combination", variant: "destructive" });
          }
          if (patch.launchAtLogin !== undefined) await electron.setAutoLaunch(patch.launchAtLogin);
          if (patch.dismissOnBlur !== undefined) await electron.setDismissOnBlur(patch.dismissOnBlur);
          if (patch.startMinimized !== undefined) await electron.setStartMinimized(patch.startMinimized);
        }
      },
      onError: () => toast({ title: "Settings update failed", variant: "destructive" }),
    });
  }, [updateSettings, queryClient, toast]);

  const handlePullModel = () => {
    if (!pullModelName.trim()) return;
    const name = pullModelName.trim();
    pullModel.mutate({ data: { name } }, {
      onSuccess: () => {
        toast({ title: `Pulling ${name}…`, description: "Downloading in background — progress shown below" });
        setPullModelName("");
        setActivePulling(name);
      },
      onError: (e: unknown) => {
        const msg = e instanceof Error ? e.message : "Check that Ollama is running";
        toast({ title: "Pull failed", description: msg, variant: "destructive" });
      },
    });
  };

  const handleDeleteModel = (name: string) => {
    deleteModel.mutate({ name }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListAiModelsQueryKey() });
        toast({ title: `Model ${name} removed` });
      },
    });
  };

  const handleRerunOnboarding = () => {
    update({ onboardingCompleted: false });
    setTimeout(() => setLocation("/onboarding"), 100);
  };

  const { data: allowedPaths = [] } = useGetAllowedPaths({ query: { queryKey: getGetAllowedPathsQueryKey() } });
  const addPath = useAddAllowedPath();
  const removePath = useRemoveAllowedPath();

  const handleAddPath = async (overridePath?: string) => {
    let pathToAdd = overridePath ?? newPathInput.trim();
    if (isElectron && !overridePath) {
      const result = await electron.openDirectoryDialog();
      if (!result) return;
      pathToAdd = result;
    }
    if (!pathToAdd) return;
    addPath.mutate({ data: { path: pathToAdd } }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() });
        setNewPathInput("");
        toast({ title: "Path added" });
      },
      onError: () => toast({ title: "Failed to add path", variant: "destructive" }),
    });
  };

  const handleBrowsePath = async () => {
    if (!isElectron) return;
    const result = await electron.openDirectoryDialog();
    if (result) setNewPathInput(result);
  };

  const handleRemovePath = (id: number) => {
    removePath.mutate({ id }, {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetAllowedPathsQueryKey() });
        toast({ title: "Path removed" });
      },
      onError: () => toast({ title: "Failed to remove path", variant: "destructive" }),
    });
  };

  const localModels = models.filter(m => m.type === "local");
  const cloudModels = models.filter(m => m.type === "cloud");

  if (isLoading || !settings) {
    return (
      <div className="p-6 space-y-4">
        {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-48 rounded-xl bg-white/5" />)}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-white/[0.07]">
        <h1 className="text-base font-semibold flex items-center gap-2">
          <SettingsIcon className="w-4 h-4 text-zinc-400" />
          Settings
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">All changes apply immediately</p>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-4">

        {/* AI Provider */}
        <Section id="ai" title="AI Provider" icon={Cpu}>
          <SettingRow label="Mode" description="Switch between local GPU (Ollama) and cloud AI">
            <div className="flex gap-2">
              <Button
                size="sm"
                className={cn("h-7 text-xs", settings.aiMode === "local" ? "btn-action" : "glass-button")}
                onClick={() => update({ aiMode: "local" })}
                data-testid="button-ai-mode-local"
              >
                <Cpu className="w-3 h-3 mr-1" />Local GPU
              </Button>
              <Button
                size="sm"
                className={cn("h-7 text-xs", settings.aiMode === "cloud" ? "btn-sky" : "glass-button")}
                onClick={() => update({ aiMode: "cloud" })}
                data-testid="button-ai-mode-cloud"
              >
                <Cloud className="w-3 h-3 mr-1" />Cloud
              </Button>
            </div>
          </SettingRow>

          {settings.aiMode === "local" && (
            <div className={cn(
              "rounded-lg p-3 border text-xs",
              aiStatus?.ollamaAvailable
                ? "bg-emerald-500/8 border-emerald-500/25"
                : "bg-amber-500/8 border-amber-500/25"
            )}>
              <div className="flex items-center gap-2">
                {aiStatus?.ollamaAvailable
                  ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  : <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                <span className={cn("flex-1", aiStatus?.ollamaAvailable ? "text-emerald-300" : "text-amber-300")}>
                  {aiStatus?.ollamaAvailable
                    ? `Ollama connected · v${aiStatus.ollamaVersion || "unknown"}`
                    : "Ollama not detected — install from ollama.ai and run `ollama serve`"}
                </span>
                {!aiStatus?.ollamaAvailable && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 text-[10px] px-2 border border-amber-500/30 text-amber-300 hover:bg-amber-500/10 shrink-0"
                    onClick={() => update({ aiMode: "cloud" })}
                    data-testid="button-fallback-to-cloud"
                  >
                    <Cloud className="w-2.5 h-2.5 mr-1" />Use Cloud
                  </Button>
                )}
              </div>
            </div>
          )}

          {settings.aiMode === "local" && (
            <>
              <SettingRow label="Ollama URL">
                <Input value={settings.ollamaBaseUrl} onChange={e => update({ ollamaBaseUrl: e.target.value })} className="glass-input h-7 text-xs w-52 font-mono" data-testid="input-ollama-url" />
              </SettingRow>
              <SettingRow label="Active Model">
                <Select value={settings.aiModel} onValueChange={v => update({ aiModel: v })}>
                  <SelectTrigger className="glass-input h-7 text-xs w-44" data-testid="select-local-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="glass-panel border-white/[0.08]">
                    {localModels.length === 0 && <SelectItem value={settings.aiModel} className="text-xs">{settings.aiModel}</SelectItem>}
                    {localModels.map(m => <SelectItem key={m.name} value={m.name} className="text-xs">{m.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </SettingRow>

              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Installed Models</p>
                {localModels.length === 0 ? (
                  <p className="text-xs text-muted-foreground/50 italic">No local models — pull one below</p>
                ) : (
                  <div className="space-y-1.5">
                    {localModels.map(m => (
                      <div key={m.name} className="flex items-center justify-between gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/[0.05]">
                        <div>
                          <span className="text-xs font-medium">{m.name}</span>
                          {m.size && <span className="text-[10px] text-muted-foreground ml-2">{m.size}</span>}
                        </div>
                        <button
                          className="w-5 h-5 flex items-center justify-center rounded hover:bg-destructive/15 transition-colors"
                          onClick={() => handleDeleteModel(m.name)}
                          data-testid={`button-delete-model-${m.name}`}
                        >
                          <Trash2 className="w-3 h-3 text-muted-foreground hover:text-destructive" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                {activePulling && pullStatus && (
                  <div className="rounded-lg border border-indigo-500/25 bg-indigo-500/8 p-2.5 space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="text-indigo-300 font-medium flex items-center gap-1">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" />Pulling {activePulling}…
                      </span>
                      <span className="text-muted-foreground">{pullStatus.progress ?? 0}%</span>
                    </div>
                    <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                      <div className="h-full rounded-full bg-indigo-400 transition-all duration-500" style={{ width: `${pullStatus.progress ?? 0}%` }} />
                    </div>
                    {pullStatus.total != null && pullStatus.total > 0 && (
                      <p className="text-[10px] text-muted-foreground/60">
                        {((pullStatus.completed ?? 0) / 1e9).toFixed(1)} / {(pullStatus.total / 1e9).toFixed(1)} GB
                      </p>
                    )}
                  </div>
                )}
                <div className="flex gap-2 mt-2">
                  <Input
                    value={pullModelName}
                    onChange={e => setPullModelName(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handlePullModel()}
                    placeholder="llama3, mistral, phi3..."
                    className="glass-input h-7 text-xs flex-1"
                    data-testid="input-pull-model"
                  />
                  <Button
                    size="sm"
                    className="h-7 text-xs glass-button"
                    onClick={handlePullModel}
                    disabled={!pullModelName.trim() || pullModel.isPending || !!activePulling}
                    data-testid="button-pull-model"
                  >
                    {pullModel.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : "Pull"}
                  </Button>
                </div>
              </div>
            </>
          )}

          {settings.aiMode === "cloud" && (
            <>
              <SettingRow label="API Key">
                <Input type="password" value={settings.cloudApiKey || ""} onChange={e => update({ cloudApiKey: e.target.value })} placeholder="sk-..." className="glass-input h-7 text-xs w-52 font-mono" data-testid="input-api-key" />
              </SettingRow>
              <SettingRow label="Base URL" description="Override for custom OpenAI-compatible endpoints">
                <Input value={settings.cloudBaseUrl || ""} onChange={e => update({ cloudBaseUrl: e.target.value })} placeholder="https://api.openai.com/v1" className="glass-input h-7 text-xs w-52 font-mono" data-testid="input-base-url" />
              </SettingRow>
              <SettingRow label="Model">
                <Select value={settings.aiModel} onValueChange={v => update({ aiModel: v })}>
                  <SelectTrigger className="glass-input h-7 text-xs w-44" data-testid="select-cloud-model">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="glass-panel border-white/[0.08]">
                    {cloudModels.map(m => (
                      <SelectItem key={m.name} value={m.name} className="text-xs">
                        {m.name}
                        {m.description && <span className="text-muted-foreground ml-1">· {m.description}</span>}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SettingRow>
            </>
          )}
        </Section>

        {/* Allowed Paths */}
        <Section id="paths" title="Allowed Paths" icon={Shield}>
          <p className="text-xs text-muted-foreground">AXIOM will only read and write within these directories.</p>
          <div className="space-y-2">
            {allowedPaths.length === 0 && <p className="text-xs text-muted-foreground/60 italic">No paths added yet.</p>}
            {allowedPaths.map((entry) => (
              <div key={entry.id} className="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2 border border-white/[0.07]">
                <FolderOpen className="w-3.5 h-3.5 text-orange-400 shrink-0" />
                <span className="text-xs font-mono flex-1 truncate">{entry.path}</span>
                <Button size="icon" variant="ghost" className="w-6 h-6 hover:bg-destructive/15 shrink-0" onClick={() => handleRemovePath(entry.id)}>
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              value={newPathInput}
              onChange={e => setNewPathInput(e.target.value)}
              placeholder="/Users/me/Documents"
              className="glass-input h-8 text-xs font-mono flex-1"
              onKeyDown={e => e.key === "Enter" && handleAddPath()}
            />
            {isElectron && (
              <Button size="icon" variant="ghost" className="h-8 w-8 glass-button" onClick={handleBrowsePath} title="Browse for folder">
                <FolderOpen className="w-3.5 h-3.5" />
              </Button>
            )}
            <Button
              size="sm"
              className="h-8 text-xs btn-action"
              onClick={() => handleAddPath()}
              disabled={addPath.isPending || (!isElectron && !newPathInput.trim())}
            >
              {addPath.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3 mr-1" />}
              Add
            </Button>
          </div>
        </Section>

        {/* Hotkey */}
        <Section id="hotkey" title="Global Hotkey" icon={Keyboard}>
          <SettingRow label="Activation Hotkey" description="Press this combination to open AXIOM from anywhere">
            <Input
              value={settings.hotkey}
              onChange={e => update({ hotkey: e.target.value })}
              placeholder="CommandOrControl+Shift+Space"
              className="glass-input h-7 text-xs w-56 font-mono"
              data-testid="input-hotkey"
            />
          </SettingRow>
        </Section>

        {/* Appearance */}
        <Section id="appearance" title="Appearance" icon={Monitor}>
          <SettingRow label="Theme">
            <Select value={settings.theme} onValueChange={v => update({ theme: v as "light" | "dark" | "system" })}>
              <SelectTrigger className="glass-input h-7 text-xs w-32" data-testid="select-theme">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="glass-panel border-white/[0.08]">
                <SelectItem value="dark" className="text-xs">Dark</SelectItem>
                <SelectItem value="light" className="text-xs">Light</SelectItem>
                <SelectItem value="system" className="text-xs">System</SelectItem>
              </SelectContent>
            </Select>
          </SettingRow>
        </Section>

        {/* Window behavior */}
        <Section id="window" title="Window Behavior" icon={Monitor}>
          <SettingRow label="Launch at Login">
            <Switch checked={!!settings.launchAtLogin} onCheckedChange={v => update({ launchAtLogin: v })} data-testid="switch-launch-at-login" />
          </SettingRow>
          <SettingRow label="Start Minimized">
            <Switch checked={!!settings.startMinimized} onCheckedChange={v => update({ startMinimized: v })} data-testid="switch-start-minimized" />
          </SettingRow>
          <SettingRow label="Dismiss on Focus Loss">
            <Switch checked={!!settings.dismissOnBlur} onCheckedChange={v => update({ dismissOnBlur: v })} data-testid="switch-dismiss-on-blur" />
          </SettingRow>
        </Section>

        {/* Notifications */}
        <Section id="notifs" title="Notifications" icon={Bell}>
          <SettingRow label="Notify on Scheduled Task Complete">
            <Switch checked={!!settings.notifyOnSchedule} onCheckedChange={v => update({ notifyOnSchedule: v })} data-testid="switch-notify-schedule" />
          </SettingRow>
          <SettingRow label="Notify on File Operations">
            <Switch checked={!!settings.notifyOnFileOp} onCheckedChange={v => update({ notifyOnFileOp: v })} data-testid="switch-notify-file-op" />
          </SettingRow>
        </Section>

        {/* About */}
        <Section id="about" title="About AXIOM" icon={Info}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-400/30 flex items-center justify-center">
              <Zap className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <p className="text-sm font-semibold">AXIOM Desktop</p>
              <p className="text-xs text-muted-foreground">Version 1.0.0 · AI-powered desktop assistant</p>
            </div>
            <Badge className="ml-auto text-[10px] bg-indigo-500/15 text-indigo-300 border-indigo-500/25">Stable</Badge>
          </div>
          <Separator className="bg-white/[0.07]" />
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg bg-white/5 border border-white/[0.06] px-3 py-2.5">
              <p className="text-muted-foreground text-[10px] uppercase tracking-wider mb-1">AI Mode</p>
              <p className="font-medium capitalize">{settings.aiMode}</p>
            </div>
            <div className="rounded-lg bg-white/5 border border-white/[0.06] px-3 py-2.5">
              <p className="text-muted-foreground text-[10px] uppercase tracking-wider mb-1">Model</p>
              <p className="font-medium font-mono truncate">{settings.aiModel}</p>
            </div>
            <div className="rounded-lg bg-white/5 border border-white/[0.06] px-3 py-2.5">
              <p className="text-muted-foreground text-[10px] uppercase tracking-wider mb-1">Allowed Paths</p>
              <p className="font-medium">{allowedPaths.length} configured</p>
            </div>
            <div className="rounded-lg bg-white/5 border border-white/[0.06] px-3 py-2.5">
              <p className="text-muted-foreground text-[10px] uppercase tracking-wider mb-1">Platform</p>
              <p className="font-medium">{isElectron ? "Desktop (Electron)" : "Web"}</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="text-xs text-muted-foreground hover:text-foreground w-full justify-start border border-transparent hover:border-white/10"
            onClick={handleRerunOnboarding}
            data-testid="button-rerun-onboarding"
          >
            Re-run onboarding wizard
          </Button>
        </Section>

      </div>
    </div>
  );
}

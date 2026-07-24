import React from "react";
import { useGetSettings, useUpdateSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Settings2, Shield, Cpu, FlaskConical, CheckSquare } from "lucide-react";

// FORGE runs fully local via Ollama — no cloud vendor, no API key, no outbound
// network dependency. The active model is chosen by the OLLAMA_MODEL env var
// on the server; this list is informational for the settings page.
const LOCAL_MODELS = [
  { value: "forge-sec", label: "Foundation-Sec-8B (Q4_K_M) — cybersecurity-specialized, recommended" },
  { value: "qwen2.5-coder:3b-instruct", label: "Qwen2.5-Coder 3B — fastest, lighter" },
  { value: "FenkoHQ/Foundation-Sec-8B:latest", label: "Foundation-Sec-8B (full fp16) — highest fidelity, slow on limited VRAM" },
];

const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

function SettingsCard({
  icon: Icon,
  iconColor,
  title,
  children,
}: {
  icon: React.ElementType;
  iconColor: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg p-6 space-y-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${iconColor}14`, border: `1px solid ${iconColor}25` }}>
          <Icon className="w-4 h-4" style={{ color: iconColor }} />
        </div>
        <span className="text-[10px] tracking-[0.25em] uppercase font-bold font-mono" style={{ color: iconColor }}>{title}</span>
      </div>
      {children}
    </div>
  );
}

function FieldLabel({ label }: { label: string }) {
  return <label className="block text-[9px] font-mono tracking-[0.2em] uppercase mb-1.5" style={{ color: '#475569' }}>{label}</label>;
}

export default function Settings() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });
  const updateSettings = useUpdateSettings();

  const [claudeModel, setClaudeModel] = React.useState("");
  const [noveltyTarget, setNoveltyTarget] = React.useState(7);
  const [complexity, setComplexity] = React.useState("moderate");
  const [platform, setPlatform] = React.useState("linux");
  const [evasionPriority, setEvasionPriority] = React.useState(3);
  const [redforgeUrl, setRedforgeUrl] = React.useState("");
  const [meliUrl, setMeliUrl] = React.useState("");
  const [sandboxEnabled, setSandboxEnabled] = React.useState(true);
  const [maxCpu, setMaxCpu] = React.useState(25);
  const [maxRam, setMaxRam] = React.useState(512);
  const [maxExec, setMaxExec] = React.useState(60);
  const [disclaimerAccepted, setDisclaimerAccepted] = React.useState(false);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (settings) {
      setClaudeModel(settings.claudeModel ?? "claude-sonnet-4-6");
      setNoveltyTarget(settings.defaultNoveltyTarget ?? 7);
      setComplexity(settings.defaultComplexity ?? "moderate");
      setPlatform(settings.defaultPlatform ?? "linux");
      setEvasionPriority(settings.defaultEvasionPriority ?? 3);
      setRedforgeUrl(settings.redforgeUrl ?? "");
      setMeliUrl(settings.meliUrl ?? "");
      setSandboxEnabled(settings.sandboxEnabled ?? true);
      setMaxCpu(settings.maxCpuPercent ?? 25);
      setMaxRam(settings.maxRamMb ?? 512);
      setMaxExec(settings.maxExecutionSeconds ?? 60);
      setDisclaimerAccepted(settings.disclaimerAccepted ?? false);
    }
  }, [settings]);

  const handleSave = async () => {
    await updateSettings.mutateAsync({
      data: {
        claudeModel,
        defaultNoveltyTarget: noveltyTarget,
        defaultComplexity: complexity,
        defaultPlatform: platform,
        defaultEvasionPriority: evasionPriority,
        redforgeUrl: redforgeUrl || undefined,
        meliUrl: meliUrl || undefined,
        sandboxEnabled,
        maxCpuPercent: maxCpu,
        maxRamMb: maxRam,
        maxExecutionSeconds: maxExec,
      },
    });
    queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (isLoading) return (
    <div className="p-8 space-y-4 max-w-3xl">
      {[60, 200, 200, 180].map((h, i) => (
        <Skeleton key={i} className="w-full rounded-lg" style={{ height: `${h}px`, background: '#0a0a14' }} />
      ))}
    </div>
  );

  return (
    <div className="p-8 max-w-3xl space-y-5">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Settings</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Configure FORGE behavior and integrations
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saved && <span className="text-[11px] font-mono font-bold" style={{ color: '#4ade80' }}>Saved</span>}
          <button
            onClick={handleSave}
            disabled={updateSettings.isPending}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all disabled:opacity-40"
            style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
            onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
            onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
          >
            {updateSettings.isPending ? "Saving..." : "Save Settings"}
          </button>
        </div>
      </div>

      {/* AI Model */}
      <SettingsCard icon={FlaskConical} iconColor="#f97316" title="AI Engine">
        <div>
          <FieldLabel label="Local Model (Ollama)" />
          <Select value={claudeModel} onValueChange={setClaudeModel}>
            <SelectTrigger className="font-mono text-xs h-10" style={inputStyle}><SelectValue /></SelectTrigger>
            <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
              {LOCAL_MODELS.map(m => <SelectItem key={m.value} value={m.value} className="font-mono text-xs">{m.label}</SelectItem>)}
            </SelectContent>
          </Select>
          <p className="text-[10px] font-mono mt-2" style={{ color: '#475569' }}>
            Runs entirely on this machine's GPU via Ollama — no cloud API, no key, no outbound calls.
            Change the active model by setting <code>OLLAMA_MODEL</code> in the server's .env and restarting.
          </p>
        </div>
      </SettingsCard>

      {/* Default Generation Parameters */}
      <SettingsCard icon={Settings2} iconColor="#60a5fa" title="Default Generation Parameters">
        <div className="space-y-5">
          <div>
            <div className="flex justify-between items-center mb-2">
              <FieldLabel label="Novelty Target" />
              <span className="text-[11px] font-black font-mono" style={{ color: '#f97316' }}>{noveltyTarget}/10</span>
            </div>
            <Slider value={[noveltyTarget]} onValueChange={([v]) => setNoveltyTarget(v)} min={1} max={10} step={1} />
          </div>
          <div>
            <div className="flex justify-between items-center mb-2">
              <FieldLabel label="Evasion Priority" />
              <span className="text-[11px] font-black font-mono" style={{ color: '#7B5EA7' }}>{evasionPriority}/5</span>
            </div>
            <Slider value={[evasionPriority]} onValueChange={([v]) => setEvasionPriority(v)} min={1} max={5} step={1} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <FieldLabel label="Default Platform" />
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger className="font-mono text-xs h-9" style={inputStyle}><SelectValue /></SelectTrigger>
                <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                  {["linux", "windows", "macos", "cloud", "network", "mobile", "iot"].map(p => (
                    <SelectItem key={p} value={p} className="font-mono text-xs">{p}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <FieldLabel label="Default Complexity" />
              <Select value={complexity} onValueChange={setComplexity}>
                <SelectTrigger className="font-mono text-xs h-9" style={inputStyle}><SelectValue /></SelectTrigger>
                <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                  {["simple", "moderate", "complex", "advanced"].map(c => (
                    <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
      </SettingsCard>

      {/* Sandbox Safety */}
      <SettingsCard icon={Cpu} iconColor="#eab308" title="Sandbox Safety Limits">
        <div className="space-y-5">
          <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: '#07070e', border: '1px solid #0f0f1a' }}>
            <div>
              <div className="text-[11px] font-bold font-mono mb-0.5" style={{ color: '#94a3b8' }}>Sandbox Enabled</div>
              <div className="text-[10px] font-mono" style={{ color: '#475569' }}>Enforce resource limits during code execution</div>
            </div>
            <Switch checked={sandboxEnabled} onCheckedChange={setSandboxEnabled} />
          </div>
          <div className={`space-y-5 transition-opacity ${sandboxEnabled ? "opacity-100" : "opacity-30 pointer-events-none"}`}>
            {[
              { label: `Max CPU`, value: maxCpu, unit: '%', onChange: setMaxCpu, min: 5, max: 100, step: 5, color: '#f87171' },
              { label: `Max RAM`, value: maxRam, unit: ' MB', onChange: setMaxRam, min: 128, max: 4096, step: 128, color: '#fb923c' },
              { label: `Max Execution`, value: maxExec, unit: 's', onChange: setMaxExec, min: 10, max: 300, step: 10, color: '#eab308' },
            ].map(({ label, value, unit, onChange, min, max, step, color }) => (
              <div key={label}>
                <div className="flex justify-between items-center mb-2">
                  <FieldLabel label={label} />
                  <span className="text-[11px] font-black font-mono" style={{ color }}>{value}{unit}</span>
                </div>
                <Slider value={[value]} onValueChange={([v]) => onChange(v)} min={min} max={max} step={step} />
              </div>
            ))}
          </div>
        </div>
      </SettingsCard>

      {/* Integration URLs */}
      <SettingsCard icon={Shield} iconColor="#4ade80" title="Integration URLs">
        <div className="space-y-4">
          <div>
            <FieldLabel label="REDFORGE URL" />
            <Input value={redforgeUrl} onChange={e => setRedforgeUrl(e.target.value)} placeholder="http://localhost:4444" className="font-mono text-xs h-9" style={inputStyle} />
            <p className="text-[10px] font-mono mt-1.5" style={{ color: '#2e3a50' }}>Your REDFORGE red team automation platform endpoint</p>
          </div>
          <div>
            <FieldLabel label="Meli Honeypot URL" />
            <Input value={meliUrl} onChange={e => setMeliUrl(e.target.value)} placeholder="http://localhost:5555" className="font-mono text-xs h-9" style={inputStyle} />
            <p className="text-[10px] font-mono mt-1.5" style={{ color: '#2e3a50' }}>Your Cowrie honeypot API endpoint for live attacker command capture</p>
          </div>
        </div>
      </SettingsCard>

      {/* Legal Compliance */}
      <SettingsCard icon={Shield} iconColor={disclaimerAccepted ? '#4ade80' : '#f87171'} title="Legal Compliance">
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: '#07070e', border: '1px solid #0f0f1a' }}>
            <div>
              <div className="text-[11px] font-bold font-mono mb-0.5" style={{ color: '#94a3b8' }}>Research Disclaimer</div>
              <div className="text-[10px] font-mono" style={{ color: '#475569' }}>All research conducted for defensive purposes on authorized systems</div>
            </div>
            <span
              className="text-[9px] font-black font-mono tracking-wider uppercase px-2.5 py-1 rounded"
              style={disclaimerAccepted
                ? { background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }
                : { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }
              }
            >
              {disclaimerAccepted ? "Accepted" : "Not Accepted"}
            </span>
          </div>
          {!disclaimerAccepted && (
            <button
              onClick={async () => {
                await updateSettings.mutateAsync({ data: { disclaimerAccepted: true } });
                setDisclaimerAccepted(true);
                queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
              style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
            >
              <CheckSquare className="w-3.5 h-3.5" />Accept Research Disclaimer
            </button>
          )}
        </div>
      </SettingsCard>

      {/* About */}
      <div className="rounded-lg p-5" style={{ background: '#09090f', border: '1px solid #0f0f1a' }}>
        <div className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono mb-4" style={{ color: '#64748b' }}>About FORGE</div>
        <div className="space-y-2 font-mono">
          {[
            { label: "Version", value: "1.0.0" },
            { label: "AI Model", value: claudeModel },
            { label: "Stack", value: "React + Express + PostgreSQL" },
            { label: "AI Provider", value: "Local (Ollama, self-hosted, no cloud)" },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-1.5" style={{ borderBottom: '1px solid #0a0a14' }}>
              <span className="text-[10px]" style={{ color: '#64748b' }}>{label}</span>
              <span className="text-[10px] font-bold" style={{ color: '#64748b' }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

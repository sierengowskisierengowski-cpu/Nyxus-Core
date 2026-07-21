import React from "react";
import { useListInputs, useGetSettings, getGetSettingsQueryKey } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Flame, Zap, AlertTriangle, X } from "lucide-react";

const ENGINES = [
  { id: "codeSplicing", label: "Code Splicing", desc: "Recombines functional code segments from multiple sources into novel attack primitives" },
  { id: "logicMutation", label: "Logic Mutation", desc: "Alters control flow, conditions, and logical structures to create behavioral variants" },
  { id: "crossDomainFusion", label: "Cross Domain Fusion", desc: "Combines techniques from different attack domains (network, host, application)" },
  { id: "evasionEvolution", label: "Evasion Evolution", desc: "Optimizes code to evade signature-based and behavioral detection systems" },
  { id: "protocolAbuse", label: "Protocol Abuse", desc: "Exploits legitimate protocol behaviors for C2 and exfiltration" },
  { id: "lolExpansion", label: "LOLBAS Expansion", desc: "Leverages living-off-the-land binaries and scripts to blend with legitimate activity" },
  { id: "payloadPolymorphism", label: "Payload Polymorphism", desc: "Generates functionally equivalent code variants with different signatures" },
];

type SSEEvent =
  | { type: "status"; message: string }
  | { type: "engine_start"; engine: string; name: string }
  | { type: "progress"; tokens: number }
  | { type: "threat_generated"; threat: { id: number; name: string; noveltyScore: number; description: string; platform: string; estimatedDetectionRate: number } }
  | { type: "error"; message: string }
  | { type: "done" };

function noveltyGradient(score: number) {
  if (score >= 9) return { background: 'linear-gradient(90deg, #7c3aed, #6d28d9)', boxShadow: '0 0 10px rgba(124,58,237,0.4)' };
  if (score >= 7) return { background: 'linear-gradient(90deg, #dc2626, #991b1b)' };
  if (score >= 4) return { background: 'linear-gradient(90deg, #ea580c, #c2410c)' };
  return { background: '#1e293b' };
}

function noveltyLabel(score: number) {
  if (score >= 9) return "UNPRECEDENTED";
  if (score >= 7) return "HIGH";
  if (score >= 4) return "MEDIUM";
  return "LOW";
}

function SectionTitle({ label, color = 'orange' }: { label: string; color?: 'orange' | 'purple' }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-[3px] h-4 rounded-full shrink-0" style={{ background: color === 'orange' ? '#f97316' : '#7B5EA7' }} />
      <span className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono" style={{ color: color === 'orange' ? '#f97316' : '#7B5EA7' }}>
        {label}
      </span>
    </div>
  );
}

export default function MutationLab() {
  const [, navigate] = useLocation();
  const { data: inputs } = useListInputs();
  const { data: settings } = useGetSettings({ query: { queryKey: getGetSettingsQueryKey() } });

  const [enabledEngines, setEnabledEngines] = React.useState<Set<string>>(new Set(ENGINES.map(e => e.id)));
  const [noveltyTarget, setNoveltyTarget] = React.useState(settings?.defaultNoveltyTarget ?? 7);
  const [platform, setPlatform] = React.useState(settings?.defaultPlatform ?? "linux");
  const [evasionPriority, setEvasionPriority] = React.useState(settings?.defaultEvasionPriority ?? 3);
  const [complexity, setComplexity] = React.useState(settings?.defaultComplexity ?? "moderate");
  const [stealthLevel, setStealthLevel] = React.useState("balanced");
  const [attackGoal, setAttackGoal] = React.useState("access");

  const [generating, setGenerating] = React.useState(false);
  const [statusMessages, setStatusMessages] = React.useState<string[]>([]);
  const [activeEngines, setActiveEngines] = React.useState<string[]>([]);
  const [generatedThreats, setGeneratedThreats] = React.useState<Array<{ id: number; name: string; noveltyScore: number; description: string; platform: string; estimatedDetectionRate: number }>>([]);
  const [progress, setProgress] = React.useState(0);

  const toggleEngine = (id: string) => {
    setEnabledEngines(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const generate = async () => {
    setGenerating(true);
    setStatusMessages([]);
    setActiveEngines([]);
    setGeneratedThreats([]);
    setProgress(0);

    try {
      const resp = await fetch("/api/threats/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inputIds: inputs?.map(i => i.id) ?? [],
          engines: Array.from(enabledEngines),
          noveltyTarget,
          complexityTarget: complexity,
          platform,
          evasionPriority,
          stealthLevel,
          attackGoal,
        }),
      });

      if (!resp.body) throw new Error("No stream");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event: SSEEvent = JSON.parse(line.slice(6));
            if (event.type === "status") setStatusMessages(p => [...p, event.message]);
            else if (event.type === "engine_start") setActiveEngines(p => [...p, event.name]);
            else if (event.type === "progress") setProgress(event.tokens);
            else if (event.type === "threat_generated") setGeneratedThreats(p => [...p, event.threat]);
            else if (event.type === "done") break;
          } catch { /* skip malformed */ }
        }
      }
    } catch {
      setStatusMessages(p => [...p, "Generation failed — check API server logs"]);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Mutation Lab</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Configure and fire the AI threat generation engines
          </p>
        </div>
        {inputs && inputs.length > 0 && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded"
            style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.25)' }}
          >
            <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#f97316' }} />
            <span className="text-[10px] font-mono tracking-wider" style={{ color: '#f97316' }}>{inputs.length} inputs queued</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Engines Panel */}
        <div className="lg:col-span-1">
          <div className="rounded-lg p-5 space-y-2" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Mutation Engines" />
            <div className="space-y-2">
              {ENGINES.map((engine) => {
                const enabled = enabledEngines.has(engine.id);
                return (
                  <div
                    key={engine.id}
                    className="relative overflow-hidden rounded-lg transition-all duration-200 cursor-pointer"
                    style={enabled ? {
                      border: '1px solid rgba(249,115,22,0.3)',
                      background: 'linear-gradient(135deg, rgba(249,115,22,0.08) 0%, rgba(249,115,22,0.02) 100%)',
                      boxShadow: '0 0 12px rgba(249,115,22,0.06)',
                    } : {
                      border: '1px solid #111118',
                      background: '#09090f',
                    }}
                    onClick={() => toggleEngine(engine.id)}
                  >
                    {enabled && (
                      <div className="absolute top-0 left-0 right-0 h-px" style={{ background: 'linear-gradient(90deg, rgba(249,115,22,0.5) 0%, rgba(249,115,22,0.1) 60%, transparent 100%)' }} />
                    )}
                    <div className="p-3.5 flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div
                          className="text-[11px] font-black tracking-wider uppercase mb-1.5"
                          style={{ color: enabled ? '#f97316' : '#2a2a3e' }}
                        >
                          {engine.label}
                        </div>
                        <p className="text-[10px] font-mono leading-relaxed" style={{ color: '#475569' }}>
                          {engine.desc}
                        </p>
                      </div>
                      <Switch
                        checked={enabled}
                        onCheckedChange={() => toggleEngine(engine.id)}
                        onClick={e => e.stopPropagation()}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Parameters + Output */}
        <div className="lg:col-span-2 space-y-4">
          {/* Parameters Card */}
          <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Generation Parameters" color="purple" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-2.5">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Novelty Target</label>
                  <span className="text-sm font-black font-mono" style={{ color: '#f97316' }}>{noveltyTarget}/10</span>
                </div>
                <Slider value={[noveltyTarget]} onValueChange={([v]) => setNoveltyTarget(v)} min={1} max={10} step={1} />
              </div>
              <div className="space-y-2.5">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Evasion Priority</label>
                  <span className="text-sm font-black font-mono" style={{ color: '#7B5EA7' }}>{evasionPriority}/5</span>
                </div>
                <Slider value={[evasionPriority]} onValueChange={([v]) => setEvasionPriority(v)} min={1} max={5} step={1} />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Platform</label>
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger className="font-mono text-xs h-9" style={{ background: '#07070e', borderColor: '#111118', color: '#64748b' }}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                    {["linux", "windows", "macos", "cloud", "network", "mobile", "iot"].map(p => (
                      <SelectItem key={p} value={p} className="font-mono text-xs">{p}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Complexity</label>
                <Select value={complexity} onValueChange={setComplexity}>
                  <SelectTrigger className="font-mono text-xs h-9" style={{ background: '#07070e', borderColor: '#111118', color: '#64748b' }}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                    {["simple", "moderate", "complex", "advanced"].map(c => (
                      <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Stealth Level</label>
                <Select value={stealthLevel} onValueChange={setStealthLevel}>
                  <SelectTrigger className="font-mono text-xs h-9" style={{ background: '#07070e', borderColor: '#111118', color: '#64748b' }}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                    {["noisy", "balanced", "stealthy", "ghostlike"].map(s => (
                      <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>Attack Goal</label>
                <Select value={attackGoal} onValueChange={setAttackGoal}>
                  <SelectTrigger className="font-mono text-xs h-9" style={{ background: '#07070e', borderColor: '#111118', color: '#64748b' }}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                    {["access", "persistence", "exfiltration", "lateral-movement", "defense-evasion", "destruction"].map(g => (
                      <SelectItem key={g} value={g} className="font-mono text-xs">{g}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Generate Button */}
          <div className="flex gap-3">
            <button
              onClick={generate}
              disabled={generating || enabledEngines.size === 0}
              className="flex-1 flex items-center justify-center gap-3 py-5 rounded-lg font-black tracking-[0.15em] uppercase text-sm transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: generating ? '#7c2d0a' : '#f97316',
                color: 'white',
                border: 'none',
                boxShadow: '0 0 32px rgba(249,115,22,0.3), 0 4px 16px rgba(0,0,0,0.5)',
              }}
              onMouseEnter={e => { if (!generating && enabledEngines.size > 0) (e.currentTarget as HTMLElement).style.boxShadow = '0 0 48px rgba(249,115,22,0.45), 0 4px 20px rgba(0,0,0,0.6)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 0 32px rgba(249,115,22,0.3), 0 4px 16px rgba(0,0,0,0.5)'; }}
            >
              {generating ? (
                <Zap className="w-5 h-5 animate-spin" />
              ) : (
                <Flame className="w-5 h-5" />
              )}
              {generating ? "Generating Threat Package..." : "Generate Threat"}
            </button>
            {generatedThreats.length > 0 && (
              <button
                onClick={() => setGeneratedThreats([])}
                className="px-4 rounded-lg transition-colors font-mono text-xs tracking-wider"
                style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* No inputs warning */}
          {!inputs?.length && !generating && (
            <div
              className="flex items-start gap-3 p-4 rounded-lg"
              style={{ background: 'rgba(234,179,8,0.05)', border: '1px solid rgba(234,179,8,0.15)' }}
            >
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: '#ca8a04' }} />
              <div className="text-[11px] font-mono leading-relaxed" style={{ color: '#713f12' }}>
                No inputs queued. FORGE will generate a novel technique from first principles.
                Add inputs in the Input Lab for more targeted results.
              </div>
            </div>
          )}

          {/* Live Status Terminal */}
          {generating && (
            <div className="rounded-lg p-4 space-y-2" style={{ background: '#04040a', border: '1px solid rgba(249,115,22,0.2)', boxShadow: '0 0 20px rgba(249,115,22,0.05)' }}>
              {activeEngines.length > 0 && (
                <div className="mb-3">
                  <div className="text-[9px] font-mono tracking-[0.3em] uppercase mb-2" style={{ color: '#475569' }}>Active Engines</div>
                  <div className="flex flex-wrap gap-1.5">
                    {activeEngines.map(e => (
                      <span
                        key={e}
                        className="px-2 py-0.5 rounded text-[10px] font-mono animate-pulse"
                        style={{ background: 'rgba(249,115,22,0.12)', border: '1px solid rgba(249,115,22,0.3)', color: '#f97316' }}
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {statusMessages.map((msg, i) => (
                  <div key={i} className="text-[11px] font-mono flex items-start gap-2" style={{ color: '#64748b' }}>
                    <span style={{ color: '#f97316' }}>›</span>
                    <span>{msg}</span>
                  </div>
                ))}
              </div>
              {progress > 0 && (
                <div className="text-[10px] font-mono" style={{ color: '#475569' }}>{progress.toLocaleString()} tokens generated</div>
              )}
              <div className="flex items-center gap-2 pt-1" style={{ color: '#f97316' }}>
                <Zap className="w-3 h-3 animate-spin" />
                <span className="text-[10px] font-mono tracking-wider">Claude is generating the threat package</span>
                <span className="animate-forge-blink text-sm">▋</span>
              </div>
            </div>
          )}

          {/* Generated Threats */}
          {generatedThreats.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-[3px] h-4 rounded-full" style={{ background: '#f97316' }} />
                <span className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono" style={{ color: '#f97316' }}>Generated Threats</span>
              </div>
              {generatedThreats.map((threat) => (
                <div
                  key={threat.id}
                  className="rounded-lg p-4 animate-slide-in-up"
                  style={{ background: 'rgba(249,115,22,0.04)', border: '1px solid rgba(249,115,22,0.2)' }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-bold mb-1.5" style={{ color: '#e2e8f0' }}>{threat.name}</div>
                      <p className="text-[11px] font-mono leading-relaxed mb-2" style={{ color: '#64748b' }}>{threat.description}</p>
                      <div className="flex items-center gap-4 text-[10px] font-mono" style={{ color: '#475569' }}>
                        <span>{threat.platform}</span>
                        <span>Detection Rate: <span style={{ color: threat.estimatedDetectionRate < 30 ? '#4ade80' : '#f97316' }}>{threat.estimatedDetectionRate}%</span></span>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <span
                        className="inline-flex items-center px-2.5 py-1 rounded text-[10px] font-black font-mono tracking-wider text-white"
                        style={noveltyGradient(threat.noveltyScore)}
                      >
                        {noveltyLabel(threat.noveltyScore)} {threat.noveltyScore}/10
                      </span>
                      <button
                        onClick={() => navigate(`/threat-analysis/${threat.id}`)}
                        className="text-[10px] font-mono font-bold tracking-wider uppercase px-3 py-1.5 rounded transition-all"
                        style={{ background: '#f97316', color: 'white', border: 'none' }}
                        onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
                        onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
                      >
                        Analyze →
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

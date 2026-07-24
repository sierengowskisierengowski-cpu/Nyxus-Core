import React from "react";
import { useParams, useLocation } from "wouter";
import {
  useGetThreat,
  useUpdateThreat,
  useSendThreatToRedforge,
  useListDetectionRules,
  getGetThreatQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { CheckSquare, Crosshair, ArrowLeft, FlaskConical, ChevronRight, Shield } from "lucide-react";

function noveltyGradient(score: number) {
  if (score >= 9) return { background: 'linear-gradient(90deg, #7c3aed, #6d28d9)', boxShadow: '0 0 10px rgba(124,58,237,0.4)' };
  if (score >= 7) return { background: 'linear-gradient(90deg, #dc2626, #991b1b)' };
  if (score >= 4) return { background: 'linear-gradient(90deg, #ea580c, #c2410c)' };
  return { background: '#1e293b' };
}

function NoveltyBadge({ score }: { score: number }) {
  const label = score >= 9 ? "UNPRECEDENTED" : score >= 7 ? "HIGH" : score >= 4 ? "MEDIUM" : "LOW";
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded text-[10px] font-black font-mono tracking-wider text-white"
      style={noveltyGradient(score)}
    >
      {label} {score}/10
    </span>
  );
}

function CodeBlock({ code, label }: { code: string; label?: string }) {
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: '1px solid #111118' }}>
      {label && (
        <div
          className="px-4 py-2.5 text-[9px] font-mono tracking-[0.25em] uppercase"
          style={{ background: '#08080e', borderBottom: '1px solid #111118', color: '#475569' }}
        >
          {label}
        </div>
      )}
      <pre
        className="p-5 overflow-x-auto text-xs font-mono leading-relaxed whitespace-pre-wrap break-all"
        style={{ background: '#04040a', color: '#4ade80' }}
      >
        {code}
      </pre>
    </div>
  );
}

function SectionTitle({ label, color = 'orange' }: { label: string; color?: 'orange' | 'purple' }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-[3px] h-4 rounded-full shrink-0" style={{ background: color === 'orange' ? '#f97316' : '#7B5EA7' }} />
      <span className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono" style={{ color: color === 'orange' ? '#f97316' : '#7B5EA7' }}>
        {label}
      </span>
    </div>
  );
}

export default function ThreatAnalysis() {
  const params = useParams<{ id: string }>();
  const id = parseInt(params.id ?? "0");
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();
  const { data: threat, isLoading, error } = useGetThreat(id, { query: { queryKey: getGetThreatQueryKey(id), enabled: !!id } });
  const { data: rules } = useListDetectionRules({});
  const updateThreat = useUpdateThreat();
  const sendToRedforge = useSendThreatToRedforge();

  const threatRules = rules?.filter(r => r.threatId === id) ?? [];
  const [notes, setNotes] = React.useState("");
  const [notesSaved, setNotesSaved] = React.useState(false);
  const saveTimeout = React.useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  React.useEffect(() => {
    if (threat?.userNotes) setNotes(threat.userNotes);
  }, [threat?.userNotes]);

  const handleNotesChange = (val: string) => {
    setNotes(val);
    setNotesSaved(false);
    clearTimeout(saveTimeout.current);
    saveTimeout.current = setTimeout(async () => {
      await updateThreat.mutateAsync({ id, data: { userNotes: val } });
      queryClient.invalidateQueries({ queryKey: getGetThreatQueryKey(id) });
      setNotesSaved(true);
    }, 1500);
  };

  const markMastered = async () => {
    await updateThreat.mutateAsync({ id, data: { mastered: !threat?.mastered } });
    queryClient.invalidateQueries({ queryKey: getGetThreatQueryKey(id) });
  };

  const sendRedforge = async () => {
    await sendToRedforge.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: getGetThreatQueryKey(id) });
  };

  if (isLoading) return (
    <div className="p-8 space-y-4 max-w-7xl">
      {[...Array(3)].map((_, i) => (
        <Skeleton key={i} className="w-full rounded-lg" style={{ height: i === 0 ? '60px' : i === 1 ? '180px' : '360px', background: '#0a0a14' }} />
      ))}
    </div>
  );

  if (error || !threat) return (
    <div className="p-8 text-center">
      <div className="text-sm font-mono mb-4" style={{ color: '#475569' }}>Threat not found.</div>
      <button
        onClick={() => navigate("/threat-library")}
        className="px-4 py-2 rounded-lg text-[11px] font-mono font-bold tracking-wider uppercase"
        style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
      >
        Back to Library
      </button>
    </div>
  );

  const sigma = threatRules.find(r => r.ruleType === "sigma");
  const snort = threatRules.find(r => r.ruleType === "snort");
  const yara = threatRules.find(r => r.ruleType === "yara");

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Header */}
      <div className="pb-6 flex items-start gap-4" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <button
          onClick={() => navigate("/threat-library")}
          className="mt-1.5 transition-colors shrink-0"
          style={{ color: '#475569' }}
          onMouseEnter={e => (e.currentTarget.style.color = '#f97316')}
          onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <h1 className="text-xl font-black tracking-tight" style={{ color: '#e2e8f0' }}>{threat.name}</h1>
            <NoveltyBadge score={threat.noveltyScore} />
            {threat.mastered && (
              <span className="px-2.5 py-1 rounded text-[9px] font-black font-mono tracking-wider" style={{ background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }}>
                MASTERED
              </span>
            )}
            {threat.sentToRedforge && (
              <span className="px-2.5 py-1 rounded text-[9px] font-black font-mono tracking-wider" style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}>
                SENT TO REDFORGE
              </span>
            )}
          </div>
          <p className="text-sm font-mono leading-relaxed" style={{ color: '#64748b' }}>{threat.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Side Panel */}
        <div className="lg:col-span-1 space-y-3">
          {/* Threat Profile */}
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Threat Profile" />
            <div className="space-y-2.5 font-mono">
              {[
                { label: "Platform", value: threat.platform, color: '#94a3b8' },
                { label: "Category", value: threat.category ?? "—", color: '#94a3b8' },
                {
                  label: "Detection Rate",
                  value: `${threat.estimatedDetectionRate}%`,
                  color: threat.estimatedDetectionRate < 30 ? '#ef4444' : threat.estimatedDetectionRate < 70 ? '#f97316' : '#4ade80'
                },
                { label: "Generated", value: new Date(threat.createdAt).toLocaleDateString(), color: '#94a3b8' },
              ].map(({ label, value, color }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-[9px] tracking-wider uppercase" style={{ color: '#475569' }}>{label}</span>
                  <span className="text-[11px] font-bold" style={{ color }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* MITRE */}
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="MITRE ATT&CK" color="purple" />
            <div className="flex flex-wrap gap-1.5">
              {threat.mitreIds?.length ? threat.mitreIds.map(mid => (
                <span key={mid} className="px-2 py-0.5 rounded text-[9px] font-mono" style={{ background: 'rgba(123,94,167,0.1)', border: '1px solid rgba(123,94,167,0.2)', color: '#a78bfa' }}>{mid}</span>
              )) : <span className="text-[11px] font-mono" style={{ color: '#475569' }}>—</span>}
            </div>
          </div>

          {/* Mutation Lineage */}
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Mutation Lineage" />
            <div className="flex flex-wrap gap-1.5">
              {threat.mutationEnginesUsed?.length ? threat.mutationEnginesUsed.map(e => (
                <span key={e} className="text-[9px] px-2 py-0.5 rounded font-mono" style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.2)', color: '#f97316' }}>{e}</span>
              )) : <span className="text-[11px] font-mono" style={{ color: '#475569' }}>—</span>}
            </div>
          </div>

          {/* Detection Rules Coverage */}
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Detection Coverage" />
            <div className="space-y-2 font-mono">
              {["sigma", "snort", "yara"].map(type => {
                const has = threatRules.some(r => r.ruleType === type);
                return (
                  <div key={type} className="flex items-center gap-2">
                    <Shield className="w-3 h-3" style={{ color: has ? '#4ade80' : '#111118' }} />
                    <span className="text-[10px] tracking-wider uppercase" style={{ color: has ? '#4ade80' : '#475569' }}>{type}</span>
                    {has && <span className="ml-auto text-[10px]" style={{ color: '#4ade80' }}>✓</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <button
              onClick={markMastered}
              disabled={updateThreat.isPending}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all disabled:opacity-40"
              style={threat.mastered
                ? { background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }
                : { background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }
              }
            >
              <CheckSquare className="w-3.5 h-3.5" />
              {threat.mastered ? "Unmark Mastered" : "Mark Mastered"}
            </button>
            <button
              onClick={sendRedforge}
              disabled={threat.sentToRedforge || sendToRedforge.isPending}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all disabled:opacity-40"
              style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}
            >
              <Crosshair className="w-3.5 h-3.5" />
              {threat.sentToRedforge ? "Sent to REDFORGE" : "Send to REDFORGE"}
            </button>
            <button
              onClick={() => navigate("/input-lab")}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
              style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
            >
              <FlaskConical className="w-3.5 h-3.5" />
              Evolve Further
            </button>
          </div>
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3 space-y-4">
          <CodeBlock code={threat.code} label="Generated Code — Authorized Defensive Research Only" />

          <Tabs defaultValue="breakdown">
            <TabsList
              className="flex flex-wrap h-auto gap-1 p-1"
              style={{ background: '#09090f', border: '1px solid #111118' }}
            >
              {["breakdown", "sigma", "snort", "yara", "defense", "testplan"].map(tab => (
                <TabsTrigger key={tab} value={tab} className="text-[10px] font-mono tracking-wider uppercase">
                  {tab === "testplan" ? "Test Plan" : tab === "breakdown" ? "Breakdown" : tab.toUpperCase()}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="breakdown" className="mt-4">
              <div className="rounded-lg p-6 space-y-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
                <div className="text-sm font-mono leading-relaxed whitespace-pre-wrap" style={{ color: '#64748b' }}>
                  {threat.technicalBreakdown}
                </div>
                {(threat.behavioralIndicators?.length || threat.networkIndicators?.length) && (
                  <div className="grid grid-cols-2 gap-6 pt-4" style={{ borderTop: '1px solid #0f0f1a' }}>
                    <div>
                      <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-3" style={{ color: '#f97316' }}>Behavioral IOCs</div>
                      <ul className="space-y-1.5 text-xs font-mono" style={{ color: '#64748b' }}>
                        {threat.behavioralIndicators?.map((b, i) => (
                          <li key={i} className="flex gap-2">
                            <ChevronRight className="w-3 h-3 shrink-0 mt-0.5" style={{ color: '#f97316' }} />{b}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-3" style={{ color: '#60a5fa' }}>Network IOCs</div>
                      <ul className="space-y-1.5 text-xs font-mono" style={{ color: '#64748b' }}>
                        {threat.networkIndicators?.map((n, i) => (
                          <li key={i} className="flex gap-2">
                            <ChevronRight className="w-3 h-3 shrink-0 mt-0.5" style={{ color: '#60a5fa' }} />{n}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
                <div className="pt-4" style={{ borderTop: '1px solid #0f0f1a' }}>
                  <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-2" style={{ color: '#475569' }}>Real-World Feasibility</div>
                  <p className="text-sm font-mono leading-relaxed" style={{ color: '#475569' }}>{threat.realWorldFeasibility}</p>
                </div>
              </div>
            </TabsContent>

            {[
              { tab: "sigma", rule: sigma, label: "Sigma Detection Rule" },
              { tab: "snort", rule: snort, label: "Snort/Suricata IDS Rule" },
              { tab: "yara", rule: yara, label: "YARA Malware Scanner Rule" },
            ].map(({ tab, rule, label }) => (
              <TabsContent key={tab} value={tab} className="mt-4">
                {rule ? <CodeBlock code={rule.content} label={label} /> : (
                  <div className="rounded-lg p-8 text-center" style={{ background: '#09090f', border: '1px solid #0f0f1a' }}>
                    <p className="text-[11px] font-mono" style={{ color: '#64748b' }}>No {tab.toUpperCase()} rule generated for this threat.</p>
                  </div>
                )}
              </TabsContent>
            ))}

            <TabsContent value="defense" className="mt-4">
              <div className="rounded-lg p-6 space-y-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
                <div>
                  <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-3" style={{ color: '#4ade80' }}>Defensive Recommendations</div>
                  <p className="text-sm font-mono leading-relaxed whitespace-pre-wrap" style={{ color: '#475569' }}>{threat.defensiveRecommendations}</p>
                </div>
                <div>
                  <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-3" style={{ color: '#4ade80' }}>Hardening Configuration</div>
                  <CodeBlock code={threat.hardeningConfig} />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="testplan" className="mt-4">
              <div className="rounded-lg p-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
                <div className="text-[9px] tracking-[0.25em] uppercase font-mono mb-4" style={{ color: '#475569' }}>Lab Test Procedure</div>
                <div className="text-sm font-mono leading-relaxed whitespace-pre-wrap" style={{ color: '#475569' }}>{threat.testPlan}</div>
              </div>
            </TabsContent>
          </Tabs>

          {/* Researcher Notes */}
          <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <div className="flex items-center justify-between mb-3">
              <SectionTitle label="Researcher Notes" />
              {notesSaved && <span className="text-[10px] font-mono" style={{ color: '#4ade80' }}>Saved</span>}
            </div>
            <Textarea
              value={notes}
              onChange={e => handleNotesChange(e.target.value)}
              placeholder="Research observations, extensions, defensive coverage gaps..."
              className="font-mono text-sm resize-none min-h-32"
              style={{ background: '#07070e', borderColor: '#111118', color: '#64748b' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

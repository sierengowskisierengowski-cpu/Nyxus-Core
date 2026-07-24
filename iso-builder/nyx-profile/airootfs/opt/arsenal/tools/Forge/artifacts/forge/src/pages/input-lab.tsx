import React from "react";
import { useListInputs, useCreateInput, useDeleteInput, useAnalyzeInputs } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { getListInputsQueryKey } from "@workspace/api-client-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { X, Plus, Zap, ArrowRight, FlaskConical } from "lucide-react";

const INPUT_TYPES = [
  { value: "code", label: "Code" },
  { value: "file", label: "File" },
  { value: "url", label: "URL" },
  { value: "meli", label: "Meli" },
  { value: "redforge", label: "REDFORGE" },
  { value: "cve", label: "CVE" },
  { value: "mitre", label: "MITRE" },
  { value: "natural", label: "Natural" },
];

const LANGUAGES = ["python", "bash", "powershell", "c", "c++", "javascript", "go", "rust", "java", "ruby"];

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

function ForgeButton({ onClick, disabled, children, variant = 'primary', className = '' }: {
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
  variant?: 'primary' | 'outline' | 'ghost';
  className?: string;
}) {
  const base = "flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-[0.1em] uppercase font-mono transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed";
  const styles: Record<string, React.CSSProperties> = {
    primary: { background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' },
    outline: { background: 'transparent', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)' },
    ghost: { background: '#09090f', color: '#64748b', border: '1px solid #111118' },
  };
  return (
    <button onClick={onClick} disabled={disabled} className={`${base} ${className}`} style={styles[variant]}>
      {children}
    </button>
  );
}

export default function InputLab() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const { data: inputs, isLoading } = useListInputs();
  const createInput = useCreateInput();
  const deleteInput = useDeleteInput();
  const analyzeInputs = useAnalyzeInputs();

  const [activeTab, setActiveTab] = React.useState("code");
  const [code, setCode] = React.useState("");
  const [language, setLanguage] = React.useState("python");
  const [url, setUrl] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [natural, setNatural] = React.useState("");
  const [cve, setCve] = React.useState("");
  const [mitre, setMitre] = React.useState("");
  const [analysisResult, setAnalysisResult] = React.useState<null | {
    techniques: string[];
    mitreIds: string[];
    patterns: string[];
    sophisticationScore: number;
    gaps: string[];
    summary: string;
  }>(null);
  const [analyzing, setAnalyzing] = React.useState(false);

  const getContent = () => {
    switch (activeTab) {
      case "code": return code;
      case "url": return url;
      case "natural": return natural;
      case "cve": return cve;
      case "mitre": return mitre;
      default: return "";
    }
  };

  const addInput = async () => {
    const content = getContent();
    if (!content.trim()) return;
    await createInput.mutateAsync({
      data: {
        inputType: activeTab,
        content,
        label: label || undefined,
        language: activeTab === "code" ? language : undefined,
      },
    });
    queryClient.invalidateQueries({ queryKey: getListInputsQueryKey() });
    setCode(""); setUrl(""); setNatural(""); setCve(""); setMitre(""); setLabel("");
  };

  const removeInput = (id: number) => {
    deleteInput.mutate({ id });
    queryClient.invalidateQueries({ queryKey: getListInputsQueryKey() });
  };

  const runAnalysis = async () => {
    if (!inputs?.length) return;
    setAnalyzing(true);
    try {
      const result = await analyzeInputs.mutateAsync({ data: { inputIds: [] } });
      setAnalysisResult(result as typeof analysisResult);
    } catch {
      // ignore
    } finally {
      setAnalyzing(false);
    }
  };

  const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Input Lab</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Queue source material for threat generation
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Area */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Input Source" />
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList
                className="flex flex-wrap h-auto gap-1 p-1 mb-4"
                style={{ background: '#09090f', border: '1px solid #111118' }}
              >
                {INPUT_TYPES.map(t => (
                  <TabsTrigger
                    key={t.value}
                    value={t.value}
                    className="text-[10px] font-mono tracking-wider uppercase px-3 py-1.5 rounded transition-all"
                    style={{ fontFamily: 'JetBrains Mono, monospace' }}
                  >
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              <TabsContent value="code" className="space-y-3">
                <div className="flex gap-2">
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger className="w-36 font-mono text-xs h-9" style={inputStyle}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                      {LANGUAGES.map(l => <SelectItem key={l} value={l} className="font-mono text-xs">{l}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Input
                    value={label}
                    onChange={e => setLabel(e.target.value)}
                    placeholder="Label (optional)"
                    className="font-mono text-xs h-9 flex-1"
                    style={inputStyle}
                  />
                </div>
                <Textarea
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  placeholder="// Paste code, scripts, malware samples, or attack techniques here..."
                  className="font-mono text-sm min-h-56 resize-y"
                  style={{ ...inputStyle, lineHeight: '1.6' }}
                />
              </TabsContent>

              <TabsContent value="url" className="space-y-3">
                <Input
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  placeholder="https://github.com/.../exploit.py"
                  className="font-mono text-sm h-9"
                  style={inputStyle}
                />
                <p className="text-[11px] font-mono" style={{ color: '#475569' }}>Paste a URL to a code file, exploit PoC, or write-up</p>
              </TabsContent>

              {(["meli", "redforge"] as const).map(t => (
                <TabsContent key={t} value={t}>
                  <div
                    className="p-4 rounded-lg text-[11px] text-muted-foreground font-mono"
                    style={{ background: '#09090f', border: '1px solid #111118', color: '#475569' }}
                  >
                    Use the {t === "meli" ? "Meli C2" : "REDFORGE"} page to import captured commands as inputs.
                  </div>
                </TabsContent>
              ))}

              <TabsContent value="cve" className="space-y-3">
                <Input
                  value={cve}
                  onChange={e => setCve(e.target.value)}
                  placeholder="CVE-2024-XXXXX or description"
                  className="font-mono text-sm h-9"
                  style={inputStyle}
                />
              </TabsContent>

              <TabsContent value="mitre" className="space-y-3">
                <Input
                  value={mitre}
                  onChange={e => setMitre(e.target.value)}
                  placeholder="T1059.001 — Command and Scripting Interpreter: PowerShell"
                  className="font-mono text-sm h-9"
                  style={inputStyle}
                />
              </TabsContent>

              <TabsContent value="natural" className="space-y-3">
                <Textarea
                  value={natural}
                  onChange={e => setNatural(e.target.value)}
                  placeholder="Describe the attack technique: e.g. 'A technique that uses Windows scheduled tasks to persist across reboots while evading EDR...'"
                  className="font-mono text-sm min-h-48 resize-y"
                  style={inputStyle}
                />
              </TabsContent>
            </Tabs>

            <div className="flex gap-2 mt-4">
              <ForgeButton onClick={addInput} disabled={!getContent().trim() || createInput.isPending}>
                <Plus className="w-3.5 h-3.5" />
                Add to Queue
              </ForgeButton>
            </div>
          </div>

          {/* Analysis Results */}
          {(analyzing || analysisResult) && (
            <div className="rounded-lg p-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
              <SectionTitle label="Analysis Results" color="purple" />
              {analyzing ? (
                <div className="space-y-3">
                  {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-4 w-full" style={{ background: '#0a0a14' }} />)}
                  <p className="text-[11px] font-mono animate-pulse" style={{ color: '#475569' }}>Local AI is analyzing inputs...</p>
                </div>
              ) : analysisResult && (
                <div className="space-y-5 font-mono">
                  <div>
                    <div className="text-[9px] tracking-[0.3em] uppercase mb-2" style={{ color: '#475569' }}>Sophistication Score</div>
                    <span
                      className="text-3xl font-black"
                      style={{ color: analysisResult.sophisticationScore >= 8 ? '#ef4444' : analysisResult.sophisticationScore >= 5 ? '#f97316' : '#475569' }}
                    >
                      {analysisResult.sophisticationScore}
                      <span className="text-lg" style={{ color: '#475569' }}>/10</span>
                    </span>
                  </div>
                  <div>
                    <div className="text-[9px] tracking-[0.3em] uppercase mb-2" style={{ color: '#475569' }}>MITRE ATT&CK IDs</div>
                    <div className="flex flex-wrap gap-1.5">
                      {analysisResult.mitreIds.map(id => (
                        <span key={id} className="px-2 py-0.5 rounded text-[10px] font-mono" style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}>{id}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] tracking-[0.3em] uppercase mb-2" style={{ color: '#475569' }}>Techniques Identified</div>
                    <div className="flex flex-wrap gap-1.5">
                      {analysisResult.techniques.map(t => (
                        <span key={t} className="px-2 py-0.5 rounded text-[10px] font-mono" style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.2)', color: '#f97316' }}>{t}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-[9px] tracking-[0.3em] uppercase mb-2" style={{ color: '#475569' }}>Summary</div>
                    <p className="text-xs leading-relaxed" style={{ color: '#475569' }}>{analysisResult.summary}</p>
                  </div>
                  <ForgeButton onClick={() => navigate("/mutation-lab")} className="w-full">
                    Proceed to Mutation Lab <ArrowRight className="w-3.5 h-3.5" />
                  </ForgeButton>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Queue */}
        <div className="space-y-4">
          <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <div className="flex items-center justify-between mb-4">
              <SectionTitle label="Input Queue" />
              <span className="text-[11px] font-black font-mono" style={{ color: '#f97316' }}>{inputs?.length ?? 0}</span>
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14 w-full" style={{ background: '#0a0a14' }} />)}
              </div>
            ) : inputs?.length === 0 ? (
              <p className="text-[11px] font-mono py-6 text-center" style={{ color: '#64748b' }}>Queue empty. Add inputs above.</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {inputs?.map(input => (
                  <div
                    key={input.id}
                    className="flex items-start justify-between p-3 rounded-lg"
                    style={{ border: '1px solid #0f0f1a', background: '#09090f' }}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span
                          className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded"
                          style={{ background: '#0a0a14', border: '1px solid #111118', color: '#64748b' }}
                        >
                          {input.inputType}
                        </span>
                        {input.analyzed && (
                          <span
                            className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded"
                            style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' }}
                          >
                            analyzed
                          </span>
                        )}
                      </div>
                      <div className="text-[10px] font-mono truncate" style={{ color: '#475569' }}>
                        {input.label || input.content.slice(0, 60)}
                      </div>
                    </div>
                    <button
                      onClick={() => removeInput(input.id)}
                      className="ml-2 shrink-0 transition-colors"
                      style={{ color: '#64748b' }}
                      onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={e => (e.currentTarget.style.color = '#1a1a2e')}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <ForgeButton
              onClick={runAnalysis}
              disabled={!inputs?.length || analyzing}
              variant="outline"
              className="w-full"
            >
              <Zap className="w-3.5 h-3.5" />
              {analyzing ? "Analyzing..." : "Analyze Queue"}
            </ForgeButton>
            <ForgeButton
              onClick={() => navigate("/mutation-lab")}
              disabled={!inputs?.length}
              className="w-full"
            >
              <FlaskConical className="w-3.5 h-3.5" />
              Proceed to Generation
            </ForgeButton>
          </div>
        </div>
      </div>
    </div>
  );
}

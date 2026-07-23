import React from "react";
import { useListThreats, useUpdateThreat, useDeleteThreat, useSendThreatToRedforge, getListThreatsQueryKey } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import { LayoutGrid, List, Search, CheckSquare, Crosshair, Trash2 } from "lucide-react";

function noveltyGradient(score: number) {
  if (score >= 9) return { background: 'linear-gradient(90deg, #7d3dff, #6d28d9)', boxShadow: '0 0 8px rgba(125,61,255,0.4)' };
  if (score >= 7) return { background: 'linear-gradient(90deg, #dc2626, #991b1b)' };
  if (score >= 4) return { background: 'linear-gradient(90deg, #ea580c, #c2410c)' };
  return { background: '#1e293b' };
}

function NoveltyBadge({ score }: { score: number }) {
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded text-[10px] font-black font-mono tracking-wider text-white shrink-0"
      style={noveltyGradient(score)}
    >
      {score}/10
    </span>
  );
}

function SectionTitle({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-[3px] h-4 rounded-full shrink-0" style={{ background: '#f97316' }} />
      <span className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono" style={{ color: '#f97316' }}>
        {label}
      </span>
    </div>
  );
}

const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

export default function ThreatLibrary() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [search, setSearch] = React.useState("");
  const [platform, setPlatform] = React.useState<string>("all");
  const [noveltyRange, setNoveltyRange] = React.useState<[number, number]>([1, 10]);
  const [masteredFilter, setMasteredFilter] = React.useState<"all" | "mastered" | "unmastered">("all");
  const [redforgeFilter, setRedforgeFilter] = React.useState<"all" | "sent" | "unsent">("all");
  const [viewMode, setViewMode] = React.useState<"grid" | "list">("grid");
  const [selectedIds, setSelectedIds] = React.useState<Set<number>>(new Set());

  const queryParams = {
    search: search || undefined,
    platform: platform !== "all" ? platform : undefined,
    noveltyMin: noveltyRange[0],
    noveltyMax: noveltyRange[1],
    mastered: masteredFilter === "all" ? undefined : masteredFilter === "mastered",
    sentToRedforge: redforgeFilter === "all" ? undefined : redforgeFilter === "sent",
    limit: 100,
    offset: 0,
  };

  const { data, isLoading } = useListThreats(queryParams, { query: { queryKey: getListThreatsQueryKey(queryParams) } });
  const threats = data?.threats ?? [];
  const total = data?.total ?? 0;

  const updateThreat = useUpdateThreat();
  const deleteThreat = useDeleteThreat();
  const sendToRedforge = useSendThreatToRedforge();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: getListThreatsQueryKey() });

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const bulkMaster = async () => {
    for (const id of selectedIds) {
      await updateThreat.mutateAsync({ id, data: { mastered: true } });
    }
    invalidate();
    setSelectedIds(new Set());
  };

  const bulkSendRedforge = async () => {
    for (const id of selectedIds) {
      await sendToRedforge.mutateAsync({ id });
    }
    invalidate();
    setSelectedIds(new Set());
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this threat?")) return;
    await deleteThreat.mutateAsync({ id });
    invalidate();
  };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Threat Library</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            {total} threats in your library
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className="p-2 rounded transition-all"
            style={viewMode === "grid"
              ? { background: 'rgba(249,115,22,0.12)', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)' }
              : { background: '#09090f', color: '#2a2a3e', border: '1px solid #111118' }
            }
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className="p-2 rounded transition-all"
            style={viewMode === "list"
              ? { background: 'rgba(249,115,22,0.12)', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)' }
              : { background: '#09090f', color: '#2a2a3e', border: '1px solid #111118' }
            }
          >
            <List className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <div className="rounded-lg p-5 space-y-5 sticky top-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <SectionTitle label="Filters" />

            <div className="space-y-2">
              <label className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: '#475569' }}>Search</label>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#2a2a3e' }} />
                <Input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search threats..."
                  className="pl-9 font-mono text-xs h-9"
                  style={inputStyle}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <label className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: '#475569' }}>Novelty Range</label>
                <span className="text-[10px] font-black font-mono" style={{ color: '#f97316' }}>{noveltyRange[0]}–{noveltyRange[1]}</span>
              </div>
              <Slider
                value={noveltyRange}
                onValueChange={v => setNoveltyRange(v as [number, number])}
                min={1} max={10} step={1} minStepsBetweenThumbs={1}
              />
            </div>

            {[
              { label: "Platform", value: platform, onChange: setPlatform, options: ["all", "linux", "windows", "macos", "cloud", "network", "mobile", "iot"] },
              { label: "Mastered", value: masteredFilter, onChange: (v: string) => setMasteredFilter(v as typeof masteredFilter), options: [{ value: "all", label: "All" }, { value: "mastered", label: "Mastered" }, { value: "unmastered", label: "Not Mastered" }] },
              { label: "REDFORGE", value: redforgeFilter, onChange: (v: string) => setRedforgeFilter(v as typeof redforgeFilter), options: [{ value: "all", label: "All" }, { value: "sent", label: "Sent" }, { value: "unsent", label: "Not Sent" }] },
            ].map(({ label, value, onChange, options }) => (
              <div key={label} className="space-y-1.5">
                <label className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: '#475569' }}>{label}</label>
                <Select value={value} onValueChange={onChange}>
                  <SelectTrigger className="font-mono text-xs h-9" style={inputStyle}><SelectValue /></SelectTrigger>
                  <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                    {options.map(opt => {
                      const v = typeof opt === 'string' ? opt : opt.value;
                      const l = typeof opt === 'string' ? opt : opt.label;
                      return <SelectItem key={v} value={v} className="font-mono text-xs">{l}</SelectItem>;
                    })}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </div>

        {/* Threat Grid/List */}
        <div className="lg:col-span-3 space-y-4">
          {/* Bulk Actions */}
          {selectedIds.size > 0 && (
            <div
              className="flex items-center gap-3 p-3 rounded-lg"
              style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.25)' }}
            >
              <span className="text-[11px] font-mono font-bold" style={{ color: '#f97316' }}>{selectedIds.size} selected</span>
              <button
                onClick={bulkMaster}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                style={{ background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }}
              >
                <CheckSquare className="w-3 h-3" />Mark Mastered
              </button>
              <button
                onClick={bulkSendRedforge}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}
              >
                <Crosshair className="w-3 h-3" />Send to REDFORGE
              </button>
              <button
                onClick={() => setSelectedIds(new Set())}
                className="ml-auto text-[10px] font-mono"
                style={{ color: '#2a2a3e' }}
              >
                Clear
              </button>
            </div>
          )}

          {isLoading ? (
            <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-3" : "space-y-2"}>
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-lg" style={{ background: '#05060a' }} />
              ))}
            </div>
          ) : threats.length === 0 ? (
            <div className="text-center py-20 font-mono">
              <div className="text-4xl mb-4" style={{ color: '#0f0f1a' }}>⊘</div>
              <p className="text-sm" style={{ color: '#475569' }}>No threats match your filters.</p>
            </div>
          ) : viewMode === "grid" ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {threats.map(threat => (
                <div key={threat.id} className="relative group">
                  <div className="absolute top-3 left-3 z-10">
                    <Checkbox
                      checked={selectedIds.has(threat.id)}
                      onCheckedChange={() => toggleSelect(threat.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity data-[state=checked]:opacity-100"
                    />
                  </div>
                  <button
                    onClick={() => navigate(`/threat-analysis/${threat.id}`)}
                    className="w-full p-4 pl-10 rounded-lg transition-all duration-150 text-left"
                    style={{ border: '1px solid #111118', background: '#0d0d1a' }}
                    onMouseEnter={e => {
                      e.currentTarget.style.borderColor = 'rgba(249,115,22,0.2)';
                      e.currentTarget.style.background = '#0f0f1e';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.borderColor = '#111118';
                      e.currentTarget.style.background = '#0d0d1a';
                    }}
                  >
                    <div
                      className="absolute top-0 left-0 right-0 h-px rounded-t-lg"
                      style={{ background: threat.noveltyScore >= 9
                        ? 'linear-gradient(90deg, rgba(125,61,255,0.4) 0%, transparent 60%)'
                        : threat.noveltyScore >= 7
                        ? 'linear-gradient(90deg, rgba(220,38,38,0.3) 0%, transparent 60%)'
                        : 'linear-gradient(90deg, rgba(249,115,22,0.2) 0%, transparent 60%)'
                      }}
                    />
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="text-sm font-semibold line-clamp-2 leading-snug" style={{ color: '#94a3b8' }}>{threat.name}</div>
                      <NoveltyBadge score={threat.noveltyScore} />
                    </div>
                    <p className="text-[11px] font-mono line-clamp-2 mb-3 leading-relaxed" style={{ color: '#475569' }}>{threat.description}</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded" style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}>{threat.platform}</span>
                      {threat.mastered && <span className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' }}>mastered</span>}
                      {threat.sentToRedforge && <span className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', color: '#60a5fa' }}>redforge</span>}
                      <span className="text-[9px] font-mono ml-auto" style={{ color: '#64748b' }}>{new Date(threat.createdAt).toLocaleDateString()}</span>
                    </div>
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); handleDelete(threat.id); }}
                    className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: '#475569' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-1.5">
              {threats.map(threat => (
                <div key={threat.id} className="flex items-center gap-3 group">
                  <Checkbox checked={selectedIds.has(threat.id)} onCheckedChange={() => toggleSelect(threat.id)} />
                  <button
                    onClick={() => navigate(`/threat-analysis/${threat.id}`)}
                    className="flex-1 flex items-center gap-4 p-3 rounded-lg transition-all duration-150 text-left"
                    style={{ border: '1px solid #111118', background: '#0d0d1a' }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(249,115,22,0.2)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#111118'; }}
                  >
                    <NoveltyBadge score={threat.noveltyScore} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: '#94a3b8' }}>{threat.name}</div>
                      <div className="text-[10px] font-mono" style={{ color: '#475569' }}>{threat.platform} · {new Date(threat.createdAt).toLocaleDateString()}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {threat.mastered && <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.08)', color: '#4ade80' }}>mastered</span>}
                      {threat.sentToRedforge && <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: 'rgba(59,130,246,0.08)', color: '#60a5fa' }}>rf</span>}
                      <span className="text-[10px] font-mono" style={{ color: '#475569' }}>Det: {threat.estimatedDetectionRate}%</span>
                    </div>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

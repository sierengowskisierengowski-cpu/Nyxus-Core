import React from "react";
import {
  useListKnowledgeEntries,
  useCreateKnowledgeEntry,
  useDeleteKnowledgeEntry,
  useGetKnowledgeStats,
  getListKnowledgeEntriesQueryKey,
  getGetKnowledgeStatsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, Search, Database } from "lucide-react";

const CATEGORIES = [
  "MITRE", "Malware", "LOLBAS", "GTFOBINS", "CVE", "Exploit", "Cowrie",
  "Custom", "OWASP", "WiFi", "Bluetooth", "Container", "IoT", "Crypto", "Supply Chain",
];

const categoryStyle: Record<string, React.CSSProperties> = {
  MITRE: { background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.2)', color: '#ff2d55' },
  Malware: { background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)', color: '#fb923c' },
  LOLBAS: { background: 'rgba(234,179,8,0.08)', border: '1px solid rgba(234,179,8,0.2)', color: '#facc15' },
  GTFOBINS: { background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' },
  CVE: { background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', color: '#60a5fa' },
  Exploit: { background: 'rgba(123,94,167,0.08)', border: '1px solid rgba(123,94,167,0.2)', color: '#a78bfa' },
  Cowrie: { background: 'rgba(236,72,153,0.08)', border: '1px solid rgba(236,72,153,0.2)', color: '#f472b6' },
  OWASP: { background: 'rgba(20,184,166,0.08)', border: '1px solid rgba(20,184,166,0.2)', color: '#2dd4bf' },
  Custom: { background: '#0f0f1a', border: '1px solid #111118', color: '#64748b' },
};

const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

export default function KnowledgeBase() {
  const queryClient = useQueryClient();
  const [activeCategory, setActiveCategory] = React.useState<string | undefined>(undefined);
  const [search, setSearch] = React.useState("");
  const [showAdd, setShowAdd] = React.useState(false);
  const [newCategory, setNewCategory] = React.useState("Custom");
  const [newTitle, setNewTitle] = React.useState("");
  const [newContent, setNewContent] = React.useState("");
  const [newSource, setNewSource] = React.useState("");

  const listParams = { category: activeCategory, search: search || undefined };
  const { data: entries, isLoading } = useListKnowledgeEntries(listParams, { query: { queryKey: getListKnowledgeEntriesQueryKey(listParams) } });
  const { data: stats } = useGetKnowledgeStats({ query: { queryKey: getGetKnowledgeStatsQueryKey() } });
  const createEntry = useCreateKnowledgeEntry();
  const deleteEntry = useDeleteKnowledgeEntry();

  const handleCreate = async () => {
    if (!newTitle.trim() || !newContent.trim()) return;
    await createEntry.mutateAsync({
      data: {
        category: newCategory,
        title: newTitle,
        content: newContent,
        source: newSource || "Manual",
        tags: [],
      },
    });
    queryClient.invalidateQueries({ queryKey: getListKnowledgeEntriesQueryKey() });
    queryClient.invalidateQueries({ queryKey: getGetKnowledgeStatsQueryKey() });
    setShowAdd(false);
    setNewTitle(""); setNewContent(""); setNewSource("");
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this knowledge entry?")) return;
    await deleteEntry.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: getListKnowledgeEntriesQueryKey() });
    queryClient.invalidateQueries({ queryKey: getGetKnowledgeStatsQueryKey() });
  };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Knowledge Base</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            {stats?.total ?? 0} entries across {stats?.byCategory?.length ?? 0} categories
          </p>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
          style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
          onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
        >
          <Plus className="w-3.5 h-3.5" />Add Entry
        </button>
      </div>

      {showAdd && (
        <div className="rounded-lg p-5 space-y-4" style={{ background: 'rgba(249,115,22,0.04)', border: '1px solid rgba(249,115,22,0.2)' }}>
          <div className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono mb-3" style={{ color: '#f97316' }}>New Knowledge Entry</div>
          <div className="grid grid-cols-2 gap-3">
            <Select value={newCategory} onValueChange={setNewCategory}>
              <SelectTrigger className="font-mono text-xs h-9" style={inputStyle}><SelectValue /></SelectTrigger>
              <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                {CATEGORIES.map(c => <SelectItem key={c} value={c} className="font-mono text-xs">{c}</SelectItem>)}
              </SelectContent>
            </Select>
            <Input value={newSource} onChange={e => setNewSource(e.target.value)} placeholder="Source URL or reference" className="font-mono text-xs h-9" style={inputStyle} />
          </div>
          <Input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Entry title" className="font-mono text-sm h-9" style={inputStyle} />
          <Textarea
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder="Paste content, code, documentation, or IOCs..."
            className="font-mono text-xs min-h-32 resize-y"
            style={inputStyle}
          />
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!newTitle.trim() || !newContent.trim() || createEntry.isPending}
              className="px-4 py-2 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono disabled:opacity-40"
              style={{ background: '#f97316', color: 'white' }}
            >
              Save Entry
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-4 py-2 rounded-lg text-[11px] font-mono"
              style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Category Sidebar */}
        <div className="space-y-4 lg:col-span-1">
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <div className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono mb-3" style={{ color: '#f97316' }}>Categories</div>
            <div className="space-y-0.5">
              <button
                onClick={() => setActiveCategory(undefined)}
                className="w-full text-left px-3 py-1.5 rounded text-[11px] font-mono flex items-center justify-between transition-all"
                style={!activeCategory
                  ? { background: 'rgba(249,115,22,0.1)', color: '#f97316' }
                  : { color: '#475569' }
                }
              >
                <span className="flex items-center gap-2"><Database className="w-3 h-3" />All</span>
                <span className="font-bold" style={{ color: '#f97316' }}>{stats?.total ?? 0}</span>
              </button>
              {CATEGORIES.map(cat => {
                const catStats = stats?.byCategory?.find((b: { category: string; count: number }) => b.category === cat);
                const count = catStats?.count ?? 0;
                const isActive = activeCategory === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setActiveCategory(cat)}
                    className="w-full text-left px-3 py-1.5 rounded text-[11px] font-mono flex items-center justify-between transition-all"
                    style={isActive
                      ? { background: 'rgba(249,115,22,0.08)', color: '#f97316' }
                      : { color: '#475569' }
                    }
                    onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = '#374151'; }}
                    onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = '#475569'; }}
                  >
                    <span>{cat}</span>
                    {count > 0 && <span className="font-bold" style={{ color: isActive ? '#f97316' : '#1a1a2e' }}>{count}</span>}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Coverage */}
          <div className="rounded-lg p-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
            <div className="text-[9px] tracking-[0.25em] uppercase font-bold font-mono mb-3" style={{ color: '#7B5EA7' }}>Top Coverage</div>
            <div className="space-y-2">
              {stats?.byCategory?.slice(0, 6).map((cat: { category: string; count: number }) => {
                const max = Math.max(...(stats?.byCategory?.map((c: { category: string; count: number }) => c.count) ?? [1]));
                const pct = Math.round((cat.count / max) * 100);
                return (
                  <div key={cat.category}>
                    <div className="flex justify-between text-[10px] font-mono mb-1">
                      <span style={{ color: '#475569' }}>{cat.category}</span>
                      <span style={{ color: '#64748b' }}>{cat.count}</span>
                    </div>
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: '#05060a' }}>
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #7B5EA7, #6d28d9)' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Entry List */}
        <div className="lg:col-span-3 space-y-4">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: '#475569' }} />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search entries..."
              className="pl-9 font-mono text-sm h-10"
              style={inputStyle}
            />
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 w-full rounded-lg" style={{ background: '#05060a' }} />)}
            </div>
          ) : entries?.length === 0 ? (
            <div className="text-center py-16">
              <Database className="w-10 h-10 mx-auto mb-3" style={{ color: '#0f0f1a' }} />
              <p className="text-sm font-mono" style={{ color: '#64748b' }}>
                {activeCategory ? `No ${activeCategory} entries yet.` : "Knowledge base is empty. Add your first entry."}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {entries?.map(entry => (
                <div
                  key={entry.id}
                  className="p-4 rounded-lg group transition-all"
                  style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span
                          className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded"
                          style={categoryStyle[entry.category] ?? categoryStyle.Custom}
                        >
                          {entry.category}
                        </span>
                        {entry.source && entry.source !== "Manual" && (
                          <span className="text-[9px] font-mono truncate max-w-48" style={{ color: '#475569' }}>{entry.source}</span>
                        )}
                      </div>
                      <div className="text-sm font-semibold mb-1.5" style={{ color: '#94a3b8' }}>{entry.title}</div>
                      <p className="text-[11px] font-mono line-clamp-3 leading-relaxed" style={{ color: '#475569' }}>{entry.content}</p>
                    </div>
                    <button
                      onClick={() => handleDelete(entry.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                      style={{ color: '#64748b' }}
                      onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                      onMouseLeave={e => (e.currentTarget.style.color = '#1a1a2e')}
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
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

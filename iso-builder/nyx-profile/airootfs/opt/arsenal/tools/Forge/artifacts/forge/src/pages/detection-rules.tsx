import React from "react";
import {
  useListDetectionRules,
  useCreateDetectionRule,
  useGetDetectionRule,
  useUpdateDetectionRule,
  useDeleteDetectionRule,
  getListDetectionRulesQueryKey,
  getGetDetectionRuleQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash2, CheckSquare, Edit2 } from "lucide-react";

const inputStyle: React.CSSProperties = { background: '#07070e', borderColor: '#111118', color: '#64748b', fontFamily: 'JetBrains Mono, monospace' };

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

export default function DetectionRules() {
  const queryClient = useQueryClient();
  const { data: rules, isLoading } = useListDetectionRules({}, { query: { queryKey: getListDetectionRulesQueryKey({}) } });
  const createRule = useCreateDetectionRule();
  const updateRule = useUpdateDetectionRule();
  const deleteRule = useDeleteDetectionRule();

  const [activeTab, setActiveTab] = React.useState("sigma");
  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [editContent, setEditContent] = React.useState("");
  const [editName, setEditName] = React.useState("");
  const [showCreate, setShowCreate] = React.useState(false);
  const [newName, setNewName] = React.useState("");
  const [newContent, setNewContent] = React.useState("");
  const [newType, setNewType] = React.useState("sigma");

  const filteredRules = rules?.filter(r => r.ruleType === activeTab) ?? [];

  const { data: selectedRule } = useGetDetectionRule(editingId!, {
    query: { queryKey: getGetDetectionRuleQueryKey(editingId!), enabled: !!editingId },
  });

  const startEdit = (rule: { id: number; name: string; content: string }) => {
    setEditingId(rule.id);
    setEditName(rule.name);
    setEditContent(rule.content);
  };

  const saveEdit = async () => {
    if (!editingId) return;
    await updateRule.mutateAsync({ id: editingId, data: { name: editName, content: editContent } });
    queryClient.invalidateQueries({ queryKey: getListDetectionRulesQueryKey({}) });
    if (editingId) queryClient.invalidateQueries({ queryKey: getGetDetectionRuleQueryKey(editingId) });
    setEditingId(null);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this rule?")) return;
    await deleteRule.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: getListDetectionRulesQueryKey({}) });
    if (editingId === id) setEditingId(null);
  };

  const createNew = async () => {
    if (!newName || !newContent) return;
    await createRule.mutateAsync({ data: { ruleType: newType, name: newName, content: newContent, mitreIds: [] } });
    queryClient.invalidateQueries({ queryKey: getListDetectionRulesQueryKey({}) });
    setShowCreate(false);
    setNewName(""); setNewContent(""); setNewType("sigma");
  };

  const typeStyle: Record<string, React.CSSProperties> = {
    sigma: { background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', color: '#60a5fa' },
    snort: { background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.25)', color: '#f97316' },
    yara: { background: 'rgba(123,94,167,0.1)', border: '1px solid rgba(123,94,167,0.25)', color: '#a78bfa' },
  };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Detection Rules Lab</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Sigma, Snort/Suricata, and YARA rules from generated threats
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
          style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
          onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
          onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
        >
          <Plus className="w-3.5 h-3.5" />
          Import Rule
        </button>
      </div>

      {showCreate && (
        <div className="rounded-lg p-5 space-y-4" style={{ background: 'rgba(249,115,22,0.04)', border: '1px solid rgba(249,115,22,0.2)' }}>
          <SectionTitle label="Import New Rule" />
          <div className="grid grid-cols-3 gap-3">
            <Select value={newType} onValueChange={setNewType}>
              <SelectTrigger className="font-mono text-xs h-9" style={inputStyle}><SelectValue /></SelectTrigger>
              <SelectContent style={{ background: '#0d0d1a', borderColor: '#1a1a2e' }}>
                <SelectItem value="sigma" className="font-mono text-xs">Sigma</SelectItem>
                <SelectItem value="snort" className="font-mono text-xs">Snort/Suricata</SelectItem>
                <SelectItem value="yara" className="font-mono text-xs">YARA</SelectItem>
              </SelectContent>
            </Select>
            <Input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Rule name" className="font-mono text-xs h-9 col-span-2" style={inputStyle} />
          </div>
          <Textarea
            value={newContent}
            onChange={e => setNewContent(e.target.value)}
            placeholder="Paste rule content..."
            className="font-mono text-xs min-h-48"
            style={{ ...inputStyle, color: '#4ade80', lineHeight: '1.6' }}
          />
          <div className="flex gap-2">
            <button
              onClick={createNew}
              disabled={!newName || !newContent || createRule.isPending}
              className="px-4 py-2 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono disabled:opacity-40"
              style={{ background: '#f97316', color: 'white' }}
            >
              Save Rule
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono"
              style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="p-1" style={{ background: '#09090f', border: '1px solid #111118' }}>
          {["sigma", "snort", "yara"].map(tab => (
            <TabsTrigger key={tab} value={tab} className="font-mono text-xs tracking-wider uppercase">
              {tab === "snort" ? "Snort/Suricata" : tab.toUpperCase()} ({rules?.filter(r => r.ruleType === tab).length ?? 0})
            </TabsTrigger>
          ))}
        </TabsList>

        {["sigma", "snort", "yara"].map(tab => (
          <TabsContent key={tab} value={tab} className="mt-5">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              {/* Rule List */}
              <div className="space-y-1.5">
                {isLoading ? (
                  [...Array(4)].map((_, i) => <Skeleton key={i} className="h-14 w-full rounded-lg" style={{ background: '#0a0a14' }} />)
                ) : filteredRules.length === 0 ? (
                  <p className="text-[11px] font-mono py-6" style={{ color: '#475569' }}>
                    No {tab} rules yet. Generate threats to auto-create rules.
                  </p>
                ) : filteredRules.map(rule => (
                  <div
                    key={rule.id}
                    className="p-3 rounded-lg cursor-pointer transition-all duration-150 group"
                    style={editingId === rule.id
                      ? { border: '1px solid rgba(249,115,22,0.4)', background: 'rgba(249,115,22,0.06)' }
                      : { border: '1px solid #111118', background: '#0d0d1a' }
                    }
                    onClick={() => startEdit(rule)}
                    onMouseEnter={e => { if (editingId !== rule.id) (e.currentTarget as HTMLElement).style.borderColor = '#1a1a2e'; }}
                    onMouseLeave={e => { if (editingId !== rule.id) (e.currentTarget as HTMLElement).style.borderColor = '#111118'; }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-semibold truncate mb-1.5" style={{ color: editingId === rule.id ? '#f97316' : '#94a3b8' }}>{rule.name}</div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] font-mono tracking-wider uppercase px-1.5 py-0.5 rounded" style={typeStyle[rule.ruleType]}>{rule.ruleType}</span>
                          {rule.tested && <span className="text-[9px] font-mono tracking-wider px-1.5 py-0.5 rounded" style={{ background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)', color: '#4ade80' }}>tested</span>}
                          {(rule.mitreIds?.length ?? 0) > 0 && <span className="text-[9px] font-mono" style={{ color: '#475569' }}>{rule.mitreIds?.[0]}</span>}
                        </div>
                      </div>
                      <button
                        onClick={e => { e.stopPropagation(); handleDelete(rule.id); }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                        style={{ color: '#475569' }}
                        onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                        onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Rule Editor */}
              <div className="lg:col-span-2">
                {editingId ? (
                  <div className="rounded-lg p-5 space-y-4" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid rgba(249,115,22,0.15)' }}>
                    <div className="flex items-center justify-between gap-3">
                      <Input
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        className="font-mono text-sm font-bold flex-1 h-9"
                        style={{ ...inputStyle, color: '#e2e8f0', fontWeight: 700 }}
                      />
                      <div className="flex gap-2 shrink-0">
                        <button
                          onClick={saveEdit}
                          disabled={updateRule.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono disabled:opacity-40"
                          style={{ background: '#f97316', color: 'white' }}
                        >
                          <CheckSquare className="w-3 h-3" />Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                          style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                    <Textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      className="font-mono text-xs leading-relaxed resize-y"
                      style={{ background: '#04040a', borderColor: '#0f0f1a', color: '#4ade80', minHeight: '420px', lineHeight: '1.7' }}
                    />
                    {selectedRule && !selectedRule.tested && (
                      <button
                        onClick={async () => {
                          await updateRule.mutateAsync({ id: editingId, data: { tested: true } });
                          queryClient.invalidateQueries({ queryKey: getListDetectionRulesQueryKey({}) });
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase"
                        style={{ background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }}
                      >
                        <CheckSquare className="w-3 h-3" />Mark as Tested
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="rounded-lg p-12 text-center" style={{ background: '#09090f', border: '1px solid #0f0f1a' }}>
                    <Edit2 className="w-8 h-8 mx-auto mb-3" style={{ color: '#2e3a50' }} />
                    <p className="text-[11px] font-mono" style={{ color: '#64748b' }}>Select a rule from the list to view and edit it.</p>
                  </div>
                )}
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

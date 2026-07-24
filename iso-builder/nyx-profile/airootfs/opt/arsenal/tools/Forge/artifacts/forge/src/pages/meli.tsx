import React from "react";
import {
  useGetMeliStatus,
  useGetMeliFeed,
  useCreateInput,
  getGetMeliStatusQueryKey,
  getGetMeliFeedQueryKey,
  getListInputsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";
import { Cpu, RefreshCw, Import, CheckCircle, Terminal, Settings, ArrowRight } from "lucide-react";

function SectionTitle({ label, color = 'orange' }: { label: string; color?: 'orange' | 'purple' | 'green' }) {
  const c = color === 'orange' ? '#f97316' : color === 'purple' ? '#7B5EA7' : '#4ade80';
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-[3px] h-4 rounded-full shrink-0" style={{ background: c }} />
      <span className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono" style={{ color: c }}>{label}</span>
    </div>
  );
}

export default function Meli() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();
  const [importedIds, setImportedIds] = React.useState<Set<number>>(new Set());

  const { data: status, refetch: refetchStatus } = useGetMeliStatus({
    query: { queryKey: getGetMeliStatusQueryKey() },
  });
  const { data: feed, isLoading: feedLoading } = useGetMeliFeed({
    query: { queryKey: getGetMeliFeedQueryKey() },
  });
  const createInput = useCreateInput();

  const handleImport = async (command: { id: number; command: string; sourceIp: string }) => {
    await createInput.mutateAsync({
      data: {
        inputType: "meli",
        content: command.command,
        label: `Meli capture: ${command.sourceIp}`,
      },
    });
    queryClient.invalidateQueries({ queryKey: getListInputsQueryKey() });
    setImportedIds(prev => new Set([...prev, command.id]));
  };

  const importAll = async () => {
    const commands = feed?.filter(c => !importedIds.has(c.id)) ?? [];
    for (const cmd of commands) {
      await createInput.mutateAsync({
        data: {
          inputType: "meli",
          content: cmd.command,
          label: `Meli capture: ${cmd.sourceIp}`,
        },
      });
      setImportedIds(prev => new Set([...prev, cmd.id]));
    }
    queryClient.invalidateQueries({ queryKey: getListInputsQueryKey() });
  };

  const unimported = feed?.filter(c => !importedIds.has(c.id)) ?? [];

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Meli Honeypot</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Live Cowrie honeypot command feed — real attacker behavior for threat generation
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unimported.length > 0 && (
            <button
              onClick={importAll}
              disabled={createInput.isPending}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all disabled:opacity-40"
              style={{ background: '#f97316', color: 'white', border: 'none', boxShadow: '0 0 16px rgba(249,115,22,0.2)' }}
              onMouseEnter={e => (e.currentTarget.style.background = '#ea6c10')}
              onMouseLeave={e => (e.currentTarget.style.background = '#f97316')}
            >
              <Import className="w-3.5 h-3.5" />Import All ({unimported.length})
            </button>
          )}
          <button
            onClick={() => navigate("/settings")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-[11px] font-bold tracking-wider uppercase font-mono transition-all"
            style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
          >
            <Settings className="w-3.5 h-3.5" />Configure
          </button>
        </div>
      </div>

      {/* Status Card */}
      <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center relative"
              style={status?.online
                ? { background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)' }
                : { background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }
              }
            >
              <Cpu className="w-5 h-5" style={{ color: status?.online ? '#4ade80' : '#f87171' }} />
              {status?.online && (
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full" style={{ background: '#4ade80', boxShadow: '0 0 4px rgba(74,222,128,0.6)' }} />
              )}
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-base font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>Meli Honeypot</span>
                <span
                  className="text-[9px] font-black font-mono tracking-wider uppercase px-2.5 py-1 rounded"
                  style={status?.online
                    ? { background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }
                    : { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }
                  }
                >
                  {status?.online ? "● ONLINE" : "● OFFLINE"}
                </span>
              </div>
              <p className="text-[11px] font-mono" style={{ color: '#475569' }}>
                {status?.details ?? "Configure Meli URL in Settings to connect"}
              </p>
              {feed && (
                <p className="text-[10px] font-mono mt-0.5" style={{ color: '#2e3a50' }}>
                  {feed.length} commands captured · {unimported.length} pending import
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => refetchStatus()}
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-mono font-bold tracking-wider uppercase transition-all"
            style={{ background: '#09090f', border: '1px solid #111118', color: '#64748b' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
          >
            <RefreshCw className="w-3.5 h-3.5" />Refresh
          </button>
        </div>
      </div>

      {/* Command Feed */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <SectionTitle label="Live Command Feed" color="green" />
          {importedIds.size > 0 && (
            <button
              onClick={() => navigate("/input-lab")}
              className="flex items-center gap-1 text-[11px] font-mono font-bold"
              style={{ color: '#7B5EA7' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#a78bfa')}
              onMouseLeave={e => (e.currentTarget.style.color = '#7B5EA7')}
            >
              {importedIds.size} imported — view in Input Lab
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {feedLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-lg" style={{ background: '#0a0a14' }} />)}
          </div>
        ) : !feed?.length ? (
          <div
            className="p-12 text-center rounded-lg"
            style={{ background: '#09090f', border: '1px solid #0f0f1a' }}
          >
            <Terminal className="w-10 h-10 mx-auto mb-3" style={{ color: '#0f0f1a' }} />
            <p className="text-sm font-mono" style={{ color: '#64748b' }}>No commands captured yet.</p>
            <p className="text-[10px] font-mono mt-2" style={{ color: '#2e3a50' }}>Connect Meli honeypot in Settings to start capturing attacker behavior.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {feed.map(cmd => (
              <div
                key={cmd.id}
                className="p-4 rounded-lg group transition-all"
                style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = '#1a1a2e')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2.5 flex-wrap">
                      <span
                        className="text-[9px] font-mono tracking-wider px-2 py-0.5 rounded"
                        style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', color: '#60a5fa' }}
                      >
                        {cmd.sourceIp}
                      </span>
                      {cmd.session && (
                        <span className="text-[10px] font-mono" style={{ color: '#475569' }}>session: {cmd.session}</span>
                      )}
                      <span className="text-[10px] font-mono ml-auto" style={{ color: '#2e3a50' }}>
                        {new Date(cmd.capturedAt).toLocaleString()}
                      </span>
                    </div>
                    <pre
                      className="text-xs font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed p-3 rounded-lg"
                      style={{ background: '#04040a', color: '#4ade80', border: '1px solid #0a0a14' }}
                    >
                      {cmd.command}
                    </pre>
                  </div>
                  <div className="shrink-0 pt-6">
                    {importedIds.has(cmd.id) ? (
                      <div className="flex items-center gap-1 text-[10px] font-mono font-bold" style={{ color: '#4ade80' }}>
                        <CheckCircle className="w-3.5 h-3.5" />Imported
                      </div>
                    ) : (
                      <button
                        onClick={() => handleImport(cmd)}
                        disabled={createInput.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono opacity-0 group-hover:opacity-100 transition-all disabled:opacity-40"
                        style={{ background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.3)', color: '#f97316' }}
                      >
                        <Import className="w-3 h-3" />Import
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

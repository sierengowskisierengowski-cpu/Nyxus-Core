import React from "react";
import {
  useGetRedforgeStatus,
  useGetRedforgeHistory,
  useListThreats,
  useSendThreatToRedforge,
  getGetRedforgeStatusQueryKey,
  getGetRedforgeHistoryQueryKey,
  getListThreatsQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";
import { Crosshair, CheckCircle, RefreshCw, Clock, Settings, ArrowRight } from "lucide-react";

function SectionTitle({ label, color = 'orange' }: { label: string; color?: 'orange' | 'purple' | 'blue' }) {
  const c = color === 'orange' ? '#f97316' : color === 'purple' ? '#7B5EA7' : '#60a5fa';
  return (
    <div className="flex items-center gap-2 mb-4">
      <div className="w-[3px] h-4 rounded-full shrink-0" style={{ background: c }} />
      <span className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono" style={{ color: c }}>{label}</span>
    </div>
  );
}

function noveltyGradient(score: number) {
  if (score >= 9) return { background: 'linear-gradient(90deg, #7d3dff, #6d28d9)', boxShadow: '0 0 8px rgba(125,61,255,0.4)' };
  if (score >= 7) return { background: 'linear-gradient(90deg, #dc2626, #991b1b)' };
  if (score >= 4) return { background: 'linear-gradient(90deg, #ea580c, #c2410c)' };
  return { background: '#1e293b' };
}

export default function Redforge() {
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();

  const { data: status, isLoading: statusLoading, refetch: refetchStatus } = useGetRedforgeStatus({
    query: { queryKey: getGetRedforgeStatusQueryKey() },
  });
  const { data: history, isLoading: historyLoading } = useGetRedforgeHistory({
    query: { queryKey: getGetRedforgeHistoryQueryKey() },
  });
  const { data: threatsData } = useListThreats({ sentToRedforge: false }, {
    query: { queryKey: getListThreatsQueryKey({ sentToRedforge: false }) },
  });
  const sendToRedforge = useSendThreatToRedforge();
  const unsentThreats = threatsData?.threats ?? [];

  const handleSend = async (id: number) => {
    await sendToRedforge.mutateAsync({ id });
    queryClient.invalidateQueries({ queryKey: getListThreatsQueryKey() });
    queryClient.invalidateQueries({ queryKey: getGetRedforgeHistoryQueryKey() });
  };

  return (
    <div className="p-8 max-w-7xl space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between pb-6" style={{ borderBottom: '1px solid #0f0f1a' }}>
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-7 rounded-full" style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }} />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>REDFORGE</h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Export generated threats as REDFORGE handoff packages
          </p>
        </div>
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

      {/* Connection Status */}
      <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center"
              style={status?.online
                ? { background: 'rgba(74,222,128,0.08)', border: '1px solid rgba(74,222,128,0.2)' }
                : { background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }
              }
            >
              <Crosshair className="w-5 h-5" style={{ color: status?.online ? '#4ade80' : '#ff2d55' }} />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="text-base font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>REDFORGE Handoff</span>
                {statusLoading ? (
                  <Skeleton className="h-5 w-16" style={{ background: '#05060a' }} />
                ) : (
                  <span
                    className="text-[9px] font-black font-mono tracking-wider uppercase px-2.5 py-1 rounded"
                    style={status?.online
                      ? { background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }
                      : { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#ff2d55' }
                    }
                  >
                    {status?.online ? "● READY" : "● UNAVAILABLE"}
                  </span>
                )}
              </div>
              <p className="text-[11px] font-mono" style={{ color: '#475569' }}>{status?.details ?? "Configure REDFORGE URL in Settings to connect"}</p>
              {status?.lastChecked && (
                <p className="text-[10px] font-mono mt-0.5" style={{ color: '#2e3a50' }}>Last checked: {new Date(status.lastChecked).toLocaleTimeString()}</p>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Send Queue */}
        <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
          <SectionTitle label={`Export Queue (${unsentThreats.length})`} />
          {unsentThreats.length === 0 ? (
            <div className="text-center py-10">
              <CheckCircle className="w-8 h-8 mx-auto mb-2" style={{ color: '#4ade80', opacity: 0.4 }} />
              <p className="text-[11px] font-mono" style={{ color: '#475569' }}>All threats exported to REDFORGE.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {unsentThreats.map(threat => (
                <div
                  key={threat.id}
                  className="flex items-start justify-between gap-3 p-3 rounded-lg group transition-all"
                  style={{ background: '#09090f', border: '1px solid #0f0f1a' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = '#111118')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = '#0f0f1a')}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-semibold mb-1.5 truncate" style={{ color: '#94a3b8' }}>{threat.name}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-[9px] font-black font-mono tracking-wider text-white px-2 py-0.5 rounded" style={noveltyGradient(threat.noveltyScore)}>
                        {threat.noveltyScore}/10
                      </span>
                      <span className="text-[9px] font-mono" style={{ color: '#475569' }}>{threat.platform}</span>
                      <span className="text-[9px] font-mono" style={{ color: threat.estimatedDetectionRate < 30 ? '#ef4444' : '#374151' }}>
                        Det: {threat.estimatedDetectionRate}%
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSend(threat.id)}
                    disabled={sendToRedforge.isPending || !status?.online}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono shrink-0 disabled:opacity-40 transition-all"
                    style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', color: '#60a5fa' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'rgba(59,130,246,0.15)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'rgba(59,130,246,0.1)')}
                  >
                    <Crosshair className="w-3 h-3" />Export
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* History */}
        <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
          <SectionTitle label="Export History" color="blue" />
          {historyLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-14 w-full rounded-lg" style={{ background: '#05060a' }} />)}
            </div>
          ) : !history?.length ? (
            <div className="text-center py-10">
              <Clock className="w-8 h-8 mx-auto mb-2" style={{ color: '#0f0f1a' }} />
              <p className="text-[11px] font-mono" style={{ color: '#475569' }}>No export history yet.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map(item => (
                <div
                  key={item.id}
                  className="p-3 rounded-lg"
                  style={{ background: '#09090f', border: '1px solid #0f0f1a' }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-[11px] font-semibold truncate mb-1" style={{ color: '#94a3b8' }}>{item.threatName}</div>
                      <div className="text-[10px] font-mono" style={{ color: '#475569' }}>
                        {item.missionId && <span className="mr-3 break-all">Artifact: {item.missionId}</span>}
                        {new Date(item.sentAt).toLocaleString()}
                      </div>
                      {item.outcome && <div className="text-[10px] font-mono mt-0.5" style={{ color: '#64748b' }}>{item.outcome}</div>}
                    </div>
                    <div className="shrink-0">
                      {item.score !== null && item.score !== undefined ? (
                        <span className="text-[10px] font-black font-mono tracking-wider px-2 py-1 rounded"
                          style={item.score >= 70
                            ? { background: 'rgba(74,222,128,0.1)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }
                            : item.score >= 40
                            ? { background: 'rgba(249,115,22,0.1)', border: '1px solid rgba(249,115,22,0.3)', color: '#f97316' }
                            : { background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#ff2d55' }
                          }
                        >
                          {item.score}/100
                        </span>
                      ) : (
                        <span className="text-[9px] font-mono" style={{ color: '#475569' }}>
                          {item.outcome ? "Completed" : "Pending"}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Suggested Training */}
      <div className="rounded-lg p-5" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
        <SectionTitle label="Suggested Training Focus" color="purple" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { title: "High Novelty Deployments", desc: "Deploy 8+ novelty threats to stress-test advanced detection capabilities.", action: "View High Novelty" },
            { title: "Unmastered Techniques", desc: "REDFORGE missions targeting techniques you haven't fully documented.", action: "View Unmastered" },
            { title: "Evasion Coverage Gaps", desc: "Focus on threats with low estimated detection rates to find blind spots.", action: "View Low Detection" },
          ].map(item => (
            <div
              key={item.title}
              className="p-4 rounded-lg group cursor-pointer transition-all"
              style={{ background: '#09090f', border: '1px solid #0f0f1a' }}
              onClick={() => navigate("/threat-library")}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#111118')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#0f0f1a')}
            >
              <div className="text-[11px] font-bold mb-1.5" style={{ color: '#94a3b8' }}>{item.title}</div>
              <p className="text-[10px] font-mono leading-relaxed mb-3" style={{ color: '#475569' }}>{item.desc}</p>
              <div className="flex items-center gap-1 text-[10px] font-mono font-bold" style={{ color: '#7B5EA7' }}>
                {item.action}
                <ArrowRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

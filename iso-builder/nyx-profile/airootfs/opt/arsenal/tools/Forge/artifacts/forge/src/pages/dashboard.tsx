import { useGetDashboardStats, useGetRecentThreats, useGetTopThreats, useGetRedforgeStatus, useGetMeliStatus } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";
import { Flame, Shield, BookOpen, Trophy, Activity, Cpu, AlertTriangle } from "lucide-react";

function noveltyGradient(score: number) {
  if (score >= 9) return { background: 'linear-gradient(90deg, #7d3dff, #6d28d9)', boxShadow: '0 0 10px rgba(125,61,255,0.4)' };
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

function NoveltyBadge({ score }: { score: number }) {
  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded text-[10px] font-black font-mono tracking-wider text-white shrink-0"
      style={noveltyGradient(score)}
    >
      {noveltyLabel(score)} {score}/10
    </span>
  );
}

function StatusIndicator({ online, name }: { online: boolean; name: string }) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-1.5 rounded"
      style={{ background: '#05060a', border: '1px solid #111118' }}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full shrink-0 ${online ? 'animate-pulse' : ''}`}
        style={online
          ? { background: '#4ade80', boxShadow: '0 0 6px rgba(74,222,128,0.7)' }
          : { background: '#ef4444' }
        }
      />
      <span className="text-[10px] font-mono tracking-[0.2em] uppercase" style={{ color: '#2e2e42' }}>{name}</span>
    </div>
  );
}

function SectionTitle({ label, color = 'orange' }: { label: string; color?: 'orange' | 'purple' }) {
  return (
    <div className="flex items-center gap-2 mb-5">
      <div
        className="w-[3px] h-4 rounded-full shrink-0"
        style={{ background: color === 'orange' ? '#f97316' : '#7B5EA7' }}
      />
      <span
        className="text-[10px] tracking-[0.22em] uppercase font-bold font-mono"
        style={{ color: color === 'orange' ? '#f97316' : '#7B5EA7' }}
      >
        {label}
      </span>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useGetDashboardStats();
  const { data: recentThreats, isLoading: recentLoading } = useGetRecentThreats();
  const { data: topThreats } = useGetTopThreats();
  const { data: redforgeStatus } = useGetRedforgeStatus();
  const { data: meliStatus } = useGetMeliStatus();
  const [, navigate] = useLocation();

  const statCards = [
    { label: "Threats Generated", value: stats?.totalThreatsGenerated ?? 0, icon: Flame },
    { label: "Library Size", value: stats?.threatLibrarySize ?? 0, icon: BookOpen },
    { label: "Detection Rules", value: stats?.detectionRulesGenerated ?? 0, icon: Shield },
    { label: "Mastered", value: stats?.masteredCount ?? 0, icon: Trophy },
    { label: "Unanalyzed Meli", value: stats?.unanalyzedMeliCommands ?? 0, icon: Cpu },
    { label: "Knowledge Base", value: stats?.knowledgeBaseSize ?? 0, icon: Activity },
  ];

  const dist = stats?.noveltyDistribution;

  return (
    <div className="p-8 space-y-7 max-w-7xl">
      {/* Page Header */}
      <div
        className="flex items-center justify-between pb-6"
        style={{ borderBottom: '1px solid #0f0f1a' }}
      >
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div
              className="w-[3px] h-7 rounded-full"
              style={{ background: '#f97316', boxShadow: '0 0 8px rgba(249,115,22,0.4)' }}
            />
            <h1 className="text-2xl font-black tracking-tight uppercase" style={{ color: '#e2e8f0' }}>
              FORGE Dashboard
            </h1>
          </div>
          <p className="text-[11px] font-mono tracking-[0.3em] uppercase ml-4" style={{ color: '#475569' }}>
            Threat Research Command Center
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusIndicator online={redforgeStatus?.online ?? false} name="REDFORGE" />
          <StatusIndicator online={meliStatus?.online ?? false} name="MELI" />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="relative overflow-hidden rounded-lg p-5 group transition-all duration-300"
            style={{
              background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)',
              border: '1px solid #111118',
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = 'rgba(249,115,22,0.25)')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#111118')}
          >
            <div
              className="absolute top-0 right-0 w-14 h-14 rounded-bl-full"
              style={{ background: 'linear-gradient(225deg, rgba(249,115,22,0.07) 0%, transparent 70%)' }}
            />
            <div
              className="absolute bottom-0 left-0 right-0 h-px"
              style={{ background: 'linear-gradient(90deg, rgba(249,115,22,0.18) 0%, transparent 60%)' }}
            />
            {statsLoading ? (
              <Skeleton className="h-12 w-full" style={{ background: '#111118' }} />
            ) : (
              <>
                <card.icon
                  className="w-4 h-4 mb-3"
                  style={{ color: '#f97316', opacity: 0.7 }}
                />
                <div
                  className="text-3xl font-black font-mono mb-1"
                  style={{ color: '#f97316' }}
                >
                  {card.value.toLocaleString()}
                </div>
                <div
                  className="text-[9px] tracking-[0.2em] uppercase font-mono"
                  style={{ color: '#475569' }}
                >
                  {card.label}
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Middle Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Novelty Distribution */}
        <div className="rounded-lg p-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
          <SectionTitle label="Novelty Distribution" />
          {dist ? (
            <div className="space-y-4">
              {[
                { label: "Unprecedented", range: "9–10", count: dist.unprecedented, color: 'linear-gradient(90deg, #7d3dff, #6d28d9)', glow: 'rgba(125,61,255,0.4)' },
                { label: "High", range: "7–8", count: dist.high, color: 'linear-gradient(90deg, #dc2626, #991b1b)', glow: 'rgba(220,38,38,0.3)' },
                { label: "Medium", range: "4–6", count: dist.medium, color: 'linear-gradient(90deg, #ea580c, #c2410c)', glow: 'rgba(234,88,12,0.3)' },
                { label: "Low", range: "1–3", count: dist.low, color: '#1e293b', glow: '' },
              ].map(({ label, range, count, color, glow }) => {
                const total = (dist.unprecedented + dist.high + dist.medium + dist.low) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={label}>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: '#2e3452' }}>{label}</span>
                        <span className="text-[9px] font-mono" style={{ color: '#64748b' }}>{range}</span>
                      </div>
                      <span className="text-[11px] font-black font-mono" style={{ color: count > 0 ? '#f97316' : '#475569' }}>{count}</span>
                    </div>
                    <div
                      className="h-1.5 rounded-full overflow-hidden"
                      style={{ background: '#05060a', border: '1px solid #0f0f1a' }}
                    >
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${Math.max(pct, count > 0 ? 4 : 0)}%`,
                          background: color,
                          boxShadow: glow ? `0 0 6px ${glow}` : 'none'
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Skeleton className="h-32 w-full" style={{ background: '#111118' }} />
          )}
        </div>

        {/* Recent Threats */}
        <div className="lg:col-span-2 rounded-lg p-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
          <div className="flex items-center justify-between mb-5">
            <SectionTitle label="Recent Threats" />
            <button
              onClick={() => navigate("/threat-library")}
              className="text-[10px] font-mono tracking-[0.15em] uppercase transition-colors"
              style={{ color: '#f97316' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#fb923c')}
              onMouseLeave={e => (e.currentTarget.style.color = '#f97316')}
            >
              View All →
            </button>
          </div>
          {recentLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" style={{ background: '#05060a' }} />
              ))}
            </div>
          ) : (recentThreats?.length ?? 0) === 0 ? (
            <div className="text-center py-10">
              <Flame className="w-8 h-8 mx-auto mb-3" style={{ color: '#64748b' }} />
              <p className="text-xs font-mono tracking-wider" style={{ color: '#475569' }}>
                No threats generated yet. Start in the Mutation Lab.
              </p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {recentThreats?.slice(0, 6).map((threat) => (
                <button
                  key={threat.id}
                  onClick={() => navigate(`/threat-analysis/${threat.id}`)}
                  className="w-full flex items-center justify-between p-3 rounded-lg transition-all duration-150 text-left group"
                  style={{ border: '1px solid #0f0f1a', background: 'transparent' }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(249,115,22,0.04)';
                    e.currentTarget.style.borderColor = 'rgba(249,115,22,0.15)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.borderColor = '#0f0f1a';
                  }}
                >
                  <div className="flex-1 min-w-0 mr-3">
                    <div className="text-sm font-semibold truncate mb-0.5" style={{ color: '#94a3b8' }}>{threat.name}</div>
                    <div className="text-[10px] font-mono tracking-wider" style={{ color: '#475569' }}>
                      {threat.platform} · {new Date(threat.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                  <NoveltyBadge score={threat.noveltyScore} />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Novelty Threats */}
      {topThreats && topThreats.length > 0 && (
        <div className="rounded-lg p-6" style={{ background: 'linear-gradient(135deg, #0e0e18 0%, #090910 100%)', border: '1px solid #111118' }}>
          <SectionTitle label="Top Novelty Threats" color="purple" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {topThreats.slice(0, 6).map((threat) => (
              <button
                key={threat.id}
                onClick={() => navigate(`/threat-analysis/${threat.id}`)}
                className="p-4 rounded-lg transition-all duration-150 text-left group"
                style={{ border: '1px solid #0f0f1a', background: '#09090f' }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'rgba(123,94,167,0.3)';
                  e.currentTarget.style.background = 'rgba(123,94,167,0.04)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = '#0f0f1a';
                  e.currentTarget.style.background = '#09090f';
                }}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="text-sm font-semibold line-clamp-2 leading-snug" style={{ color: '#94a3b8' }}>{threat.name}</div>
                  <NoveltyBadge score={threat.noveltyScore} />
                </div>
                <div className="text-[10px] font-mono tracking-wider" style={{ color: '#475569' }}>{threat.platform}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action Banner */}
      {((stats?.unanalyzedMeliCommands ?? 0) > 0 || (stats?.unsentToRedforge ?? 0) > 0) && (
        <div
          className="p-4 rounded-lg flex items-center gap-4"
          style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.2)' }}
        >
          <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: '#f97316' }} />
          <div className="flex-1">
            <div className="text-sm font-bold tracking-wide mb-1" style={{ color: '#fb923c' }}>Recommended Actions</div>
            <div className="text-xs font-mono space-y-0.5" style={{ color: '#64748b' }}>
              {(stats?.unanalyzedMeliCommands ?? 0) > 0 && (
                <div>
                  {stats?.unanalyzedMeliCommands} Meli commands awaiting analysis —{" "}
                  <button
                    onClick={() => navigate("/meli")}
                    className="underline transition-colors"
                    style={{ color: '#f97316' }}
                  >
                    review now
                  </button>
                </div>
              )}
              {(stats?.unsentToRedforge ?? 0) > 0 && (
                <div>
                  {stats?.unsentToRedforge} threats not yet sent to REDFORGE —{" "}
                  <button
                    onClick={() => navigate("/redforge")}
                    className="underline transition-colors"
                    style={{ color: '#f97316' }}
                  >
                    deploy
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

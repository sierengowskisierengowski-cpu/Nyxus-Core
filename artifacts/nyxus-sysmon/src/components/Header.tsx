import React from 'react';
import { SysmonData } from '../hooks/useSysmon';

export function Header({ data, isOffline }: { data: SysmonData | null, isOffline: boolean }) {
  const [now, setNow] = React.useState(new Date());

  React.useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-10 flex items-center justify-between px-4 bg-nyxus-panel border-b border-nyxus-dim/30 neon-border shrink-0">
      <div className="flex items-center gap-4">
        <div className="text-nyxus-pink font-bold text-lg glow-text-pink tracking-wider">
          ▣ NYXUS_SYSMON <span className="text-xs text-nyxus-dim">v1.0</span>
        </div>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: 'rgba(255,0,255,0.35)', letterSpacing: '0.22em' }}>NYX-J5W-2026</span>
      </div>
      
      <div className="flex items-center gap-8 text-sm text-nyxus-text">
        <div>hostname: <span className="text-white font-bold">{data?.system?.hostname || 'unknown'}</span></div>
        <div>uptime: <span className="text-nyxus-green">{data?.system?.uptime || '00:00:00'}</span></div>
      </div>

      <div className="flex items-center gap-3 font-mono text-sm">
        {isOffline ? (
          <div className="text-red-500 font-bold flex items-center gap-2 glow-text-red">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" /> OFFLINE
          </div>
        ) : (
          <div className="text-nyxus-green font-bold flex items-center gap-2 glow-text-green">
            <span className="w-2 h-2 rounded-full bg-nyxus-green animate-pulse" /> LIVE
          </div>
        )}
        <div className="text-nyxus-dim">[{now.toLocaleTimeString('en-US', { hour12: false })}]</div>
      </div>
    </header>
  );
}

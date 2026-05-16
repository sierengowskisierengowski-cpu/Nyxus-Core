import React from 'react';
import { useSysmon } from '../hooks/useSysmon';
import { Header } from '../components/Header';
import { CpuCard } from '../components/CpuCard';
import { MemoryCard } from '../components/MemoryCard';
import { NetworkCard } from '../components/NetworkCard';
import { DiskCard } from '../components/DiskCard';
import { CpuCoreGrid } from '../components/CpuCoreGrid';
import { NetworkChart } from '../components/NetworkChart';
import { ProcessTable } from '../components/ProcessTable';

export default function SysMon() {
  const { data, isDemoMode, cpuHistory, networkHistory } = useSysmon();

  return (
    <div className="w-screen h-screen flex flex-col bg-nyxus-bg overflow-hidden p-2 gap-2 text-nyxus-text selection:bg-nyxus-pink/30">
      {isDemoMode && (
        <div style={{
          position: 'fixed', top: 8, right: 12, zIndex: 9999,
          background: 'rgba(255,85,0,0.18)', border: '1.5px solid #ff5500',
          borderRadius: 5, padding: '2px 12px',
          fontFamily: "'Caveat', cursive", fontSize: 14, color: '#ff8844',
          letterSpacing: '0.08em',
        }}>
          ◉ DEMO MODE — start nyxus_sysmon.py for live data
        </div>
      )}
      <Header data={data} isOffline={false} />
      
      {/* Top Cards Row */}
      <div className="flex gap-2 h-48 shrink-0">
        <div className="flex-1 min-w-0"><CpuCard data={data} /></div>
        <div className="flex-1 min-w-0"><MemoryCard data={data} /></div>
        <div className="flex-1 min-w-0"><NetworkCard data={data} /></div>
        <div className="flex-1 min-w-0"><DiskCard data={data} /></div>
      </div>

      {/* CPU Core Grid Row */}
      <div className="shrink-0">
        <CpuCoreGrid data={data} history={cpuHistory} />
      </div>

      {/* Bottom Row - Charts & Table */}
      <div className="flex gap-2 flex-1 min-h-0">
        <div className="flex-[4] min-w-0">
          <NetworkChart 
            history={networkHistory} 
            currentUp={data?.network.total_bytes_sent_per_sec || 0}
            currentDown={data?.network.total_bytes_recv_per_sec || 0}
          />
        </div>
        <div className="flex-[6] min-w-0">
          <ProcessTable data={data} />
        </div>
      </div>
    </div>
  );
}

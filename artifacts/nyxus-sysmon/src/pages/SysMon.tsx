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
  const { data, isOffline, cpuHistory, networkHistory } = useSysmon();

  if (isOffline) {
    return (
      <div className="w-screen h-screen flex flex-col items-center justify-center bg-nyxus-bg text-red-500 p-8">
        <div className="border-4 border-red-500 p-12 flex flex-col items-center gap-6 offline-border bg-red-900/10">
          <h1 className="text-6xl font-bold tracking-widest glow-text-red">SYSMON OFFLINE</h1>
          <p className="text-xl text-red-400">Connection to localhost:9191 refused.</p>
          <div className="mt-8 px-6 py-3 bg-black/50 border border-red-500/50 text-red-300 font-mono text-lg">
            $ start nyxus_sysmon.py
          </div>
          <p className="text-sm mt-4 text-red-500/60 animate-pulse">Retrying connection...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-screen h-screen flex flex-col bg-nyxus-bg overflow-hidden p-2 gap-2 text-nyxus-text selection:bg-nyxus-pink/30">
      <Header data={data} isOffline={isOffline} />
      
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

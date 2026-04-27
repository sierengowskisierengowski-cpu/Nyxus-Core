import React from 'react';
import { SysmonData } from '../hooks/useSysmon';
import { formatBytes } from '../lib/format';

export function MemoryCard({ data }: { data: SysmonData | null }) {
  const mem = data?.memory;
  
  const ramPercent = mem?.ram_percent || 0;
  const swapPercent = mem?.swap_percent || 0;

  return (
    <div className="panel p-4 flex flex-col relative justify-center gap-4">
      <div className="text-nyxus-purple text-xs absolute top-2 left-2 font-bold opacity-70">MEMORY</div>
      
      <div className="mt-4">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-nyxus-dim">RAM</span>
          <span className="text-white font-bold">{formatBytes(mem?.ram_used || 0)} / {formatBytes(mem?.ram_total || 0)}</span>
        </div>
        <div className="h-4 w-full bg-nyxus-dim/20 rounded-sm overflow-hidden border border-nyxus-dim/30">
          <div 
            className="h-full bg-nyxus-purple transition-all duration-500 ease-in-out relative"
            style={{ width: `${ramPercent}%`, boxShadow: '0 0 10px rgba(204,0,255,0.8)' }}
          >
            <div className="absolute inset-0 opacity-20 bg-[repeating-linear-gradient(45deg,transparent,transparent_4px,rgba(255,255,255,0.5)_4px,rgba(255,255,255,0.5)_8px)]" />
          </div>
        </div>
        <div className="text-[10px] text-right mt-1 text-nyxus-green">
          {formatBytes(mem?.ram_free || 0)} FREE
        </div>
      </div>

      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-nyxus-dim">SWAP</span>
          <span className="text-white">{formatBytes(mem?.swap_used || 0)} / {formatBytes(mem?.swap_total || 0)}</span>
        </div>
        <div className="h-3 w-full bg-nyxus-dim/20 rounded-sm overflow-hidden border border-nyxus-dim/30">
          <div 
            className="h-full bg-nyxus-blue transition-all duration-500 ease-in-out"
            style={{ width: `${swapPercent}%`, boxShadow: '0 0 8px rgba(0,136,255,0.6)' }}
          />
        </div>
      </div>
    </div>
  );
}

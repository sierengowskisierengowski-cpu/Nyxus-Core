import React from 'react';
import { SysmonData } from '../hooks/useSysmon';
import { formatBytes } from '../lib/format';
import { ArrowUp, ArrowDown } from 'lucide-react';

export function NetworkCard({ data }: { data: SysmonData | null }) {
  const net = data?.network;
  
  const up = net?.total_bytes_sent_per_sec || 0;
  const down = net?.total_bytes_recv_per_sec || 0;
  
  const totalUp = net?.total_bytes_sent || 0;
  const totalDown = net?.total_bytes_recv || 0;
  
  const interfaces = Object.entries(net?.interfaces || {}).filter(([_, stats]) => stats.bytes_recv_per_sec > 0 || stats.bytes_sent_per_sec > 0);

  return (
    <div className="panel p-4 flex flex-col relative justify-center">
      <div className="text-nyxus-blue text-xs absolute top-2 left-2 font-bold opacity-70">NETWORK</div>
      
      <div className="flex flex-col gap-4 mt-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-nyxus-blue/10 border border-nyxus-blue/30 rounded p-2 flex flex-col items-center">
            <div className="text-nyxus-dim text-[10px] mb-1 flex items-center"><ArrowUp size={12} className="text-nyxus-orange mr-1" /> UPLOAD</div>
            <div className="text-nyxus-orange font-bold">{formatBytes(up)}/s</div>
          </div>
          <div className="bg-nyxus-blue/10 border border-nyxus-blue/30 rounded p-2 flex flex-col items-center">
            <div className="text-nyxus-dim text-[10px] mb-1 flex items-center"><ArrowDown size={12} className="text-nyxus-blue mr-1" /> DOWNLOAD</div>
            <div className="text-nyxus-blue font-bold">{formatBytes(down)}/s</div>
          </div>
        </div>

        <div className="text-[10px] space-y-1">
          <div className="flex justify-between">
            <span className="text-nyxus-dim">SESSION UL:</span>
            <span className="text-nyxus-text">{formatBytes(totalUp)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-nyxus-dim">SESSION DL:</span>
            <span className="text-nyxus-text">{formatBytes(totalDown)}</span>
          </div>
        </div>
        
        <div className="mt-1 flex flex-wrap gap-1">
          {interfaces.length > 0 ? (
            interfaces.map(([name]) => (
              <span key={name} className="px-1.5 py-0.5 bg-nyxus-green/20 text-nyxus-green border border-nyxus-green/30 rounded text-[9px]">
                {name} UP
              </span>
            ))
          ) : (
            <span className="px-1.5 py-0.5 bg-nyxus-dim/20 text-nyxus-dim rounded text-[9px]">NO ACTIVE IFACE</span>
          )}
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { SysmonData } from '../hooks/useSysmon';
import { formatBytes, getColorForPercent } from '../lib/format';

export function DiskCard({ data }: { data: SysmonData | null }) {
  const disks = data?.disks || [];

  return (
    <div className="panel p-4 flex flex-col relative">
      <div className="text-nyxus-green text-xs absolute top-2 left-2 font-bold opacity-70">DISK I/O</div>
      
      <div className="mt-6 flex flex-col gap-3 h-full overflow-y-auto pr-1">
        {disks.length === 0 ? (
          <div className="text-nyxus-dim text-xs text-center my-auto">NO DISKS DETECTED</div>
        ) : (
          disks.map((d, i) => {
            const color = getColorForPercent(d.percent);
            return (
              <div key={i} className="text-xs">
                <div className="flex justify-between mb-1">
                  <span className="truncate max-w-[150px] text-nyxus-text" title={`${d.device} -> ${d.mountpoint}`}>
                    {d.mountpoint} <span className="text-nyxus-dim text-[10px]">({d.device})</span>
                  </span>
                  <span className="font-bold" style={{ color }}>{d.percent}%</span>
                </div>
                <div className="h-2 w-full bg-nyxus-dim/20 rounded-sm overflow-hidden">
                  <div 
                    className="h-full transition-all duration-1000 ease-in-out"
                    style={{ width: `${d.percent}%`, backgroundColor: color, boxShadow: `0 0 5px ${color}` }}
                  />
                </div>
                <div className="text-[9px] text-nyxus-dim text-right mt-0.5">
                  {formatBytes(d.free)} free / {formatBytes(d.total)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

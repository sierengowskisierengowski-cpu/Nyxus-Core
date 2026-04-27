import React from 'react';
import { SysmonData, CpuDataPoint } from '../hooks/useSysmon';
import { AreaChart, Area, ResponsiveContainer, YAxis } from 'recharts';
import { getColorForPercent } from '../lib/format';

export function CpuCoreGrid({ data, history }: { data: SysmonData | null, history: CpuDataPoint[] }) {
  const cores = data?.cpu?.per_core || [];

  return (
    <div className="panel flex flex-col relative h-[250px]">
      <div className="p-4 flex-1 overflow-y-auto">
        <div className="text-nyxus-text/50 text-[10px] font-bold mb-3 tracking-widest">LOGICAL CORES</div>
        
        <div className="grid grid-cols-4 md:grid-cols-8 lg:grid-cols-12 gap-2">
          {cores.map((c, i) => {
            const color = getColorForPercent(c);
            return (
              <div key={i} className="bg-black/50 border border-nyxus-dim/20 p-1.5 rounded flex flex-col items-center justify-between">
                <div className="text-[9px] text-nyxus-dim mb-1">CORE {i}</div>
                <div className="w-full h-12 bg-nyxus-dim/20 rounded-sm overflow-hidden flex items-end">
                  <div 
                    className="w-full transition-all duration-300" 
                    style={{ height: `${c}%`, backgroundColor: color, boxShadow: `0 0 5px ${color}` }}
                  />
                </div>
                <div className="text-[10px] font-bold mt-1 text-white">{c.toFixed(0)}%</div>
              </div>
            );
          })}
        </div>
      </div>
      
      <div className="h-20 w-full border-t border-nyxus-dim/30 relative">
        <div className="absolute top-1 left-2 text-[9px] text-nyxus-pink/50 z-10">60s HISTORY</div>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff00ff" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#ff00ff" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <YAxis domain={[0, 100]} hide />
            <Area 
              type="monotone" 
              dataKey="percent" 
              stroke="#ff00ff" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#cpuGradient)" 
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

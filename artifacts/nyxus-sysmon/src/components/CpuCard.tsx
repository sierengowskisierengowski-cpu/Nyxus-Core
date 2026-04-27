import React from 'react';
import { SysmonData } from '../hooks/useSysmon';

export function CpuCard({ data }: { data: SysmonData | null }) {
  const cpu = data?.cpu;
  const percent = cpu?.percent || 0;
  
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percent / 100) * circumference;

  return (
    <div className="panel p-4 flex flex-col items-center justify-center relative">
      <div className="text-nyxus-pink text-xs absolute top-2 left-2 font-bold opacity-70">CPU USAGE</div>
      
      <div className="relative w-32 h-32 flex items-center justify-center my-2">
        <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
          <circle
            className="text-nyxus-dim/20 stroke-current"
            strokeWidth="8"
            cx="50" cy="50" r="40"
            fill="transparent"
          />
          <circle
            className="text-nyxus-pink stroke-current transition-all duration-500 ease-in-out"
            strokeWidth="8"
            strokeLinecap="round"
            cx="50" cy="50" r="40"
            fill="transparent"
            style={{
              strokeDasharray: circumference,
              strokeDashoffset: strokeDashoffset,
              filter: 'drop-shadow(0 0 6px rgba(255,0,255,0.6))'
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-white glow-text-pink">{percent.toFixed(1)}%</span>
        </div>
      </div>

      <div className="text-xs text-nyxus-text/80 text-center w-full mt-2">
        <div>
          <span className="text-nyxus-dim">FREQ:</span> {(cpu?.freq_mhz || 0) / 1000} GHz 
          <span className="text-nyxus-dim text-[10px] ml-1">/ {(cpu?.freq_max_mhz || 0) / 1000} GHz</span>
        </div>
        <div className="mt-2 flex justify-center gap-2">
          <span className="text-nyxus-dim">LOAD:</span>
          {cpu?.load_avg?.map((l, i) => (
            <span key={i} className="bg-nyxus-dim/20 px-1.5 py-0.5 rounded text-[10px]">{l.toFixed(2)}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

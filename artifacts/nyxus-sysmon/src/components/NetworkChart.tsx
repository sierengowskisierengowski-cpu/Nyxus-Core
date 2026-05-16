import React from 'react';
import { NetworkDataPoint } from '../hooks/useSysmon';
import { AreaChart, Area, ResponsiveContainer, YAxis, Tooltip } from 'recharts';
import { formatBytes } from '../lib/format';

export function NetworkChart({ history, currentUp, currentDown }: { history: NetworkDataPoint[], currentUp: number, currentDown: number }) {
  return (
    <div className="panel p-4 flex flex-col relative h-full">
      <div className="flex justify-between items-start z-10 mb-4">
        <div className="text-nyxus-blue text-xs font-bold opacity-70">NETWORK THROUGHPUT</div>
        <div className="flex gap-4 text-xs font-bold">
          <div className="text-nyxus-orange glow-text-orange flex items-center">
            <span className="text-lg">↑</span> {formatBytes(currentUp)}/s
          </div>
          <div className="text-nyxus-blue glow-text-blue flex items-center">
            <span className="text-lg">↓</span> {formatBytes(currentDown)}/s
          </div>
        </div>
      </div>
      
      <div className="flex-1 relative w-full h-full min-h-[150px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="upGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ff5500" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#ff5500" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="downGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0088ff" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#0088ff" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#07030f', border: '1px solid #333' }}
              labelStyle={{ display: 'none' }}
              formatter={(val: number) => formatBytes(val) + '/s'}
            />
            <Area 
              type="monotone" 
              dataKey="download" 
              stroke="#0088ff" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#downGrad)" 
              isAnimationActive={false}
            />
            <Area 
              type="monotone" 
              dataKey="upload" 
              stroke="#ff5500" 
              strokeWidth={2}
              fillOpacity={1} 
              fill="url(#upGrad)" 
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

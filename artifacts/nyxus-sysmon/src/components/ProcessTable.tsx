import React, { useState } from 'react';
import { SysmonData } from '../hooks/useSysmon';
import { getColorForPercent } from '../lib/format';

export function ProcessTable({ data }: { data: SysmonData | null }) {
  const [sortCol, setSortCol] = useState<'cpu' | 'mem' | 'pid'>('cpu');
  const [sortDesc, setSortDesc] = useState(true);

  const processes = [...(data?.processes || [])];
  
  processes.sort((a, b) => {
    let valA = a[sortCol];
    let valB = b[sortCol];
    if (valA < valB) return sortDesc ? 1 : -1;
    if (valA > valB) return sortDesc ? -1 : 1;
    return 0;
  });

  const topProcesses = processes.slice(0, 20);

  const handleSort = (col: 'cpu' | 'mem' | 'pid') => {
    if (sortCol === col) setSortDesc(!sortDesc);
    else {
      setSortCol(col);
      setSortDesc(true);
    }
  };

  return (
    <div className="panel flex flex-col h-full overflow-hidden">
      <div className="p-3 bg-nyxus-dim/10 border-b border-nyxus-dim/30 flex justify-between items-center shrink-0">
        <div className="text-nyxus-text/70 text-xs font-bold">PROCESS TABLE</div>
        <div className="text-[10px] text-nyxus-dim">TOP 20 PROCESSES</div>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs text-left border-collapse">
          <thead className="sticky top-0 bg-[#0a0514] border-b border-nyxus-dim/30 text-nyxus-dim text-[10px]">
            <tr>
              <th className="p-2 cursor-pointer hover:text-white" onClick={() => handleSort('pid')}>PID {sortCol === 'pid' ? (sortDesc ? '↓' : '↑') : ''}</th>
              <th className="p-2">NAME</th>
              <th className="p-2 cursor-pointer hover:text-white" onClick={() => handleSort('cpu')}>CPU% {sortCol === 'cpu' ? (sortDesc ? '↓' : '↑') : ''}</th>
              <th className="p-2 cursor-pointer hover:text-white" onClick={() => handleSort('mem')}>MEM% {sortCol === 'mem' ? (sortDesc ? '↓' : '↑') : ''}</th>
              <th className="p-2">STATUS</th>
            </tr>
          </thead>
          <tbody>
            {topProcesses.map((p, i) => (
              <tr key={p.pid} className={`border-b border-nyxus-dim/10 hover:bg-nyxus-dim/20 ${i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.02]'}`}>
                <td className="p-2 font-mono text-nyxus-dim">{p.pid}</td>
                <td className="p-2 font-mono text-white truncate max-w-[150px]" title={p.name}>{p.name}</td>
                <td className="p-2 font-mono font-bold" style={{ color: getColorForPercent(p.cpu) }}>{p.cpu.toFixed(1)}</td>
                <td className="p-2 font-mono font-bold" style={{ color: getColorForPercent(p.mem) }}>{p.mem.toFixed(1)}</td>
                <td className="p-2">
                  <span className={`px-1.5 py-0.5 rounded text-[9px] ${
                    p.status === 'running' ? 'bg-nyxus-green/20 text-nyxus-green border border-nyxus-green/30' :
                    p.status === 'sleeping' ? 'bg-nyxus-dim/20 text-nyxus-dim border border-nyxus-dim/30' :
                    'bg-red-500/20 text-red-500 border border-red-500/30'
                  }`}>
                    {p.status.toUpperCase()}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

import { useState, useEffect, useRef, useCallback } from 'react';

export interface SysmonData {
  cpu: {
    percent: number;
    per_core: number[];
    count_logical: number;
    count_physical: number;
    freq_mhz: number;
    freq_max_mhz: number;
    load_avg: number[];
    temperatures?: {
      coretemp?: { label: string; current: number }[];
    };
  };
  memory: {
    ram_total: number;
    ram_used: number;
    ram_free: number;
    ram_percent: number;
    swap_total: number;
    swap_used: number;
    swap_percent: number;
  };
  disks: {
    mountpoint: string;
    device: string;
    total: number;
    used: number;
    free: number;
    percent: number;
  }[];
  processes: {
    pid: number;
    name: string;
    cpu: number;
    mem: number;
    status: string;
  }[];
  network: {
    interfaces: Record<string, { bytes_sent_per_sec: number; bytes_recv_per_sec: number }>;
    total_bytes_sent_per_sec: number;
    total_bytes_recv_per_sec: number;
    total_bytes_sent?: number;
    total_bytes_recv?: number;
  };
  system: {
    hostname: string;
    uptime: string;
    uptime_seconds: number;
    pid_count: number;
    boot_time: string;
  };
  timestamp: string;
}

export interface NetworkDataPoint {
  time: string;
  upload: number;
  download: number;
}

export interface CpuDataPoint {
  time: string;
  percent: number;
}

export function useSysmon() {
  const [data, setData] = useState<SysmonData | null>(null);
  const [isOffline, setIsOffline] = useState(true);
  
  const [cpuHistory, setCpuHistory] = useState<CpuDataPoint[]>([]);
  const [networkHistory, setNetworkHistory] = useState<NetworkDataPoint[]>([]);
  
  const pollInterval = useRef<number | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:9191/api/all');
      if (!res.ok) throw new Error('Failed to fetch');
      const json: SysmonData = await res.json();
      
      setData(json);
      setIsOffline(false);
      
      const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
      
      setCpuHistory(prev => {
        const next = [...prev, { time: timeStr, percent: json.cpu.percent }];
        if (next.length > 60) return next.slice(next.length - 60);
        return next;
      });
      
      setNetworkHistory(prev => {
        const next = [...prev, { 
          time: timeStr, 
          upload: json.network.total_bytes_sent_per_sec,
          download: json.network.total_bytes_recv_per_sec
        }];
        if (next.length > 60) return next.slice(next.length - 60);
        return next;
      });

    } catch (err) {
      setIsOffline(true);
    }
  }, []);

  useEffect(() => {
    // Fill initial empty history arrays
    const initTime = new Date().toLocaleTimeString('en-US', { hour12: false });
    const initCpu = Array(60).fill(0).map((_, i) => ({ time: initTime, percent: 0 }));
    const initNet = Array(60).fill(0).map((_, i) => ({ time: initTime, upload: 0, download: 0 }));
    setCpuHistory(initCpu);
    setNetworkHistory(initNet);

    fetchData();
    pollInterval.current = window.setInterval(fetchData, 2000);
    
    return () => {
      if (pollInterval.current) clearInterval(pollInterval.current);
    };
  }, [fetchData]);

  return { data, isOffline, cpuHistory, networkHistory };
}

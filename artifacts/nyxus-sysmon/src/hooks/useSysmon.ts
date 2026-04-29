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

function makeDemoData(): SysmonData {
  const r = Math.random;
  return {
    cpu: {
      percent: Math.round((15 + r() * 65) * 10) / 10,
      per_core: Array(8).fill(0).map(() => Math.round(r() * 100)),
      count_logical: 8,
      count_physical: 4,
      freq_mhz: Math.round(3200 + r() * 1200),
      freq_max_mhz: 5200,
      load_avg: [
        Math.round((0.8 + r() * 2.0) * 100) / 100,
        Math.round((1.0 + r() * 2.5) * 100) / 100,
        Math.round((1.2 + r() * 3.0) * 100) / 100,
      ],
      temperatures: {
        coretemp: Array(8).fill(0).map((_, i) => ({
          label: `Core ${i}`,
          current: Math.round(42 + r() * 38),
        })),
      },
    },
    memory: {
      ram_total:    32 * 1024 ** 3,
      ram_used:     (10 + r() * 12) * 1024 ** 3,
      ram_free:     10 * 1024 ** 3,
      ram_percent:  Math.round((35 + r() * 30) * 10) / 10,
      swap_total:   8 * 1024 ** 3,
      swap_used:    r() * 0.8 * 1024 ** 3,
      swap_percent: Math.round(r() * 10 * 10) / 10,
    },
    disks: [
      { mountpoint: '/', device: '/dev/nvme0n1p2', total: 500e9, used: 185e9, free: 315e9, percent: 37 },
      { mountpoint: '/home', device: '/dev/nvme0n1p3', total: 1000e9, used: 430e9, free: 570e9, percent: 43 },
    ],
    processes: [
      { pid: 1,    name: 'systemd',  cpu: 0.0,                           mem: 0.1, status: 'sleeping' },
      { pid: 1842, name: 'Hyprland', cpu: Math.round((2+r()*2)*10)/10,   mem: 1.2, status: 'running'  },
      { pid: 2203, name: 'waybar',   cpu: Math.round(r()*5*10)/10,       mem: 0.5, status: 'running'  },
      { pid: 3112, name: 'kitty',    cpu: Math.round(r()*3*10)/10,       mem: 0.3, status: 'running'  },
      { pid: 4891, name: 'firefox',  cpu: Math.round((6+r()*8)*10)/10,   mem: 9.1, status: 'running'  },
      { pid: 5234, name: 'code',     cpu: Math.round((1+r()*5)*10)/10,   mem: 5.3, status: 'running'  },
      { pid: 6001, name: 'spotify',  cpu: Math.round((0.5+r()*2)*10)/10, mem: 2.8, status: 'running'  },
      { pid: 6788, name: 'discord',  cpu: Math.round((0.8+r()*2)*10)/10, mem: 3.4, status: 'running'  },
      { pid: 7001, name: 'pipewire', cpu: Math.round(r()*1.5*10)/10,     mem: 0.2, status: 'running'  },
      { pid: 7892, name: 'rofi',     cpu: 0.0,                           mem: 0.1, status: 'sleeping' },
    ],
    network: {
      interfaces: {
        'enp3s0': {
          bytes_sent_per_sec: r() * 400e3,
          bytes_recv_per_sec: r() * 2.5e6,
        },
      },
      total_bytes_sent_per_sec: r() * 400e3,
      total_bytes_recv_per_sec: r() * 2.5e6,
      total_bytes_sent: 42e9,
      total_bytes_recv: 180e9,
    },
    system: {
      hostname:        'nyx-arch',
      uptime:          '2d 14h 32m',
      uptime_seconds:  225120,
      pid_count:       287 + Math.floor(r() * 10),
      boot_time:       '2026-04-27 01:45:00',
    },
    timestamp: new Date().toISOString(),
  };
}

export function useSysmon() {
  const [data, setData]           = useState<SysmonData>(() => makeDemoData());
  const [isDemoMode, setIsDemoMode] = useState(true);

  const [cpuHistory, setCpuHistory] = useState<CpuDataPoint[]>(() => {
    const t = new Date().toLocaleTimeString('en-US', { hour12: false });
    return Array(60).fill(0).map(() => ({ time: t, percent: 0 }));
  });
  const [networkHistory, setNetworkHistory] = useState<NetworkDataPoint[]>(() => {
    const t = new Date().toLocaleTimeString('en-US', { hour12: false });
    return Array(60).fill(0).map(() => ({ time: t, upload: 0, download: 0 }));
  });

  const pollInterval = useRef<number | null>(null);

  const pushHistory = useCallback((json: SysmonData) => {
    const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false });
    setCpuHistory(prev => {
      const next = [...prev, { time: timeStr, percent: json.cpu.percent }];
      return next.length > 60 ? next.slice(next.length - 60) : next;
    });
    setNetworkHistory(prev => {
      const next = [...prev, {
        time: timeStr,
        upload:   json.network.total_bytes_sent_per_sec,
        download: json.network.total_bytes_recv_per_sec,
      }];
      return next.length > 60 ? next.slice(next.length - 60) : next;
    });
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:9191/api/all', {
        signal: AbortSignal.timeout(1500),
      });
      if (!res.ok) throw new Error('bad status');
      const json: SysmonData = await res.json();
      setData(json);
      setIsDemoMode(false);
      pushHistory(json);
    } catch {
      const demo = makeDemoData();
      setData(demo);
      setIsDemoMode(true);
      pushHistory(demo);
    }
  }, [pushHistory]);

  useEffect(() => {
    fetchData();
    pollInterval.current = window.setInterval(fetchData, 2000);
    return () => { if (pollInterval.current) clearInterval(pollInterval.current); };
  }, [fetchData]);

  return { data, isOffline: false, isDemoMode, cpuHistory, networkHistory };
}

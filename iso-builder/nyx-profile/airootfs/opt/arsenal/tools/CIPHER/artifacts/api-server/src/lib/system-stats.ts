import fs from "node:fs/promises";
import os from "node:os";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

export interface GpuInfo {
  index: number;
  name: string;
  temperatureCelsius: number | null;
  utilizationPercent: number | null;
  memUsedMb: number | null;
  memTotalMb: number | null;
  powerWatts: number | null;
}

export interface CpuInfo {
  model: string;
  cores: number;
  usagePercent: number;
  loadAvg1: number;
  loadAvg5: number;
  loadAvg15: number;
}

export interface MemoryInfo {
  totalMb: number;
  usedMb: number;
  freeMb: number;
  usagePercent: number;
}

export interface SystemStats {
  cpu: CpuInfo;
  memory: MemoryInfo;
  gpus: GpuInfo[];
  gpuAvailable: boolean;
}

interface CpuSample {
  idle: number;
  total: number;
}

async function readCpuSample(): Promise<CpuSample | null> {
  try {
    const stat = await fs.readFile("/proc/stat", "utf8");
    const line = stat.split("\n").find((l) => l.startsWith("cpu "));
    if (!line) return null;
    const parts = line.trim().split(/\s+/).slice(1).map(Number);
    const [user, nice, system, idle, iowait = 0, irq = 0, softirq = 0, steal = 0] = parts;
    const idleAll = idle + iowait;
    const total = user + nice + system + idleAll + irq + softirq + steal;
    return { idle: idleAll, total };
  } catch {
    return null;
  }
}

/** Real CPU utilization sampled from /proc/stat over a short interval. */
async function getCpuUsagePercent(): Promise<number> {
  const first = await readCpuSample();
  if (!first) return 0;
  await new Promise((r) => setTimeout(r, 150));
  const second = await readCpuSample();
  if (!second) return 0;
  const totalDelta = second.total - first.total;
  const idleDelta = second.idle - first.idle;
  if (totalDelta <= 0) return 0;
  const usage = (1 - idleDelta / totalDelta) * 100;
  return Math.max(0, Math.min(100, Math.round(usage * 10) / 10));
}

async function getMemoryInfo(): Promise<MemoryInfo> {
  // Prefer /proc/meminfo (accounts for buffers/cache as available).
  try {
    const raw = await fs.readFile("/proc/meminfo", "utf8");
    const map: Record<string, number> = {};
    for (const line of raw.split("\n")) {
      const m = line.match(/^(\w+):\s+(\d+)\s+kB/);
      if (m) map[m[1]] = Number(m[2]);
    }
    if (map.MemTotal) {
      const totalMb = Math.round(map.MemTotal / 1024);
      const availMb = Math.round((map.MemAvailable ?? map.MemFree ?? 0) / 1024);
      const usedMb = totalMb - availMb;
      return {
        totalMb,
        usedMb,
        freeMb: availMb,
        usagePercent: totalMb > 0 ? Math.round((usedMb / totalMb) * 1000) / 10 : 0,
      };
    }
  } catch {
    /* fall back to os */
  }
  const totalMb = Math.round(os.totalmem() / 1024 / 1024);
  const freeMb = Math.round(os.freemem() / 1024 / 1024);
  const usedMb = totalMb - freeMb;
  return {
    totalMb,
    usedMb,
    freeMb,
    usagePercent: totalMb > 0 ? Math.round((usedMb / totalMb) * 1000) / 10 : 0,
  };
}

function parseNum(v: string): number | null {
  const t = v.trim();
  if (t === "" || /\[?N\/A\]?/i.test(t) || t === "[Not Supported]") return null;
  const n = Number.parseFloat(t);
  return Number.isFinite(n) ? n : null;
}

/**
 * Query real NVIDIA GPU telemetry via nvidia-smi. Returns [] when no NVIDIA
 * GPU / driver is present (no fabricated fallback).
 */
export async function getGpus(): Promise<GpuInfo[]> {
  try {
    const { stdout } = await execFileAsync(
      "nvidia-smi",
      [
        "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
        "--format=csv,noheader,nounits",
      ],
      { timeout: 5000 },
    );
    return stdout
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0)
      .map((line) => {
        const cols = line.split(",");
        return {
          index: parseNum(cols[0] ?? "") ?? 0,
          name: (cols[1] ?? "GPU").trim(),
          temperatureCelsius: parseNum(cols[2] ?? ""),
          utilizationPercent: parseNum(cols[3] ?? ""),
          memUsedMb: parseNum(cols[4] ?? ""),
          memTotalMb: parseNum(cols[5] ?? ""),
          powerWatts: parseNum(cols[6] ?? ""),
        } satisfies GpuInfo;
      });
  } catch {
    return [];
  }
}

export async function getSystemStats(): Promise<SystemStats> {
  const cpus = os.cpus();
  const [usagePercent, memory, gpus] = await Promise.all([
    getCpuUsagePercent(),
    getMemoryInfo(),
    getGpus(),
  ]);
  const [l1, l5, l15] = os.loadavg();
  return {
    cpu: {
      model: cpus[0]?.model?.trim() ?? "Unknown CPU",
      cores: cpus.length,
      usagePercent,
      loadAvg1: Math.round(l1 * 100) / 100,
      loadAvg5: Math.round(l5 * 100) / 100,
      loadAvg15: Math.round(l15 * 100) / 100,
    },
    memory,
    gpus,
    gpuAvailable: gpus.length > 0,
  };
}

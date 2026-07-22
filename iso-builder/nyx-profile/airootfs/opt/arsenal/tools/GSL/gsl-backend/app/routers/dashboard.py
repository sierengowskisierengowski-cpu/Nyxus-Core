from fastapi import APIRouter, Depends
from typing import List
import aiosqlite
import asyncio
import subprocess
import re
import psutil
import time
from ..database import get_db
from ..models import DashboardSummary, Run, NetworkDevice
from ..tools_data import TOOLS, CATEGORIES
from ..routers.runs import row_to_run

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT COUNT(*) as cnt FROM runs") as cur:
        total_runs_row = await cur.fetchone()
    async with db.execute("SELECT COUNT(*) as cnt FROM runs WHERE is_flagged = 1") as cur:
        findings_row = await cur.fetchone()
    async with db.execute("SELECT COUNT(*) as cnt FROM tool_favorites WHERE is_favorite = 1") as cur:
        fav_row = await cur.fetchone()
    async with db.execute("SELECT MAX(started_at) as last FROM runs") as cur:
        last_row = await cur.fetchone()

    return {
        "totalTools": len(TOOLS),
        "totalRuns": total_runs_row["cnt"] if total_runs_row else 0,
        "totalCategories": len(CATEGORIES),
        "favoriteCount": fav_row["cnt"] if fav_row else 0,
        "findingsCount": findings_row["cnt"] if findings_row else 0,
        "recentActivity": (last_row["last"] or "No runs yet") if last_row else "No runs yet",
    }

@router.get("/recent-runs", response_model=List[Run])
async def get_recent_runs(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 10") as cur:
        rows = await cur.fetchall()
    return [row_to_run(r) for r in rows]

@router.get("/devices", response_model=List[NetworkDevice])
async def get_network_devices():
    """Run a quick ARP ping to discover live 192.168.0.x devices."""
    devices: List[dict] = []
    try:
        result = subprocess.run(
            ["nmap", "-sn", "-PR", "--send-eth", "192.168.0.0/24"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        # Parse nmap -sn output
        blocks = output.split("Nmap scan report for ")
        for block in blocks[1:]:
            lines = block.strip().splitlines()
            if not lines:
                continue
            first = lines[0].strip()
            # Extract hostname and IP
            m = re.match(r"(.*)\s*\((\d+\.\d+\.\d+\.\d+)\)", first)
            if m:
                hostname = m.group(1).strip()
                ip = m.group(2)
            else:
                hostname = None
                ip = first.strip()

            status = "up"
            mac = None
            vendor = None
            for line in lines[1:]:
                if "Host is down" in line:
                    status = "down"
                if "MAC Address:" in line:
                    mac_match = re.search(r"MAC Address: ([0-9A-Fa-f:]+)\s*\(?(.*?)\)?$", line)
                    if mac_match:
                        mac = mac_match.group(1)
                        vendor = mac_match.group(2).strip() or None

            devices.append({
                "ip": ip,
                "hostname": hostname,
                "mac": mac,
                "vendor": vendor,
                "status": status,
            })
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # nmap not available or timed out — return known static hosts
        devices = [
            {"ip": "192.168.0.172", "hostname": "nyx-cosmic", "mac": None, "vendor": None, "status": "up"},
            {"ip": "192.168.0.125", "hostname": "pi-zero-honeypot", "mac": None, "vendor": None, "status": "unknown"},
            {"ip": "192.168.0.80", "hostname": "pi5-kali", "mac": None, "vendor": None, "status": "unknown"},
        ]

    return devices


@router.get("/system-stats")
async def get_system_stats():
    """Return live CPU, RAM, disk, and network stats for nyx-cosmic."""
    cpu_percent = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # Network I/O (bytes since boot — compute delta over 1s)
    net1 = psutil.net_io_counters()
    await asyncio.sleep(0.5)
    net2 = psutil.net_io_counters()
    rx_rate = (net2.bytes_recv - net1.bytes_recv) * 2  # per second
    tx_rate = (net2.bytes_sent - net1.bytes_sent) * 2

    def fmt_bytes(b: float) -> str:
        if b >= 1_073_741_824:
            return f"{b / 1_073_741_824:.1f} GB"
        if b >= 1_048_576:
            return f"{b / 1_048_576:.1f} MB"
        if b >= 1024:
            return f"{b / 1024:.0f} KB"
        return f"{b:.0f} B"

    # CPU load average
    try:
        load1, load5, load15 = psutil.getloadavg()
    except Exception:
        load1 = load5 = load15 = 0.0

    # Uptime
    boot_time = psutil.boot_time()
    uptime_secs = int(time.time() - boot_time)
    uptime_days = uptime_secs // 86400
    uptime_hours = (uptime_secs % 86400) // 3600
    uptime_mins = (uptime_secs % 3600) // 60
    uptime_str = f"{uptime_days}d {uptime_hours}h {uptime_mins}m" if uptime_days else f"{uptime_hours}h {uptime_mins}m"

    return {
        "cpu": {
            "percent": round(cpu_percent, 1),
            "load1": round(load1, 2),
            "load5": round(load5, 2),
            "load15": round(load15, 2),
            "count": psutil.cpu_count(),
        },
        "memory": {
            "percent": round(mem.percent, 1),
            "used": fmt_bytes(mem.used),
            "total": fmt_bytes(mem.total),
            "available": fmt_bytes(mem.available),
        },
        "disk": {
            "percent": round(disk.percent, 1),
            "used": fmt_bytes(disk.used),
            "total": fmt_bytes(disk.total),
            "free": fmt_bytes(disk.free),
        },
        "network": {
            "rx_rate": fmt_bytes(rx_rate) + "/s",
            "tx_rate": fmt_bytes(tx_rate) + "/s",
            "bytes_recv_total": fmt_bytes(net2.bytes_recv),
            "bytes_sent_total": fmt_bytes(net2.bytes_sent),
        },
        "uptime": uptime_str,
    }

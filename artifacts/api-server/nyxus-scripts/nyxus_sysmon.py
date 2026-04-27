#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS_SYSMON — Local System Statistics Server                       ║
# ║  Serves live CPU/RAM/Disk/Network/Process data to NYXUS SysMon UI    ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# Install deps:  pip install psutil flask flask-cors
# Run:           python3 ~/.nyxus/nyxus_sysmon.py
# Dashboard:     Open NYXUS SysMon in Chromium on workspace 6
#
# Auto-starts via: exec-once = python3 ~/.nyxus/nyxus_sysmon.py &

import json
import time
import socket
import threading
import subprocess
from datetime import datetime

try:
    import psutil
except ImportError:
    print("[NYXUS_SYSMON] psutil not found. Installing...")
    subprocess.run(["pip", "install", "psutil", "flask", "flask-cors"], check=True)
    import psutil

try:
    from flask import Flask, jsonify
    from flask_cors import CORS
except ImportError:
    print("[NYXUS_SYSMON] flask not found. Installing...")
    subprocess.run(["pip", "install", "flask", "flask-cors"], check=True)
    from flask import Flask, jsonify
    from flask_cors import CORS

PORT = 9191
app = Flask(__name__)
CORS(app, origins="*")

# ── Cache for network diff ────────────────────────────────────────────────────
_net_prev = None
_net_prev_time = None
_net_lock = threading.Lock()

def get_net_speed():
    global _net_prev, _net_prev_time
    now = time.time()
    counters = psutil.net_io_counters(pernic=True)
    with _net_lock:
        if _net_prev is None:
            _net_prev = counters
            _net_prev_time = now
            return {}
        elapsed = now - _net_prev_time
        if elapsed < 0.01:
            return {}
        speeds = {}
        for iface, cur in counters.items():
            prev = _net_prev.get(iface)
            if prev:
                speeds[iface] = {
                    "bytes_sent_per_sec": max(0, (cur.bytes_sent - prev.bytes_sent) / elapsed),
                    "bytes_recv_per_sec": max(0, (cur.bytes_recv - prev.bytes_recv) / elapsed),
                    "bytes_sent": cur.bytes_sent,
                    "bytes_recv": cur.bytes_recv,
                    "packets_sent": cur.packets_sent,
                    "packets_recv": cur.packets_recv,
                    "errin": cur.errin,
                    "errout": cur.errout,
                    "dropin": cur.dropin,
                    "dropout": cur.dropout,
                }
        _net_prev = counters
        _net_prev_time = now
        return speeds

# ── CPU ───────────────────────────────────────────────────────────────────────
@app.route("/api/cpu")
def cpu():
    freq = psutil.cpu_freq(percpu=False)
    freq_per = psutil.cpu_freq(percpu=True)
    temps = {}
    try:
        t = psutil.sensors_temperatures()
        if t:
            for key, entries in t.items():
                if entries:
                    temps[key] = [{"label": e.label or key, "current": e.current, "high": e.high, "critical": e.critical} for e in entries]
    except (AttributeError, Exception):
        pass
    return jsonify({
        "percent": psutil.cpu_percent(interval=None),
        "per_core": psutil.cpu_percent(percpu=True, interval=None),
        "count_logical": psutil.cpu_count(logical=True),
        "count_physical": psutil.cpu_count(logical=False),
        "freq_mhz": freq.current if freq else None,
        "freq_max_mhz": freq.max if freq else None,
        "freq_per_core": [f.current for f in freq_per] if freq_per else [],
        "load_avg": list(psutil.getloadavg()),
        "ctx_switches": psutil.cpu_stats().ctx_switches,
        "interrupts": psutil.cpu_stats().interrupts,
        "temperatures": temps,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── Memory ────────────────────────────────────────────────────────────────────
@app.route("/api/memory")
def memory():
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return jsonify({
        "ram": {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "free": vm.free,
            "percent": vm.percent,
            "buffers": getattr(vm, "buffers", 0),
            "cached": getattr(vm, "cached", 0),
            "shared": getattr(vm, "shared", 0),
        },
        "swap": {
            "total": sw.total,
            "used": sw.used,
            "free": sw.free,
            "percent": sw.percent,
            "sin": sw.sin,
            "sout": sw.sout,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── Disk ──────────────────────────────────────────────────────────────────────
@app.route("/api/disk")
def disk():
    partitions = []
    for p in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(p.mountpoint)
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            })
        except PermissionError:
            pass
    io = psutil.disk_io_counters(perdisk=True) or {}
    disk_io = {}
    for dev, c in io.items():
        disk_io[dev] = {
            "read_bytes": c.read_bytes,
            "write_bytes": c.write_bytes,
            "read_count": c.read_count,
            "write_count": c.write_count,
            "read_time": c.read_time,
            "write_time": c.write_time,
        }
    return jsonify({
        "partitions": partitions,
        "io": disk_io,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── Network ───────────────────────────────────────────────────────────────────
@app.route("/api/network")
def network():
    speeds = get_net_speed()
    interfaces = {}
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for iface, addr_list in addrs.items():
        s = stats.get(iface)
        addresses = []
        for a in addr_list:
            addresses.append({
                "family": str(a.family),
                "address": a.address,
                "netmask": a.netmask,
                "broadcast": a.broadcast,
            })
        interfaces[iface] = {
            "addresses": addresses,
            "is_up": s.isup if s else False,
            "speed_mbps": s.speed if s else 0,
            "mtu": s.mtu if s else 0,
            "speed": speeds.get(iface, {}),
        }
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"
    conns = []
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == "ESTABLISHED":
                conns.append({
                    "pid": c.pid,
                    "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                    "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                    "status": c.status,
                    "type": "TCP",
                })
    except (psutil.AccessDenied, Exception):
        pass
    return jsonify({
        "hostname": hostname,
        "local_ip": local_ip,
        "interfaces": interfaces,
        "connections": conns[:50],
        "connection_count": len(conns),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── Processes ─────────────────────────────────────────────────────────────────
@app.route("/api/processes")
def processes():
    procs = []
    for p in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info", "status", "create_time", "num_threads"]):
        try:
            info = p.info
            procs.append({
                "pid": info["pid"],
                "name": info["name"] or "",
                "user": info["username"] or "",
                "cpu": round(info["cpu_percent"] or 0, 1),
                "mem": round(info["memory_percent"] or 0, 2),
                "mem_rss": info["memory_info"].rss if info["memory_info"] else 0,
                "status": info["status"] or "",
                "threads": info["num_threads"] or 0,
                "started": datetime.fromtimestamp(info["create_time"]).isoformat() if info["create_time"] else "",
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return jsonify({
        "processes": procs[:60],
        "total": len(procs),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── System Info ───────────────────────────────────────────────────────────────
@app.route("/api/system")
def system_info():
    boot = psutil.boot_time()
    uptime_secs = int(time.time() - boot)
    h, rem = divmod(uptime_secs, 3600)
    m, s = divmod(rem, 60)
    users = []
    for u in psutil.users():
        users.append({"name": u.name, "terminal": u.terminal, "host": u.host, "started": datetime.fromtimestamp(u.started).isoformat()})
    return jsonify({
        "hostname": socket.gethostname(),
        "platform": __import__("platform").platform(),
        "boot_time": datetime.fromtimestamp(boot).isoformat(),
        "uptime": f"{h:02d}:{m:02d}:{s:02d}",
        "uptime_seconds": uptime_secs,
        "users": users,
        "pid_count": len(list(psutil.pids())),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

# ── All (single poll endpoint) ────────────────────────────────────────────────
@app.route("/api/all")
def all_stats():
    from concurrent.futures import ThreadPoolExecutor
    def _cpu():
        freq = psutil.cpu_freq(percpu=False)
        temps = {}
        try:
            t = psutil.sensors_temperatures()
            if t:
                for key, entries in t.items():
                    if entries:
                        temps[key] = [{"label": e.label or key, "current": e.current} for e in entries]
        except Exception:
            pass
        return {
            "percent": psutil.cpu_percent(interval=None),
            "per_core": psutil.cpu_percent(percpu=True, interval=None),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
            "freq_mhz": freq.current if freq else None,
            "freq_max_mhz": freq.max if freq else None,
            "load_avg": list(psutil.getloadavg()),
            "temperatures": temps,
        }
    def _mem():
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return {
            "ram_total": vm.total, "ram_used": vm.used, "ram_free": vm.available, "ram_percent": vm.percent,
            "swap_total": sw.total, "swap_used": sw.used, "swap_percent": sw.percent,
        }
    def _disk():
        parts = []
        for p in psutil.disk_partitions():
            try:
                u = psutil.disk_usage(p.mountpoint)
                parts.append({"mountpoint": p.mountpoint, "device": p.device, "total": u.total, "used": u.used, "free": u.free, "percent": u.percent})
            except Exception:
                pass
        return parts
    def _procs():
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                i = p.info
                procs.append({"pid": i["pid"], "name": i["name"] or "", "cpu": round(i["cpu_percent"] or 0, 1), "mem": round(i["memory_percent"] or 0, 2), "status": i["status"] or ""})
            except Exception:
                pass
        procs.sort(key=lambda x: x["cpu"], reverse=True)
        return procs[:20]

    speeds = get_net_speed()
    with ThreadPoolExecutor(max_workers=4) as ex:
        fc = ex.submit(_cpu)
        fm = ex.submit(_mem)
        fd = ex.submit(_disk)
        fp = ex.submit(_procs)
        cpu_data = fc.result()
        mem_data = fm.result()
        disk_data = fd.result()
        proc_data = fp.result()

    boot = psutil.boot_time()
    uptime_secs = int(time.time() - boot)
    h, rem = divmod(uptime_secs, 3600)
    mi, s = divmod(rem, 60)

    total_bytes_sent = sum(v.get("bytes_sent_per_sec", 0) for v in speeds.values())
    total_bytes_recv = sum(v.get("bytes_recv_per_sec", 0) for v in speeds.values())

    return jsonify({
        "cpu": cpu_data,
        "memory": mem_data,
        "disks": disk_data,
        "processes": proc_data,
        "network": {
            "interfaces": {k: {"bytes_sent_per_sec": v.get("bytes_sent_per_sec", 0), "bytes_recv_per_sec": v.get("bytes_recv_per_sec", 0)} for k, v in speeds.items()},
            "total_bytes_sent_per_sec": total_bytes_sent,
            "total_bytes_recv_per_sec": total_bytes_recv,
        },
        "system": {
            "hostname": socket.gethostname(),
            "uptime": f"{h:02d}:{mi:02d}:{s:02d}",
            "uptime_seconds": uptime_secs,
            "pid_count": len(list(psutil.pids())),
            "boot_time": datetime.fromtimestamp(boot).isoformat(),
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "ONLINE", "port": PORT, "timestamp": datetime.utcnow().isoformat() + "Z"})

# ── Banner ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\033[35m\033[1m")
    print("  ███   ██  ██  ██  ██  ██  ██  █████ ")
    print("  ████  ██   ████   ██  ██  ██  ██    ")
    print("  ██ █  ██    ██    ██  ██  ██   ████ ")
    print("  ██  █ ██    ██     ████   ██      ██ ")
    print("  ██   ████   ██      ██    ██  █████ ")
    print(f"\033[0m  \033[2mSYSMON · localhost:{PORT} · © 2026 SIERENGOWSKI\033[0m\n")

    # warm up cpu percent
    psutil.cpu_percent(interval=0.1)
    psutil.cpu_percent(percpu=True, interval=None)
    get_net_speed()

    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)

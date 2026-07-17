#!/usr/bin/env python3
"""
Heimdall Memory v0.1.1

Rolling event buffer with thread safety, TTL cleanup,
and capped key counts.
"""

from __future__ import annotations
import logging
import threading
import time
from collections import deque

log = logging.getLogger("heimdall.memory")

BUFFER_SIZE = 10
MAX_TRACKED_IPS = 500
MAX_TRACKED_PROCESSES = 200
TTL_SECONDS = 3600

_lock = threading.Lock()
_ip_buffer: dict[str, deque] = {}
_ip_last_seen: dict[str, float] = {}
_process_buffer: dict[str, deque] = {}
_process_last_seen: dict[str, float] = {}
_global_buffer: deque = deque(maxlen=BUFFER_SIZE * 5)


def _evict_stale():
    now = time.time()
    stale_ips = [
        ip for ip, ts in _ip_last_seen.items()
        if now - ts > TTL_SECONDS
    ]
    for ip in stale_ips:
        _ip_buffer.pop(ip, None)
        _ip_last_seen.pop(ip, None)

    stale_procs = [
        p for p, ts in _process_last_seen.items()
        if now - ts > TTL_SECONDS
    ]
    for p in stale_procs:
        _process_buffer.pop(p, None)
        _process_last_seen.pop(p, None)


def _cap_buffers():
    if len(_ip_buffer) > MAX_TRACKED_IPS:
        oldest = sorted(_ip_last_seen, key=_ip_last_seen.get)
        for ip in oldest[:len(_ip_buffer) - MAX_TRACKED_IPS]:
            _ip_buffer.pop(ip, None)
            _ip_last_seen.pop(ip, None)

    if len(_process_buffer) > MAX_TRACKED_PROCESSES:
        oldest = sorted(_process_last_seen, key=_process_last_seen.get)
        for p in oldest[:len(_process_buffer) - MAX_TRACKED_PROCESSES]:
            _process_buffer.pop(p, None)
            _process_last_seen.pop(p, None)


def update_buffer(compressed: dict) -> list:
    """
    Adds a compressed event to the rolling buffer.
    Returns the current buffer context as a list.
    Thread safe.
    """
    ip = compressed.get("ip")
    process = compressed.get("process") or compressed.get("event_type")
    now = time.time()

    # Inject timestamp if missing
    if "ts" not in compressed:
        compressed = dict(compressed)
        compressed["ts"] = now

    with _lock:
        _evict_stale()
        _global_buffer.append(compressed)

        if ip:
            if ip not in _ip_buffer:
                _ip_buffer[ip] = deque(maxlen=BUFFER_SIZE)
            _ip_buffer[ip].append(compressed)
            _ip_last_seen[ip] = now
            _cap_buffers()
            return list(_ip_buffer[ip])

        if process:
            if process not in _process_buffer:
                _process_buffer[process] = deque(maxlen=BUFFER_SIZE)
            _process_buffer[process].append(compressed)
            _process_last_seen[process] = now
            _cap_buffers()
            return list(_process_buffer[process])

        return list(_global_buffer)[-BUFFER_SIZE:]


def get_chain_for_ip(ip: str) -> list:
    with _lock:
        return list(_ip_buffer.get(ip, []))


def get_chain_for_process(process: str) -> list:
    with _lock:
        return list(_process_buffer.get(process, []))


def get_recent_events(n: int = 10) -> list:
    with _lock:
        events = list(_global_buffer)
        return events[-n:]


def get_attack_chain(compressed: dict) -> list:
    ip = compressed.get("ip")
    process = compressed.get("process")

    with _lock:
        if ip and ip in _ip_buffer and len(_ip_buffer[ip]) > 1:
            return list(_ip_buffer[ip])
        if process and process in _process_buffer:
            chain = list(_process_buffer[process])
            if len(chain) > 1:
                return chain
        events = list(_global_buffer)
        return events[-BUFFER_SIZE:]


def clear_ip_buffer(ip: str):
    with _lock:
        _ip_buffer.pop(ip, None)
        _ip_last_seen.pop(ip, None)
    log.debug(f"Memory: cleared IP buffer for {ip}")


def clear_process_buffer(process: str):
    with _lock:
        _process_buffer.pop(process, None)
        _process_last_seen.pop(process, None)
    log.debug(f"Memory: cleared process buffer for {process}")


def get_stats(include_sensitive: bool = False) -> dict:
    with _lock:
        stats = {
            "ip_buffers": len(_ip_buffer),
            "process_buffers": len(_process_buffer),
            "global_buffer_size": len(_global_buffer),
        }
        if include_sensitive:
            stats["tracked_ips"] = list(_ip_buffer.keys())
            stats["tracked_processes"] = list(
                _process_buffer.keys()
            )[:20]
        else:
            stats["tracked_ips"] = "[redacted]"
            stats["tracked_processes"] = "[redacted]"
        return stats


def format_chain_for_prompt(events: list) -> str:
    """
    Formats event chain as string for Heimdall prompt.
    Includes timestamps for attack chain reasoning.
    """
    if not events:
        return "No events in buffer."

    lines = ["Security event sequence for analysis:"]
    for i, event in enumerate(events, 1):
        event_type = event.get("event_type", "unknown")
        boundary = event.get("boundary", "UNKNOWN")
        alert = event.get("alert_signal", "none")
        ip = event.get("ip", "none")
        path = event.get("path", "none")
        command = str(event.get("command", "none"))[:60]
        ts = event.get("ts", "")
        ts_str = f" t={ts:.0f}" if isinstance(ts, (int, float)) else ""
        lines.append(
            f"{i}.{ts_str} [{boundary}] type={event_type} "
            f"ip={ip} path={path} "
            f"command={command} alert={alert}"
        )

    return "\n".join(lines)

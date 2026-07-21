#!/usr/bin/env python3
"""
cowrie_to_meli.py — Forward Cowrie JSON log to Meli ingest.

Tails the Cowrie JSON log file and publishes new events to Meli over either
MQTT (recommended) or HTTP. Designed to run as a long-lived systemd service.

Features:
  - Persistent offset (survives restarts without replaying or losing events)
  - Handles log rotation (file truncation / inode change)
  - Auto-reconnecting MQTT client (paho-mqtt loop_start)
  - HTTP retries with exponential backoff
  - Graceful shutdown on SIGTERM/SIGINT

Usage:
    python3 cowrie_to_meli.py --log /opt/cowrie/var/log/cowrie/cowrie.json
    python3 cowrie_to_meli.py --log /opt/cowrie/var/log/cowrie/cowrie.json \\
        --mode http --url http://192.168.0.10:17654/api/v1/events/ingest \\
        --token YOUR_TOKEN
"""
import argparse
import json
import os
import signal
import sys
import time

DEFAULT_OFFSET_FILE = "/var/lib/cowrie-to-meli/offset.json"

_shutdown = False


def _handle_signal(signum, frame):  # noqa: ARG001
    global _shutdown
    _shutdown = True


def _load_offset(offset_file: str, log_path: str) -> int:
    try:
        with open(offset_file, "r") as f:
            data = json.load(f)
        if data.get("path") == log_path:
            return int(data.get("offset", 0))
    except (FileNotFoundError, ValueError, OSError):
        pass
    return 0


def _save_offset(offset_file: str, log_path: str, offset: int) -> None:
    try:
        os.makedirs(os.path.dirname(offset_file), exist_ok=True)
        tmp = offset_file + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"path": log_path, "offset": offset}, f)
        os.replace(tmp, offset_file)
    except OSError as e:
        print(f"[cowrie_to_meli] WARN: could not persist offset: {e}", file=sys.stderr)


def tail_file(path: str, start_offset: int, offset_file: str):
    """Yield (line, new_offset) tuples. Handles rotation and waits for the
    file to exist."""
    f = None
    inode = None
    offset = start_offset
    last_save = 0.0

    while not _shutdown:
        # Open / re-open the file if needed.
        if f is None:
            if not os.path.exists(path):
                time.sleep(1.0)
                continue
            try:
                f = open(path, "r")
                st = os.fstat(f.fileno())
                inode = st.st_ino
                size = st.st_size
                if offset > size:
                    # File was truncated / rotated — start from the beginning.
                    offset = 0
                f.seek(offset)
            except OSError as e:
                print(f"[cowrie_to_meli] open error: {e}", file=sys.stderr)
                f = None
                time.sleep(1.0)
                continue

        line = f.readline()
        if line:
            offset = f.tell()
            now = time.time()
            if now - last_save > 2.0:
                _save_offset(offset_file, path, offset)
                last_save = now
            yield line.strip(), offset
            continue

        # No new data — check for rotation, then sleep briefly.
        try:
            st_disk = os.stat(path)
            if st_disk.st_ino != inode or st_disk.st_size < offset:
                # Rotated or truncated — reopen from start.
                print("[cowrie_to_meli] log rotation detected, reopening")
                f.close()
                f = None
                offset = 0
                continue
        except FileNotFoundError:
            f.close()
            f = None
            offset = 0
            continue

        time.sleep(0.25)

    if f is not None:
        _save_offset(offset_file, path, offset)
        f.close()


class MqttPublisher:
    def __init__(self, host: str, port: int, topic: str, client_id: str):
        import paho.mqtt.client as mqtt

        self.topic = topic
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.client.connect_async(host, port, keepalive=60)
        self.client.loop_start()

    def publish(self, event: dict) -> None:
        payload = json.dumps(event)
        info = self.client.publish(self.topic, payload, qos=1)
        # Block briefly so we surface errors instead of silently dropping.
        info.wait_for_publish(timeout=5)

    def close(self) -> None:
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass


class HttpPublisher:
    def __init__(self, url: str, token: str):
        import requests

        self.url = url
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/json"

    def publish(self, event: dict) -> None:
        import requests

        delay = 1.0
        for attempt in range(5):
            try:
                resp = self.session.post(self.url, json=event, timeout=5)
                if resp.status_code < 300:
                    return
                if resp.status_code < 500 and resp.status_code != 429:
                    raise RuntimeError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except requests.RequestException as e:
                if attempt == 4:
                    raise RuntimeError(f"request failed: {e}") from e
            time.sleep(delay)
            delay = min(delay * 2, 15)

    def close(self) -> None:
        self.session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Forward Cowrie JSON log to Meli")
    parser.add_argument("--log", required=True, help="Path to cowrie.json log file")
    parser.add_argument("--mode", default="mqtt", choices=["mqtt", "http"])
    parser.add_argument("--host", default="127.0.0.1", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--topic", default="meli/events/ingest")
    parser.add_argument(
        "--url", default="http://127.0.0.1:17654/api/v1/events/ingest"
    )
    parser.add_argument("--token", default="", help="Meli ingest token")
    parser.add_argument(
        "--client-id",
        default=f"cowrie-to-meli-{os.uname().nodename}",
        help="MQTT client id",
    )
    parser.add_argument(
        "--offset-file",
        default=DEFAULT_OFFSET_FILE,
        help="Where to persist read offset across restarts",
    )
    parser.add_argument(
        "--from-start",
        action="store_true",
        help="Ignore saved offset and read from beginning of file",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if args.mode == "mqtt":
        publisher = MqttPublisher(args.host, args.port, args.topic, args.client_id)
        endpoint = f"mqtt://{args.host}:{args.port}/{args.topic}"
    else:
        publisher = HttpPublisher(args.url, args.token)
        endpoint = args.url

    start = 0 if args.from_start else _load_offset(args.offset_file, args.log)
    print(
        f"[cowrie_to_meli] watching {args.log} -> {endpoint} "
        f"(start_offset={start})",
        flush=True,
    )

    count = 0
    errors = 0
    try:
        for line, offset in tail_file(args.log, start, args.offset_file):
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                publisher.publish(event)
                count += 1
                if count % 100 == 0:
                    print(
                        f"[cowrie_to_meli] forwarded {count} events "
                        f"(errors={errors}, offset={offset})",
                        flush=True,
                    )
            except Exception as e:
                errors += 1
                print(f"[cowrie_to_meli] publish error: {e}", file=sys.stderr, flush=True)
                # Brief backoff to avoid hot-looping on broker outage.
                time.sleep(1.0)
    finally:
        publisher.close()
        print(
            f"[cowrie_to_meli] shutting down (forwarded={count}, errors={errors})",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

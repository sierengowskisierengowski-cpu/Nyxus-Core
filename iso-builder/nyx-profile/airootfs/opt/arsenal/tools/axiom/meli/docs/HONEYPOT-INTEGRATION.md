# Honeypot Integration Guide

This guide covers connecting each supported honeypot type to Meli.

## Event Format

### Canonical Meli Format

Send JSON with this structure for the cleanest parsing:

```json
{
  "timestamp": "2024-01-15T12:00:00Z",
  "network": {
    "source_ip": "1.2.3.4",
    "source_port": 54321,
    "destination_port": 22,
    "protocol": "tcp",
    "transport": "ssh"
  },
  "honeypot": {
    "type": "cowrie",
    "name": "my-vps-cowrie"
  },
  "action": {
    "type": "login_attempt",
    "details": {
      "username": "root",
      "password": "toor"
    }
  },
  "session": {
    "session_id": "abc123def456"
  }
}
```

Action types: `connection`, `login_attempt`, `successful_auth`, `command`,
`file_download`, `file_upload`, `port_forward`, `session_close`, `web_request`,
`smtp_probe`, `unknown`.

---

## Cowrie (SSH/Telnet Honeypot)

Cowrie natively outputs JSON in a format Meli understands.

### Via MQTT (recommended)

Install Cowrie's MQTT output plugin:

```bash
pip install paho-mqtt  # inside Cowrie's venv
```

In `etc/cowrie.cfg`:
```ini
[output_mqtt]
enabled = true
host = 127.0.0.1
port = 1883
topic = meli/events/ingest
qos = 1
# No auth needed for local Mosquitto
```

Restart Cowrie:
```bash
systemctl restart cowrie
# or
bin/cowrie restart
```

### Via log file forwarding

Use `mosquitto_pub` to forward from the JSON log:

```bash
# One-liner forwarder (add to crontab or systemd timer)
tail -n 0 -F /opt/cowrie/var/log/cowrie/cowrie.json | \
  mosquitto_pub -h 127.0.0.1 -t meli/events/ingest -l
```

Or use the `cowrie_to_meli.py` helper in `meli/scripts/`:
```bash
python3 meli/scripts/cowrie_to_meli.py --log /opt/cowrie/var/log/cowrie/cowrie.json
```

### Deploying the forwarder as a systemd service (recommended)

For a long-lived Cowrie host (e.g. a Raspberry Pi), use the bundled deploy
script — it copies the forwarder, installs the systemd unit, creates an
unprivileged service user, and enables the service in one shot.

From a workstation that can SSH into the honeypot:

```bash
# Same-host (Meli + Cowrie + Mosquitto all on the Pi):
meli/scripts/deploy_cowrie_forwarder.sh pi@192.168.0.125

# Meli running on a different host on your LAN:
MELI_MQTT_HOST=192.168.0.10 \
    meli/scripts/deploy_cowrie_forwarder.sh pi@192.168.0.125
```

The script provisions:
- `cowrie-meli` system user (no shell, member of `cowrie` group for log read)
- `/opt/cowrie-to-meli/cowrie_to_meli.py`
- `/etc/systemd/system/cowrie-to-meli.service` (auto-restart, hardened)
- `/var/lib/cowrie-to-meli/offset.json` — persisted read offset so restarts
  never replay or skip events

Verify end-to-end:

```bash
# On the Pi: watch the forwarder
ssh pi@192.168.0.125 'sudo journalctl -u cowrie-to-meli -f'

# From another machine: trigger a Cowrie session
ssh -p 2222 root@192.168.0.125   # any password — Cowrie will accept/log it
```

Events should appear in Meli's Live Feed within a few seconds, and the
attacker IP should show up under Attackers with an incrementing event count.

---

## Heralding (Multi-Service Credential Capture)

Heralding supports JSON log output.

In `heralding.yml`:
```yaml
output_plugins:
  - type: json_log
    filename: /var/log/heralding/heralding.json
```

Forward events:
```bash
tail -n 0 -F /var/log/heralding/heralding.json | \
  mosquitto_pub -h 127.0.0.1 -t meli/events/ingest -l
```

Or add a custom output plugin that POSTs directly (see `scripts/heralding_webhook.py`).

---

## Dionaea (Malware Capture)

Dionaea logs to SQLite by default. Use the bridge script:

```bash
python3 meli/scripts/dionaea_bridge.py \
  --db /opt/dionaea/var/dionaea/logsql.sqlite \
  --meli-url http://127.0.0.1:17654/api/v1/events/ingest \
  --token YOUR_INGEST_TOKEN
```

Or configure Dionaea's HPFEED output plugin to publish to your Mosquitto instance.

---

## HTTP Honeypots (bundled, Snare/Tanner, nginx)

### Bundled Meli HTTP honeypot (recommended)

Meli ships a small stdlib-only HTTP honeypot that runs alongside Cowrie on
the same Pi. It logs every request as a canonical Meli event and publishes
straight to the `meli/events/ingest` MQTT topic — no separate forwarder
needed because we control the source.

Events carry `honeypot.type = "http"` so the Live Feed and Attackers view
distinguish them from Cowrie SSH/Telnet traffic automatically.

Deploy from your workstation:

```bash
# Same-host (Meli + Cowrie + Mosquitto + HTTP honeypot all on the Pi):
meli/scripts/deploy_http_honeypot.sh pi@192.168.0.125

# Meli on a different LAN host, and redirect :80 -> :8080 on the Pi:
MELI_MQTT_HOST=192.168.0.10 \
    MELI_HTTP_REDIRECT_80=1 \
    meli/scripts/deploy_http_honeypot.sh pi@192.168.0.125
```

The script provisions:
- `meli-http` system user (no shell, no home)
- `/opt/meli-http-honeypot/meli_http_honeypot.py`
- `/etc/systemd/system/meli-http-honeypot.service` (auto-restart, hardened)
- `/var/lib/meli-http-honeypot/backup.jsonl` — MQTT-outage fallback log
- (optional) iptables PREROUTING rule redirecting port 80 to 8080

Verify end-to-end:
```bash
curl http://<pi-ip>:8080/wp-admin/
ssh pi@<pi-ip> 'sudo journalctl -u meli-http-honeypot -f'
```

A `web_request` event should appear in Meli Live Feed within seconds, and
the source IP should show up under Attackers tagged with `HTTP` (or
`SSH | HTTP` if it also hit Cowrie).

Standalone run for testing:
```bash
python3 meli/scripts/meli_http_honeypot.py --port 8080 \
    --mqtt-host 127.0.0.1 --backup-log /tmp/meli-http-backup.jsonl
```

### Snare/Tanner

Snare → Tanner can be configured to POST to Meli directly via a custom reporter:

```python
# In tanner/reporter/meli_reporter.py
import requests
requests.post("http://127.0.0.1:17654/api/v1/events/ingest",
              headers={"Authorization": "Bearer TOKEN"},
              json=event_data)
```

### Custom nginx honeypot

Log in JSON format and forward:

```nginx
log_format meli_json escape=json '{'
  '"timestamp":"$time_iso8601",'
  '"remote_addr":"$remote_addr",'
  '"method":"$request_method",'
  '"path":"$request_uri",'
  '"status":$status,'
  '"user_agent":"$http_user_agent"'
  '}';

access_log /var/log/nginx/meli.json meli_json;
```

Then:
```bash
tail -n 0 -F /var/log/nginx/meli.json | \
  mosquitto_pub -h 127.0.0.1 -t meli/events/ingest -l
```

---

## Remote Honeypots (Different Server)

If your honeypot runs on a different machine:

1. Expose the Meli HTTP ingest endpoint (change `http_ingest.host` to `0.0.0.0`)
2. Use a firewall rule to restrict access to trusted IPs only
3. Send events with Bearer token authentication

Or set up MQTT federation:
```bash
# On the honeypot server, bridge its local Mosquitto to your Meli server
# In /etc/mosquitto/conf.d/meli_bridge.conf:
connection meli-bridge
address MELI_SERVER_IP:1883
topic meli/events/ingest out 1
```

---

## Testing the Connection

```bash
# Test HTTP ingest
curl -X POST http://127.0.0.1:17654/api/v1/events/ingest \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "network": {"source_ip": "203.0.113.1", "destination_port": 22},
    "honeypot": {"type": "cowrie"},
    "action": {"type": "login_attempt",
                "details": {"username": "root", "password": "qwerty"}},
    "timestamp": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"
  }'

# Test MQTT
mosquitto_pub -h 127.0.0.1 -t meli/events/ingest -m '{
  "src_ip": "203.0.113.1",
  "eventid": "cowrie.login.failed",
  "username": "admin",
  "password": "admin123",
  "timestamp": "2024-01-15T12:00:00Z"
}'
```

Events should appear in Meli's Live Feed within seconds.

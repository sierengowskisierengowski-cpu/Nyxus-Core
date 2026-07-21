#!/usr/bin/env bash
# deploy_http_honeypot.sh — Push the Meli HTTP honeypot + systemd unit to a
# remote host (typically the same Pi already running Cowrie) and bring it up.
#
# Run this from your laptop, NOT from the Pi itself. It uses ssh/scp, so the
# Pi must be reachable and your SSH key authorized.
#
# Usage:
#   ./deploy_http_honeypot.sh pi@192.168.0.125
#
# Optional environment overrides:
#   MELI_HTTP_PORT=8080           # honeypot listens here (default 8080)
#   MELI_MQTT_HOST=127.0.0.1      # set if Meli runs on a different host
#   MELI_MQTT_PORT=1883
#   MELI_MQTT_TOPIC=meli/events/ingest
#   MELI_HTTP_REDIRECT_80=1       # add iptables 80 -> MELI_HTTP_PORT redirect

set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
    echo "usage: $0 user@host" >&2
    exit 2
fi

MELI_HTTP_PORT="${MELI_HTTP_PORT:-8080}"
MELI_MQTT_HOST="${MELI_MQTT_HOST:-127.0.0.1}"
MELI_MQTT_PORT="${MELI_MQTT_PORT:-1883}"
MELI_MQTT_TOPIC="${MELI_MQTT_TOPIC:-meli/events/ingest}"
MELI_HTTP_REDIRECT_80="${MELI_HTTP_REDIRECT_80:-0}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Checking $TARGET is reachable"
ssh -o ConnectTimeout=5 -o BatchMode=yes "$TARGET" \
    'echo "connected as $(whoami) on $(hostname)"'

echo "==> Creating service user + install dir"
ssh "$TARGET" "sudo bash -s" <<'REMOTE'
set -euo pipefail
id meli-http >/dev/null 2>&1 || sudo useradd --system --no-create-home \
    --shell /usr/sbin/nologin meli-http
sudo mkdir -p /opt/meli-http-honeypot /var/lib/meli-http-honeypot
sudo chown meli-http:meli-http /var/lib/meli-http-honeypot
REMOTE

echo "==> Installing paho-mqtt"
ssh "$TARGET" "sudo apt-get install -y python3-paho-mqtt >/dev/null 2>&1 || \
    sudo pip3 install --break-system-packages paho-mqtt"

echo "==> Copying script"
scp "$SCRIPT_DIR/meli_http_honeypot.py" "$TARGET:/tmp/meli_http_honeypot.py"
ssh "$TARGET" "sudo install -m 0755 -o root -g root \
    /tmp/meli_http_honeypot.py /opt/meli-http-honeypot/meli_http_honeypot.py \
    && rm /tmp/meli_http_honeypot.py"

echo "==> Copying systemd unit"
scp "$REPO_ROOT/meli-http-honeypot.service" \
    "$TARGET:/tmp/meli-http-honeypot.service"
ssh "$TARGET" "sudo bash -s" <<REMOTE
set -euo pipefail
sudo install -m 0644 /tmp/meli-http-honeypot.service \
    /etc/systemd/system/meli-http-honeypot.service
sudo sed -i \
    -e "s|^Environment=MELI_HTTP_PORT=.*|Environment=MELI_HTTP_PORT=$MELI_HTTP_PORT|" \
    -e "s|^Environment=MELI_MQTT_HOST=.*|Environment=MELI_MQTT_HOST=$MELI_MQTT_HOST|" \
    -e "s|^Environment=MELI_MQTT_PORT=.*|Environment=MELI_MQTT_PORT=$MELI_MQTT_PORT|" \
    -e "s|^Environment=MELI_MQTT_TOPIC=.*|Environment=MELI_MQTT_TOPIC=$MELI_MQTT_TOPIC|" \
    /etc/systemd/system/meli-http-honeypot.service
rm /tmp/meli-http-honeypot.service
sudo systemctl daemon-reload
sudo systemctl enable --now meli-http-honeypot.service
REMOTE

if [[ "$MELI_HTTP_REDIRECT_80" == "1" ]]; then
    echo "==> Installing iptables redirect 80 -> $MELI_HTTP_PORT"
    ssh "$TARGET" "sudo bash -s" <<REMOTE
set -euo pipefail
# Idempotent: remove any existing rule for this port pair before adding.
sudo iptables -t nat -C PREROUTING -p tcp --dport 80 \
    -j REDIRECT --to-port $MELI_HTTP_PORT 2>/dev/null && \
    sudo iptables -t nat -D PREROUTING -p tcp --dport 80 \
        -j REDIRECT --to-port $MELI_HTTP_PORT
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 \
    -j REDIRECT --to-port $MELI_HTTP_PORT
# Best-effort persist (works on Debian/Ubuntu with iptables-persistent).
if command -v netfilter-persistent >/dev/null 2>&1; then
    sudo netfilter-persistent save || true
fi
REMOTE
fi

echo "==> Service status"
ssh "$TARGET" "systemctl --no-pager --full status meli-http-honeypot.service | head -20"

echo "==> Recent logs"
ssh "$TARGET" "sudo journalctl -u meli-http-honeypot.service -n 20 --no-pager"

cat <<EOF

Done. To verify end-to-end:
  1. From another host:  curl http://<pi-ip>:$MELI_HTTP_PORT/wp-admin/
  2. Watch the honeypot: ssh $TARGET 'sudo journalctl -u meli-http-honeypot -f'
  3. Open Meli's Live Feed — a 'web_request' event with honeypot.type=http
     should appear within a few seconds, distinguishable from Cowrie's SSH
     events by the service column.
EOF

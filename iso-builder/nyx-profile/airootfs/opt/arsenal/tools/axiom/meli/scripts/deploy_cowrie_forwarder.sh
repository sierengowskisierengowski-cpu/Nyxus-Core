#!/usr/bin/env bash
# deploy_cowrie_forwarder.sh — Push cowrie_to_meli.py + systemd unit to a
# remote host (e.g. a Pi running Cowrie) and bring up the service.
#
# Run this from your laptop, NOT from the Pi itself. It uses ssh/scp, so the
# Pi must be reachable and your SSH key authorized.
#
# Usage:
#   ./deploy_cowrie_forwarder.sh pi@192.168.0.125
#
# Optional environment overrides:
#   COWRIE_LOG=/opt/cowrie/var/log/cowrie/cowrie.json
#   MELI_MQTT_HOST=127.0.0.1      # set to your Meli host if it's not the Pi
#   MELI_MQTT_PORT=1883
#   MELI_MQTT_TOPIC=meli/events/ingest

set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
    echo "usage: $0 user@host" >&2
    exit 2
fi

COWRIE_LOG="${COWRIE_LOG:-/opt/cowrie/var/log/cowrie/cowrie.json}"
MELI_MQTT_HOST="${MELI_MQTT_HOST:-127.0.0.1}"
MELI_MQTT_PORT="${MELI_MQTT_PORT:-1883}"
MELI_MQTT_TOPIC="${MELI_MQTT_TOPIC:-meli/events/ingest}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Checking $TARGET is reachable"
ssh -o ConnectTimeout=5 -o BatchMode=yes "$TARGET" 'echo "connected as $(whoami) on $(hostname)"'

echo "==> Checking Cowrie log exists at $COWRIE_LOG"
ssh "$TARGET" "test -f '$COWRIE_LOG'" || {
    echo "ERROR: $COWRIE_LOG not found on $TARGET" >&2
    echo "Set COWRIE_LOG=... and re-run, or start Cowrie first." >&2
    exit 1
}

echo "==> Creating service user + install dir"
ssh "$TARGET" "sudo bash -s" <<'REMOTE'
set -euo pipefail
id cowrie-meli >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin cowrie-meli
sudo mkdir -p /opt/cowrie-to-meli /var/lib/cowrie-to-meli
sudo chown cowrie-meli:cowrie-meli /var/lib/cowrie-to-meli
# Let cowrie-meli read the cowrie log dir (typical Cowrie installs allow group read).
sudo usermod -a -G cowrie cowrie-meli 2>/dev/null || true
REMOTE

echo "==> Installing paho-mqtt"
ssh "$TARGET" "sudo apt-get install -y python3-paho-mqtt >/dev/null 2>&1 || sudo pip3 install --break-system-packages paho-mqtt"

echo "==> Copying script"
scp "$SCRIPT_DIR/cowrie_to_meli.py" "$TARGET:/tmp/cowrie_to_meli.py"
ssh "$TARGET" "sudo install -m 0755 -o root -g root /tmp/cowrie_to_meli.py /opt/cowrie-to-meli/cowrie_to_meli.py && rm /tmp/cowrie_to_meli.py"

echo "==> Copying systemd unit"
scp "$REPO_ROOT/cowrie-to-meli.service" "$TARGET:/tmp/cowrie-to-meli.service"
ssh "$TARGET" "sudo bash -s" <<REMOTE
set -euo pipefail
# Rewrite the Environment= defaults to the values you passed in.
sudo install -m 0644 /tmp/cowrie-to-meli.service /etc/systemd/system/cowrie-to-meli.service
sudo sed -i \
    -e "s|^Environment=COWRIE_LOG=.*|Environment=COWRIE_LOG=$COWRIE_LOG|" \
    -e "s|^Environment=MELI_MQTT_HOST=.*|Environment=MELI_MQTT_HOST=$MELI_MQTT_HOST|" \
    -e "s|^Environment=MELI_MQTT_PORT=.*|Environment=MELI_MQTT_PORT=$MELI_MQTT_PORT|" \
    -e "s|^Environment=MELI_MQTT_TOPIC=.*|Environment=MELI_MQTT_TOPIC=$MELI_MQTT_TOPIC|" \
    /etc/systemd/system/cowrie-to-meli.service
rm /tmp/cowrie-to-meli.service
sudo systemctl daemon-reload
sudo systemctl enable --now cowrie-to-meli.service
REMOTE

echo "==> Service status"
ssh "$TARGET" "systemctl --no-pager --full status cowrie-to-meli.service | head -20"

echo "==> Recent logs"
ssh "$TARGET" "sudo journalctl -u cowrie-to-meli.service -n 20 --no-pager"

cat <<EOF

Done. To verify end-to-end:
  1. From another host:  ssh -p 2222 root@<pi-ip>   # trigger a Cowrie session
  2. Watch the forwarder: ssh $TARGET 'sudo journalctl -u cowrie-to-meli -f'
  3. Open Meli's Live Feed — events should appear within a few seconds.
EOF

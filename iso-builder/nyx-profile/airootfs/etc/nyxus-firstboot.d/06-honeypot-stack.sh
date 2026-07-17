#!/usr/bin/env bash
# NYXUS firstboot · bring the honeypot/Docker stack up exactly once.
# After this, docker.service + each container's restart:unless-stopped
# policy is 100% of what keeps them running across future reboots —
# same mechanism as the machine this ISO was built from, no extra unit.
set -u
MARKER=/var/lib/nyxus/honeypot-stack.done
[[ -f "${MARKER}" ]] && exit 0

if ! command -v docker >/dev/null 2>&1; then
  echo "[firstboot] docker not installed — skipping honeypot stack"
  exit 0
fi
systemctl start docker.service 2>/dev/null

cd /opt/honeypot || exit 0

if grep -q '^GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME_ON_FIRST_BOOT$' .env 2>/dev/null; then
  GEN_PW="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20)"
  sed -i "s/^GF_SECURITY_ADMIN_PASSWORD=.*/GF_SECURITY_ADMIN_PASSWORD=${GEN_PW}/" .env
  {
    echo "Grafana admin password (generated on first boot): ${GEN_PW}"
    echo "Log in at http://localhost:3000 (user: admin)"
  } > /root/nyxus-grafana-admin-password.txt
  chmod 0600 /root/nyxus-grafana-admin-password.txt
fi

if [[ -d images ]]; then
  for tar in images/*.tar; do
    [[ -f "${tar}" ]] && docker load -i "${tar}"
  done
fi

if docker compose -f docker-compose.yml --env-file .env up -d; then
  echo "[firstboot] honeypot stack started"
else
  echo "[firstboot] honeypot stack failed to start — check 'docker compose logs' in /opt/honeypot"
fi

mkdir -p /var/lib/nyxus
date -Iseconds > "${MARKER}"

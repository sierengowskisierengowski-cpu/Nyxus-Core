#!/usr/bin/env bash
# NYXUS — NYXUS Notifications bootstrap installer
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_notifications_install.sh | bash
# (c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

B=$'\e[1m'; R=$'\e[0m'; PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'; DIM=$'\e[2m'
step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    printf "  ${DIM}elevating with sudo (you'll be prompted)…${R}\n\n"
    if [[ -f "$0" && -r "$0" ]]; then
      exec sudo -E bash "$0" "$@"
    else
      exec sudo -E bash -c "curl -fsSL 'https://nyxus-core.replit.app/api/download/nyxus/nyxus_notifications_install.sh' | bash"
    fi
  fi
  fail "must be run as root"; exit 1
fi

BASE="${NYXUS_BASE:-https://nyxus-core.replit.app/api/download/nyxus}"
TGZ_URL="${BASE}/nyxus-notifications.tgz"

step "fetch nyxus-notifications.tgz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if command -v curl >/dev/null; then
  curl -fsSL "$TGZ_URL" -o "$TMP/nyxus-notifications.tgz" || { fail "download failed"; exit 1; }
elif command -v wget >/dev/null; then
  wget -q -O "$TMP/nyxus-notifications.tgz" "$TGZ_URL" || { fail "download failed"; exit 1; }
else
  fail "neither curl nor wget present"; exit 1
fi
ok "downloaded $(du -h "$TMP/nyxus-notifications.tgz" | cut -f1)"

step "extract"
tar xzf "$TMP/nyxus-notifications.tgz" -C "$TMP"
ok "extracted"

step "run install.sh"
chmod +x "$TMP/nyxus-notifications/install.sh"
"$TMP/nyxus-notifications/install.sh" "$@"

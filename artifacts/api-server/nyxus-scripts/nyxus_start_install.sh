#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# NYXUS Start — top-level installer
#
# Pulls the nyxus-start.tgz tarball from the NYXUS download portal,
# extracts it to a temp dir, and runs the inner install.sh.
#
# Usage (on the target Arch box):
#     curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_start_install.sh | sudo bash
#
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

B=$'\e[1m'; R=$'\e[0m'; PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

DIM=$'\e[2m'

# ── ROOT CHECK + SELF-ESCALATION ────────────────────────────────────────
# This installer needs root for pacman + ownership-preserving file ops.
# Without it the inner install.sh hits a chown failure under `set -e` and
# bails partway through, leaving the user with a half-applied state
# (downloads succeed, files never deploy, fonts never register, Waybar
# never gets patched). Auto-elevate via sudo. When invoked through
# `curl … | bash` $0 is /dev/stdin, so we re-curl ourselves under sudo.
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    printf "  ${DIM}elevating with sudo (you'll be prompted)…${R}\n\n"
    if [[ -f "$0" && -r "$0" ]]; then
      exec sudo -E bash "$0" "$@"
    else
      exec sudo -E bash -c "curl -fsSL 'https://nyxus-core.replit.app/api/download/nyxus/nyxus_start_install.sh' | bash"
    fi
  fi
  fail "must be run as root (sudo not available)"; exit 1
fi

BASE="${NYXUS_BASE:-https://nyxus-core.replit.app/api/download/nyxus}"
TGZ_URL="${BASE}/nyxus-start.tgz"

step "fetch nyxus-start.tgz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if command -v curl >/dev/null; then
  curl -fsSL "$TGZ_URL" -o "$TMP/nyxus-start.tgz" || { fail "download failed"; exit 1; }
elif command -v wget >/dev/null; then
  wget -q -O "$TMP/nyxus-start.tgz" "$TGZ_URL" || { fail "download failed"; exit 1; }
else
  fail "neither curl nor wget present"; exit 1
fi
ok "downloaded $(du -h "$TMP/nyxus-start.tgz" | cut -f1)"

step "extract"
tar xzf "$TMP/nyxus-start.tgz" -C "$TMP"
ok "extracted to $TMP/start"

step "run install.sh"
chmod +x "$TMP/start/install.sh"
"$TMP/start/install.sh" "$@"

cat <<EOF

──────────────────────────────────────────────────────────────────────
${B}NYXUS Start install complete.${R}
Launch with: ${GOLD}nyxus-start${R}
──────────────────────────────────────────────────────────────────────
EOF

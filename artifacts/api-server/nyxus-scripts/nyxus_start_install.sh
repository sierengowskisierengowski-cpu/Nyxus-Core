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

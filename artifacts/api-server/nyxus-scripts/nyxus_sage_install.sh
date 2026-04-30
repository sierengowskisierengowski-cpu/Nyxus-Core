#!/usr/bin/env bash
# ============================================================================
# NYXUS SAGE · one-shot installer
# Downloads nyxus-sage.tgz, extracts, runs install.sh
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_sage_install.sh | bash
# ============================================================================
set -euo pipefail

BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
TGZ="nyxus-sage.tgz"
WORK="$(mktemp -d /tmp/nyxus-sage.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

# colors
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
      exec sudo -E bash -c "curl -fsSL '${BASE_URL}/api/download/nyxus/nyxus_sage_install.sh' | bash"
    fi
  fi
  fail "must be run as root (sudo not available)"; exit 1
fi

step "preflight"
for cmd in curl tar bash python3; do
  command -v "$cmd" >/dev/null 2>&1 || { fail "$cmd not found — install it first"; exit 1; }
done
ok "curl, tar, bash, python3 present"

step "fetch ${TGZ}"
curl -fsSL "${BASE_URL}/api/download/nyxus/${TGZ}" -o "${WORK}/${TGZ}"
ok "downloaded → $(du -h "${WORK}/${TGZ}" | cut -f1)"

step "extract"
tar -xzf "${WORK}/${TGZ}" -C "${WORK}"
ok "extracted to ${WORK}"

step "install"
if [[ ! -d "${WORK}/sage" ]]; then
  fail "tarball missing 'sage/' directory"; exit 1
fi
bash "${WORK}/sage/install.sh"

cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS SAGE is ready.${R}

  ${B}gui:${R}     nyxus-sage      ${DIM}(or just: sage)${R}
  ${B}cli:${R}     nyxus-audit <path>
  ${B}menu:${R}    NYXUS SAGE in your application launcher

  ${B}try it:${R}  nyxus-audit ~/.local/bin
            nyxus-audit ~/repos/some-project

  ${PURPLE}A U D I T  ·  L E A R N  ·  K N O W${R}

EOF

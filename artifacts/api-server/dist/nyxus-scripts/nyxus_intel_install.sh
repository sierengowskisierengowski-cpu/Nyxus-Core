#!/usr/bin/env bash
# ============================================================================
# NYXUS INTEL · one-shot installer
# Downloads nyxus-intel.tgz, extracts, runs install.sh
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_intel_install.sh | bash
# ============================================================================
set -euo pipefail

BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
TGZ="nyxus-intel.tgz"
WORK="$(mktemp -d /tmp/nyxus-intel.XXXXXX)"
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
      exec sudo -E bash -c "curl -fsSL '${BASE_URL}/api/download/nyxus/nyxus_intel_install.sh' | bash"
    fi
  fi
  fail "must be run as root (sudo not available)"; exit 1
fi

cat <<EOF

${PURPLE}  ███╗   ██╗██╗   ██╗██╗  ██╗██╗   ██╗███████╗${R}
${PURPLE}  ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝██║   ██║██╔════╝${R}
${PURPLE}  ██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██║   ██║███████╗${R}
${PURPLE}  ██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║   ██║╚════██║${R}
${PURPLE}  ██║ ╚████║   ██║   ██╔╝ ██╗╚██████╔╝███████║${R}
${PURPLE}  ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝${R}
                  ${B}I N T E L${R}
        ${DIM}open source intelligence workstation${R}

EOF

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
if [[ ! -d "${WORK}/intel" ]]; then
  fail "tarball missing 'intel/' directory"; exit 1
fi
bash "${WORK}/intel/install.sh"

cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS Intel is ready.${R}

  ${B}launch:${R}    ${PINK}nyxus-intel${R}
  ${B}config:${R}    \$HOME/.config/nyxus-intel/config.json
  ${B}cases:${R}     \$HOME/.config/nyxus-intel/cases/  ${DIM}(encrypted)${R}

  First launch: legal disclaimer → set master password → unlock.
  Add API keys in ${B}Settings → API Keys${R} (every key is optional;
  modules without a key show a hint instead of fake data).

  ${PURPLE}I N V E S T I G A T E   R E S P O N S I B L Y${R}

EOF

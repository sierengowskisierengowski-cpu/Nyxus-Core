#!/usr/bin/env bash
# ============================================================================
# NYXUS PANEL · one-shot installer
# Downloads nyxus-panel.tgz, extracts, runs install.sh
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_panel_install.sh | bash
# ============================================================================
set -euo pipefail

BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
TGZ="nyxus-panel.tgz"
WORK="$(mktemp -d /tmp/nyxus-panel.XXXXXX)"
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
      exec sudo -E bash -c "curl -fsSL '${BASE_URL}/api/download/nyxus/nyxus_panel_install.sh' | bash"
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
                  ${B}P A N E L${R}
        ${DIM}news · weather · system stats${R}

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
if [[ ! -d "${WORK}/panel" ]]; then
  fail "tarball missing 'panel/' directory"; exit 1
fi
bash "${WORK}/panel/install.sh"

cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS Panel is ready.${R}

  ${B}launch:${R}    ${PINK}nyxus-panel${R}     ${DIM}(toggles open / close)${R}
  ${B}eww:${R}       See ~/.config/eww/README.md for the EWW bar (replaces waybar)
  ${B}config:${R}    \$HOME/.config/nyxus-panel/config.json

  ${PURPLE}N E W S  ·  W E A T H E R  ·  S Y S T E M${R}

EOF

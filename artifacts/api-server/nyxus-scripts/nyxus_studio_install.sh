#!/usr/bin/env bash
# ============================================================================
# NYXUS Studio · one-shot installer
# Downloads nyxus-studio.tgz, extracts, runs install.sh
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_studio_install.sh | bash
# ============================================================================
set -euo pipefail

BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
TGZ="nyxus-studio.tgz"
WORK="$(mktemp -d /tmp/nyxus-studio.XXXXXX)"
trap 'rm -rf "$WORK"' EXIT

# colors
B=$'\e[1m'; R=$'\e[0m'; PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; DIM=$'\e[2m'

step() { printf "\n${PINK}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    printf "  ${DIM}elevating with sudo (you'll be prompted)…${R}\n\n"
    if [[ -f "$0" && -r "$0" ]]; then
      exec sudo -E bash "$0" "$@"
    else
      exec sudo -E bash -c "curl -fsSL '${BASE_URL}/api/download/nyxus/nyxus_studio_install.sh' | bash"
    fi
  fi
  fail "must be run as root (sudo not available)"; exit 1
fi

step "preflight"
for cmd in curl tar bash; do
  command -v "$cmd" >/dev/null 2>&1 || { fail "$cmd not found — install it first"; exit 1; }
done
ok "curl, tar, bash present"

step "fetch ${TGZ}"
curl -fsSL "${BASE_URL}/api/download/nyxus/${TGZ}" -o "${WORK}/${TGZ}"
ok "downloaded → ${WORK}/${TGZ}"

step "extract"
tar -xzf "${WORK}/${TGZ}" -C "${WORK}"
ok "extracted to ${WORK}"

step "install"
if [[ ! -d "${WORK}/studio" ]]; then
  fail "tarball missing 'studio/' directory"; exit 1
fi
bash "${WORK}/studio/install.sh"
ok "studio installed"

cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS Studio is ready.${R}

  ${B}launch:${R}    nyxus-studio

  ${B}modules:${R}   Paint · Vector · 3D · Video · Animate
              Photo · Layout · Type · Voice

  ${PINK}P A I N T  ·  V E C T O R  ·  3 D  ·  V I D E O${R}
  ${PINK}A N I M A T E  ·  P H O T O  ·  L A Y O U T${R}
  ${PINK}T Y P E  ·  V O I C E${R}

EOF

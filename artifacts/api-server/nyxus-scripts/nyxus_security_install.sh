#!/usr/bin/env bash
# ============================================================================
#  NYXUS Security Stack — one-shot installer
#  © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Installs all three NYXUS security apps in one go:
#    • Phantom  — silent systemd security daemon
#    • Shield   — everyday GTK4 security GUI
#    • GodsApp  — 30-module pro security suite
#
#  Usage:
#    curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_security_install.sh | bash
#
#  Or skip individual apps:
#    NYXUS_SKIP_PHANTOM=1  NYXUS_SKIP_SHIELD=1  NYXUS_SKIP_GODSAPP=1
# ============================================================================
set -uo pipefail

BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
WORK_DIR="${TMPDIR:-/tmp}/nyxus-security-$$"

# ── colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  R="\033[0m"; B="\033[1m"; DIM="\033[2m"
  PINK="\033[38;5;213m"; GREEN="\033[38;5;120m"
  GOLD="\033[38;5;220m"; PURPLE="\033[38;5;177m"
  RED="\033[38;5;203m";  BLUE="\033[38;5;111m"
else
  R="";B="";DIM="";PINK="";GREEN="";GOLD="";PURPLE="";RED="";BLUE=""
fi

ok()    { printf "  ${GREEN}✓${R}  %s\n" "$*"; }
warn()  { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail()  { printf "  ${RED}✗${R}  %s\n" "$*"; }
step()  { printf "\n${PURPLE}${B}── %s ──${R}\n" "$*"; }

# ── banner ───────────────────────────────────────────────────────────────────
clear 2>/dev/null || true
cat <<EOF
${PINK}${B}
   ███╗   ██╗██╗   ██╗██╗  ██╗██╗   ██╗███████╗
   ████╗  ██║╚██╗ ██╔╝╚██╗██╔╝██║   ██║██╔════╝
   ██╔██╗ ██║ ╚████╔╝  ╚███╔╝ ██║   ██║███████╗
   ██║╚██╗██║  ╚██╔╝   ██╔██╗ ██║   ██║╚════██║
   ██║ ╚████║   ██║   ██╔╝ ██╗╚██████╔╝███████║
   ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
${R}${GOLD}            S E C U R I T Y   S T A C K${R}
${DIM}              phantom · shield · godsapp${R}

EOF

# ── elevation ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    printf "  ${DIM}elevating with sudo (you'll be prompted)…${R}\n\n"
    exec sudo -E bash "$0" "$@"
  fi
  fail "must be run as root (sudo not available)"
  exit 1
fi

# ── pre-flight ───────────────────────────────────────────────────────────────
step "preflight"
for cmd in curl tar bash; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    fail "$cmd not found — install it first"; exit 1
  fi
done
ok "tools present (curl, tar, bash)"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
ok "workspace: $WORK_DIR"

# ── installer for one app ────────────────────────────────────────────────────
install_app() {
  local app="$1"        # phantom | shield | godsapp
  local skip_var="$2"   # NYXUS_SKIP_PHANTOM etc.
  local pkg="nyxus-${app}.tgz"

  if [[ "${!skip_var:-0}" == "1" ]]; then
    warn "skipping ${app} (${skip_var}=1)"
    return 0
  fi

  step "${app}"
  printf "  ${DIM}downloading ${pkg}…${R}\n"
  if ! curl -fsSL --retry 3 --retry-delay 2 -o "$pkg" "$BASE_URL/api/download/nyxus/$pkg"; then
    fail "download failed: $pkg"
    return 1
  fi
  ok "downloaded $(du -h "$pkg" | cut -f1)"

  printf "  ${DIM}extracting…${R}\n"
  if ! tar xzf "$pkg"; then
    fail "extract failed: $pkg"
    return 1
  fi
  ok "extracted ${app}/ + theme/"

  if [[ ! -d "$app" ]]; then
    fail "expected directory '$app' not found in tarball"
    return 1
  fi

  printf "  ${DIM}running ${app}/install.sh…${R}\n\n"
  if ( cd "$app" && bash install.sh ); then
    ok "${app} installed"
    return 0
  else
    fail "${app} installer exited with error"
    return 1
  fi
}

# ── run all three ────────────────────────────────────────────────────────────
declare -i failed=0
declare -a failed_apps=()

for app_pair in "phantom:NYXUS_SKIP_PHANTOM" "shield:NYXUS_SKIP_SHIELD" "godsapp:NYXUS_SKIP_GODSAPP"; do
  app="${app_pair%%:*}"
  skip_var="${app_pair##*:}"
  if ! install_app "$app" "$skip_var"; then
    failed+=1
    failed_apps+=("$app")
  fi
done

# ── post-install: enable phantom service ─────────────────────────────────────
if [[ "${NYXUS_SKIP_PHANTOM:-0}" != "1" ]] && systemctl list-unit-files 2>/dev/null | grep -q '^nyxus-phantom\.service'; then
  step "phantom systemd service"
  printf "  ${DIM}enabling + starting nyxus-phantom.service…${R}\n"
  if systemctl enable --now nyxus-phantom.service 2>/dev/null; then
    ok "nyxus-phantom is running"
    sleep 1
    systemctl --no-pager --lines=0 status nyxus-phantom.service 2>/dev/null \
      | head -3 | sed 's/^/    /'
  else
    warn "could not enable nyxus-phantom (check: journalctl -u nyxus-phantom)"
  fi
fi

# ── cleanup ──────────────────────────────────────────────────────────────────
cd /
rm -rf "$WORK_DIR" 2>/dev/null || true

# ── summary ──────────────────────────────────────────────────────────────────
echo
printf "${DIM}──────────────────────────────────────────────────────────────────────${R}\n"
echo
if [[ $failed -eq 0 ]]; then
  printf "  ${GREEN}${B}NYXUS Security Stack installed.${R}\n\n"
  printf "  ${PURPLE}${B}Phantom${R}   ${DIM}silent daemon — no GUI${R}\n"
  printf "    ${DIM}status:  systemctl status nyxus-phantom${R}\n"
  printf "    ${DIM}live:    journalctl -fu nyxus-phantom${R}\n\n"
  printf "  ${PURPLE}${B}Shield${R}    ${DIM}everyday GUI${R}\n"
  printf "    ${DIM}launch:  nyxus-shield${R}\n\n"
  printf "  ${PURPLE}${B}GodsApp${R}   ${DIM}30-module pro suite${R}\n"
  printf "    ${DIM}launch:  nyxus-godsapp${R}\n"
  printf "    ${DIM}legal:   cat /opt/nyxus-godsapp/LEGAL.md${R}\n\n"
  printf "  ${GOLD}${B}P R O T E C T E D · S I L E N T · A L W A Y S${R}\n"
else
  printf "  ${RED}${B}${failed} app(s) failed to install:${R}\n"
  for a in "${failed_apps[@]}"; do
    printf "    ${RED}✗${R}  ${DIM}${a}${R}\n"
  done
  echo
  printf "  ${DIM}Re-run with verbose mode for details:${R}\n"
  printf "  ${DIM}  curl -fsSL ${BASE_URL}/api/download/nyxus/nyxus_security_install.sh | bash -x${R}\n"
  exit 1
fi
echo

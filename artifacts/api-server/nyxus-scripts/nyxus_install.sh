#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║        NYXUS OS — One-Line Installer                     ║
# ║  Downloads all 4 NYXUS terminal scripts in one shot      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-LOCKED        ║
# ╚══════════════════════════════════════════════════════════╝
#
# Usage:
#   curl -fsSL <BASE_URL>/api/download/nyxus/nyxus_install.sh | bash
#
# Or to a specific directory:
#   curl -fsSL <BASE_URL>/api/download/nyxus/nyxus_install.sh | bash -s -- --dir ~/nyxus

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_URL="${NYXUS_BASE_URL:-https://nyxus-os.replit.app}"
API_PATH="/api/download/nyxus"
INSTALL_DIR="${1:-$HOME/.nyxus}"

SCRIPTS=(
  "nyxus_preboot.py"
  "nyxus_motd.py"
  "nyxus_splash.py"
  "nyxus_error.py"
)

# ── COLORS ────────────────────────────────────────────────────────────────────
R="\033[0m"
B="\033[1m"
PURPLE="\033[38;5;135m"
PINK="\033[38;5;213m"
GOLD="\033[38;5;220m"
DIM="\033[2m"
GREEN="\033[92m"
RED="\033[91m"

# ── HEADER ────────────────────────────────────────────────────────────────────
echo ""
printf "${PURPLE}${B}██   ██  ██  ██   ██   ██  ██   ██   █████ ${R}\n"
printf "${PINK}${B}███  ██   █████    ██ ██   ██   ██  ██     ${R}\n"
printf "${GOLD}${B}██ █ ██    ███     ███    ██   ██   █████  ${R}\n"
printf "${PINK}${B}██  ███    ███    ██ ██   ██   ██       ██ ${R}\n"
printf "${PURPLE}${B}██   ██    ███   ██   ██   █████   █████  ${R}\n"
echo ""
printf "  ${DIM}S I L E N T · D A R K · P U R E L Y   F U N C T I O N A L${R}\n"
printf "  ${DIM}© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED${R}\n"
echo ""
printf "${DIM}──────────────────────────────────────────────────────────${R}\n"

# ── INSTALL DIR ───────────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
printf "  ${DIM}Target: ${R}${GOLD}${INSTALL_DIR}${R}\n"
echo ""

# ── DOWNLOAD EACH SCRIPT ─────────────────────────────────────────────────────
failed=0
for script in "${SCRIPTS[@]}"; do
  printf "  ${DIM}downloading${R} ${PURPLE}${script}${R} ... "
  url="${BASE_URL}${API_PATH}/${script}"
  dest="${INSTALL_DIR}/${script}"

  if curl -fsSL -o "$dest" "$url" 2>/dev/null; then
    chmod +x "$dest"
    printf "${GREEN}${B}✓${R}\n"
  else
    printf "${RED}✗ FAILED${R}\n"
    failed=$((failed + 1))
  fi
done

echo ""
printf "${DIM}──────────────────────────────────────────────────────────${R}\n"

if [[ $failed -eq 0 ]]; then
  printf "  ${GREEN}${B}All scripts installed.${R}\n"
  echo ""
  printf "  ${GOLD}Quick start:${R}\n"
  printf "    ${DIM}python3 ${INSTALL_DIR}/nyxus_preboot.py${R}\n"
  printf "    ${DIM}python3 ${INSTALL_DIR}/nyxus_motd.py${R}\n"
  printf "    ${DIM}python3 ${INSTALL_DIR}/nyxus_splash.py${R}\n"
  printf "    ${DIM}python3 ${INSTALL_DIR}/nyxus_error.py${R}\n"
  echo ""
  printf "  ${PURPLE}${B}NYXUS OS is ready. Run the sequence:${R}\n"
  printf "  ${DIM}python3 ${INSTALL_DIR}/nyxus_preboot.py --next 'python3 ${INSTALL_DIR}/nyxus_splash.py'${R}\n"
else
  printf "  ${RED}${B}${failed} script(s) failed to download.${R}\n"
  printf "  ${DIM}Check your connection or BASE_URL and try again.${R}\n"
  exit 1
fi

echo ""

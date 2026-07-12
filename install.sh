#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  NYXUS — One-Command Terminal Installer                                  ║
# ║  Installs NYXUS configs, EWW bars, Hyprland theme, and GTK apps         ║
# ║                                                                          ║
# ║  Usage (run on a live NYXUS session or compatible Arch/Hyprland setup): ║
# ║    curl -fsSL https://raw.githubusercontent.com/sierengowskisierengowski-cpu/Nyxus-Core/main/install.sh | bash
# ║                                                                          ║
# ║  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED          ║
# ╚══════════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── Design tokens · DARK MIRROR palette ──────────────────────────────────────
R="\033[0m"
B="\033[1m"
DIM="\033[2m"
VIOLET="\033[38;2;160;107;255m"   # #a06bff — obsidian prism violet
CYAN="\033[38;2;58;216;255m"      # #3ad8ff — starlight cyan
GOLD="\033[38;5;220m"
GREEN="\033[92m"
RED="\033[91m"

# ── Helpers ───────────────────────────────────────────────────────────────────
ok()   { printf "  ${GREEN}${B}✓${R}  %s\n" "$1"; }
fail() { printf "  ${RED}${B}✗${R}  %s\n" "$1" >&2; }
warn() { printf "  ${GOLD}${B}!${R}  %s\n" "$1"; }
hdr()  { printf "\n${VIOLET}${B}── %s${R}\n" "$1"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
printf "\n"
printf "${VIOLET}${B}  ███   ██  ██  ██  ██  ██  ██  █████ ${R}\n"
printf "${CYAN}${B}  ████  ██   ████   ██  ██  ██  ██    ${R}\n"
printf "${VIOLET}${B}  ██ █  ██    ██    ██  ██  ██   ████ ${R}\n"
printf "${CYAN}${B}  ██  █ ██    ██     ████   ██      ██ ${R}\n"
printf "${VIOLET}${B}  ██   ████   ██      ██    ██  █████ ${R}\n"
printf "\n"
printf "  ${DIM}DARK MIRROR · OBSIDIAN/PRISM · HYPRLAND${R}\n"
printf "  ${DIM}© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED${R}\n"
printf "\n"
printf "  ${CYAN}${B}Nyxus-Core ${R}${DIM}— https://github.com/sierengowskisierengowski-cpu/Nyxus-Core${R}\n"
printf "\n"

# ── Prerequisites ─────────────────────────────────────────────────────────────
hdr "Prerequisites"

# Bash version check
if (( BASH_VERSINFO[0] < 5 )); then
  fail "bash 5+ required (you have bash ${BASH_VERSION})"
  exit 1
fi
ok "bash ${BASH_VERSION}"

# Required tools
for tool in curl git; do
  if ! command -v "${tool}" &>/dev/null; then
    fail "${tool} not found — install it first"
    exit 1
  fi
  ok "${tool} $(${tool} --version 2>&1 | head -1)"
done

# Arch Linux check (hard requirement — NYXUS is Arch-based)
if [[ -f /etc/os-release ]]; then
  # shellcheck source=/dev/null
  source /etc/os-release
  if [[ "${ID:-}" != "arch" && "${ID_LIKE:-}" != *"arch"* && "${ID:-}" != "nyxus" ]]; then
    fail "NYXUS requires Arch Linux (detected: ${PRETTY_NAME:-unknown})"
    fail "This installer will only work on Arch Linux or NYXUS."
    exit 1
  fi
  ok "OS: ${PRETTY_NAME:-Arch Linux}"
else
  fail "Could not detect OS — /etc/os-release missing. Cannot confirm Arch Linux."
  exit 1
fi

# Hyprland check (soft warning)
if ! command -v hyprctl &>/dev/null; then
  warn "Hyprland not detected — EWW bar launch step will be skipped"
  HYPRLAND_RUNNING=0
else
  ok "Hyprland: $(hyprctl version 2>/dev/null | head -1 || echo 'detected')"
  HYPRLAND_RUNNING=1
fi

# ── Confirmation ──────────────────────────────────────────────────────────────
printf "\n"
printf "  ${GOLD}${B}WARNING:${R} This installer will:\n"
printf "  ${DIM}• Write NYXUS configs to your ~/.config/{eww,hypr,rofi,dunst,...}${R}\n"
printf "  ${DIM}• Install/update NYXUS Python apps to ~/.local/bin/${R}\n"
printf "  ${DIM}• Reload your running EWW/Hyprland session (if detected)${R}\n"
printf "\n"

# Respect non-interactive environments (e.g., piped curl | bash)
if [[ -t 0 ]]; then
  read -r -p "  Proceed? [y/N] " CONFIRM
  CONFIRM="${CONFIRM,,}"
  if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "yes" ]]; then
    printf "\n  ${DIM}Aborted.${R}\n\n"
    exit 0
  fi
else
  warn "Non-interactive mode detected — proceeding automatically."
  warn "Pass NYXUS_NO_CONFIRM=0 to abort non-interactive runs."
  if [[ "${NYXUS_NO_CONFIRM:-1}" == "0" ]]; then
    printf "\n  ${DIM}Aborted (NYXUS_NO_CONFIRM=0).${R}\n\n"
    exit 0
  fi
fi

# ── Determine install source ──────────────────────────────────────────────────
NYXUS_REPO_DIR="${NYXUS_REPO_DIR:-}"
NYXUS_BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
RAW_BASE="https://raw.githubusercontent.com/sierengowskisierengowski-cpu/Nyxus-Core/main"

hdr "Install method"

# Option A: local repo clone available → run directly
if [[ -z "${NYXUS_REPO_DIR}" ]]; then
  for candidate in \
    "${HOME}/Nyxus-Core" \
    "${HOME}/nyxus-core" \
    "${HOME}/.nyxus/repo" \
    "/opt/nyxus/repo"
  do
    if [[ -f "${candidate}/artifacts/api-server/nyxus-scripts/nyxus_install.sh" ]]; then
      NYXUS_REPO_DIR="${candidate}"
      break
    fi
  done
fi

if [[ -n "${NYXUS_REPO_DIR}" ]]; then
  ok "Local repo found: ${NYXUS_REPO_DIR}"
  INSTALL_SCRIPT="${NYXUS_REPO_DIR}/artifacts/api-server/nyxus-scripts/nyxus_install.sh"
else
  # Option B: download nyxus_install.sh from the API or GitHub raw
  warn "No local repo found — fetching nyxus_install.sh from network"
  INSTALL_SCRIPT="$(mktemp /tmp/nyxus_install.XXXXXX.sh)"
  # shellcheck disable=SC2064
  trap "rm -f ${INSTALL_SCRIPT}" EXIT

  DOWNLOAD_OK=0
  # Try API endpoint first
  if curl -fsSL --connect-timeout 10 \
       -o "${INSTALL_SCRIPT}" \
       "${NYXUS_BASE_URL}/api/download/nyxus/nyxus_install.sh" 2>/dev/null; then
    DOWNLOAD_OK=1
    ok "Downloaded from API: ${NYXUS_BASE_URL}"
  fi

  # Fallback: GitHub raw
  if [[ "${DOWNLOAD_OK}" -eq 0 ]]; then
    if curl -fsSL --connect-timeout 15 \
         -o "${INSTALL_SCRIPT}" \
         "${RAW_BASE}/artifacts/api-server/nyxus-scripts/nyxus_install.sh" 2>/dev/null; then
      DOWNLOAD_OK=1
      ok "Downloaded from GitHub raw"
    fi
  fi

  if [[ "${DOWNLOAD_OK}" -eq 0 ]]; then
    fail "Could not download nyxus_install.sh — check your network connection"
    printf "\n  ${DIM}Manual download:${R}\n"
    printf "  ${DIM}  curl -fsSL ${NYXUS_BASE_URL}/api/download/nyxus/nyxus_install.sh -o /tmp/nyxus_install.sh${R}\n"
    printf "  ${DIM}  bash /tmp/nyxus_install.sh${R}\n\n"
    exit 1
  fi

  chmod +x "${INSTALL_SCRIPT}"
fi

# ── Run the installer ─────────────────────────────────────────────────────────
hdr "Running NYXUS installer"
printf "  ${DIM}Script: ${INSTALL_SCRIPT}${R}\n\n"

if bash "${INSTALL_SCRIPT}"; then
  INSTALL_EXIT=0
else
  INSTALL_EXIT=$?
fi

# ── Save repo location for nyxus-sync ─────────────────────────────────────────
if [[ -n "${NYXUS_REPO_DIR}" ]]; then
  mkdir -p "${HOME}/.nyxus"
  printf '%s\n' "${NYXUS_REPO_DIR}" > "${HOME}/.nyxus/repo"
  ok "Repo path saved to ~/.nyxus/repo"
fi

# ── Post-install summary ──────────────────────────────────────────────────────
printf "\n"
printf "${DIM}──────────────────────────────────────────────────────────────────────${R}\n"
printf "\n"

if [[ "${INSTALL_EXIT}" -eq 0 ]]; then
  printf "  ${GREEN}${B}✓ NYXUS installation complete.${R}\n\n"
  printf "  ${VIOLET}${B}Key bindings:${R}\n"
  printf "  ${DIM}  Super+Space     — NYXUS Launcher (nyxus-start)${R}\n"
  printf "  ${DIM}  Super+\`         — Quick Control overlay${R}\n"
  printf "  ${DIM}  Super+L         — Lock screen (hyprlock)${R}\n"
  printf "  ${DIM}  Super+Shift+E   — Logout menu (wlogout)${R}\n"
  printf "  ${DIM}  Super+0         — NYXUS Home (Obsidian Reactor)${R}\n"
  printf "  ${DIM}  Super+F3        — Mission Control${R}\n"
  printf "  ${DIM}  Super+Alt+W     — Reload wallpaper${R}\n"
  printf "\n"
  printf "  ${CYAN}${B}Live sync:${R}  ${DIM}nyxus-sync${R}  ${DIM}(pull + hot-reload)${R}\n"
  printf "  ${CYAN}${B}Auto-update:${R} enable with ${DIM}systemctl --user enable --now nyxus-update.timer${R}\n"
  printf "\n"
  printf "  ${DIM}S I L E N T · D A R K · P U R E L Y   F U N C T I O N A L${R}\n\n"
else
  printf "  ${RED}${B}✗ Installer exited with code ${INSTALL_EXIT}${R}\n"
  printf "  ${DIM}Check /tmp/nyxus-eww.log for EWW issues.${R}\n"
  printf "  ${DIM}Re-run: curl -fsSL ${RAW_BASE}/install.sh | bash${R}\n\n"
  exit "${INSTALL_EXIT}"
fi

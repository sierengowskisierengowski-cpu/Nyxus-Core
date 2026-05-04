#!/usr/bin/env bash
# ============================================================================
# NYXUS — Bulk Resync All Apps
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus-resync-all.sh | sudo bash
#
# What this does (in order):
#   1. Kills every running NYXUS process (so stale chrome.py is evicted)
#   2. Downloads + installs every app tarball from production:
#        nyxus-start (waybar patch + chrome.py + start menu + App Store)
#        nyxus-panel
#        nyxus-godsapp / home / weather / notepad / passwords
#        nyxus-intel / sage / studio / shield
#        nyxus-phantom (background daemon)
#   3. Reloads waybar so the new NYXUS modules show up
#   4. Verifies chrome.py SHA, waybar module count, /usr/local/bin launchers
#
# Safe to re-run any number of times. Each app's installer is idempotent.
# ============================================================================

set -uo pipefail

# ── pretty output (only if attached to a tty) ────────────────────────────────
if [[ -t 1 ]]; then
  R=$'\e[0m'; B=$'\e[1m'; DIM=$'\e[2m'
  CYAN=$'\e[38;5;51m'; GREEN=$'\e[38;5;120m'; GOLD=$'\e[38;5;220m'
  PINK=$'\e[38;5;213m'; PURPLE=$'\e[38;5;177m'; BLUE=$'\e[38;5;111m'
else
  R="";B="";DIM="";CYAN="";GREEN="";GOLD="";PINK="";PURPLE="";BLUE=""
fi
ok()    { printf "  ${GREEN}✓${R}  %s\n" "$*"; }
warn()  { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail()  { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }
step()  { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
hr()    { printf "${DIM}──────────────────────────────────────────────────────────────${R}\n"; }

# ── self-elevate ──────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "[NYXUS Resync] elevating with sudo …"
    exec sudo -E bash "$0" "$@"
  fi
  fail "must be run as root (sudo not available)"
  exit 1
fi

# ── resolve real user (script runs under sudo) ───────────────────────────────
REAL_USER="${SUDO_USER:-${USER:-nyx}}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
[[ -z "$REAL_HOME" || ! -d "$REAL_HOME" ]] && REAL_HOME="/home/$REAL_USER"

PROD="https://nyxus-core.replit.app/api/download/nyxus"
TMP="/tmp/nyxus-resync-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

# Apps install order matters: start FIRST (lays down chrome.py at ~/.nyxus/),
# then panel, then GUI apps, then phantom (background daemon).
APPS=(
  "nyxus-start"
  "nyxus-panel"
  "nyxus-godsapp"
  "nyxus-home"
  "nyxus-weather"
  "nyxus-notepad"
  "nyxus-passwords"
  "nyxus-intel"
  "nyxus-sage"
  "nyxus-studio"
  "nyxus-shield"
  "nyxus-phantom"
)

# ── header ────────────────────────────────────────────────────────────────────
echo
hr
printf "  ${B}${CYAN}NYXUS · Bulk Resync All Apps${R}\n"
printf "  ${DIM}target user:${R} %s    ${DIM}home:${R} %s\n" "$REAL_USER" "$REAL_HOME"
printf "  ${DIM}source:${R} %s\n" "$PROD"
hr

# ── 1/4 KILL stale processes ─────────────────────────────────────────────────
step "1/4 · KILL all running NYXUS processes (evict stale chrome.py from memory)"
killed=0
for pat in "$REAL_HOME/\.nyxus/" "$REAL_HOME/\.local/share/nyxus-" "/opt/nyxus-"; do
  if pkill -f "$pat" 2>/dev/null; then
    killed=$((killed + 1))
  fi
done
ok "killed stale NYXUS app processes"

# ── 2/4 INSTALL every app from prod ──────────────────────────────────────────
step "2/4 · DOWNLOAD + INSTALL every app from production"
declare -A RESULT
for app in "${APPS[@]}"; do
  echo
  printf "${BLUE}── %s ──${R}\n" "$app"

  # download
  if ! curl -fsSL --max-time 90 "$PROD/${app}.tgz" -o "$TMP/${app}.tgz"; then
    fail "download failed — skipping"
    RESULT[$app]="✗ download"
    continue
  fi
  ok "downloaded $(stat -c%s "$TMP/${app}.tgz" 2>/dev/null || echo "?") bytes"

  # extract
  rm -rf "$TMP/${app}-extract"
  mkdir -p "$TMP/${app}-extract"
  if ! tar -xzf "$TMP/${app}.tgz" -C "$TMP/${app}-extract" 2>/dev/null; then
    fail "extract failed — skipping"
    RESULT[$app]="✗ extract"
    continue
  fi
  ok "extracted"

  # locate install.sh (depth varies: start/install.sh, godsapp/install.sh,
  # nyxus-weather/install.sh, etc.). Pick the SHALLOWEST one named install.sh.
  installer=$(find "$TMP/${app}-extract" -maxdepth 4 -name install.sh -printf '%d %p\n' 2>/dev/null | sort -n | head -1 | awk '{print $2}')
  if [[ -z "$installer" || ! -f "$installer" ]]; then
    warn "no install.sh found — app may not be GUI-installable, skipping"
    RESULT[$app]="!  no installer"
    continue
  fi

  # run installer (each one self-elevates internally; we already are root)
  log="$TMP/${app}-install.log"
  if SUDO_USER="$REAL_USER" bash "$installer" >"$log" 2>&1; then
    ok "$app installed"
    RESULT[$app]="✓ installed"
  else
    rc=$?
    fail "$app install exited rc=$rc (see $log) — last 6 lines:"
    tail -6 "$log" | sed "s/^/      ${DIM}/" | sed "s/$/${R}/"
    RESULT[$app]="✗ rc=$rc"
  fi
done

# ── 3/5 INSTALL Hyprland window rules (float NYXUS apps + 900x650 default) ─
step "3/5 · INSTALL Hyprland window rules (float NYXUS apps at sensible size)"
HYPR_DIR="$REAL_HOME/.config/hypr"
HYPR_CONF_D="$HYPR_DIR/conf.d"
HYPR_RULES="$HYPR_CONF_D/nyxus-windowrules.conf"
HYPR_MAIN="$HYPR_DIR/hyprland.conf"
SOURCE_LINE='source = ~/.config/hypr/conf.d/nyxus-windowrules.conf'

mkdir -p "$HYPR_CONF_D"
chown -R "$REAL_USER:$REAL_USER" "$HYPR_DIR"
if curl -fsSL --max-time 30 "$PROD/nyxus-hyprland-rules.conf" -o "$HYPR_RULES"; then
  chown "$REAL_USER:$REAL_USER" "$HYPR_RULES"
  chmod 644 "$HYPR_RULES"
  ok "wrote $HYPR_RULES"
else
  fail "could not download nyxus-hyprland-rules.conf — apps may still tile-stretch"
fi

# Ensure hyprland.conf sources the rules file (idempotent — only appends if missing)
if [[ -f "$HYPR_MAIN" ]]; then
  if grep -qF "nyxus-windowrules.conf" "$HYPR_MAIN"; then
    ok "hyprland.conf already sources nyxus-windowrules.conf"
  else
    {
      echo
      echo "# NYXUS — float-and-size rules for nyxus-* apps (added by nyxus-resync-all.sh)"
      echo "$SOURCE_LINE"
    } >> "$HYPR_MAIN"
    chown "$REAL_USER:$REAL_USER" "$HYPR_MAIN"
    ok "appended source line to $HYPR_MAIN"
  fi
else
  warn "$HYPR_MAIN not found — drop this line into your hyprland.conf manually:"
  printf "      ${DIM}%s${R}\n" "$SOURCE_LINE"
fi

# Live-reload Hyprland so the rules apply RIGHT NOW (no logout needed)
if command -v hyprctl >/dev/null 2>&1 && pgrep -x Hyprland >/dev/null 2>&1; then
  if sudo -u "$REAL_USER" hyprctl reload >/dev/null 2>&1; then
    ok "hyprctl reload — rules active immediately"
  else
    warn "hyprctl reload failed — log out + back in, or run 'hyprctl reload' manually"
  fi
fi

# ── 4/5 RELOAD waybar ────────────────────────────────────────────────────────
step "4/5 · RELOAD waybar (so the new NYXUS modules show up)"
# SIGUSR2 reloads config in place — preserves the running waybar process and
# its taskbar state, but picks up the freshly patched config.json.
if pgrep -x waybar >/dev/null 2>&1; then
  pkill -SIGUSR2 -x waybar 2>/dev/null && ok "sent SIGUSR2 to running waybar (config reloaded)"
else
  warn "waybar not running — Hyprland will respawn it on next session, or start it manually"
fi

# ── 5/5 VERIFY ──────────────────────────────────────────────────────────────
step "5/5 · VERIFICATION"

echo
echo "${B}Per-app install result:${R}"
for app in "${APPS[@]}"; do
  printf "  %-22s  %s\n" "$app" "${RESULT[$app]:-?}"
done

echo
echo "${B}System checks:${R}"

# chrome.py SHA on disk
chrome_path="$REAL_HOME/.nyxus/nyxus_chrome.py"
if [[ -f "$chrome_path" ]]; then
  sha=$(sha256sum "$chrome_path" | cut -c1-12)
  if [[ "$sha" == "6ef320c0d69e" ]]; then
    ok "chrome.py SHA = $sha (universal Caveat + hover-scramble + size policy)"
  else
    warn "chrome.py SHA = $sha (expected 6ef320c0d69e — start install may have failed)"
  fi
else
  fail "chrome.py NOT FOUND at $chrome_path — start install failed"
fi

# waybar config NYXUS module count
waybar_cfg="$REAL_HOME/.config/waybar/config"
if [[ -f "$waybar_cfg" ]]; then
  cnt=$(grep -cE 'custom/nyxus-(start|panel|notifications|settings)' "$waybar_cfg" 2>/dev/null || echo 0)
  if (( cnt >= 8 )); then
    ok "waybar has $cnt NYXUS module references (expected ≥8)"
  else
    warn "waybar has only $cnt NYXUS module references (expected 8) — patch may have missed"
  fi
else
  warn "waybar config not found at $waybar_cfg"
fi

# launchers in /usr/local/bin
echo
echo "${B}Launchers in /usr/local/bin:${R}"
for app in "${APPS[@]}"; do
  if [[ -x "/usr/local/bin/$app" ]]; then
    printf "  ${GREEN}✓${R} %s\n" "$app"
  else
    printf "  ${PINK}✗${R} %s ${DIM}(not installed)${R}\n" "$app"
  fi
done

echo
hr
printf "  ${B}${GREEN}DONE.${R} Open any NYXUS app from the Start menu or App Store —\n"
printf "  it will load the new chrome (graffiti background + frosted glass +\n"
printf "  Caveat title + neon palette) on first paint.\n"
hr
echo

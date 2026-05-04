#!/usr/bin/env bash
# ============================================================================
# NYXUS — Bulk Resync All Apps
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus-resync-all.sh | sudo bash
#
# What this does (in order):
#   1. Kills every running NYXUS process (so stale chrome.py is evicted)
#   2. Downloads + installs every app tarball from production
#   3. Installs Hyprland window rules (float NYXUS apps at 900x650, center)
#   4. Installs lock + screensaver stack:
#        - /etc/pam.d/hyprlock                           (login error fix)
#        - ~/.config/hypr/hyprlock.conf                  (NYXUS lock screen)
#        - ~/.config/hypr/hypridle.conf                  (idle pipeline)
#        - /usr/share/nyxus/scripts/nyxus_screensaver.py
#        - /usr/share/nyxus/scripts/nyxus_demon_wake.py
#        - /usr/share/nyxus/demon.png
#        - /usr/local/bin/nyxus-screensaver              (wrapper)
#        - /usr/local/bin/nyxus-demon-wake               (wrapper)
#        - restarts hypridle so the new pipeline is live
#   5. Reloads waybar so the new NYXUS modules show up
#   6. Verifies chrome.py SHA, waybar module count, /usr/local/bin launchers,
#      PAM file, screensaver wrappers, demon image
#
# Safe to re-run any number of times. Each step is idempotent.
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
NYXUS_RESYNC_VERSION="2026.05.04-r8"
echo
hr
printf "  ${B}${CYAN}NYXUS · Bulk Resync All Apps${R}    ${DIM}(script version:${R} ${B}%s${R}${DIM})${R}\n" "$NYXUS_RESYNC_VERSION"
printf "  ${DIM}target user:${R} %s    ${DIM}home:${R} %s\n" "$REAL_USER" "$REAL_HOME"
printf "  ${DIM}source:${R} %s\n" "$PROD"
hr

# ── 1/6 KILL stale processes ─────────────────────────────────────────────────
step "1/6 · KILL all running NYXUS processes (evict stale chrome.py from memory)"
killed=0
for pat in "$REAL_HOME/\.nyxus/" "$REAL_HOME/\.local/share/nyxus-" "/opt/nyxus-"; do
  if pkill -f "$pat" 2>/dev/null; then
    killed=$((killed + 1))
  fi
done
ok "killed stale NYXUS app processes"

# ── 2/6 INSTALL every app from prod ──────────────────────────────────────────
step "2/6 · DOWNLOAD + INSTALL every app from production"
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

  # locate install.sh (depth varies). Pick the SHALLOWEST one named install.sh.
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

# ── 3/6 INSTALL Hyprland window rules ────────────────────────────────────────
## ─────────────────────────────────────────────────────────────────────────────
## STEP 2.5 — DIRECT chrome.py refresh (r5)
## ─────────────────────────────────────────────────────────────────────────────
## The per-app installers above sometimes leave a stale nyxus_chrome.py at
## ~/.nyxus/ (because the start tarball doesn't always bundle the latest
## copy). Force-overwrite it directly from production so r5+ chrome changes
## actually land on the user's machine. Without this step every chrome.py
## update would silently no-op until the start.tgz happened to be repacked.
step "2.5/6 · DIRECT-DOWNLOAD nyxus_chrome.py (force-refresh from production)"
NYX_HOME_DIR="$REAL_HOME/.nyxus"
mkdir -p "$NYX_HOME_DIR"
chown "$REAL_USER:$REAL_USER" "$NYX_HOME_DIR"
chrome_dst="$NYX_HOME_DIR/nyxus_chrome.py"
if curl -fsSL --max-time 30 "$PROD/nyxus_chrome.py" -o "$chrome_dst.new"; then
  # Validate the file actually parses before swapping it in — protects users
  # from a half-downloaded file bricking every NYXUS app on next launch.
  if python3 -c "import ast,sys; ast.parse(open('$chrome_dst.new').read())" 2>/dev/null; then
    mv "$chrome_dst.new" "$chrome_dst"
    chown "$REAL_USER:$REAL_USER" "$chrome_dst"
    chmod 644 "$chrome_dst"
    chrome_ver=$(grep '^NYXUS_CHROME_VERSION' "$chrome_dst" | head -1 | cut -d'"' -f2)
    chrome_sha=$(sha256sum "$chrome_dst" | cut -c1-12)
    ok "wrote $chrome_dst (version=$chrome_ver, sha=$chrome_sha)"
  else
    rm -f "$chrome_dst.new"
    fail "downloaded chrome.py failed Python syntax check — kept previous copy"
  fi
else
  fail "could not download nyxus_chrome.py — apps will keep their old chrome"
fi

step "3/6 · INSTALL Hyprland window rules (float NYXUS apps + 900x650 default)"
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

# ── 4/6 INSTALL lock + screensaver stack ─────────────────────────────────────
step "4/6 · INSTALL lock + screensaver stack (PAM fix + hyprlock + hypridle + demon jumpscare)"

# 4a. PAM module for hyprlock — THIS IS THE LOGIN ERROR FIX.
# Without /etc/pam.d/hyprlock, hyprlock can't authenticate the password and
# every unlock attempt returns "Failed to authenticate" / silent rejection.
# `auth include system-auth` delegates to the user's existing PAM stack,
# which is the canonical Arch + Hyprland setup.
PAM_FILE="/etc/pam.d/hyprlock"
PAM_BODY=$'#%PAM-1.0\n# NYXUS — installed by nyxus-resync-all.sh so hyprlock can authenticate.\nauth        include    system-auth\naccount     include    system-auth\npassword    include    system-auth\nsession     include    system-auth\n'
if [[ -f "$PAM_FILE" ]] && grep -q "system-auth" "$PAM_FILE" 2>/dev/null; then
  ok "$PAM_FILE already configured (system-auth include present)"
else
  printf '%s' "$PAM_BODY" > "$PAM_FILE"
  chmod 644 "$PAM_FILE"
  chown root:root "$PAM_FILE"
  ok "wrote $PAM_FILE — hyprlock can now authenticate via system-auth"
fi

# 4b. Lock screen + idle config
for cf in hyprlock.conf hypridle.conf; do
  dst="$HYPR_DIR/$cf"
  if curl -fsSL --max-time 30 "$PROD/$cf" -o "$dst.new"; then
    mv "$dst.new" "$dst"
    chown "$REAL_USER:$REAL_USER" "$dst"
    chmod 644 "$dst"
    ok "wrote $dst"
  else
    fail "could not download $cf"
  fi
done

# 4c. Screensaver + demon-wake Python scripts
NYX_SHARE="/usr/share/nyxus"
NYX_SCRIPTS="$NYX_SHARE/scripts"
mkdir -p "$NYX_SCRIPTS"
for pyf in nyxus_screensaver.py nyxus_demon_wake.py; do
  dst="$NYX_SCRIPTS/$pyf"
  if curl -fsSL --max-time 30 "$PROD/$pyf" -o "$dst.new"; then
    mv "$dst.new" "$dst"
    chmod 755 "$dst"
    ok "wrote $dst"
  else
    fail "could not download $pyf"
  fi
done

# 4d. Demon image
DEMON_DST="$NYX_SHARE/demon.png"
if curl -fsSL --max-time 30 "$PROD/nyxus-demon.png" -o "$DEMON_DST.new"; then
  mv "$DEMON_DST.new" "$DEMON_DST"
  chmod 644 "$DEMON_DST"
  ok "wrote $DEMON_DST ($(stat -c%s "$DEMON_DST" 2>/dev/null || echo "?") bytes)"
else
  fail "could not download nyxus-demon.png — demon wake will show ☠ glyph fallback"
fi

# 4e. /usr/local/bin wrappers so hypridle on-timeout/on-resume can find them
for pair in "nyxus-screensaver:nyxus_screensaver.py" "nyxus-demon-wake:nyxus_demon_wake.py"; do
  bin_name="${pair%%:*}"
  py_name="${pair##*:}"
  dst="/usr/local/bin/$bin_name"
  cat > "$dst" <<EOF
#!/usr/bin/env bash
# NYXUS — $bin_name wrapper (installed by nyxus-resync-all.sh)
exec python3 "$NYX_SCRIPTS/$py_name" "\$@"
EOF
  chmod 755 "$dst"
  ok "wrote $dst"
done

# 4f. Restart hypridle so the new 6-stage idle pipeline is live RIGHT NOW.
# CRITICAL: hypridle needs the user's Wayland session env to talk to Hyprland —
# specifically XDG_RUNTIME_DIR (where the wayland socket and hyprland IPC live)
# and HYPRLAND_INSTANCE_SIGNATURE. Launching it from a sudo shell loses both,
# so we resolve them from the user's running Hyprland process and re-export
# them in the child shell. Falls back gracefully if Hyprland isn't running.
if command -v hypridle >/dev/null 2>&1; then
  pkill -x hypridle 2>/dev/null || true
  sleep 0.3
  REAL_UID="$(id -u "$REAL_USER" 2>/dev/null || echo "")"
  HYPR_PID="$(pgrep -u "$REAL_USER" -x Hyprland | head -1 || true)"
  if [[ -n "$HYPR_PID" && -n "$REAL_UID" ]]; then
    # Pull HYPRLAND_INSTANCE_SIGNATURE + WAYLAND_DISPLAY straight from the
    # running Hyprland process's environ — guaranteed to match the live session.
    HIS="$(tr '\0' '\n' < /proc/$HYPR_PID/environ 2>/dev/null | grep -E '^HYPRLAND_INSTANCE_SIGNATURE=' | cut -d= -f2- || true)"
    WLD="$(tr '\0' '\n' < /proc/$HYPR_PID/environ 2>/dev/null | grep -E '^WAYLAND_DISPLAY=' | cut -d= -f2- || true)"
    XRD="/run/user/$REAL_UID"
    [[ -z "$WLD" ]] && WLD="wayland-1"
    sudo -u "$REAL_USER" \
      env XDG_RUNTIME_DIR="$XRD" WAYLAND_DISPLAY="$WLD" HYPRLAND_INSTANCE_SIGNATURE="$HIS" \
      nohup hypridle >/dev/null 2>&1 &
    disown 2>/dev/null || true
    sleep 0.5
    if pgrep -u "$REAL_USER" -x hypridle >/dev/null 2>&1; then
      ok "restarted hypridle as $REAL_USER with full session env (new idle pipeline active)"
    else
      warn "hypridle process didn't appear after restart — try logging out and back in"
    fi
  else
    warn "Hyprland isn't running for $REAL_USER — hypridle will start at next login"
  fi
else
  warn "hypridle not installed — install it with:  sudo pacman -S hypridle"
fi

# 4g. Live-reload Hyprland so the window rules apply immediately
if command -v hyprctl >/dev/null 2>&1 && pgrep -x Hyprland >/dev/null 2>&1; then
  if sudo -u "$REAL_USER" hyprctl reload >/dev/null 2>&1; then
    ok "hyprctl reload — rules + screensaver hooks active immediately"
  else
    warn "hyprctl reload failed — log out + back in, or run 'hyprctl reload' manually"
  fi
fi

# ── 5/6 RELOAD waybar ────────────────────────────────────────────────────────
step "5/6 · RELOAD waybar (so the new NYXUS modules show up)"
# SIGUSR2 reloads config in place — preserves the running waybar process and
# its taskbar state, but picks up the freshly patched config.json.
if pgrep -x waybar >/dev/null 2>&1; then
  pkill -SIGUSR2 -x waybar 2>/dev/null && ok "sent SIGUSR2 to running waybar (config reloaded)"
else
  warn "waybar not running — Hyprland will respawn it on next session, or start it manually"
fi

# ── 6/6 VERIFY ──────────────────────────────────────────────────────────────
step "6/6 · VERIFICATION"

echo
echo "${B}Per-app install result:${R}"
for app in "${APPS[@]}"; do
  printf "  %-22s  %s\n" "$app" "${RESULT[$app]:-?}"
done

echo
echo "${B}System checks:${R}"

# chrome.py SHA + version on disk (r5 expected)
chrome_path="$REAL_HOME/.nyxus/nyxus_chrome.py"
if [[ -f "$chrome_path" ]]; then
  sha=$(sha256sum "$chrome_path" | cut -c1-12)
  ver=$(grep '^NYXUS_CHROME_VERSION' "$chrome_path" | head -1 | cut -d'"' -f2)
  if [[ "$sha" == "dd5f06042d75" ]]; then
    ok "chrome.py version=$ver  sha=$sha (transparent windows + universal hover-scramble)"
  elif [[ -n "$ver" && "$ver" == 2026.05.04-r* ]]; then
    ok "chrome.py version=$ver  sha=$sha (r4+ — visual changes will be live next app launch)"
  else
    warn "chrome.py sha=$sha version=${ver:-unknown} (expected dd5f06042d75 / r4+ — direct-download step may have failed)"
  fi
else
  fail "chrome.py NOT FOUND at $chrome_path — direct-download step failed"
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

# PAM file for hyprlock
if [[ -f "$PAM_FILE" ]] && grep -q "system-auth" "$PAM_FILE"; then
  ok "$PAM_FILE present (hyprlock auth fixed)"
else
  fail "$PAM_FILE missing or misconfigured — hyprlock unlock will fail"
fi

# Screensaver + demon-wake wrappers
for bin_name in nyxus-screensaver nyxus-demon-wake; do
  if [[ -x "/usr/local/bin/$bin_name" ]]; then
    ok "/usr/local/bin/$bin_name installed"
  else
    fail "/usr/local/bin/$bin_name missing"
  fi
done

# Demon image
if [[ -f "$DEMON_DST" ]]; then
  ok "$DEMON_DST present ($(stat -c%s "$DEMON_DST" 2>/dev/null || echo "?") bytes)"
else
  warn "$DEMON_DST missing — jumpscare will fall back to ☠ glyph"
fi

# Hypridle running
if pgrep -x hypridle >/dev/null 2>&1; then
  ok "hypridle running (idle pipeline active)"
else
  warn "hypridle not running — start it with:  hypridle &"
fi

# App launchers — check BOTH /usr/local/bin AND ~/.local/bin AND ~/.nyxus/.
# Different installers land in different places (some system-wide via
# /usr/local/bin, some user-local via ~/.local/bin, some via .desktop entry +
# install dir under ~/.nyxus/<app>/). We check all three so we don't false-
# negative on apps that installed perfectly but elsewhere.
echo
echo "${B}App launchers (checking /usr/local/bin, ~/.local/bin, ~/.nyxus/<app>/):${R}"
USER_LOCAL_BIN="$REAL_HOME/.local/bin"
NYXUS_INSTALL_ROOT="$REAL_HOME/.nyxus"
for app in "${APPS[@]}"; do
  found=""
  if [[ -x "/usr/local/bin/$app" ]]; then
    found="/usr/local/bin"
  elif [[ -x "$USER_LOCAL_BIN/$app" ]]; then
    found="~/.local/bin"
  elif [[ -d "$NYXUS_INSTALL_ROOT/$app" ]]; then
    found="~/.nyxus/$app/"
  elif [[ -f "/usr/share/applications/$app.desktop" ]] || [[ -f "$REAL_HOME/.local/share/applications/$app.desktop" ]]; then
    found=".desktop"
  fi
  if [[ -n "$found" ]]; then
    printf "  ${GREEN}✓${R} %-22s ${DIM}(%s)${R}\n" "$app" "$found"
  else
    printf "  ${PINK}✗${R} %-22s ${DIM}(not installed anywhere — check install log above)${R}\n" "$app"
  fi
done

echo
hr
printf "  ${B}${GREEN}DONE.${R} ${DIM}(resync script v%s)${R}\n" "$NYXUS_RESYNC_VERSION"
printf "  The NYXUS apps will load the new chrome on next launch.\n"
printf "  ${DIM}Idle pipeline:${R} 2min dim → 3min screensaver → 5min lock → 8min DPMS off → 15min suspend\n"
printf "  ${DIM}Test the jumpscare without waiting:${R}  ${B}nyxus-demon-wake${R}\n"
printf "  ${DIM}Test the lock screen:${R}                ${B}loginctl lock-session${R}\n"
hr
echo

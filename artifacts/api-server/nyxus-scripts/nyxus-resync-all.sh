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
NYXUS_RESYNC_VERSION="2026.05.09-r22"
echo
hr
printf "  ${B}${CYAN}NYXUS · Bulk Resync All Apps${R}    ${DIM}(script version:${R} ${B}%s${R}${DIM})${R}\n" "$NYXUS_RESYNC_VERSION"
printf "  ${DIM}target user:${R} %s    ${DIM}home:${R} %s\n" "$REAL_USER" "$REAL_HOME"
printf "  ${DIM}source:${R} %s\n" "$PROD"
hr

# ── 1/6 KILL stale processes ─────────────────────────────────────────────────
# Bulletproof PID-by-PID killer. For every process under $REAL_USER we read
# /proc/$pid/cmdline; if it references a NYXUS path AND is NOT a wallpaper
# daemon, we send SIGTERM. This avoids any pkill -f regex pitfalls where
# argv layout (wrapper scripts, env vars, hashbangs) defeats the pattern.
step "1/6 · KILL stale NYXUS apps  (wallpaper daemons explicitly protected)"
WALLPAPER_RE='swaybg|hyprpaper|mpvpaper|wpaperd|swww-daemon|swww'
NYXUS_RE="$REAL_HOME/\.nyxus/|$REAL_HOME/\.local/share/nyxus-|/opt/nyxus-|nyxus-godsapp|nyxus-shield|nyxus-sage|nyxus-studio|nyxus-home|nyxus-notepad|nyxus-weather|nyxus-passwords|nyxus-intel|nyxus-phantom|nyxus-panel|nyxus-start"
killed_pids=()
skipped_wp=()
for pid in $(pgrep -u "$REAL_USER" "" 2>/dev/null); do
  cmd="$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null)"
  [[ -z "$cmd" ]] && continue
  if echo "$cmd" | grep -qE "$WALLPAPER_RE"; then
    skipped_wp+=("$pid")
    continue
  fi
  if echo "$cmd" | grep -qE "$NYXUS_RE"; then
    kill -TERM "$pid" 2>/dev/null && killed_pids+=("$pid")
  fi
done
sleep 0.5
# Force-kill any survivors after grace period
for pid in "${killed_pids[@]}"; do
  kill -KILL "$pid" 2>/dev/null || true
done
ok "killed ${#killed_pids[@]} NYXUS app PIDs ; skipped ${#skipped_wp[@]} wallpaper daemons"

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

step "2.7/6 · INSTALL hypr-doctor diagnostic (writes report to ~/.cache/hypr-doctor/)"
DOCTOR_DST="/usr/local/bin/hypr-doctor"
if curl -fsSL --max-time 30 "$PROD/hypr-doctor.sh" -o "$DOCTOR_DST.new"; then
  if bash -n "$DOCTOR_DST.new" 2>/dev/null; then
    mv "$DOCTOR_DST.new" "$DOCTOR_DST"
    chmod 755 "$DOCTOR_DST"
    chown root:root "$DOCTOR_DST"
    ok "wrote $DOCTOR_DST — run as user with: hypr-doctor  (or hypr-doctor --full)"
  else
    rm -f "$DOCTOR_DST.new"
    fail "downloaded hypr-doctor.sh failed bash syntax check — kept previous copy"
  fi
else
  fail "could not download hypr-doctor.sh"
fi

step "3/6 · INSTALL Hyprland window rules (13-rule baseline) + compositor blur kernel"
HYPR_DIR="$REAL_HOME/.config/hypr"
HYPR_CONF_D="$HYPR_DIR/conf.d"
HYPR_RULES="$HYPR_CONF_D/nyxus-windowrules.conf"
HYPR_BLUR="$HYPR_CONF_D/nyxus-hyprland-blur.conf"
HYPR_OPACITY="$HYPR_CONF_D/nyxus-hyprland-opacity.conf"
HYPR_GENERAL="$HYPR_CONF_D/nyxus-hyprland-general.conf"
HYPR_FROST_OLD="$HYPR_CONF_D/nyxus-seattle-frost.conf"
HYPR_MAIN="$HYPR_DIR/hyprland.conf"
SOURCE_LINE='source = ~/.config/hypr/conf.d/nyxus-windowrules.conf'
BLUR_SOURCE_LINE='source = ~/.config/hypr/conf.d/nyxus-hyprland-blur.conf'
OPACITY_SOURCE_LINE='source = ~/.config/hypr/conf.d/nyxus-hyprland-opacity.conf'
GENERAL_SOURCE_LINE='source = ~/.config/hypr/conf.d/nyxus-hyprland-general.conf'

mkdir -p "$HYPR_CONF_D"
chown -R "$REAL_USER:$REAL_USER" "$HYPR_DIR"

# r15 cleanup — remove the Seattle Frost decoration conf that whitewashed
# the system (brightness=1.4 + opacity 0.85/0.70 made everything look milky)
# and stripped its source line from hyprland.conf so reload picks up clean.
if [[ -f "$HYPR_FROST_OLD" ]]; then
  rm -f "$HYPR_FROST_OLD"
  ok "removed stale $HYPR_FROST_OLD  (was whitewashing the screen)"
fi
if [[ -f "$HYPR_MAIN" ]] && grep -qF "nyxus-seattle-frost.conf" "$HYPR_MAIN"; then
  sed -i '/nyxus-seattle-frost.conf/d;/Seattle Frost decoration/d' "$HYPR_MAIN"
  ok "stripped Seattle Frost source line from hyprland.conf"
fi

# r17/r18 migration — Hyprland 0.49+ removed `windowrulev2` (and
# `layerrulev2`) in favor of unified `windowrule` / `layerrule`. Stale
# installs still have the old syntax — rewrite every line in-place
# RECURSIVELY across the ENTIRE ~/.config/hypr/ tree (main hyprland.conf,
# conf.d/, hyprland/, anywhere) so reload stops throwing 400+ deprecation
# errors. Idempotent: if a file is already unified, it's a no-op.
HYPR_RULES_OLD="$HYPR_CONF_D/nyxus-hyprland-rules.conf"
v2_total=0
v2_files=0
while IFS= read -r -d '' f; do
  [[ -f "$f" ]] || continue
  n=$(grep -cE '^[[:space:]]*(window|layer)rulev2[[:space:]]*=' "$f" 2>/dev/null)
  n=${n:-0}
  if (( n > 0 )); then
    sed -i -E 's/^([[:space:]]*)windowrulev2([[:space:]]*=)/\1windowrule\2/; s/^([[:space:]]*)layerrulev2([[:space:]]*=)/\1layerrule\2/' "$f"
    rel="${f#$HYPR_DIR/}"
    ok "migrated $n v2 rule(s) → unified syntax in $rel"
    v2_total=$((v2_total + n))
    v2_files=$((v2_files + 1))
  fi
done < <(find "$HYPR_DIR" -type f -name '*.conf' -print0 2>/dev/null)
if (( v2_total > 0 )); then
  ok "total v2 → unified rule rewrites: $v2_total across $v2_files file(s)  (was throwing $v2_total deprecation errors at hyprctl reload)"
else
  ok "no deprecated v2 rules found anywhere under $HYPR_DIR — already migrated"
fi

# r17 PASS-2 — opacity rules with two values (e.g. `opacity 0.92 0.78,
# class:...`) are rejected by Hyprland 0.49+ unified parser as "invalid
# field class:...: missing a value" because opacity values stack
# multiplicatively across rules, and the parser can't disambiguate the
# two-float form from a single-float-plus-extra-field. Fix: insert the
# `override` keyword after each float (per Hyprland wiki) which forces
# absolute values and unambiguous parsing. Idempotent: skips lines that
# already contain `override`.
opa_total=0
opa_files=0
while IFS= read -r -d '' f; do
  [[ -f "$f" ]] || continue
  # Lines we need to touch: windowrule = opacity FLOAT FLOAT[ FLOAT][, ...]
  # without `override` anywhere on the line.
  n=$(grep -cE '^[[:space:]]*windowrule[[:space:]]*=[[:space:]]*opacity[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+' "$f" 2>/dev/null)
  n=${n:-0}
  if (( n > 0 )) && grep -E '^[[:space:]]*windowrule[[:space:]]*=[[:space:]]*opacity[[:space:]]+[0-9.]+[[:space:]]+[0-9.]+' "$f" | grep -vqE 'override'; then
    perl -i -pe '
      if (/^\s*windowrule\s*=\s*opacity/ && !/override/) {
        s{^(\s*windowrule\s*=\s*opacity\s+)([0-9.]+)(\s+)([0-9.]+)(?:(\s+)([0-9.]+))?(\s*,)}{
          my $r = "$1$2 override $4 override";
          $r .= " $6 override" if defined $6;
          "$r$7"
        }e;
      }
    ' "$f"
    rel="${f#$HYPR_DIR/}"
    ok "added 'override' to $n opacity rule(s) in $rel"
    opa_total=$((opa_total + n))
    opa_files=$((opa_files + 1))
  fi
done < <(find "$HYPR_DIR" -type f -name '*.conf' -print0 2>/dev/null)
if (( opa_total > 0 )); then
  ok "total opacity 'override' fixups: $opa_total across $opa_files file(s)  (these were the 'invalid field class: missing a value' errors)"
else
  ok "no opacity rules need 'override' keyword — already correct"
fi

# The shipped rules file has been renamed from nyxus-hyprland-rules.conf
# to nyxus-windowrules.conf. If the old path still exists, replace it with
# the freshly-downloaded clean version below AND drop its source line.
if [[ -f "$HYPR_RULES_OLD" ]]; then
  rm -f "$HYPR_RULES_OLD"
  ok "removed legacy $HYPR_RULES_OLD  (replaced by nyxus-windowrules.conf)"
fi
if [[ -f "$HYPR_MAIN" ]] && grep -qF "nyxus-hyprland-rules.conf" "$HYPR_MAIN"; then
  sed -i '/nyxus-hyprland-rules.conf/d' "$HYPR_MAIN"
  ok "stripped legacy nyxus-hyprland-rules.conf source line from hyprland.conf"
fi

# rev r22 — GENERIC strip of ALL legacy non-conf.d source lines from
# hyprland.conf. Old ISO builds shipped any of:
#     source = ~/.config/hypr/nyxus-hyprland-general.conf
#     source = ~/.config/hypr/nyxus-hyprland-blur.conf
#     source = ~/.config/hypr/nyxus-hyprland-opacity.conf
#     source = ~/.config/hypr/nyxus-hyprland-rules.conf
#     source = ~/.config/hypr/nyxus-hyprland-layerblur.conf
#     source = ~/.config/hypr/nyxus-hyprland-fog.conf
# all WITHOUT the conf.d/ subdir. Those files no longer exist at that path
# and Hyprland throws "globbing error: found no match" on every reload,
# blocking the entire chrome (waybar styling, opacity, blur) from loading.
# rev r22 fix: strip ANY `source = ~/.config/hypr/nyxus-hyprland-*.conf`
# without `conf.d/` regardless of suffix — catches future variants too.
if [[ -f "$HYPR_MAIN" ]]; then
  before=$(wc -l < "$HYPR_MAIN")
  # Match `source = ~/.config/hypr/nyxus-hyprland-<anything>.conf` BUT
  # only when the path does NOT contain `conf.d/`. Allows optional spaces
  # around `=` and trailing whitespace.
  sed -i -E '/^[[:space:]]*source[[:space:]]*=[[:space:]]*~\/\.config\/hypr\/nyxus-hyprland-[^\/]+\.conf[[:space:]]*$/d' "$HYPR_MAIN"
  after=$(wc -l < "$HYPR_MAIN")
  legacy_stripped=$((before - after))
  if (( legacy_stripped > 0 )); then
    ok "stripped $legacy_stripped legacy non-conf.d source line(s) from hyprland.conf — globbing errors fixed (rev r22)"
  fi
fi

# rev r19 — overwrite the user's hyprland.conf with the canonical version
# IF it still references the old non-conf.d paths (defensive belt-and-braces
# in case the per-line strip above missed something the user hand-edited).
# We do NOT touch hyprland.conf if it already looks clean — preserves any
# custom keybinds the user has added.
if [[ -f "$HYPR_MAIN" ]] && grep -qE "^\s*source\s*=\s*~/.config/hypr/nyxus-hyprland-" "$HYPR_MAIN"; then
  cp -f "$HYPR_MAIN" "${HYPR_MAIN}.bak.$(date +%s)" 2>/dev/null || true
  if curl -fsSL --max-time 30 "$PROD/hyprland.conf" -o "$HYPR_MAIN.new" 2>/dev/null; then
    mv -f "$HYPR_MAIN.new" "$HYPR_MAIN"
    chown "$REAL_USER:$REAL_USER" "$HYPR_MAIN"
    chmod 644 "$HYPR_MAIN"
    ok "rewrote $HYPR_MAIN from canonical (legacy backup at .bak.*)"
  fi
fi

if curl -fsSL --max-time 30 "$PROD/nyxus-hyprland-rules.conf" -o "$HYPR_RULES"; then
  chown "$REAL_USER:$REAL_USER" "$HYPR_RULES"
  chmod 644 "$HYPR_RULES"
  ok "wrote $HYPR_RULES  ($(grep -c '^windowrule' "$HYPR_RULES") rules — proven baseline)"
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

# ── Frosted-white FEATURE 1: compositor blur kernel (no opacity, no brightness)
# This file ONLY enables Hyprland's blur kernel. You will NOT see visual frost
# yet — that arrives with feature 2 (per-app opacity rules) and feature 3
# (chrome.py rgba backgrounds). Shipping it standalone first proves Hyprland
# parses a decoration{} block without the brightness=1.4 whitewash bug.
if curl -fsSL --max-time 30 "$PROD/nyxus-hyprland-blur.conf" -o "$HYPR_BLUR"; then
  chown "$REAL_USER:$REAL_USER" "$HYPR_BLUR"
  chmod 644 "$HYPR_BLUR"
  ok "wrote $HYPR_BLUR  (compositor blur kernel — no opacity yet)"
else
  warn "could not download nyxus-hyprland-blur.conf — frosted-white feature 1 skipped"
fi

if [[ -f "$HYPR_MAIN" ]] && [[ -f "$HYPR_BLUR" ]]; then
  if grep -qF "nyxus-hyprland-blur.conf" "$HYPR_MAIN"; then
    ok "hyprland.conf already sources nyxus-hyprland-blur.conf"
  else
    {
      echo
      echo "# NYXUS — compositor blur kernel (added by nyxus-resync-all.sh, feature 1)"
      echo "$BLUR_SOURCE_LINE"
    } >> "$HYPR_MAIN"
    chown "$REAL_USER:$REAL_USER" "$HYPR_MAIN"
    ok "appended blur source line to $HYPR_MAIN"
  fi
fi

# ── Frosted-white FEATURE 2: per-window opacity (notepad canary first)
# Gentle 0.92/0.88 alpha so blur becomes visible behind the window without
# the whitewash that 0.85/0.70 + brightness=1.4 caused before. Only one
# app's class is in the rule for now — if notepad looks right, the same
# rule's regex gets expanded to all 11 NYXUS apps.
if curl -fsSL --max-time 30 "$PROD/nyxus-hyprland-opacity.conf" -o "$HYPR_OPACITY"; then
  chown "$REAL_USER:$REAL_USER" "$HYPR_OPACITY"
  chmod 644 "$HYPR_OPACITY"
  ok "wrote $HYPR_OPACITY  (canary: nyxus-notepad only)"
else
  warn "could not download nyxus-hyprland-opacity.conf — frosted-white feature 2 skipped"
fi

if [[ -f "$HYPR_MAIN" ]] && [[ -f "$HYPR_OPACITY" ]]; then
  if grep -qF "nyxus-hyprland-opacity.conf" "$HYPR_MAIN"; then
    ok "hyprland.conf already sources nyxus-hyprland-opacity.conf"
  else
    {
      echo
      echo "# NYXUS — per-window opacity (added by nyxus-resync-all.sh, feature 2)"
      echo "$OPACITY_SOURCE_LINE"
    } >> "$HYPR_MAIN"
    chown "$REAL_USER:$REAL_USER" "$HYPR_MAIN"
    ok "appended opacity source line to $HYPR_MAIN"
  fi
fi

# ── DARK MIRROR FEATURE 4: window edges (white→off-white→black border)
# col.active_border gradient + 2px border + 15px rounding + ink shadow.
# Combined with blur + opacity, every window reads as a starlight-rimmed
# dark glass tile floating above the wallpaper. Without this file the
# Hyprland default hot-pink border bleeds through and breaks the look.
if curl -fsSL --max-time 30 "$PROD/nyxus-hyprland-general.conf" -o "$HYPR_GENERAL"; then
  chown "$REAL_USER:$REAL_USER" "$HYPR_GENERAL"
  chmod 644 "$HYPR_GENERAL"
  ok "wrote $HYPR_GENERAL  (DARK MIRROR window edges)"
else
  warn "could not download nyxus-hyprland-general.conf — DARK MIRROR border skipped"
fi

if [[ -f "$HYPR_MAIN" ]] && [[ -f "$HYPR_GENERAL" ]]; then
  if grep -qF "nyxus-hyprland-general.conf" "$HYPR_MAIN"; then
    ok "hyprland.conf already sources nyxus-hyprland-general.conf"
  else
    {
      echo
      echo "# NYXUS — DARK MIRROR window edges (added by nyxus-resync-all.sh)"
      echo "$GENERAL_SOURCE_LINE"
    } >> "$HYPR_MAIN"
    chown "$REAL_USER:$REAL_USER" "$HYPR_MAIN"
    ok "appended general source line to $HYPR_MAIN"
  fi
fi

# Try to reload Hyprland so blur+opacity take effect immediately. Best-effort
# — if it fails (xauth/permissions), the user can run `hyprctl reload`
# manually after the script finishes. The runtime check in step 7/7 will
# show whether the reload actually picked up.
if command -v hyprctl >/dev/null 2>&1; then
  if sudo -u "$REAL_USER" \
       XDG_RUNTIME_DIR="/run/user/$(id -u "$REAL_USER")" \
       HYPRLAND_INSTANCE_SIGNATURE="$(ls -1t /run/user/$(id -u "$REAL_USER")/hypr 2>/dev/null | head -1)" \
       hyprctl reload >/dev/null 2>&1; then
    ok "hyprctl reload succeeded — blur + opacity should now be live"
  else
    warn "hyprctl reload didn't take — run it manually:  hyprctl reload"
  fi
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

# 4b.5  hyprlock background image — same obsidian-wave starfield as SDDM
# login (nyxus-login-stars.png). hyprlock.conf reads from
# ~/.config/nyxus/wallpaper.png (per nyxus-hyprlock.conf line 22).
NYX_CFG_DIR="$REAL_HOME/.config/nyxus"
mkdir -p "$NYX_CFG_DIR"
chown "$REAL_USER:$REAL_USER" "$NYX_CFG_DIR"
LOCK_BG_DST="$NYX_CFG_DIR/wallpaper.png"
if curl -fsSL --max-time 30 "$PROD/nyxus-login-stars.png" -o "$LOCK_BG_DST.new"; then
  if [[ -s "$LOCK_BG_DST.new" ]]; then
    mv "$LOCK_BG_DST.new" "$LOCK_BG_DST"
    chown "$REAL_USER:$REAL_USER" "$LOCK_BG_DST"
    chmod 644 "$LOCK_BG_DST"
    ok "wrote $LOCK_BG_DST — hyprlock now uses the obsidian-starfield bg"
  else
    rm -f "$LOCK_BG_DST.new"
    fail "downloaded hyprlock bg was empty — kept previous copy"
  fi
else
  fail "could not download hyprlock background image"
fi

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

# ── 4.5/6  REFRESH palette + waybar CSS/JSON  (r22 fix) ─────────────────────
# Without this step every change to nyxus-palette.css, waybar-style.css, or
# waybar-config.json is INVISIBLE on user machines: the original install
# pulled them once and nothing ever overwrote them. r22 adds explicit pulls
# so palette/waybar edits actually land.
step "4.5/6 · REFRESH palette + waybar CSS/JSON  (r22: was previously missed)"

NYX_HOME_DIR="${NYX_HOME_DIR:-$REAL_HOME/.nyxus}"
WAYBAR_DIR="$REAL_HOME/.config/waybar"
mkdir -p "$NYX_HOME_DIR" "$WAYBAR_DIR"
chown "$REAL_USER:$REAL_USER" "$NYX_HOME_DIR" "$WAYBAR_DIR"

# 4.5a  nyxus-palette.css — the single source of truth every CSS @imports
PAL_DST="$NYX_HOME_DIR/nyxus-palette.css"
if curl -fsSL --max-time 30 "$PROD/nyxus-palette.css" -o "$PAL_DST.new"; then
  if grep -q "nyx_black_smoke\|nyx_glass_dark" "$PAL_DST.new"; then
    mv "$PAL_DST.new" "$PAL_DST"
    chown "$REAL_USER:$REAL_USER" "$PAL_DST"
    chmod 644 "$PAL_DST"
    pal_sha=$(sha256sum "$PAL_DST" | cut -c1-12)
    ok "wrote $PAL_DST (sha=$pal_sha)"
    # Mirror to every consumer dir so @import 'nyxus-palette.css' resolves
    mirrored=0
    for dest in "$WAYBAR_DIR" "$REAL_HOME/.config/wlogout" "$REAL_HOME/.config/dunst" \
                "$REAL_HOME/.config/rofi" "$REAL_HOME/.config/hypr" "$NYX_HOME_DIR"; do
      if [[ -d "$dest" ]]; then
        cp -f "$PAL_DST" "$dest/nyxus-palette.css"
        chown "$REAL_USER:$REAL_USER" "$dest/nyxus-palette.css"
        mirrored=$((mirrored+1))
      fi
    done
    ok "mirrored palette to $mirrored consumer dir(s)"
  else
    rm -f "$PAL_DST.new"
    fail "downloaded nyxus-palette.css missing palette tokens — kept previous copy"
  fi
else
  fail "could not download nyxus-palette.css — palette edits will not be visible"
fi

# 4.5b  Pull background images so waybar style.css path substitutions resolve
NYX_BG_DIR="$NYX_HOME_DIR/backgrounds"
mkdir -p "$NYX_BG_DIR"; chown "$REAL_USER:$REAL_USER" "$NYX_BG_DIR"
for bg in nyxus-taskbar-bg.png nyxus-rightbar-bg.png nyxus-frost-sierengowski.png nyxus-starlight.png nyxus-waybar-stars.png nyxus-starfield-wall.png nyxus-void-wallpaper.mp4; do
  bgdst="$NYX_BG_DIR/$bg"
  if [[ ! -f "$bgdst" ]] || [[ "${1:-}" == "--force-bg" ]]; then
    if curl -fsSL --max-time 60 "$PROD/$bg" -o "$bgdst.new"; then
      mv "$bgdst.new" "$bgdst"
      chown "$REAL_USER:$REAL_USER" "$bgdst"
      chmod 644 "$bgdst"
    fi
  fi
done

# 4.5c  waybar-config.json
WB_CFG="$WAYBAR_DIR/config"
if curl -fsSL --max-time 30 "$PROD/waybar-config.json" -o "$WB_CFG.new"; then
  if python3 -c "import json,sys; json.load(open('$WB_CFG.new'))" 2>/dev/null \
     || python3 -c "import json,sys; json.loads(open('$WB_CFG.new').read().split('//')[0] if False else open('$WB_CFG.new').read())" 2>/dev/null; then
    mv "$WB_CFG.new" "$WB_CFG"
    chown "$REAL_USER:$REAL_USER" "$WB_CFG"
    chmod 644 "$WB_CFG"
    ok "wrote $WB_CFG"
  else
    # waybar config supports JSONC (//-comments). Just trust it if non-empty.
    if [[ -s "$WB_CFG.new" ]]; then
      mv "$WB_CFG.new" "$WB_CFG"
      chown "$REAL_USER:$REAL_USER" "$WB_CFG"
      chmod 644 "$WB_CFG"
      ok "wrote $WB_CFG (JSONC, accepted as-is)"
    else
      rm -f "$WB_CFG.new"
      fail "downloaded waybar-config.json was empty — kept previous copy"
    fi
  fi
else
  fail "could not download waybar-config.json"
fi

# 4.5d  waybar-style.css  + run the same path substitutions install.sh does
WB_CSS="$WAYBAR_DIR/style.css"
WALL_PATH="$NYX_BG_DIR/nyxus-frost-sierengowski.png"
TASKBAR_BG_PATH="$NYX_BG_DIR/nyxus-taskbar-bg.png"
RIGHTBAR_BG_PATH="$NYX_BG_DIR/nyxus-rightbar-bg.png"
STARLIGHT_BG_PATH="$NYX_BG_DIR/nyxus-starlight.png"
WAYBAR_STARS_PATH="$NYX_BG_DIR/nyxus-waybar-stars.png"
if curl -fsSL --max-time 30 "$PROD/waybar-style.css" -o "$WB_CSS.new"; then
  if [[ -s "$WB_CSS.new" ]]; then
    sed -i "s|NYXUS_WALL_PATH|${WALL_PATH}|g"                  "$WB_CSS.new"
    sed -i "s|NYXUS_TASKBAR_BG|file://${TASKBAR_BG_PATH}|g"    "$WB_CSS.new"
    sed -i "s|NYXUS_RIGHTBAR_BG|file://${RIGHTBAR_BG_PATH}|g"  "$WB_CSS.new"
    sed -i "s|NYXUS_STARLIGHT_BG|file://${STARLIGHT_BG_PATH}|g" "$WB_CSS.new"
    sed -i "s|NYXUS_WAYBAR_STARS|file://${WAYBAR_STARS_PATH}|g" "$WB_CSS.new"
    sed -i "s|file:///home/nyx/|file://$REAL_HOME/|g"          "$WB_CSS.new"
    mv "$WB_CSS.new" "$WB_CSS"
    chown "$REAL_USER:$REAL_USER" "$WB_CSS"
    chmod 644 "$WB_CSS"
    css_sha=$(sha256sum "$WB_CSS" | cut -c1-12)
    smoke_hits=$(grep -c "nyx_black_smoke\|nyx_glass_dark" "$WB_CSS" || echo 0)
    ok "wrote $WB_CSS (sha=$css_sha, palette tokens=$smoke_hits)"
  else
    rm -f "$WB_CSS.new"
    fail "downloaded waybar-style.css was empty — kept previous copy"
  fi
else
  fail "could not download waybar-style.css"
fi

# 4.5e  waybar-ticker.sh — REAL live-stats marquee (rev r22 fix: was
# previously NEVER refreshed by resync — old ticker.sh stayed on disk
# even after downloads of style.css/config.json, so users saw stale data
# and never got the new red `.error` class on probe failures).
WB_TICKER="$NYX_HOME_DIR/waybar-ticker.sh"
if curl -fsSL --max-time 30 "$PROD/waybar-ticker.sh" -o "$WB_TICKER.new"; then
  if [[ -s "$WB_TICKER.new" ]]; then
    mv -f "$WB_TICKER.new" "$WB_TICKER"
    chown "$REAL_USER:$REAL_USER" "$WB_TICKER"
    chmod 755 "$WB_TICKER"
    tk_sha=$(sha256sum "$WB_TICKER" | cut -c1-12)
    tk_rev=$(grep -m1 -E '^# NYXUS Waybar Marquee Ticker' "$WB_TICKER" | sed 's/^# //')
    ok "wrote $WB_TICKER (sha=$tk_sha) — $tk_rev"
  else
    rm -f "$WB_TICKER.new"
    fail "downloaded waybar-ticker.sh was empty — kept previous copy"
  fi
else
  fail "could not download waybar-ticker.sh — top-bar ticker will stay stale"
fi

# ── 5/6 RELOAD waybar ────────────────────────────────────────────────────────
step "5/6 · RELOAD waybar (so the new NYXUS modules show up)"
# rev r22 — FULL kill+respawn instead of SIGUSR2. SIGUSR2 reloads the CSS
# but does NOT reliably re-evaluate structural changes (modules added,
# removed, moved between bars). After the rev r19→r21 reorganisation
# moving status pebbles top→right, SIGUSR2 left orphan modules from the
# old layout. Full restart guarantees the new config is live.
if pgrep -x waybar >/dev/null 2>&1; then
  pkill -x waybar 2>/dev/null
  # wait up to 2s for waybar to fully exit
  for _ in 1 2 3 4 5 6 7 8; do
    pgrep -x waybar >/dev/null 2>&1 || break
    sleep 0.25
  done
  ok "waybar killed — Hyprland exec-once will respawn it with new config"
fi
# Defensive respawn — if Hyprland's exec-once doesn't fire (script run
# outside a fresh session), launch waybar directly as the real user.
if ! pgrep -x waybar >/dev/null 2>&1; then
  if [[ -n "${REAL_USER:-}" ]] && command -v sudo >/dev/null 2>&1; then
    sudo -u "$REAL_USER" \
      env XDG_RUNTIME_DIR="/run/user/$(id -u "$REAL_USER")" \
          WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}" \
      nohup waybar \
        --config "$REAL_HOME/.config/waybar/config" \
        --style  "$REAL_HOME/.config/waybar/style.css" \
        >/dev/null 2>&1 &
    sleep 0.5
    if pgrep -x waybar >/dev/null 2>&1; then
      ok "waybar respawned manually with new config"
    else
      warn "waybar failed to respawn — run \`waybar --config ~/.config/waybar/config --style ~/.config/waybar/style.css &\` manually"
    fi
  fi
fi

# ── 6/6 VERIFY ──────────────────────────────────────────────────────────────
step "6/6 · VERIFICATION"
# Print the chrome.py version that actually landed on disk — so you can
# eyeball it and confirm the new chrome is live, not the cached one.
CHROME_ON_DISK=""
for cand in "$REAL_HOME/.nyxus/nyxus_chrome.py" "/opt/nyxus/nyxus_chrome.py" "$REAL_HOME/.local/share/nyxus/nyxus_chrome.py"; do
  if [[ -f "$cand" ]]; then
    ver=$(grep -E '^NYXUS_CHROME_VERSION' "$cand" | head -1)
    printf "  ${B}chrome on disk:${R}  %-60s  %s\n" "$cand" "$ver"
    CHROME_ON_DISK="$cand"
    break
  fi
done
if [[ -z "$CHROME_ON_DISK" ]]; then
  warn "could not find nyxus_chrome.py on disk in any standard location"
fi
# rev r29 — STARFIELD STILL WALLPAPER. Replaces the rev r25 mpvpaper void
# animation with a static cratered-starfield PNG via swaybg. Image is a
# 2048x576 letterbox starfield — `-m fill` crops to screen, the uniform
# starfield hides the crop. Letterbox color is pure black so any seam
# blends invisibly into the black starfield background.
STAR_PNG="$NYX_BG_DIR/nyxus-starfield-wall.png"
if [[ -s "$STAR_PNG" ]] && command -v swaybg >/dev/null 2>&1; then
  pkill -x swaybg    2>/dev/null || true
  pkill -x hyprpaper 2>/dev/null || true
  pkill -x mpvpaper  2>/dev/null || true
  pkill -x wpaperd   2>/dev/null || true
  sleep 0.4
  if [[ -n "${REAL_USER:-}" ]] && command -v sudo >/dev/null 2>&1; then
    sudo -u "$REAL_USER" \
      env XDG_RUNTIME_DIR="/run/user/$(id -u "$REAL_USER")" \
          WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}" \
          HOME="$REAL_HOME" \
      nohup swaybg -i "$STAR_PNG" -m fill -c "#000000" \
        >/tmp/nyxus-swaybg.log 2>&1 &
    sleep 0.5
    if pgrep -x swaybg >/dev/null 2>&1; then
      ok "wallpaper restarted as swaybg · cratered-starfield still"
    else
      warn "swaybg failed to spawn — see /tmp/nyxus-swaybg.log"
    fi
  fi
elif ! command -v swaybg >/dev/null 2>&1; then
  warn "swaybg not installed — run:  sudo pacman -S swaybg  (then re-run this script)"
elif [[ ! -s "$STAR_PNG" ]]; then
  warn "wallpaper image missing at $STAR_PNG — re-run with --force-bg"
fi

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
step "7/7 · DIAGNOSE Hyprland (auto-runs hypr-doctor — instant error surface)"
# Run hypr-doctor as the REAL user (not root) so it sees their config + logs.
# Pass through WAYLAND_DISPLAY / XDG_RUNTIME_DIR so [8] runtime checks work
# when the user is currently in a Hyprland session (otherwise hyprctl can't
# reach the running compositor).
DOCTOR_BIN="/usr/local/bin/hypr-doctor"
if [[ ! -x "$DOCTOR_BIN" ]]; then
  warn "hypr-doctor not installed — skipping auto-diagnosis"
else
  REAL_UID=$(id -u "$REAL_USER")
  DOCTOR_OUT=$(sudo -u "$REAL_USER" \
    HOME="$REAL_HOME" \
    XDG_RUNTIME_DIR="/run/user/$REAL_UID" \
    WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-1}" \
    "$DOCTOR_BIN" 2>&1 || true)

  # Save full report path for the user
  REPORT_FILE=$(echo "$DOCTOR_OUT" | grep -m1 "^Log file:" | awk '{print $3}')
  [[ -n "$REPORT_FILE" ]] && ok "full report: $REPORT_FILE"

  # ── Surface the DEFINITIVE error list from `hyprctl configerrors`
  # (section [8a] of the doctor). This is what powers the red waybar
  # overlay — if it's empty, the user is clean.
  echo
  printf "  ${B}Hyprland config errors (section [8a] — powers the waybar overlay):${R}\n"
  CFGBLOCK=$(echo "$DOCTOR_OUT" | awk '
    /^── 8a · hyprctl configerrors/ {capture=1; next}
    /^── 8b ·|^\[8b\]/ {capture=0}
    capture && NF { print }
  ')
  if [[ -z "$CFGBLOCK" ]] || echo "$CFGBLOCK" | grep -q "OK: hyprctl configerrors reports no errors"; then
    ok "hyprctl configerrors: 0 errors — waybar overlay should be clean"
  else
    echo "$CFGBLOCK" | sed 's/^/      /'
  fi

  # Show source-chain resolution — missing source = is #1 cause of cascades
  echo
  printf "  ${B}Hyprland source chain (section [5]):${R}\n"
  echo "$DOCTOR_OUT" | awk '
    /^\[5\] Source chain check/ {capture=1; next}
    /^\[6\] / {capture=0}
    capture && NF { print "      " $0 }
  '

  # Show whatever Hyprland's own log (~/.cache/hyprland/hyprland.log) says
  echo
  printf "  ${B}Hyprland log tail (section [9a] — parse errors land here):${R}\n"
  echo "$DOCTOR_OUT" | awk '
    /^── 9a ·/ {capture=1; next}
    /^── 9b ·|^\[9b\]|^── End/ {capture=0}
    capture && NF { print "      " $0 }
  ' | head -30
fi

echo
hr
printf "  ${B}${GREEN}DONE.${R} ${DIM}(resync script v%s)${R}\n" "$NYXUS_RESYNC_VERSION"
printf "  The NYXUS apps will load the new chrome on next launch.\n"
printf "  ${DIM}Re-run hypr-doctor any time:${R}  hypr-doctor  ${DIM}or${R}  hypr-doctor --full\n"
printf "  ${DIM}Idle pipeline:${R} 2min dim → 3min screensaver → 5min lock → 8min DPMS off → 15min suspend\n"
printf "  ${DIM}Test the jumpscare without waiting:${R}  ${B}nyxus-demon-wake${R}\n"
printf "  ${DIM}Test the lock screen:${R}                ${B}loginctl lock-session${R}\n"
hr
echo

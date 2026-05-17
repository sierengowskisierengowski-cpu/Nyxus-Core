#!/usr/bin/env bash
set -euo pipefail

# ============================================================
#  NYXUS · hypr-doctor.sh
#  Hyprland config + environment diagnostic (no root required)
#
#  Usage:
#    hypr-doctor              # standard report
#    hypr-doctor --full       # adds verbose hyprctl -j dumps
#
#  Output:
#    Prints a summary to stdout AND writes a full report to
#    ~/.cache/hypr-doctor/hypr-doctor-YYYYmmdd-HHMMSS.log
#
#  Install:
#    curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/hypr-doctor.sh \
#      | sudo tee /usr/local/bin/hypr-doctor >/dev/null
#    sudo chmod +x /usr/local/bin/hypr-doctor
#  (or installed automatically by nyxus-resync-all.sh r15+)
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Version log:
#    r1 — initial release
#    r2 — fix tilde expansion in source-chain check (was false-flagging
#         every ~/-rooted source path as missing)
#    r3 — add `hyprctl configerrors` (THE definitive list that powers
#         the red waybar overlay) + show actual rule file contents +
#         tail Hyprland's own log file (~/.cache/hyprland/hyprland.log)
# ============================================================

HYPR_DOCTOR_VERSION="2026.05.05-r3"
FULL=0
if [[ "${1:-}" == "--full" ]]; then
  FULL=1
fi

ts() { date +"%Y-%m-%d %H:%M:%S"; }
hr() { printf '%*s\n' "${COLUMNS:-80}" '' | tr ' ' -; }

OUTDIR="${XDG_CACHE_HOME:-$HOME/.cache}/hypr-doctor"
mkdir -p "$OUTDIR"
LOG="$OUTDIR/hypr-doctor-$(date +%Y%m%d-%H%M%S).log"

# Tee all output to log
exec > >(tee -a "$LOG") 2>&1

echo "Hypr Doctor report @ $(ts)  (version $HYPR_DOCTOR_VERSION)"
echo "Log file: $LOG"
hr

# --- Basic system/session info ---
echo "[1] Session / system"
echo "User: $(id -un) (uid=$(id -u))"
echo "Host: $(hostnamectl --static 2>/dev/null || hostname)"
echo "Kernel: $(uname -r)"
echo "Shell: ${SHELL:-unknown}"
echo "XDG_SESSION_TYPE: ${XDG_SESSION_TYPE:-}"
echo "XDG_CURRENT_DESKTOP: ${XDG_CURRENT_DESKTOP:-}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-}"
echo "DISPLAY: ${DISPLAY:-}"
echo "XDG_RUNTIME_DIR: ${XDG_RUNTIME_DIR:-}"
echo

# --- Binaries presence ---
echo "[2] Binary checks"
need_bins=(hyprctl Hyprland)
for b in "${need_bins[@]}"; do
  if command -v "$b" >/dev/null 2>&1; then
    echo "OK: $b -> $(command -v "$b")"
  else
    echo "MISSING: $b (not in PATH)"
  fi
done
echo

# --- Versions ---
echo "[3] Versions (best-effort)"
if command -v Hyprland >/dev/null 2>&1; then
  echo "Hyprland:"
  Hyprland --version 2>/dev/null || true
fi
if command -v hyprctl >/dev/null 2>&1; then
  echo "hyprctl:"
  hyprctl version 2>/dev/null || true
fi
echo

# --- Config discovery ---
echo "[4] Config locations"
HYPRDIR="${XDG_CONFIG_HOME:-$HOME/.config}/hypr"
MAINCFG="$HYPRDIR/hyprland.lua"
echo "HYPRDIR: $HYPRDIR"
echo "MAINCFG: $MAINCFG"
if [[ -f "$MAINCFG" ]]; then
  echo "OK: main config exists"
else
  echo "ERROR: main config missing: $MAINCFG"
fi
echo

# Collect config files (main + any required modules we can resolve)
declare -a FILES=()
if [[ -f "$MAINCFG" ]]; then
  FILES+=("$MAINCFG")
fi

# Helper: trim quotes/spaces
trim() {
  local s="$1"
  s="${s#\"}"; s="${s%\"}"
  s="${s#\'}"; s="${s%\'}"
  echo "$s"
}

echo "[5] Include chain check"
if [[ -f "$MAINCFG" ]]; then
  mapfile -t includes < <(grep -REn '^[[:space:]]*(source[[:space:]]*=|require[[:space:]]*\()' "$MAINCFG" 2>/dev/null || true)
  if [[ ${#includes[@]} -eq 0 ]]; then
    echo "No source/require include lines found in main config (that's fine if you keep it monolithic)."
  else
    echo "Found includes:"
    printf '%s\n' "${includes[@]}"
  fi

  echo
  echo "Resolved include targets:"
  while IFS= read -r line; do
    resolved=""
    if [[ "$line" == *"source"* ]]; then
      src="${line#*:source}"
      src="${src#*source}"
      src="${src#*=}"
      src="$(echo "$src" | sed 's/#.*$//' | xargs)"
      src="$(trim "$src")"
      [[ -z "$src" ]] && continue

      # Expand leading ~ to $HOME first (tilde expansion does NOT happen
      # inside double quotes via eval — that was the bug that falsely
      # reported every NYXUS source line as missing).
      src_expanded="${src/#\~/$HOME}"
      eval "resolved=\"$src_expanded\"" 2>/dev/null || resolved="$src_expanded"

      shopt -s nullglob
      matches=( $resolved )
      shopt -u nullglob
    else
      req="${line#*:}"
      req="${req#*require}"
      req="${req#*(}"
      req="${req%%)*}"
      req="$(trim "$(echo "$req" | sed 's/#.*$//' | xargs)")"
      [[ -z "$req" ]] && continue
      req_path="${req//./\/}.lua"
      resolved="${HYPRDIR}/${req_path}"
      matches=( "$resolved" )
      src="require(${req})"
    fi

    if [[ ${#matches[@]} -eq 0 ]]; then
      echo "ERROR: source target does not exist / glob matched nothing: $src  (resolved: $resolved)"
    else
      for m in "${matches[@]}"; do
        if [[ -f "$m" ]]; then
          echo "OK: $src -> $m"
          FILES+=("$m")
        else
          echo "ERROR: source target is not a file: $src -> $m"
        fi
      done
    fi
  done < <(printf '%s\n' "${includes[@]}")
else
  echo "Skipping source check (main config missing)."
fi
echo

# Deduplicate FILES
if [[ ${#FILES[@]} -gt 0 ]]; then
  mapfile -t FILES < <(printf '%s\n' "${FILES[@]}" | awk '!seen[$0]++')
fi

echo "[6] Config file list (${#FILES[@]} files)"
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No config files found to scan."
else
  printf '%s\n' "${FILES[@]}"
fi
echo

# --- Scan for common issues ---
echo "[7] Config scans (common pitfalls)"
scan_file() {
  local f="$1"

  if LC_ALL=C grep -n $'\r' "$f" >/dev/null 2>&1; then
    echo "WARN: CRLF line endings detected in $f (can cause weird parse issues). Convert with: sed -i 's/\r\$//' '$f'"
  fi

  if LC_ALL=C grep -nP $'\t' "$f" >/dev/null 2>&1; then
    echo "INFO: tabs found in $f (usually fine, but be careful around alignment)."
  fi

  if grep -En '^[[:space:]]*exec[[:space:]]*=' "$f" >/dev/null 2>&1; then
    echo "NOTE: 'exec =' found in $f. If these launch daemons, consider 'exec-once =' to avoid respawns on reload."
  fi

  if grep -En '^[[:space:]]*source[[:space:]]*=[[:space:]]*$' "$f" >/dev/null 2>&1; then
    echo "ERROR: empty 'source =' line in $f"
  fi
}

if [[ ${#FILES[@]} -gt 0 ]]; then
  for f in "${FILES[@]}"; do
    echo "Scanning: $f"
    scan_file "$f"
  done
else
  echo "Skipping scans (no files)."
fi
echo

# --- Hyprland runtime checks (only if running / accessible) ---
echo "[8] Runtime checks (hyprctl)"
if command -v hyprctl >/dev/null 2>&1; then
  if hyprctl -j monitors >/dev/null 2>&1; then
    echo "OK: hyprctl can talk to Hyprland (Hyprland likely running)."

    # ── 8a · CONFIG ERRORS — THIS IS THE LIST THAT POWERS THE RED WAYBAR
    # OVERLAY. If hyprctl configerrors prints anything, those are the
    # exact errors the user sees on screen, with file + line numbers.
    echo
    echo "── 8a · hyprctl configerrors  (THE definitive error list) ──"
    CFGERRS="$(hyprctl configerrors 2>/dev/null || true)"
    if [[ -z "$CFGERRS" ]] || echo "$CFGERRS" | grep -qiE '^no errors|^\s*$'; then
      echo "OK: hyprctl configerrors reports no errors"
    else
      echo "ERROR: Hyprland is reporting active config errors:"
      echo "$CFGERRS" | sed 's/^/    /'
    fi

    if [[ $FULL -eq 1 ]]; then
      echo
      echo "Monitors:"
      hyprctl monitors || true
      echo
      echo "Clients:"
      hyprctl clients || true
      echo
      echo "Active window:"
      hyprctl activewindow || true
      echo
      hr
      echo "[FULL] hyprctl -j dumps"
      for cmd in monitors workspaces clients devices binds activewindow configerrors; do
        echo "--- hyprctl -j $cmd"
        hyprctl -j "$cmd" 2>/dev/null || true
      done
    fi
  else
    echo "WARN: hyprctl cannot connect to Hyprland."
    echo "This is normal if Hyprland is not running or WAYLAND_DISPLAY/XDG_RUNTIME_DIR are not set for this shell."
    echo "Try running this script from inside your Hyprland session."
  fi
else
  echo "hyprctl not installed/found; skipping runtime checks."
fi
echo

# ── 8b · NYXUS rules file: show what's actually on disk RIGHT NOW
echo "[8b] NYXUS windowrules file on disk"
NYXUS_RULES="$HYPRDIR/conf.d/nyxus-windowrules.conf"
if [[ -f "$NYXUS_RULES" ]]; then
  RULES_SHA=$(sha256sum "$NYXUS_RULES" 2>/dev/null | cut -c1-12)
  RULES_LINES=$(wc -l < "$NYXUS_RULES")
  RULES_RULECOUNT=$(grep -cE '^[[:space:]]*windowrule(v2)?[[:space:]]*=' "$NYXUS_RULES")
  echo "Path:        $NYXUS_RULES"
  echo "SHA (12):    $RULES_SHA"
  echo "Lines:       $RULES_LINES"
  echo "Rule count:  $RULES_RULECOUNT"
  echo "── Contents ──"
  cat -n "$NYXUS_RULES" | sed 's/^/    /'
  echo "── End contents ──"
else
  echo "WARN: $NYXUS_RULES not found (resync may not have run)"
fi
echo

# --- Recent logs ---
echo "[9] Logs"

# 9a · Hyprland's OWN log file — this is where parse errors land EVEN WHEN
# debug:disable_logs is true, because errors bypass the disable flag.
echo "── 9a · Hyprland's own log (parse errors land here) ──"
HLOG_CACHE="$HOME/.cache/hyprland/hyprland.log"
HLOG_RUN=""
if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" && -n "${XDG_RUNTIME_DIR:-}" ]]; then
  HLOG_RUN="$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/hyprland.log"
fi
HLOG=""
[[ -f "$HLOG_CACHE" ]] && HLOG="$HLOG_CACHE"
[[ -z "$HLOG" && -f "$HLOG_RUN" ]] && HLOG="$HLOG_RUN"

if [[ -n "$HLOG" ]]; then
  echo "Found: $HLOG"
  echo "── Last 50 lines containing 'error' or 'invalid' ──"
  grep -iE 'error|invalid|fail|warn' "$HLOG" 2>/dev/null | tail -n 50 | sed 's/^/    /' || true
  echo "── End ──"
else
  echo "WARN: no Hyprland log found at $HLOG_CACHE or \$XDG_RUNTIME_DIR/hypr/<sig>/hyprland.log"
  echo "Tip: enable verbose logging by setting in hyprland.lua:"
  echo "    debug { disable_logs = false }"
fi
echo

# 9b · Journal (best-effort; may be empty if Hyprland wasn't started by the DM)
echo "── 9b · journalctl --user (Hyprland-related) ──"
if command -v journalctl >/dev/null 2>&1; then
  journalctl --user -b 0 2>/dev/null | grep -iE 'hyprland|wlroots' | grep -iE 'error|invalid|fail|warn' | tail -n 50 | sed 's/^/    /' || true
else
  echo "journalctl not found; skipping."
fi

echo
hr
echo "Done. Report saved to: $LOG"
echo "Tip: paste the last ~80 lines of the report (especially sections [5], [7], [8], [9]) when asking for help."

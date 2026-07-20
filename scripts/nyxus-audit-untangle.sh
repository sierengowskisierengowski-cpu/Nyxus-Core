#!/usr/bin/env bash
# NYXUS · nyxus-audit-untangle — detect cross-project refs and NYXUS wiring drift.
# Non-destructive. Called by nyxus-verify-build (or standalone).
set -u

FAIL=0
WARN=0
ok()  { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; FAIL=$((FAIL+1)); }
warn(){ printf '  WARN %s\n' "$*"; WARN=$((WARN+1)); }

REPO="${NYXUS_REPO:-$HOME/Nyxus-Core}"
CANON="${REPO}/artifacts/api-server/nyxus-scripts"

# Paths that ship NYXUS Hyprland (not sharkdash/qtile/gowskinet)
NYXUS_DIRS=(
  "${HOME}/.config/hypr"
  "${HOME}/.config/eww"
  "${HOME}/.config/rofi"
  "${HOME}/.config/dunst"
  "${HOME}/.config/wlogout"
  "${HOME}/.config/kitty"
  "${HOME}/.config/alacritty"
  "${HOME}/.config/nyxus"
  "${HOME}/.nyxus"
  "${CANON}"
)

# Separate projects — must NOT appear in NYXUS ship paths (except deepcore status labels)
FORBIDDEN_PATTERNS=(
  'sharkdash'
  '\bgowski\b'
  '/Projects/bifrost'
  '/Downloads/sharkdash'
  '@theme "nexus"'
  'nexus\.jpg'
  'apex-lock'
  'gowskinet-flip'
)
ALLOWED_EXCEPTIONS=(
  'deepcore.sh'
  'deepcore.yuck'
  'NYXUS_BUILD.md'
)

echo "── NYXUS · untangle audit ──────────────────────────────────────"

is_allowed() {
  local f="$1"
  for ex in "${ALLOWED_EXCEPTIONS[@]}"; do
    [[ "$(basename "$f")" == "$ex" ]] && return 0
  done
  return 1
}

# 1. Forbidden cross-project references
hits=0
while IFS= read -r -d '' f; do
  is_allowed "$f" && continue
  matched=0
  for pat in "${FORBIDDEN_PATTERNS[@]}"; do
    if grep -qiE "$pat" "$f" 2>/dev/null; then
      matched=1
      break
    fi
  done
  [[ $matched -eq 1 ]] || continue
  [[ $hits -lt 8 ]] && bad "stale ref in ${f#${HOME}/}"
  hits=$((hits+1))
done < <(find "${NYXUS_DIRS[@]}" -type f \
  \( -name '*.conf' -o -name '*.sh' -o -name '*.yuck' -o -name '*.rasi' -o -name '*.css' -o -name '*.toml' -o -name '*.json' -o -name '*.py' \) \
  ! -path '*/.restore-points/*' ! -path '*/nyxus-restore-backup-*/*' ! -path '*/nyxus-safe-backup-*/*' \
  ! -path '*/accent-baseline/*' ! -path '*/__pycache__/*' \
  -print0 2>/dev/null)

[[ $hits -eq 0 ]] && ok "no sharkdash/bifrost/nexus refs in NYXUS ship paths"
[[ $hits -gt 8 ]] && bad "... and $((hits-8)) more stale refs"

# 2. EWW CSS pipeline
if [[ -f "${HOME}/.config/eww/eww.scss" && -f "${HOME}/.config/eww/eww.css" ]]; then
  bad "live eww has both eww.scss and eww.css"
else
  ok "live eww scss/css layout clean"
fi
if [[ -f "${CANON}/eww/eww.scss" && -f "${CANON}/eww/eww.css" ]]; then
  bad "canonical eww has both eww.scss and eww.css"
fi

# 3. hyprlock / hyprexpo policy
# lock_cmd = hyprlock in hypridle.conf is correct — hypridle's lock_cmd IS
# the session lock handler and must invoke hyprlock directly. Only flag
# direct keybind exec or on-timeout invocations (bypassing loginctl).
if grep -rE '^bind.*exec.*\bhyprlock\b|^[^#]*on-timeout.*\bhyprlock\b' \
   "${HOME}/.config/hypr"/*.conf "${HOME}/.config/hypr"/conf.d/*.conf 2>/dev/null | grep -qv '^#'; then
  bad "hyprlock still wired in active hypr config (use loginctl lock-session for keybinds)"
else
  ok "hyprlock not directly bound (loginctl lock-session → hypridle → hyprlock is correct)"
fi

if grep -rE '^[^#]*hyprexpo' "${HOME}/.config/hypr" 2>/dev/null | grep -qE 'load hyprexpo|hyprexpo:expo'; then
  bad "hyprexpo load/toggle still enabled in hypr config"
else
  ok "hyprexpo not autoloaded or keybound"
fi

# 4. Palette mirror
SRC="${HOME}/.nyxus/nyxus-palette.css"
[[ -f "$SRC" ]] || SRC="${CANON}/nyxus-palette.css"
if [[ -f "$SRC" ]]; then
  mirror_ok=1
  for dest in \
    "${HOME}/.config/eww/nyxus-palette.css" \
    "${HOME}/.config/hypr/nyxus-palette.css" \
    "${HOME}/.config/rofi/nyxus-palette.css" \
    "${HOME}/.config/dunst/nyxus-palette.css" \
    "${HOME}/.config/wlogout/nyxus-palette.css"; do
    if [[ ! -f "$dest" ]] || ! cmp -s "$SRC" "$dest" 2>/dev/null; then
      warn "palette drift: ${dest#${HOME}/}"
      mirror_ok=0
    fi
  done
  [[ $mirror_ok -eq 1 ]] && ok "nyxus-palette.css mirrored to all consumers"
else
  warn "nyxus-palette.css source missing"
fi

# 5. Accent primary spot-check
if [[ -f "${HOME}/.config/nyxus/accent.json" ]]; then
  pri="$(jq -r '.presets[.active].primary // empty' "${HOME}/.config/nyxus/accent.json" 2>/dev/null)"
  if [[ -n "$pri" ]]; then
  for f in "${HOME}/.config/eww/accent.scss" "${HOME}/.config/dunst/dunstrc" "${HOME}/.config/wlogout/style.css"; do
    [[ -f "$f" ]] || continue
    if ! grep -qi "${pri#\#}" "$f" 2>/dev/null; then
      warn "accent $pri missing from ${f#${HOME}/}"
    fi
  done
  ok "accent preset active ($pri)"
  fi
fi

# 6. Keybind / onclick binary sanity (sample of critical targets)
check_bin() {
  local label="$1" cmd="$2"
  if command -v "$cmd" >/dev/null 2>&1 || [[ -x "${HOME}/.local/bin/$cmd" ]] || [[ -x "$cmd" ]]; then
    return 0
  fi
  [[ -f "$cmd" ]] && return 0
  bad "missing target for $label: $cmd"
  return 1
}

check_bin "nyxus-start" nyxus-start
check_bin "nyxus-home" nyxus-home
check_bin "nyxus-settings" nyxus-settings
check_bin "nyxus-mission" nyxus-mission-control-toggle
[[ -x "${HOME}/.config/eww/scripts/wifi-action.sh" ]] && ok "eww wifi-action.sh present" || bad "eww wifi-action.sh missing"
[[ -x "${HOME}/.config/eww/scripts/compile-eww-css.sh" ]] && ok "compile-eww-css.sh present" || warn "compile-eww-css.sh missing"

# 7. sharkdash on PATH is OK (local-only) but must not be in NYXUS exec-once
if grep -rE 'exec-once.*sharkdash|bind.*sharkdash' "${HOME}/.config/hypr" 2>/dev/null | grep -qv '^#'; then
  bad "hypr exec-once/bind still references sharkdash"
else
  ok "hyprland does not autostart sharkdash"
fi

echo "── untangle: $([[ $FAIL -eq 0 ]] && echo PASS || echo "$FAIL check(s) failed") · ${WARN} warning(s) ──"
exit "$FAIL"

#!/usr/bin/env bash
# NYXUS · nyxus-verify-build — daily-driver health checks (non-destructive).
set -u

FAIL=0
ok()  { printf '  OK  %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; FAIL=$((FAIL+1)); }
warn(){ printf '  WARN %s\n' "$*"; }

echo "── NYXUS · verify build ────────────────────────────────────────"

# EWW daemon singleton
cnt="$(pgrep -x eww 2>/dev/null | wc -l | tr -d " ")"
[[ "${cnt:-0}" -eq 1 ]] && ok "eww daemon count = 1" || bad "eww daemon count = ${cnt:-0} (want 1)"

# CSS pipeline
if [[ -f "${HOME}/.config/eww/eww.css" ]]; then
  if head -1 "${HOME}/.config/eww/eww.css" | grep -q '@charset'; then
    bad "eww.css contains @charset (eww 0.5 will reject)"
  else
    ok "eww.css present ($(wc -c < "${HOME}/.config/eww/eww.css") bytes, no @charset)"
  fi
else
  bad "missing ~/.config/eww/eww.css"
fi
if [[ -f "${HOME}/.config/eww/eww.scss" && -f "${HOME}/.config/eww/eww.css" ]]; then
  bad "both eww.scss and eww.css present (eww 0.5 conflict)"
elif [[ -f "${HOME}/.config/eww/eww.scss.source" ]]; then
  ok "eww.scss.source present"
fi

# Bars
if command -v eww >/dev/null 2>&1; then
  bars="$(eww active-windows 2>/dev/null | grep -cE '^(bar-bottom|bar-top|bar-left|bar-right):' || true)"
  [[ "$bars" -eq 4 ]] && ok "four bar windows open" || bad "bar count = $bars (want 4)"
  fx_on=1
  [[ -f "${HOME}/.config/eww/nyxus.conf" ]] && grep -q '^NYXUS_BAR_FX=off' "${HOME}/.config/eww/nyxus.conf" && fx_on=0
  if [[ $fx_on -eq 0 ]]; then
    ok "NYXUS_BAR_FX=off (static rims)"
  else
    anim_ok=0
    for pat in 'eww/scripts/prism-anim' 'eww/scripts/starlight-anim' 'python3 -u -'; do
      pgrep -f "$pat" >/dev/null 2>&1 && anim_ok=$((anim_ok+1))
    done
    if pgrep -f 'eww/scripts/prism-anim' >/dev/null || pgrep -f 'eww/scripts/starlight-anim' >/dev/null; then
      ok "bar FX deflisten scripts running"
    elif [[ $anim_ok -gt 0 ]]; then
      warn "bar FX may be running (python deflisten; confirm rims animate visually)"
    else
      warn "prism/starlight deflisten not visible in ps (confirm rims animate visually)"
    fi
  fi
else
  bad "eww not on PATH"
fi

# Hyprland
if command -v hyprctl >/dev/null 2>&1; then
  err="$(hyprctl configerrors 2>/dev/null | tr -d '\n' | xargs)"
  [[ -z "$err" ]] && ok "hyprctl configerrors clean" || bad "hyprctl configerrors: $err"
  plugs="$(hyprctl plugin list 2>/dev/null)"
  if echo "$plugs" | grep -qi 'no plugins'; then
    ok "no hyprland plugins loaded"
  elif echo "$plugs" | grep -qi hyprexpo; then
    bad "hyprexpo loaded (crash risk)"
  else
    warn "plugins: $(echo "$plugs" | head -3)"
  fi
fi

# Wallpaper
wall_ok=0
if command -v awww >/dev/null 2>&1; then
  if awww query 2>/dev/null | grep -q 'nyxus-urban-alien'; then
    ok "awww shows nyxus-urban-alien"
    wall_ok=1
  fi
fi
if [[ $wall_ok -eq 0 ]] && [[ -f "${HOME}/.config/nyxus/wallpaper.conf" ]]; then
  grep -q 'urban-alien\|nyxus-urban-alien' "${HOME}/.config/nyxus/wallpaper.conf" && \
    ok "wallpaper.conf points at urban-alien" || warn "wallpaper.conf may not be urban-alien"
fi

# Accent
if [[ -f "${HOME}/.config/nyxus/accent.json" ]]; then
  pri="$(jq -r '.presets[.active].primary // .presets.prism.primary // empty' "${HOME}/.config/nyxus/accent.json" 2>/dev/null)"
  [[ -n "$pri" ]] && ok "accent active primary=$pri" || warn "accent.json unreadable"
fi
if [[ -f "${HOME}/.config/nyxus/accent-baseline/home/cosmic/.config/eww/eww.scss" ]]; then
  ok "accent baseline eww.scss baked"
else
  warn "accent baseline missing (run nyxus-save-state)"
fi

# Canonical drift (quick)
REPO="${NYXUS_REPO:-$HOME/Nyxus-Core}"
CANON="${REPO}/artifacts/api-server/nyxus-scripts"
if [[ -d "$CANON/eww" ]]; then
  if [[ -f "$CANON/eww/eww.scss" && -f "$CANON/eww/eww.css" ]]; then
    bad "canonical eww has both eww.scss and eww.css"
  else
    ok "canonical eww scss/css layout clean"
  fi
  drift="$(diff -qr "${HOME}/.config/eww" "$CANON/eww" 2>/dev/null | grep -v '\.map$' | wc -l)"
  [[ "$drift" -eq 0 ]] && ok "live eww matches canonical" || warn "live vs canonical eww: $drift difference(s) — run nyxus-save-state"
fi

# hyprexpo autoload line
if grep -r '^exec-once.*nyxus-plugins load hyprexpo' "${HOME}/.config/hypr" 2>/dev/null | grep -qv '^#'; then
  bad "hyprexpo autoload exec-once still enabled in hypr config"
else
  ok "hyprexpo not autoloaded on boot"
fi

# Starfield lock veil assets
if [[ -f "${HOME}/.config/eww/assets/starfield-lock-base.png" ]]; then
  ok "starfield lock veil assets present"
else
  bad "missing starfield-lock-base.png — run gen-starfield-lock.py"
fi

# Comet-fire + station shards sourced
if grep -q 'nyxus-cometfire.conf' "${HOME}/.config/hypr/hyprland.conf" 2>/dev/null; then
  ok "nyxus-cometfire.conf sourced"
else
  warn "nyxus-cometfire.conf not sourced in hyprland.conf"
fi
if grep -q 'nyxus-stations.conf' "${HOME}/.config/hypr/hyprland.conf" 2>/dev/null; then
  ok "nyxus-stations.conf sourced"
else
  warn "nyxus-stations.conf not sourced in hyprland.conf"
fi

# Starlight headliner assets (bar FX)
if [[ -f "${HOME}/.config/eww/assets/starlight-strip.png" ]]; then
  ok "starlight headliner assets present"
else
  bad "missing starlight-strip.png — run gen-starlight-assets.py"
fi
asset_cnt="$(find "${HOME}/.config/eww/assets" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l | tr -d ' ')"
[[ "${asset_cnt:-0}" -ge 60 ]] && ok "eww assets count=${asset_cnt}" || warn "eww assets sparse (${asset_cnt:-0} pngs) — run sync-eww + generators"

# Untangle / cross-project / wiring audit
if [[ -x "${REPO}/scripts/nyxus-audit-untangle.sh" ]]; then
  echo ""
  "${REPO}/scripts/nyxus-audit-untangle.sh" || FAIL=$((FAIL+1))
fi

echo "── result: $([[ $FAIL -eq 0 ]] && echo PASS || echo "$FAIL check(s) failed") ──"
exit "$FAIL"

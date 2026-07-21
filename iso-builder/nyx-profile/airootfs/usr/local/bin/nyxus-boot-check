#!/usr/bin/env bash
# NYXUS · post-login bar health — fix grey/missing bars after reboot.
# Only relaunches when bars are actually missing. Never races a healthy session.
set -u

export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"

sleep 2

# grep -c exits 1 when count is 0, which would make `|| echo 0` produce "0\n0".
bars="$(eww active-windows 2>/dev/null | grep -cE '^bar-' || true)"
bars="${bars:-0}"

css_ok=0
if [[ -f "${HOME}/.config/eww/eww.css" ]] && ! head -1 "${HOME}/.config/eww/eww.css" | grep -q '@charset'; then
  css_ok=1
fi

# Already healthy — do not touch eww (avoids dual-daemon with persist-login).
if [[ "$bars" -eq 4 && "$css_ok" -eq 1 ]]; then
  exit 0
fi

# Single-flight lock so boot-check cannot overlap persist-login's launch-safe.
lock="${XDG_RUNTIME_DIR:-/tmp}/nyxus-eww-launch.lock"
exec 9>"$lock"
if ! flock -n 9; then
  # Another launcher owns eww right now — let it finish.
  exit 0
fi

mkdir -p "${HOME}/.cache/nyxus-eww"
{
  echo "[$(date '+%F %T')] boot-check repair bars=${bars} css_ok=${css_ok}"
  if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
    nyxus-eww-launch-safe
  fi
} >>"${HOME}/.cache/nyxus-eww/boot-check.log" 2>&1

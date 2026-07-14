#!/usr/bin/env bash
# NYXUS · post-login bar health — fix grey/missing bars after reboot.
set -u

sleep 2
bars="$(eww active-windows 2>/dev/null | grep -cE '^bar-' || echo 0)"
css_ok=0
[[ -f "${HOME}/.config/eww/eww.css" ]] && ! head -1 "${HOME}/.config/eww/eww.css" | grep -q '@charset' && css_ok=1

if [[ "$bars" -eq 4 && "$css_ok" -eq 1 ]]; then
  exit 0
fi

if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
  nyxus-eww-launch-safe >>"${HOME}/.cache/nyxus-eww/boot-check.log" 2>&1
fi

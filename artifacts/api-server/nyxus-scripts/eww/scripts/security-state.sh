#!/usr/bin/env bash
set -u

state() {
  local cmd="$1" fallback="$2"
  if command -v "$cmd" >/dev/null 2>&1; then
    "$cmd" status 2>/dev/null || echo "$fallback"
  else
    echo "$fallback"
  fi
}

hacker="$(state nyxus-hacker-mode off)"
ghost="$(state nyxus-ghost off)"
panic="$(state nyxus-panic idle)"

printf '{"hacker":"%s","ghost":"%s","panic":"%s"}\n' "$hacker" "$ghost" "$panic"

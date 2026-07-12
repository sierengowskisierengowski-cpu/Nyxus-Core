#!/usr/bin/env bash
# NYXUS · EWW · pending update package list (for the updates window)
# Emits {count, checked, packages:[{name, old, new}]}
# Uses checkupdates (pacman-contrib) when present, else the local sync DB.
set -u

rows=""
if command -v checkupdates >/dev/null 2>&1; then
  rows=$(checkupdates 2>/dev/null)
  src="checkupdates"
else
  rows=$(pacman -Qu 2>/dev/null | grep -v '\[ignored\]')
  src="pacman -Qu"
fi

checked=$(date +'%H:%M')

if command -v jq >/dev/null 2>&1; then
  printf '%s\n' "$rows" | jq -Rsc --arg checked "$checked" --arg src "$src" '
    split("\n") | map(select(length>0)) | map(
      # "name 1.2-1 -> 1.3-1"
      capture("^(?<name>\\S+)\\s+(?<old>\\S+)\\s+->\\s+(?<new>\\S+)$") // {name:., old:"", new:""}
    ) | {count: length, checked: $checked, source: $src, packages: .}'
else
  count=$(printf '%s\n' "$rows" | grep -c .)
  printf '{"count":%s,"checked":"%s","source":"%s","packages":[]}\n' "$count" "$checked" "$src"
fi

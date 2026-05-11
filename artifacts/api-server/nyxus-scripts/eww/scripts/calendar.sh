#!/usr/bin/env bash
# NYXUS · EWW · calendar grid for dashboard card.
# Outputs JSON {"month":"NOV 2026","grid":"<multi-line text>"} via jq.
set -u

month=$(date '+%b %Y' | tr 'a-z' 'A-Z')

# `cal` produces a localized monthly grid; first line is the title (we drop
# it since we render our own), the rest is "Mo Tu We …" header + weeks.
grid=$(cal | tail -n +2)

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg m "$month" --arg g "$grid" '{month:$m, grid:$g}'
else
  grid="${grid//\"/}"; grid="${grid//\\/}"
  grid="${grid//$'\n'/\\n}"
  printf '{"month":"%s","grid":"%s"}\n' "$month" "$grid"
fi

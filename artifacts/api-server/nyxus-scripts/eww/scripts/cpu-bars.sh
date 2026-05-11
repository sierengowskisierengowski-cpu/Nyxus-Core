#!/usr/bin/env bash
# NYXUS · EWW · per-core CPU usage (returns JSON array of percents).
# Sampled across a 0.5s window for a real reading (not a single snapshot).
set -u

if [[ ! -r /proc/stat ]]; then
  echo '{"cores":[]}'; exit 0
fi

# Snapshot 1
mapfile -t s1 < <(grep -E '^cpu[0-9]+ ' /proc/stat)
sleep 0.5
mapfile -t s2 < <(grep -E '^cpu[0-9]+ ' /proc/stat)

cores=()
for i in "${!s1[@]}"; do
  read -r _ a1 b1 c1 d1 e1 f1 g1 h1 i1 j1 <<<"${s1[i]}"
  read -r _ a2 b2 c2 d2 e2 f2 g2 h2 i2 j2 <<<"${s2[i]}"
  idle1=$(( d1 + e1 ))
  idle2=$(( d2 + e2 ))
  total1=$(( a1+b1+c1+d1+e1+f1+g1+h1+i1+j1 ))
  total2=$(( a2+b2+c2+d2+e2+f2+g2+h2+i2+j2 ))
  dt=$(( total2 - total1 ))
  di=$(( idle2 - idle1 ))
  pct=0
  [[ $dt -gt 0 ]] && pct=$(( (100 * (dt - di)) / dt ))
  cores+=("$pct")
done

if command -v jq >/dev/null 2>&1; then
  printf '%s\n' "${cores[@]}" | jq -sc '{cores:.}'
else
  joined=$(IFS=,; echo "${cores[*]}")
  printf '{"cores":[%s]}\n' "$joined"
fi

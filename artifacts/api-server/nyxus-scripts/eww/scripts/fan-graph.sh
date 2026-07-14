#!/usr/bin/env bash
# NYXUS . EWW . bottom-bar fan live graph (Phase 6, rev 2026-07-14b)
# Headline fan RPM + rolling block-character sparkline (ghost-HUD label
# render, same technique as CAVA/sys-graph). Reads MSI hw_profile fan
# paths when available, falls back to lm_sensors.
#
# Output: {"rpm":7868,"pct":87,"spark":"...","tooltip":"FAN1 7868 RPM . FAN2 8000 RPM"}
set -u
export LC_ALL=C.UTF-8

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-fan-graph"
STATE="${STATE_DIR}/hist.csv"
HIST_LEN=24
MAX_RPM=9000
mkdir -p "${STATE_DIR}"
BLOCKS=( "▁" "▂" "▃" "▄" "▅" "▆" "▇" "█" )
have() { command -v "$1" >/dev/null 2>&1; }

spark() {  # CSV of 0..100 -> block string
  local csv="$1" out="" v lvl
  local -a a
  IFS=',' read -r -a a <<<"$csv"
  (( ${#a[@]} == 0 )) && { printf '%s' "${BLOCKS[0]}"; return; }
  for v in "${a[@]}"; do
    [[ "$v" =~ ^[0-9]+$ ]] || v=0
    lvl=$(( v * 7 / 100 ))
    (( lvl < 0 )) && lvl=0; (( lvl > 7 )) && lvl=7
    out+="${BLOCKS[$lvl]}"
  done
  printf '%s' "$out"
}

trim() {
  awk -v s="$1" -v n="$HIST_LEN" 'BEGIN{k=split(s,a,","); st=(k>n?k-n+1:1);
    for(i=st;i<=k;i++) printf (i>st?",":"") a[i]}'
}

# ---- collect fan RPMs (hw_profile first, then lm_sensors) ---------------
HW="${HOME}/.config/nyxus/hw_profile.json"
labels=(); rpms=()
if [[ -r "$HW" ]] && have jq; then
  while IFS=$'\t' read -r label path; do
    [[ -z "$label" || -z "$path" || ! -r "$path" ]] && continue
    v=$(<"$path")
    [[ "$v" =~ ^[0-9]+$ ]] || continue
    labels+=("${label// /}"); rpms+=("$v")
  done < <(jq -r '
    .hwmon[]? | select(.name == "msi_wmi_platform" or (.fans | length) > 0) |
    .fans[]? | "\(.label // ("FAN" + (.idx|tostring)))\t\(.path)"
  ' "$HW" 2>/dev/null | head -4)
fi
if [[ ${#rpms[@]} -eq 0 ]] && have sensors; then
  while read -r l v; do
    labels+=("$l"); rpms+=("$v")
  done < <(sensors 2>/dev/null | awk '
    /[Ff]an[0-9]*:/ { gsub(/:/,"",$1); gsub(/[^0-9]/,"",$2)
      if ($2+0 > 0) printf "%s %s\n", toupper($1), $2 }' | head -4)
fi

# headline = fastest fan; tooltip lists every spinning fan; fan1/fan2 = the
# first two fans (stacked in the bar so both are always visible).
rpm=0; tooltip="Fans: no sensors"
fan1=${rpms[0]:-0}; fan2=${rpms[1]:-0}
if [[ ${#rpms[@]} -gt 0 ]]; then
  parts=()
  for i in "${!rpms[@]}"; do
    (( rpms[i] > rpm )) && rpm=${rpms[i]}
    (( rpms[i] > 0 )) && parts+=("${labels[$i]} ${rpms[$i]} RPM")
  done
  (( ${#parts[@]} == 0 )) && parts=("fans idle")
  tooltip=$(IFS=' . '; echo "${parts[*]}")
fi
clamppct() { local p=$(( $1 * 100 / MAX_RPM )); (( p > 100 )) && p=100; echo "$p"; }
pct=$(clamppct "$rpm"); pct1=$(clamppct "$fan1"); pct2=$(clamppct "$fan2")

# ---- roll history + sparkline (headline + one per fan) ------------------
roll() {  # $1 = state file, $2 = new pct -> echoes sparkline
  local st="$1" p="$2" hh=""
  [[ -r "$st" ]] && read -r hh < "$st"
  hh=$(trim "${hh:+$hh,}$p"); printf '%s\n' "$hh" > "$st"
  spark "$hh"
}
sp=$(roll "$STATE" "$pct")
sp1=$(roll "${STATE_DIR}/hist1.csv" "$pct1")
sp2=$(roll "${STATE_DIR}/hist2.csv" "$pct2")

printf '{"rpm":%d,"pct":%d,"spark":"%s","fan1":%d,"fan2":%d,"spark1":"%s","spark2":"%s","tooltip":"%s"}\n' \
  "$rpm" "$pct" "$sp" "$fan1" "$fan2" "$sp1" "$sp2" "${tooltip//\"/}"

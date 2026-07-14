#!/usr/bin/env bash
# NYXUS . EWW . unified system live-graph source (Phase 6, rev 2026-07-14)
# CPU% / CPU-package temp / NVIDIA dGPU util+temp, each with a rolling
# pixel-scaled sparkline history for the bottom-bar monitoring cluster.
#
# MSI GS77 hybrid GPU: the dGPU is queried via nvidia-smi ONLY when its PCI
# runtime power state is "active", so a suspended/asleep dGPU is never woken
# (no power spike, no error) - it degrades gracefully to present=false and a
# flat history until it powers back up on its own.
#
# Output (one line JSON):
# {"cpu":{"val":23,"hot":0,"hist":[px..]},
#  "temp":{"val":86,"hot":0,"hist":[px..]},
#  "gpu":{"val":12,"temp":73,"present":true,"hot":0,"hist":[px..]}}
set -u
export LC_ALL=C

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-sys-graph"
STATE="${STATE_DIR}/state.json"
HIST_LEN=18          # samples kept (each ~2s -> ~36s window)
SPARK_MIN=2          # px floor so an idle line still reads as a hairline
SPARK_MAX=22         # px ceiling (fits the 48px bottom bar cell)
mkdir -p "${STATE_DIR}"

have() { command -v "$1" >/dev/null 2>&1; }

# ---- scale a 0..100 value to SPARK_MIN..SPARK_MAX pixels ----------------
px_pct() { awk -v v="$1" -v lo="$SPARK_MIN" -v hi="$SPARK_MAX" \
  'BEGIN{ if(v<0)v=0; if(v>100)v=100; printf "%d", lo + (hi-lo)*v/100 }'; }
# ---- scale a temperature (30..100C) to pixels --------------------------
px_temp() { awk -v v="$1" -v lo="$SPARK_MIN" -v hi="$SPARK_MAX" \
  'BEGIN{ v=(v-30)/70; if(v<0)v=0; if(v>1)v=1; printf "%d", lo + (hi-lo)*v }'; }

# ---- CPU: busy% across a short window from /proc/stat ------------------
read_cpu() {
  read -r _ a1 b1 c1 d1 e1 f1 g1 rest < <(grep '^cpu ' /proc/stat)
  local idle1=$(( d1 + e1 )) tot1=$(( a1+b1+c1+d1+e1+f1+g1 ))
  sleep 0.4
  read -r _ a2 b2 c2 d2 e2 f2 g2 rest < <(grep '^cpu ' /proc/stat)
  local idle2=$(( d2 + e2 )) tot2=$(( a2+b2+c2+d2+e2+f2+g2 ))
  local dt=$(( tot2 - tot1 )) di=$(( idle2 - idle1 ))
  (( dt <= 0 )) && { echo 0; return; }
  echo $(( (100 * (dt - di)) / dt ))
}

# ---- CPU package temperature (coretemp preferred, thermal_zone0 else) --
read_temp() {
  local t=""
  if have sensors; then
    t=$(sensors 2>/dev/null | awk -F'[+.]' '/Package id 0:/{print $2; exit}')
  fi
  if [[ -z "$t" ]]; then
    for z in /sys/class/thermal/thermal_zone*/temp; do
      [[ -r "$z" ]] || continue
      t=$(awk '{printf "%d", $1/1000}' "$z"); break
    done
  fi
  [[ "$t" =~ ^[0-9]+$ ]] && echo "$t" || echo 0
}

# ---- NVIDIA dGPU, only if the card's PCI runtime state is active -------
gpu_present=false; gpu_util=0; gpu_temp=0
nvidia_path=""
for d in /sys/bus/pci/devices/*/; do
  [[ "$(cat "$d/vendor" 2>/dev/null)" == "0x10de" ]] || continue
  case "$(cat "$d/class" 2>/dev/null)" in 0x0300*|0x0302*) nvidia_path="$d"; break;; esac
done
if [[ -n "$nvidia_path" ]] && have nvidia-smi; then
  rt="$(cat "${nvidia_path}power/runtime_status" 2>/dev/null || echo unknown)"
  # Query only when awake (active/unknown). A suspended dGPU is left asleep.
  if [[ "$rt" != "suspended" ]]; then
    if read -r u t < <(timeout 3 nvidia-smi --query-gpu=utilization.gpu,temperature.gpu \
        --format=csv,noheader,nounits 2>/dev/null | awk -F', *' 'NR==1{print $1, $2}'); then
      [[ "$u" =~ ^[0-9]+$ ]] && { gpu_util="$u"; gpu_present=true; }
      [[ "$t" =~ ^[0-9]+$ ]] && gpu_temp="$t"
    fi
  fi
fi

cpu=$(read_cpu)
temp=$(read_temp)

cpu_px=$(px_pct "$cpu")
temp_px=$(px_temp "$temp")
gpu_px=$(px_pct "$gpu_util")

# hot flags drive the reactive ember state in the theme
chot=0; thot=0; ghot=0
(( cpu  >= 88 )) && chot=1
(( temp >= 90 )) && thot=1
(( gpu_util >= 90 )) && ghot=1

# ---- roll the histories (jq if present; flat fallback otherwise) -------
if have jq; then
  prev="{}"; [[ -r "$STATE" ]] && prev=$(cat "$STATE")
  # guard against a corrupt state file (fall back to empty object)
  echo "$prev" | jq -e . >/dev/null 2>&1 || prev="{}"
  jq -nc --argjson p "$prev" \
     --argjson n "$HIST_LEN" \
     --argjson cpu "$cpu" --argjson cpupx "$cpu_px" --argjson chot "$chot" \
     --argjson temp "$temp" --argjson temppx "$temp_px" --argjson thot "$thot" \
     --argjson gpu "$gpu_util" --argjson gpupx "$gpu_px" --argjson gtemp "$gpu_temp" \
     --argjson ghot "$ghot" --argjson present "$gpu_present" '
    def push(arr; v): (arr + [v]) | if length > $n then .[-$n:] else . end;
    {
      cpu:  {val:$cpu,  hot:$chot, hist: push($p.cpu.hist  // []; $cpupx)},
      temp: {val:$temp, hot:$thot, hist: push($p.temp.hist // []; $temppx)},
      gpu:  {val:$gpu, temp:$gtemp, present:$present, hot:$ghot,
             hist: push($p.gpu.hist // []; $gpupx)}
    }' | tee "$STATE"
else
  printf '{"cpu":{"val":%s,"hot":%s,"hist":[%s]},"temp":{"val":%s,"hot":%s,"hist":[%s]},"gpu":{"val":%s,"temp":%s,"present":%s,"hot":%s,"hist":[%s]}}\n' \
    "$cpu" "$chot" "$cpu_px" "$temp" "$thot" "$temp_px" "$gpu_util" "$gpu_temp" "$gpu_present" "$ghot" "$gpu_px"
fi

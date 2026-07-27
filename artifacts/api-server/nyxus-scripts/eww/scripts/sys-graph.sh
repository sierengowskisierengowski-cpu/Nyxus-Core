#!/usr/bin/env bash
# NYXUS . EWW . unified system live-graph source (Phase 6, rev 2026-07-14b)
# CPU% / CPU-package temp / NVIDIA dGPU util+temp, each rendered as a rolling
# block-character sparkline (reliable label render, same technique as CAVA)
# for the bottom-bar monitoring cluster.
#
# MSI GS77 hybrid GPU: the dGPU is queried via nvidia-smi ONLY when its PCI
# runtime power state is "active", so a suspended/asleep dGPU is never woken
# (no power spike, no error) - it degrades gracefully to present=false and a
# flat baseline sparkline until it powers back up on its own.
#
# Output (one line JSON):
# {"cpu":{"val":23,"hot":0,"spark":"..."},
#  "temp":{"val":86,"hot":0,"spark":"..."},
#  "gpu":{"val":12,"temp":73,"present":true,"hot":0,"spark":"..."}}
set -u
export LC_ALL=C.UTF-8

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-sys-graph"
STATE="${STATE_DIR}/hist.csv"     # 3 lines: cpu / temp(0-100 norm) / gpu
HIST_LEN=34
mkdir -p "${STATE_DIR}"
BLOCKS=( "▁" "▂" "▃" "▄" "▅" "▆" "▇" "█" )
have() { command -v "$1" >/dev/null 2>&1; }

# ---- build a block-char sparkline from a CSV of 0..100 values ----------
spark() {
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

trim() {  # keep last HIST_LEN comma values
  awk -v s="$1" -v n="$HIST_LEN" 'BEGIN{k=split(s,a,","); st=(k>n?k-n+1:1);
    for(i=st;i<=k;i++) printf (i>st?",":"") a[i]}'
}

# ---- CPU busy% over a short window ------------------------------------
read -r _ a1 b1 c1 d1 e1 f1 g1 _ < <(grep '^cpu ' /proc/stat)
sleep 0.4
read -r _ a2 b2 c2 d2 e2 f2 g2 _ < <(grep '^cpu ' /proc/stat)
dt=$(( (a2+b2+c2+d2+e2+f2+g2) - (a1+b1+c1+d1+e1+f1+g1) ))
di=$(( (d2+e2) - (d1+e1) ))
cpu=0; (( dt > 0 )) && cpu=$(( (100*(dt-di))/dt ))

# ---- CPU package temperature ------------------------------------------
temp=0
if have sensors; then
  temp=$(sensors 2>/dev/null | awk -F'[+.]' '/Package id 0:/{print $2; exit}')
fi
if [[ ! "$temp" =~ ^[0-9]+$ ]]; then
  # nullglob: unmatched glob expands to nothing (no literal "*/temp" arg)
  shopt -s nullglob
  for z in /sys/class/thermal/thermal_zone*/temp; do
    [[ -r "$z" ]] && { temp=$(awk '{printf "%d",$1/1000}' "$z"); break; }
  done
  shopt -u nullglob
fi
[[ "$temp" =~ ^[0-9]+$ ]] || temp=0
# normalise 30..100C -> 0..100 for the sparkline scale
tnorm=$(( (temp - 30) * 100 / 70 ))
(( tnorm < 0 )) && tnorm=0; (( tnorm > 100 )) && tnorm=100

# ---- NVIDIA dGPU, only when its PCI runtime state is not suspended -----
gpu_present=false; gpu_util=0; gpu_temp=0
nvpath=""
# nullglob: don't iterate a literal path when no PCI devices match
shopt -s nullglob
for d in /sys/bus/pci/devices/*/; do
  [[ "$(cat "$d/vendor" 2>/dev/null)" == "0x10de" ]] || continue
  case "$(cat "$d/class" 2>/dev/null)" in 0x0300*|0x0302*) nvpath="$d"; break;; esac
done
shopt -u nullglob
if [[ -n "$nvpath" ]] && have nvidia-smi; then
  rt="$(cat "${nvpath}power/runtime_status" 2>/dev/null || echo unknown)"
  if [[ "$rt" != "suspended" ]]; then
    if read -r u t < <(timeout 3 nvidia-smi --query-gpu=utilization.gpu,temperature.gpu \
        --format=csv,noheader,nounits 2>/dev/null | awk -F', *' 'NR==1{print $1,$2}'); then
      [[ "$u" =~ ^[0-9]+$ ]] && { gpu_util="$u"; gpu_present=true; }
      [[ "$t" =~ ^[0-9]+$ ]] && gpu_temp="$t"
    fi
  fi
fi

# ---- RAM used% (MemTotal - MemAvailable) ------------------------------
mem=0
{ read -r _ mtot _; read -r _ _ _; read -r _ mavail _; } < <(grep -E '^(MemTotal|MemFree|MemAvailable):' /proc/meminfo)
if [[ "${mtot:-0}" =~ ^[0-9]+$ ]] && (( mtot > 0 )) && [[ "${mavail:-}" =~ ^[0-9]+$ ]]; then
  mem=$(( (mtot - mavail) * 100 / mtot ))
fi
(( mem < 0 )) && mem=0; (( mem > 100 )) && mem=100

# ---- roll histories ----------------------------------------------------
ch=""; th=""; gh=""; mh=""
if [[ -r "$STATE" ]]; then { read -r ch; read -r th; read -r gh; read -r mh; } < "$STATE"; fi
ch=$(trim "${ch:+$ch,}$cpu")
th=$(trim "${th:+$th,}$tnorm")
gh=$(trim "${gh:+$gh,}$gpu_util")
mh=$(trim "${mh:+$mh,}$mem")
printf '%s\n%s\n%s\n%s\n' "$ch" "$th" "$gh" "$mh" > "$STATE"

# ---- hot flags ---------------------------------------------------------
chot=0; thot=0; ghot=0; mhot=0
(( cpu >= 88 )) && chot=1
(( temp >= 90 )) && thot=1
(( gpu_util >= 90 )) && ghot=1
(( mem >= 90 )) && mhot=1

cpu_spark=$(spark "$ch")
temp_spark=$(spark "$th")
gpu_spark=$(spark "$gh")
mem_spark=$(spark "$mh")

printf '{"cpu":{"val":%d,"hot":%d,"spark":"%s"},"temp":{"val":%d,"hot":%d,"spark":"%s"},"gpu":{"val":%d,"temp":%d,"present":%s,"hot":%d,"spark":"%s"},"mem":{"val":%d,"hot":%d,"spark":"%s"}}\n' \
  "$cpu" "$chot" "$cpu_spark" "$temp" "$thot" "$temp_spark" \
  "$gpu_util" "$gpu_temp" "$gpu_present" "$ghot" "$gpu_spark" \
  "$mem" "$mhot" "$mem_spark"

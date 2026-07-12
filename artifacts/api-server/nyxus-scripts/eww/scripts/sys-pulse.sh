#!/usr/bin/env bash
# NYXUS · EWW · system pulse
# CPU% / MEM% / temp°C / load / swap% / GPU% / GPU°C / fan RPM / net rx·tx
set -u

cpu=$(top -bn1 2>/dev/null | awk '/Cpu\(s\)/{printf "%d", $2+$4}' || echo 0)
mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%d", $3/$2*100}' || echo 0)
swap=$(free -m 2>/dev/null | awk '/Swap:/{ if ($2>0) printf "%d", $3/$2*100; else print 0 }' || echo 0)
load=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)

temp_file="/sys/class/thermal/thermal_zone0/temp"
if [[ -r "$temp_file" ]]; then
  temp=$(awk '{printf "%d", $1/1000}' "$temp_file")
else
  temp="--"
fi

# ── GPU (NVIDIA) — utilization % + temp°C; fall back to -- if absent ──
gpu="--"; gputemp="--"
if command -v nvidia-smi >/dev/null 2>&1; then
  read -r gpu gputemp < <(nvidia-smi --query-gpu=utilization.gpu,temperature.gpu \
      --format=csv,noheader,nounits 2>/dev/null | awk -F', *' 'NR==1{print $1, $2}')
  [[ -z "${gpu:-}" ]] && gpu="--"
  [[ -z "${gputemp:-}" ]] && gputemp="--"
fi

# ── Fan RPM — highest reading from lm_sensors (0 if none spinning) ──
fan="--"
if command -v sensors >/dev/null 2>&1; then
  fan=$(sensors 2>/dev/null | awk '/[Ff]an[0-9]*:/{gsub(/[^0-9]/,"",$2); if($2+0>max)max=$2+0} END{if(max=="")print "--"; else print max}')
  [[ -z "${fan:-}" ]] && fan="--"
fi

# ── Network throughput — sample /proc/net/dev twice, sum non-lo ifaces ──
read_bytes() {
  awk 'NR>2 && $1!~/^lo:/ {gsub(/:/,"",$1); rx+=$2; tx+=$10} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null
}
fmt_rate() {  # bytes/sec -> compact human string
  awk -v b="$1" 'BEGIN{
    if (b<1024) printf "%dB", b;
    else if (b<1048576) printf "%.0fK", b/1024;
    else printf "%.1fM", b/1048576;
  }'
}
read -r rx1 tx1 < <(read_bytes)
sleep 0.5
read -r rx2 tx2 < <(read_bytes)
if [[ -n "${rx1:-}" && -n "${rx2:-}" ]]; then
  netrx=$(fmt_rate $(( (rx2 - rx1) * 2 )))
  nettx=$(fmt_rate $(( (tx2 - tx1) * 2 )))
else
  netrx="--"; nettx="--"
fi

# ── load / thermal alert flag — drives the reactive red bar glow ──
hot=0
[[ "$cpu"  =~ ^[0-9]+$ ]] && (( cpu  >= 90 )) && hot=1
[[ "$temp" =~ ^[0-9]+$ ]] && (( temp >= 97 )) && hot=1

# ── per-tile ember alerts (STARFALL rev 2026-07-11) — computed here so
#    yuck never has to coerce string JSON fields into numbers ──
chot=0; mhot=0; thot=0; ghot=0
[[ "$cpu"  =~ ^[0-9]+$ ]] && (( cpu  >= 85 )) && chot=1
[[ "$mem"  =~ ^[0-9]+$ ]] && (( mem  >= 90 )) && mhot=1
[[ "$temp" =~ ^[0-9]+$ ]] && (( temp >= 90 )) && thot=1
[[ "$gpu"  =~ ^[0-9]+$ ]] && (( gpu  >= 90 )) && ghot=1

printf '{"cpu":"%s","mem":"%s","temp":"%s","load":"%s","swap":"%s","gpu":"%s","gputemp":"%s","fan":"%s","netrx":"%s","nettx":"%s","hot":"%s","chot":%s,"mhot":%s,"thot":%s,"ghot":%s}\n' \
  "$cpu" "$mem" "$temp" "$load" "$swap" "$gpu" "$gputemp" "$fan" "$netrx" "$nettx" "$hot" "$chot" "$mhot" "$thot" "$ghot"

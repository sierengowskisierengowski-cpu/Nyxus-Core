#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker — TRUE sliding marquee.
#
# Strategy:
#   * The full segment string ("text") is regenerated at most every
#     REGEN_SECS (default 30s) and cached at $CACHE_TEXT.
#   * Each call increments an offset stored at $CACHE_OFFSET and prints
#     a fixed-width WINDOW characters wide of the (text+text) ribbon
#     starting at that offset, so the marquee scrolls one column per
#     poll. Doubling the text guarantees seamless wrap-around.
#   * defpoll runs this at 0.1s -> 10fps, smooth on any modern box.
#
# Output: single-line JSON {"text":"...", "tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

CACHE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-ticker"
CACHE_TEXT="${CACHE_DIR}/text"
CACHE_TS="${CACHE_DIR}/ts"
CACHE_OFFSET="${CACHE_DIR}/offset"
CACHE_TIP="${CACHE_DIR}/tooltip"
REGEN_SECS=30
# Column count — full-length ribbon. 180 monospace cols at ~7px each
# ≈ 1260px, filling a 1920px top bar minus the brand pill (left) and
# now-playing pill (right). Override per-machine via NYXUS_TICKER_COLS
# in ~/.config/eww/nyxus.conf.
[[ -r "${HOME}/.config/eww/nyxus.conf" ]] && . "${HOME}/.config/eww/nyxus.conf" 2>/dev/null || true
WINDOW="${NYXUS_TICKER_COLS:-180}"
mkdir -p "${CACHE_DIR}"

now=$(date +%s)
last=0
[[ -r "${CACHE_TS}" ]] && last=$(<"${CACHE_TS}")

regen_segments() {
  local UP LOAD PROCS USERS KERN HOST DISK INET GW cpu mem TEMP WIFI PKG TIME
  UP=$(uptime -p 2>/dev/null | sed 's/^up //')
  LOAD=$(awk '{print $1, $2, $3}' /proc/loadavg 2>/dev/null)
  PROCS=$(ps -e --no-headers 2>/dev/null | wc -l)
  USERS=$(who | wc -l)
  KERN=$(uname -r 2>/dev/null)
  HOST=$(hostname 2>/dev/null)
  DISK=$(df -h --output=pcent / 2>/dev/null | tail -1 | tr -d ' %')
  INET=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1)
  GW=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')
  cpu=$(top -bn1 2>/dev/null | awk '/Cpu\(s\)/{printf "%d", $2+$4}')
  mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%d", $3/$2*100}')
  local temp_file="/sys/class/thermal/thermal_zone0/temp"
  if [[ -r "${temp_file}" ]]; then
    TEMP="$(awk '{printf "%d", $1/1000}' "${temp_file}")°C"
  else
    TEMP="--"
  fi
  WIFI=""
  if command -v nmcli >/dev/null 2>&1; then
    WIFI=$(nmcli -t -f IN-USE,SSID,SIGNAL device wifi list 2>/dev/null \
           | awk -F: '/^\*/{print $2 " " $3 "%"; exit}')
  fi
  PKG=""
  command -v pacman >/dev/null 2>&1 && PKG=$(pacman -Qq 2>/dev/null | wc -l)
  TIME=$(date '+%H:%M:%S')

  local segs=(
    "▌ NYXUS · DARK MIRROR · LIVE"
    "▌ TIME ${TIME}"
    "▌ HOST ${HOST:-?}"
    "▌ KERNEL ${KERN:-?}"
    "▌ UPTIME ${UP:-?}"
    "▌ LOAD ${LOAD:-? ? ?}"
    "▌ CPU ${cpu:-?}%"
    "▌ MEM ${mem:-?}%"
    "▌ TEMP ${TEMP}"
    "▌ DISK ${DISK:-?}%"
    "▌ PROCS ${PROCS:-?}"
    "▌ USERS ${USERS:-?}"
    "▌ NET ${INET:-offline}"
    "▌ GW ${GW:-—}"
    "▌ WIFI ${WIFI:-—}"
    "▌ PKGS ${PKG:-?}"
  )

  # Fisher-Yates shuffle so consecutive regens look fresh.
  local i j tmp
  for ((i=${#segs[@]}-1; i>0; i--)); do
    j=$(( RANDOM % (i + 1) ))
    tmp="${segs[i]}"; segs[i]="${segs[j]}"; segs[j]="${tmp}"
  done

  local out=""
  for s in "${segs[@]}"; do out+="${s}     "; done
  printf '%s' "${out}" > "${CACHE_TEXT}"
  printf '%s' "${now}" > "${CACHE_TS}"
  printf 'NYXUS LIVE · %s · CPU %s%% · MEM %s%% · TEMP %s · NET %s' \
         "${TIME}" "${cpu:-?}" "${mem:-?}" "${TEMP}" "${INET:-offline}" \
         > "${CACHE_TIP}"
}

# ── regen if stale or missing ────────────────────────────────────────
if [[ ! -s "${CACHE_TEXT}" ]] || (( now - last >= REGEN_SECS )); then
  regen_segments
fi

# ── pad text so doubled length always >= WINDOW ─────────────────────
text=$(<"${CACHE_TEXT}")
tooltip=$(<"${CACHE_TIP}" 2>/dev/null || echo "NYXUS LIVE")
len=${#text}
if (( len < WINDOW )); then
  while (( ${#text} < WINDOW + 1 )); do text+="${text}     "; done
  len=${#text}
fi

# ── advance offset ───────────────────────────────────────────────────
off=0
[[ -r "${CACHE_OFFSET}" ]] && off=$(<"${CACHE_OFFSET}")
off=$(( (off + 1) % len ))
printf '%d' "${off}" > "${CACHE_OFFSET}"

# ── window slice from doubled ribbon ─────────────────────────────────
double="${text}${text}"
window="${double:${off}:${WINDOW}}"

# JSON-escape (\ and " only — eww label is plain text)
window="${window//\\/\\\\}"
window="${window//\"/\\\"}"
tooltip="${tooltip//\\/\\\\}"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "${window}" "${tooltip}"

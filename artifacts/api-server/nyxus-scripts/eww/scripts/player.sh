#!/usr/bin/env bash
# NYXUS · EWW · now-playing (playerctl)
# Emits: status, title, artist, icon, tooltip, plus playback progress
# (pos/len seconds, formatted M:SS, integer progress 0-100) and album art
# url so the bottom-bar saucer music face can render a real transport UI.
set -u

status="Stopped"
title="—"
artist=""
icon="□"
pos_fmt="0:00"
len_fmt="0:00"
progress=0
arturl=""

fmt_time() { # seconds(float/int) -> M:SS
  local s=${1%.*}
  [[ -z "$s" || "$s" -lt 0 ]] 2>/dev/null && s=0
  printf '%d:%02d' $((s / 60)) $((s % 60))
}

if command -v playerctl >/dev/null 2>&1; then
  status=$(playerctl status 2>/dev/null || echo Stopped)
  if [[ "$status" != "Stopped" && "$status" != "No players found" ]]; then
    title=$(playerctl metadata title  2>/dev/null || echo "—")
    artist=$(playerctl metadata artist 2>/dev/null || echo "")
    arturl=$(playerctl metadata mpris:artUrl 2>/dev/null || echo "")

    # mpris:length is in microseconds; position is in seconds (float)
    len_us=$(playerctl metadata mpris:length 2>/dev/null || echo 0)
    [[ "$len_us" =~ ^[0-9]+$ ]] || len_us=0
    pos_s=$(playerctl position 2>/dev/null || echo 0)
    [[ "$pos_s" =~ ^[0-9.]+$ ]] || pos_s=0

    len_s=$((len_us / 1000000))
    pos_i=${pos_s%.*}
    [[ "$pos_i" =~ ^[0-9]+$ ]] || pos_i=0

    if [[ "$len_s" -gt 0 ]]; then
      progress=$(( pos_i * 100 / len_s ))
      [[ "$progress" -gt 100 ]] && progress=100
      [[ "$progress" -lt 0 ]] && progress=0
      len_fmt=$(fmt_time "$len_s")
    else
      len_fmt="--:--"
      progress=0
    fi
    pos_fmt=$(fmt_time "$pos_i")
  else
    status="Stopped"
  fi
fi

# Universal fallback (rev 2026-07-25): MPRIS only covers players that
# implement it — bare mpv (no mpv-mpris plugin), some games, browser tabs
# without a MediaSession all report nothing, so the saucer never flipped
# to the music face even with real audio playing. If MPRIS found nothing,
# check PipeWire/Pulse directly for any live sink-input (any app actively
# rendering audio) and treat that as "Playing" so the flip still fires —
# just without real track metadata to show.
if [[ "$status" == "Stopped" ]] && command -v pactl >/dev/null 2>&1; then
  if pactl list short sink-inputs 2>/dev/null | grep -q .; then
    status="Playing"
    title="Now Playing"
    artist=""
    pos_fmt="--:--"
    len_fmt="--:--"
    progress=0
  fi
fi

case "$status" in
  Playing) icon="▶" ;;
  Paused)  icon="⏸" ;;
  *)       icon="□" ;;
esac

[[ -n "$artist" && "$artist" != "—" ]] && tooltip="${icon} ${artist} — ${title}" || tooltip="${icon} ${title}"

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg status "$status" --arg title "$title" --arg artist "$artist" \
        --arg icon "$icon" --arg tooltip "$tooltip" \
        --arg pos "$pos_fmt" --arg len "$len_fmt" \
        --argjson progress "${progress:-0}" --arg art "$arturl" \
    '{status:$status,title:$title,artist:$artist,icon:$icon,tooltip:$tooltip,pos:$pos,len:$len,progress:$progress,art:$art}'
else
  printf '{"status":"%s","title":"%s","artist":"%s","icon":"%s","tooltip":"%s","pos":"%s","len":"%s","progress":%s,"art":"%s"}\n' \
    "$status" "${title//\"/}" "${artist//\"/}" "$icon" "${tooltip//\"/}" "$pos_fmt" "$len_fmt" "${progress:-0}" "${arturl//\"/}"
fi

#!/usr/bin/env bash
# ============================================================
#  NYXUS PULSE — audio-reactive prism halo (rev r1 · 2026-07-07)
#
#  The focused window's violet shadow bloom thumps with whatever
#  is playing: a dedicated cava instance taps the PipeWire monitor
#  (~/.config/nyxus/pulse-cava.conf, 20fps, 2 bars = L/R), this
#  daemon maps the loudest channel (0-7) to shadow alpha + radius
#  and applies both in one `hyprctl --batch` call.
#
#  Zero idle cost: cava's sleep_timer stops frames when audio is
#  silent, and hyprctl only fires when the level BUCKET changes.
#  Attack is instant, decay is 1 level/frame — thump, then breathe.
#
#  usage: nyxus-pulse.sh start|stop|toggle|status|run
#  SUPER+ALT+P toggles (nyxus-hyprland-flair.conf); autostarted
#  from hyprland.conf. Stock halo is restored on any exit.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

PIDFILE=/tmp/.nyxus-pulse.pid
FIFO=/tmp/.nyxus-pulse.fifo
CFG="$HOME/.config/nyxus/pulse-cava.conf"

# ACCENT-AWARE (rev r2): the halo hue is read from the LIVE compositor,
# not hardcoded — nyxus-apply-accent / accent-from-wallpaper can re-skin
# the desktop at any time and the pulse follows. The stock rgb+alpha are
# re-read at daemon start and again at the start of every burst that
# begins from silence, so an accent change lands on the next beat.
STOCK_RGB="784bff"     # overwritten by read_stock() before first apply
STOCK_ALPHA="3a"
STOCK_RANGE=42

read_stock() {
    # decoration:shadow:color int is AARRGGBB
    local hex
    hex=$(printf '%08x' "$(hyprctl getoption decoration:shadow:color -j 2>/dev/null \
        | jq -r '.int // empty' 2>/dev/null)" 2>/dev/null) || return 0
    if [ "${#hex}" = 8 ]; then
        STOCK_ALPHA=${hex:0:2}
        STOCK_RGB=${hex:2:6}
    fi
    STOCK_RANGE=$(hyprctl getoption decoration:shadow:range -j 2>/dev/null \
        | jq -r '.int // 42' 2>/dev/null) || STOCK_RANGE=42
}

restore() {
    hyprctl --batch \
        "keyword decoration:shadow:color rgba(${STOCK_RGB}${STOCK_ALPHA}) ; keyword decoration:shadow:range $STOCK_RANGE" \
        >/dev/null 2>&1
}

run() {
    # per-level shadow alpha + bloom radius (index = cava level 0-7);
    # level 0 mirrors the stock 3a/42 halo from nyxus-hyprland-general.conf
    local alpha=(3a 46 52 5e 6a 78 88 99)
    local range=(42 46 50 55 60 66 72 80)
    local cur=0 last=-1 target c
    local cavapid=""

    read_stock

    echo $$ >"$PIDFILE"

    if [ "${NYXUS_PULSE_TEST:-0}" = 1 ]; then
        # test harness: frames come from stdin, no restore on exit so
        # the applied values can be inspected after EOF
        trap 'rm -f "$PIDFILE"' EXIT
    else
        rm -f "$FIFO"; mkfifo "$FIFO"
        cava -p "$CFG" >"$FIFO" &
        cavapid=$!
        trap 'kill "$cavapid" 2>/dev/null; restore; rm -f "$PIDFILE" "$FIFO"' EXIT
        exec <"$FIFO"
    fi

    while IFS= read -r line; do
        # frame like "3;5;" — take the loudest channel
        target=0
        for c in ${line//;/ }; do
            case "$c" in *[!0-9]*|'') continue ;; esac
            [ "$c" -gt "$target" ] && target=$c
        done
        [ "$target" -gt 7 ] && target=7

        # burst starting from silence: pick up the current accent first,
        # so a wallpaper/accent re-skin is honored on the next beat
        if [ "$cur" -eq 0 ] && [ "$target" -gt 0 ] && [ "${NYXUS_PULSE_TEST:-0}" != 1 ]; then
            read_stock
        fi

        # instant attack, 1-level-per-frame decay
        if [ "$target" -gt "$cur" ]; then
            cur=$target
        elif [ "$cur" -gt 0 ]; then
            cur=$((cur - 1))
        fi

        if [ "$cur" -ne "$last" ]; then
            hyprctl --batch \
                "keyword decoration:shadow:color rgba(${STOCK_RGB}${alpha[cur]}) ; keyword decoration:shadow:range ${range[cur]}" \
                >/dev/null 2>&1
            last=$cur
        fi
    done
}

running() { [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; }

case "${1:-toggle}" in
    run)    run ;;
    start)
        running && exit 0
        command -v cava >/dev/null || { notify-send -u critical "NYXUS Pulse" "cava is not installed"; exit 1; }
        setsid "$0" run >/dev/null 2>&1 &
        ;;
    stop)
        running && kill "$(cat "$PIDFILE")" 2>/dev/null
        ;;
    toggle)
        if running; then
            "$0" stop
            notify-send -u low -t 2000 "◤ ♪ ◥ NYXUS PULSE" "halo static" 2>/dev/null
        else
            "$0" start
            notify-send -u low -t 2000 "◤ ♪ ◥ NYXUS PULSE" "halo is listening" 2>/dev/null
        fi
        ;;
    status)
        running && echo "pulse: running ($(cat "$PIDFILE"))" || echo "pulse: stopped"
        ;;
esac

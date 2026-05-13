#!/bin/sh
# Briefly show a snap-confirmation toast.
set -eu
text="${1:-Snapped}"
eww update snap-toast-text="$text"
eww open snap-toast
( sleep 1.0 && eww close snap-toast ) &

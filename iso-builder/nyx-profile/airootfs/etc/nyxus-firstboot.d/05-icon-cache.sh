#!/usr/bin/env bash
# 05-icon-cache.sh — refresh icon caches on first boot so NYXUS-Dark
# (and any other newly installed themes) are visible to GTK lookups.
set -euo pipefail

LOG="/var/log/nyxus-firstboot.log"
log() { printf '[%(%F %T)T] icon-cache: %s\n' -1 "$*" | tee -a "$LOG"; }

if ! command -v gtk-update-icon-cache >/dev/null 2>&1; then
  log "gtk-update-icon-cache not present, skipping"
  exit 0
fi

for theme in NYXUS-Dark Papirus-Dark Adwaita hicolor; do
  dir="/usr/share/icons/${theme}"
  if [[ -d "${dir}" ]]; then
    if gtk-update-icon-cache -q -f -t "${dir}" 2>>"$LOG"; then
      log "refreshed ${theme}"
    else
      log "WARN failed to refresh ${theme}"
    fi
  fi
done

exit 0

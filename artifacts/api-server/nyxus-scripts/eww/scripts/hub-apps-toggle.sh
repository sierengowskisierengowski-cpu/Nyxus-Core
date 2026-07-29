#!/usr/bin/env bash
# NYXUS · EWW · Hub "ALL APPS / NYXUS ONLY" toggle
#
# The Hub's APPS section can list every installed .desktop or only the NYXUS
# apps. The mode is a flag file: present => NYXUS-only, absent => show all.
#
# WHY THIS IS A SCRIPT AND NOT AN INLINE :onclick
# ---------------------------------------------------------------------------
# It used to be inline, and it wrote the WRONG file. The flag was renamed
# hub-apps-all -> hub-apps-nyxus on 2026-07-20 (default flipped to show-all),
# both defpolls were updated to read the new name, and the button was missed.
# It kept creating/removing hub-apps-all, which nothing reads, so clicking the
# toggle did nothing at all. One name, defined once, in one place now.
#
# It also pushes the new values straight into eww. The two backing defpolls run
# on a 10s interval, so without this the label and the list did not change for
# up to ten seconds after the click and the button felt broken even once the
# flag was right.
set -u

FLAG_DIR="${HOME}/.cache/nyxus-eww"
FLAG="${FLAG_DIR}/hub-apps-nyxus"

mkdir -p "${FLAG_DIR}" 2>/dev/null || true

if [[ -f "${FLAG}" ]]; then
  rm -f "${FLAG}"
else
  : > "${FLAG}"
fi

if [[ -f "${FLAG}" ]]; then
  mode="nyxus"; only="--nyxus"
else
  mode="all";   only=""
fi

apps="$(nyxus-hub-apps ${only} 2>/dev/null)" || apps=""
[[ -n "${apps}" ]] || apps="[]"

# Repaint immediately instead of waiting out the poll interval.
eww update "HUBAPPS_MODE=${mode}" 2>/dev/null || true
eww update "HUBAPPS=${apps}"      2>/dev/null || true

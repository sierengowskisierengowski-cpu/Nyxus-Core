#!/usr/bin/env bash
# NYXUS Start Menu — app enumerator
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Emits a single JSON document consumed by the (defpoll STARTAPPS …)
# in eww.yuck:
#
#   { "pinned":  [ [tile,tile,tile,tile], … 3 rows ],
#     "recents": [ {name,path,exec}, … up to 8 ],
#     "all":     [ {name,exec}, … filtered by $1==search query ],
#     "user":    "<login>",
#     "host":    "<hostname>",
#     "avatar":  "<path or empty>" }
#
# Pinned tiles are read from $XDG_CONFIG_HOME/nyxus/startmenu-pinned.list
# (one .desktop basename per line). When that file is absent we fall
# back to a sensible NYXUS default set.
#
# Recents are read from ~/.local/share/nyxus/recent-apps.log — a tail
# of the last app launches written by this script when called as
# `startmenu-apps.sh launch <desktop_id>`.
#
# Search mode (`startmenu-apps.sh search <query>`) writes the same JSON
# but with `all` filtered by case-insensitive substring match against
# the .desktop Name= field, so the eww :onchange handler can refresh.

set -u
shopt -s nullglob

CFG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nyxus"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nyxus"
PINNED_FILE="$CFG_DIR/startmenu-pinned.list"
RECENT_LOG="$DATA_DIR/recent-apps.log"
mkdir -p "$CFG_DIR" "$DATA_DIR"

# ── handle launch logging side-channel ────────────────────────────────
if [ "${1:-}" = "launch" ] && [ -n "${2:-}" ]; then
  printf '%s\t%s\n' "$(date +%s)" "$2" >> "$RECENT_LOG"
  # keep last 200 lines only
  tail -n 200 "$RECENT_LOG" > "$RECENT_LOG.tmp" && mv "$RECENT_LOG.tmp" "$RECENT_LOG"
  exit 0
fi

QUERY=""
if [ "${1:-}" = "search" ]; then
  QUERY="${2:-}"
fi

# ── enumerate all .desktop files ──────────────────────────────────────
declare -A SEEN
ALL_JSON=""
APPS_DIRS=(
  /usr/share/applications
  /usr/local/share/applications
  /var/lib/flatpak/exports/share/applications
  "$HOME/.local/share/applications"
  "$HOME/.local/share/flatpak/exports/share/applications"
)

# Build a tab-separated table: id<TAB>name<TAB>exec<TAB>icon<TAB>nodisplay
TABLE="$(
  for d in "${APPS_DIRS[@]}"; do
    [ -d "$d" ] || continue
    for f in "$d"/*.desktop; do
      id="$(basename "$f" .desktop)"
      [ -n "${SEEN[$id]:-}" ] && continue
      SEEN[$id]=1
      name="$(awk -F= '/^\[/{s=0} /^\[Desktop Entry\]/{s=1} s && /^Name=/{print $2; exit}' "$f")"
      execv="$(awk -F= '/^\[/{s=0} /^\[Desktop Entry\]/{s=1} s && /^Exec=/{sub(/^Exec=/,""); print; exit}' "$f")"
      icon="$(awk -F= '/^\[/{s=0} /^\[Desktop Entry\]/{s=1} s && /^Icon=/{print $2; exit}' "$f")"
      nodisp="$(awk -F= '/^\[/{s=0} /^\[Desktop Entry\]/{s=1} s && /^NoDisplay=/{print $2; exit}' "$f")"
      # strip field codes (%U %F %u %f %i %c %k)
      execv="$(printf '%s' "$execv" | sed -E 's/ ?%[fFuUdDnNickvm]//g')"
      [ -z "$name" ] && continue
      [ -z "$execv" ] && continue
      printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$name" "$execv" "$icon" "$nodisp"
    done
  done | sort -t$'\t' -k2,2 -f
)"

# ── jq helpers ────────────────────────────────────────────────────────
have_jq=0
command -v jq >/dev/null 2>&1 && have_jq=1

# Build `all` JSON array of {id,name,exec,glyph} (filtered by QUERY).
# Glyph is a unicode block we pick from the Name's first letter for a
# zero-icon-theme-dependency look (matches the rest of NYXUS' EWW).
build_all() {
  local q_lc="${QUERY,,}"
  if [ "$have_jq" -eq 1 ]; then
    awk -F'\t' -v q="$q_lc" '
      BEGIN { print "[" ; first=1 }
      $5 == "true" { next }
      {
        n_lc = tolower($2)
        if (q != "" && index(n_lc, q) == 0) next
        gsub(/\\/, "\\\\", $2); gsub(/"/, "\\\"", $2)
        gsub(/\\/, "\\\\", $3); gsub(/"/, "\\\"", $3)
        glyph = toupper(substr($2,1,1))
        if (!first) printf ","
        first=0
        printf "{\"id\":\"%s\",\"name\":\"%s\",\"exec\":\"%s\",\"glyph\":\"%s\"}", $1, $2, $3, glyph
      }
      END { print "]" }
    ' <<<"$TABLE"
  else
    echo "[]"
  fi
}

# Pinned tiles — read PINNED_FILE or fall back to defaults. Output
# arranged as 3 rows × 4 columns.
build_pinned() {
  local pinned_ids
  if [ -f "$PINNED_FILE" ]; then
    pinned_ids="$(grep -v '^\s*#' "$PINNED_FILE" | grep -v '^\s*$')"
  else
    pinned_ids=$'org.kde.dolphin\nfirefox\nkitty\nnyxus-settings\nnyxus-software-store\ncode\nthunderbird\nvlc\nlibreoffice-startcenter\ngimp\nobs\nnyxus-sysmon'
  fi

  echo "["
  local row=0 col=0 first_row=1 first_col=1
  printf "  ["
  while IFS= read -r id; do
    [ -z "$id" ] && continue
    line="$(awk -F'\t' -v want="$id" '$1==want {print; exit}' <<<"$TABLE")"
    [ -z "$line" ] && continue
    name="$(cut -f2 <<<"$line")"
    execv="$(cut -f3 <<<"$line")"
    name_esc="${name//\\/\\\\}" ; name_esc="${name_esc//\"/\\\"}"
    exec_esc="${execv//\\/\\\\}" ; exec_esc="${exec_esc//\"/\\\"}"
    glyph="${name:0:1}" ; glyph="${glyph^^}"
    if [ $col -eq 0 ] && [ $first_row -eq 0 ]; then
      printf "],\n  ["
    fi
    [ $col -ne 0 ] && printf ", "
    printf '{"name":"%s","exec":"%s","glyph":"%s"}' "$name_esc" "$exec_esc" "$glyph"
    col=$((col+1))
    first_col=0
    if [ $col -eq 4 ]; then
      col=0
      row=$((row+1))
      first_row=0
      [ $row -ge 3 ] && break
    fi
  done <<<"$pinned_ids"
  printf "]\n]"
}

# Recents — last 8 unique launches, newest first.
build_recents() {
  echo "["
  local first=1
  if [ -f "$RECENT_LOG" ]; then
    tac "$RECENT_LOG" 2>/dev/null | awk -F'\t' '!seen[$2]++' | head -n 8 | while IFS=$'\t' read -r ts id; do
      line="$(awk -F'\t' -v want="$id" '$1==want {print; exit}' <<<"$TABLE")"
      [ -z "$line" ] && continue
      name="$(cut -f2 <<<"$line")"
      execv="$(cut -f3 <<<"$line")"
      name_esc="${name//\\/\\\\}" ; name_esc="${name_esc//\"/\\\"}"
      exec_esc="${execv//\\/\\\\}" ; exec_esc="${exec_esc//\"/\\\"}"
      [ $first -eq 0 ] && printf ","
      first=0
      printf '{"name":"%s","path":"%s","exec":"%s"}' "$name_esc" "$exec_esc" "$exec_esc"
    done
  fi
  printf "]"
}

USER_NAME="${USER:-$(id -un)}"
HOST_NAME="$(hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo nyxus)"
AVATAR=""
[ -f "$HOME/.face" ] && AVATAR="$HOME/.face"

PINNED_JSON="$(build_pinned)"
RECENTS_JSON="$(build_recents)"
ALL_JSON="$(build_all)"

cat <<EOF
{
  "pinned":  $PINNED_JSON,
  "recents": $RECENTS_JSON,
  "all":     $ALL_JSON,
  "user":    "$USER_NAME",
  "host":    "$HOST_NAME",
  "avatar":  "$AVATAR"
}
EOF

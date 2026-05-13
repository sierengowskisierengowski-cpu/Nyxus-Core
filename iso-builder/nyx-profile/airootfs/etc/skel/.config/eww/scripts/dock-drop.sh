#!/usr/bin/env bash
# Drop-zone handler. eww calls when a file URI is dropped on a dock icon.
#   $1 = entry id (e.g. firefox, nyxus-notepad)
#   $2..$n = file paths (or file:// URIs)
set -u

id="${1:-}"; shift || true
if [[ -z "$id" || $# -eq 0 ]]; then exit 0; fi

paths=()
for arg in "$@"; do
  case "$arg" in
    file://*) paths+=("$(python3 -c 'import sys,urllib.parse; print(urllib.parse.unquote(sys.argv[1][7:]))' "$arg")") ;;
    *)        paths+=("$arg") ;;
  esac
done

case "$id" in
  trash)
    for p in "${paths[@]}"; do gio trash "$p" 2>/dev/null || mv "$p" "$HOME/.local/share/Trash/files/" ; done
    ;;
  firefox|chromium|brave)        "$id" "${paths[@]}" >/dev/null 2>&1 & ;;
  nyxus-notepad|gedit|nano|code) ${id##nyxus-} "${paths[@]}" >/dev/null 2>&1 & ;;
  *)
    # default: hand off to xdg-open per file (lets the user's MIME assoc decide)
    for p in "${paths[@]}"; do xdg-open "$p" >/dev/null 2>&1 & done
    ;;
esac

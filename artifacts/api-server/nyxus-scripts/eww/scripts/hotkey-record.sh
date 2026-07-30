#!/usr/bin/env bash
# Wrapper for the nyxus-hotkey record helper.
# Used by the GTK Settings page through subprocess.run; never sees user shell.
set -euo pipefail
# nyxus-hotkey ships to /usr/local/bin. ~/.local/bin does not exist on the
# live ISO, so a hardcoded ~/.local/bin path is dead there (2026-07-30).
exec nyxus-hotkey record

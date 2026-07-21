#!/usr/bin/env bash
# Wrapper for the nyxus-hotkey record helper.
# Used by the GTK Settings page through subprocess.run; never sees user shell.
set -euo pipefail
exec "${HOME}/.local/bin/nyxus-hotkey" record

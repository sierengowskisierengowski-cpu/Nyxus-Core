#!/usr/bin/env bash
# NYXUS firstboot · seed XDG user dirs for the freshly created user.
set -e
xdg-user-dirs-update --force 2>/dev/null || true

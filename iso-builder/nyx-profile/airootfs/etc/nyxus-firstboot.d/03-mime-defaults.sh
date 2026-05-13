#!/usr/bin/env bash
# NYXUS firstboot · set NYXUS apps as the default for common MIME types.
set -e
xdg-mime default nyxus-files.desktop      inode/directory                       2>/dev/null || true
xdg-mime default nyxus-notepad.desktop    text/plain                            2>/dev/null || true
xdg-mime default org.kde.kate.desktop     text/x-c text/x-c++ text/x-python     2>/dev/null || true

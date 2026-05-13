#!/usr/bin/env bash
# NYXUS firstboot · regenerate machine-id (live ISO uses a fixed one).
set -e
if [ -f /etc/machine-id ] && [ "$(stat -c%s /etc/machine-id)" -lt 33 ]; then
  echo "[firstboot] regenerating machine-id"
  rm -f /etc/machine-id /var/lib/dbus/machine-id
  systemd-machine-id-setup
  ln -sf /etc/machine-id /var/lib/dbus/machine-id
fi

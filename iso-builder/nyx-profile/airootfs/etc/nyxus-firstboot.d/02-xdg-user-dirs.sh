#!/usr/bin/env bash
# NYXUS firstboot · repair XDG user dirs for existing human accounts.
#
# THIS SCRIPT USED TO BE ONE LINE: `xdg-user-dirs-update --force`. Every
# fragment here runs from nyxus-firstboot.service, which has NO User=, so it ran
# as root — and `xdg-user-dirs-update` writes to $HOME. It created
# /root/Documents, /root/Downloads, /root/Pictures and so on, and the nyx user
# never got any of them. `2>/dev/null || true` hid the whole thing.
#
# The real fix is not here: /etc/skel now ships the directories and
# .config/user-dirs.dirs, so any account created with `useradd -m` (which
# includes the live nyx user and anything Calamares makes) gets them at creation
# time with no command needing to run. This fragment is only a repair pass for
# accounts that predate that — it explicitly enters each human user's own
# context instead of assuming root's is theirs.
set -u

for _home in /home/*; do
  [[ -d "${_home}" ]] || continue
  _user="$(basename "${_home}")"
  id -u "${_user}" >/dev/null 2>&1 || continue

  # Seed the config from skel if the account is older than this change, so the
  # updater has the NYXUS layout to work from rather than inventing a locale
  # default.
  if [[ ! -f "${_home}/.config/user-dirs.dirs" && -f /etc/skel/.config/user-dirs.dirs ]]; then
    install -o "${_user}" -g "${_user}" -m 0644 -D \
      /etc/skel/.config/user-dirs.dirs "${_home}/.config/user-dirs.dirs" || true
  fi

  # runuser, not `su -c`: no PAM session, no password prompt, and $HOME is set
  # from the account rather than inherited from root.
  runuser -u "${_user}" -- xdg-user-dirs-update --force || true
done

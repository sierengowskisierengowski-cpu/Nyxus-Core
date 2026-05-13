#!/usr/bin/env bash
# NYXUS post-install hook — runs once inside the new install root from
# Calamares' shellprocess@nyxus_postinstall stage.
#
# Responsibilities (idempotent — safe to re-run):
#   1. Enable system-level NYXUS services that ship disabled.
#   2. Generate icon cache so first boot has working menu icons.
#   3. Touch the first-boot flag so nyxus-bootstrap runs the welcome
#      wizard exactly once for the new account.
#   4. Mark the bedtime / parental dirs world-readable (helper
#      contract — does not enable any blocks; everything stays OFF).
#   5. Refuse to enable fail2ban / pam_faillock / pam_tally — these
#      are explicitly OFF until post-install per project policy. We
#      actively MASK them here so a stray distro preset can't turn
#      them on behind our back.
#
# Logs to /var/log/nyxus-postinstall.log AND to stdout (Calamares
# streams stdout into /var/log/Calamares.log).
#
# Exit non-zero on hard failure so Calamares surfaces a real error
# instead of silently shipping a broken install.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail
IFS=$'\n\t'

LOG=/var/log/nyxus-postinstall.log
say() {
  printf '%s nyxus-postinstall: %s\n' "$(date -Iseconds)" "$*" \
    | tee -a "$LOG"
}

say "starting (root=$(id -un))"

# ── 1. system services ────────────────────────────────────────────
SYS_UNITS=(
  NetworkManager.service
  bluetooth.service
  systemd-timesyncd.service
  cups.service
  nyxus-firewall.service
)
for u in "${SYS_UNITS[@]}"; do
  if systemctl list-unit-files "$u" >/dev/null 2>&1; then
    if systemctl enable "$u" >/dev/null 2>&1; then
      say "enabled $u"
    else
      say "WARN: could not enable $u"
    fi
  fi
done

# ── 2. icon / desktop / font caches ───────────────────────────────
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  for theme in /usr/share/icons/*; do
    [[ -d "$theme/icons" || -f "$theme/index.theme" ]] || continue
    gtk-update-icon-cache -q -t -f "$theme" 2>/dev/null \
      && say "icon cache refreshed: $(basename "$theme")" || true
  done
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications 2>/dev/null \
    && say "desktop database refreshed" || true
fi
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -fr 2>/dev/null && say "font cache refreshed" || true
fi

# ── 3. first-boot flag (consumed by nyxus-bootstrap) ──────────────
mkdir -p /etc/skel/.config/nyxus
touch    /etc/skel/.config/nyxus/.first-boot
chmod 0644 /etc/skel/.config/nyxus/.first-boot
say "first-boot flag staged in /etc/skel"

# ── 4. parental dirs (world-readable, NO entries) ─────────────────
mkdir -p /etc/hosts.d
if [[ ! -f /etc/hosts.d/nyxus-parental ]]; then
  cat > /etc/hosts.d/nyxus-parental <<'EOF'
# NYXUS Parental Controls — managed file, do not edit by hand
EOF
  chmod 0644 /etc/hosts.d/nyxus-parental
  say "created empty parental blocklist"
fi

# ── 5. lockout policies stay OFF (project policy) ─────────────────
# Mask anything that could lock the new user out of their own machine
# during install/recovery. The user can manually unmask + enable post
# install if they really want to.
LOCKOUT_UNITS=(fail2ban.service)
for u in "${LOCKOUT_UNITS[@]}"; do
  if systemctl list-unit-files "$u" >/dev/null 2>&1; then
    systemctl mask "$u" >/dev/null 2>&1 \
      && say "masked $u (lockout policy OFF until user enables)" \
      || say "WARN: could not mask $u"
  fi
done
# PAM faillock: ensure it is NOT in /etc/pam.d/system-auth.
if [[ -f /etc/pam.d/system-auth ]] \
    && grep -q "pam_faillock" /etc/pam.d/system-auth; then
  say "ERROR: pam_faillock present in /etc/pam.d/system-auth — " \
      "removing per NYXUS policy"
  sed -i '/pam_faillock/d' /etc/pam.d/system-auth
fi
if [[ -f /etc/pam.d/system-auth ]] \
    && grep -q "pam_tally" /etc/pam.d/system-auth; then
  say "ERROR: pam_tally present in /etc/pam.d/system-auth — " \
      "removing per NYXUS policy"
  sed -i '/pam_tally/d' /etc/pam.d/system-auth
fi

say "done"
exit 0

#!/usr/bin/env bash
# ============================================================
#  NYXUS — switch the login greeter to greetd + regreet (Wayland)
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Why: SDDM's greeter uses X11, whose VT/GPU handoff kept failing on this
#  hybrid Intel+NVIDIA laptop (first a GL SIGSEGV, then an invisible greeter
#  frozen on VT1). Hyprland/COSMIC work fine because they are Wayland. This
#  moves the greeter onto the same Wayland/DRM path via greetd + regreet,
#  with a never-lock-out fallback chain (regreet -> tuigreet -> agreety).
#
#  Run once:  sudo scripts/nyxus-setup-greetd.sh
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
GS="${NS}/greetd"
REAL_USER="${SUDO_USER:-${USER}}"

if [[ $EUID -ne 0 ]]; then
  echo "elevating with sudo …"
  exec sudo -E bash "$0" "$@"
fi

echo "▌ NYXUS — installing greetd + regreet login for ${REAL_USER}"

# 1. Packages (all official 'extra' repo — no AUR). cage is already present.
#    Resilient: if pacman can't run (offline / db lock) but every binary is
#    already present, keep going so a re-run still redeploys the greeter/config
#    instead of aborting on `set -e` before the important steps below.
echo "  · installing greetd-regreet, greetd-tuigreet, cage …"
if ! pacman -S --needed --noconfirm greetd greetd-regreet greetd-tuigreet cage; then
  missing=""
  for b in greetd regreet tuigreet cage; do
    command -v "$b" >/dev/null 2>&1 || missing="${missing} ${b}"
  done
  if [[ -n "${missing}" ]]; then
    echo "  ✗ pacman failed and these are still missing:${missing}" >&2
    echo "    get online and re-run: sudo scripts/nyxus-setup-greetd.sh" >&2
    exit 1
  fi
  echo "  ! pacman unavailable but all greeter binaries already present — continuing"
fi

# 2. greeter chain script on PATH.
install -Dm755 "${GS}/nyxus-greeter" /usr/local/bin/nyxus-greeter

# 3. greetd + regreet config, themed CSS, and the login background.
#    Background must live under /etc/greetd — the 'greeter' user can't read
#    the operator's home.
install -Dm644 "${GS}/config.toml"  /etc/greetd/config.toml
install -Dm644 "${GS}/regreet.toml" /etc/greetd/regreet.toml
install -Dm644 "${GS}/regreet.css"  /etc/greetd/regreet.css
install -Dm644 "${GS}/nyxus-login-bg.png" /etc/greetd/nyxus-login-bg.png
# regreet writes its cache/state here as the greeter user.
install -d -o greeter -g greeter /var/lib/greetd 2>/dev/null || true
install -d -o greeter -g greeter /var/cache/regreet 2>/dev/null || true

# 4. Nyxus fonts system-wide so the greeter can render the wordmark/clock.
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"
if [[ -d "${REAL_HOME}/.local/share/fonts/nyxus" ]]; then
  install -d -m0755 /usr/share/fonts/nyxus
  install -m0644 "${REAL_HOME}/.local/share/fonts/nyxus/"*.ttf /usr/share/fonts/nyxus/ 2>/dev/null || true
  fc-cache -f >/dev/null 2>&1 || true
fi

# 5. Session entrypoint (greeter launches this for the NYXUS session).
install -Dm755 "${NS}/nyxus-session-start" /usr/local/bin/nyxus-session-start

# 6. Switch display-manager: SDDM off, greetd on. greetd.service aliases
#    display-manager.service, so enabling it repoints the symlink.
systemctl disable sddm.service          >/dev/null 2>&1 || true
systemctl disable cosmic-greeter.service >/dev/null 2>&1 || true
systemctl enable greetd.service
DM="$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null || true)"
echo "  · display-manager.service -> ${DM}"

# 7. Verify the deploy so a single run is trustworthy. This catches the exact
#    failure mode behind "the custom greeter never shows": a stale
#    /usr/local/bin/nyxus-greeter missing the anti-flash HOME/cache + iGPU-pin
#    block, which makes regreet fail EGL init ("//.cache permission denied",
#    "libEGL … fd -1") and silently fall through to the text login.
echo "  · verifying deploy …"
verify_ok=1
if ! grep -q "ANTI-FLASH #3" /usr/local/bin/nyxus-greeter 2>/dev/null; then
  echo "    ✗ /usr/local/bin/nyxus-greeter is stale (missing the anti-flash/iGPU startup)" >&2
  verify_ok=0
fi
if ! grep -q "nyxus-greeter" /etc/greetd/config.toml 2>/dev/null; then
  echo "    ✗ /etc/greetd/config.toml does not point at nyxus-greeter" >&2
  verify_ok=0
fi
for f in /etc/greetd/regreet.toml /etc/greetd/regreet.css /etc/greetd/nyxus-login-bg.png; do
  [[ -s "$f" ]] || { echo "    ✗ missing/empty $f" >&2; verify_ok=0; }
done
# greeter user must be able to write its GL/pipeline caches (anti-flash #1).
for d in /var/lib/greetd /var/cache/regreet; do
  if ! sudo -u greeter test -w "$d" 2>/dev/null; then
    echo "    ! $d not writable by 'greeter' — fixing ownership" >&2
    chown -R greeter:greeter "$d" 2>/dev/null || true
  fi
done
if [[ "$verify_ok" -ne 1 ]]; then
  echo "  ✗ deploy verification failed — regreet would fall back to the text login." >&2
  echo "    Re-run: sudo scripts/nyxus-setup-greetd.sh" >&2
  exit 1
fi
echo "    ✓ greeter, greetd config, regreet theme + background all in place"

cat <<EOF

── done. SAFE TO REBOOT ──────────────────────────────────────────────
On reboot you should get the themed NYXUS (regreet) login. If regreet
ever fails to start, greetd automatically falls through to a text login
(tuigreet) — you will NOT be dropped to a frozen screen again.

  sudo systemctl reboot

At the greeter: pick NYXUS (Hyprland) or COSMIC and log in.

If anything looks wrong you are still safe:
  - a text login (tuigreet) appears instead of the themed one, OR
  - switch to a TTY (Ctrl+Alt+F2) and: journalctl -b -u greetd
Recovery log from the greeter chain: /tmp/nyxus-greeter.log
To revert to SDDM:  sudo systemctl disable greetd && sudo systemctl enable sddm && reboot
──────────────────────────────────────────────────────────────────────
EOF

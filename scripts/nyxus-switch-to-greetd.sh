#!/usr/bin/env bash
# NYXUS — switch the live login from SDDM to greetd.  Run with sudo:
#     sudo bash ~/nyxus-switch-to-greetd.sh
#
# WHY: SDDM's X11 greeter starts cleanly but paints nothing on this laptop's
# hybrid Intel Iris Xe + NVIDIA RTX 3060 — the classic X-on-hybrid-GPU blank
# greeter. greetd is already installed and CONFIGURED for exactly this box
# (/etc/greetd/config.toml even documents the reason). It runs a Wayland
# greeter on VT1 and, through nyxus-greeter, falls through:
#     regreet (themed) -> regreet (software) -> tuigreet (text) -> agreety
# so even if the themed greeter cannot render, you land on a TEXT login that
# works on any GPU. That fall-through is the never-lock-out guarantee SDDM
# never had.
#
# This script is REVERSIBLE. It prints the one command to undo it, and it
# refuses to switch unless the text fallbacks that make greetd safe are
# actually present.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "run me with sudo:  sudo bash $0" >&2
  exit 1
fi

REAL_USER="${SUDO_USER:-cosmic}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BK="/root/nyxus-greeter-switch-${STAMP}"
mkdir -p "$BK"
REPO_GREETER="/home/${REAL_USER}/Nyxus-Core/artifacts/api-server/nyxus-scripts/greetd/nyxus-greeter"

say() { printf '  %s\n' "$*"; }
die() { printf '\n[ABORT] %s\n' "$*" >&2; exit 1; }

echo "▌ NYXUS · SDDM → greetd"
echo

# ── 1. Preflight: the pieces that make greetd SAFE must all exist ──────────
echo "1. preflight"
command -v greetd  >/dev/null || die "greetd is not installed"
[[ -f /etc/greetd/config.toml ]] || die "/etc/greetd/config.toml missing"
GCMD="$(sed -nE 's/^\s*command\s*=\s*"([^"]+)".*/\1/p' /etc/greetd/config.toml | head -1)"
GBIN="${GCMD%% *}"
[[ -x "$GBIN" ]] || die "greetd command '$GBIN' is not executable"
say "greetd runs: $GCMD"

# The never-lock-out chain: at least one text greeter MUST be present, or a
# render failure would leave no way in. This is the check that makes the
# switch safe — do not remove it.
TEXT_OK=0
for t in tuigreet agreety; do command -v "$t" >/dev/null && { say "text fallback: $t ✓"; TEXT_OK=1; }; done
[[ "$TEXT_OK" -eq 1 ]] || die "no tuigreet/agreety text greeter — refusing to switch (no safe fallback)"
command -v cage    >/dev/null && say "cage ✓ (themed path available)"
command -v regreet >/dev/null && say "regreet ✓ (themed path available)"

# ── 2. Deploy the newer, crash-loop-protected nyxus-greeter if we have it ──
echo "2. greeter script"
if [[ -f "$REPO_GREETER" ]] && ! cmp -s "$REPO_GREETER" "$GBIN"; then
  cp -a "$GBIN" "$BK/nyxus-greeter.live-before"
  # Validate before installing — never ship a greeter that won't parse.
  if bash -n "$REPO_GREETER"; then
    install -m755 "$REPO_GREETER" "$GBIN"
    say "deployed newer nyxus-greeter ($(wc -l <"$GBIN") lines; old backed up)"
  else
    say "repo greeter failed syntax check — keeping the current one"
  fi
else
  say "current nyxus-greeter is up to date"
fi
bash -n "$GBIN" || die "installed greeter does not parse — aborting before switch"

# ── 3. Record rollback state ───────────────────────────────────────────────
echo "3. backup + rollback record"
systemctl is-enabled sddm   >"$BK/sddm.was"   2>&1 || true
systemctl is-enabled greetd >"$BK/greetd.was" 2>&1 || true
cp -a /etc/greetd/config.toml "$BK/" 2>/dev/null || true
say "state saved under $BK"

# ── 4. Switch ──────────────────────────────────────────────────────────────
echo "4. switching display manager"
systemctl disable sddm.service   >/dev/null 2>&1 || true
systemctl enable  greetd.service >/dev/null 2>&1
say "sddm disabled, greetd enabled"

echo
echo "✓ Done. greetd is now the login manager."
echo
echo "  TEST IT (from this TTY, keeps a session you can return to):"
echo "      sudo systemctl stop sddm      # stop the blank SDDM greeter"
echo "      sudo systemctl start greetd   # bring up the greetd login on VT1"
echo "  or just reboot. If the themed login can't render, it falls through to"
echo "  a text login automatically — you will not be blank-locked."
echo
echo "  UNDO (back to SDDM):"
echo "      sudo systemctl disable greetd && sudo systemctl enable sddm && sudo reboot"
echo
echo "  Backup + rollback state: $BK"

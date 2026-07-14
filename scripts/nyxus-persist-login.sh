#!/usr/bin/env bash
# NYXUS · persist-login — restore theme/bars after every Hyprland login.
set -u

# PATH SELF-HEAL: under greetd/display-manager launches, ~/.local/bin is not
# always on PATH (see hyprland.conf autostart comments). Guarantee the nyxus
# launchers we call below (nyxus-eww-launch-safe, nyxus-restore-session, …)
# resolve no matter how the session was started.
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

LOG="${HOME}/.cache/nyxus-eww/persist-login.log"
mkdir -p "$(dirname "$LOG")"
ts() { date '+%F %T'; }

# SYMLINK SELF-HEAL: the recovery launchers in ~/.local/bin are ABSOLUTE-PATH
# symlinks into the Nyxus-Core clone (intentionally uncommitted). If they get
# wiped, the exec-once lines silently no-op and no bars appear. Recreate any
# that are missing/broken from the repo so the desktop keeps restoring even
# after the symlinks are lost. Repo location is derived from this script's own
# resolved path, so it works from any clone.
nyxus_heal_symlinks() {
  local self repo_scripts
  self="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null)" || return 0
  repo_scripts="$(dirname "$self")"
  [ -d "$repo_scripts" ] || return 0
  mkdir -p "${HOME}/.local/bin"
  local name src dst
  for name in nyxus-persist-login nyxus-boot-check nyxus-restore-session \
              nyxus-restore-login nyxus-overlay-unstick; do
    src="${repo_scripts}/${name}.sh"
    dst="${HOME}/.local/bin/${name}"
    [ -f "$src" ] || continue
    if [ ! -e "$dst" ] || [ "$(readlink -f "$dst" 2>/dev/null)" != "$src" ]; then
      ln -sf "$src" "$dst" 2>/dev/null || true
    fi
  done
}
nyxus_heal_symlinks || true

{
  echo "[$(ts)] persist-login start"

  # Self-heal the recovery symlinks in ~/.local/bin. These are intentionally
  # NOT committed (they are absolute-path symlinks into this repo checkout), so
  # a fresh checkout / accidental wipe can leave them missing — which would
  # silently break the exec-once autostart on the NEXT login. We can resolve
  # our own repo location from this script's real path and re-create the whole
  # recovery launcher set idempotently on every login.
  SELF="$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")"
  REPO_SCRIPTS="$(cd "$(dirname "$SELF")" && pwd)"
  BIN="${HOME}/.local/bin"
  mkdir -p "$BIN"
  for s in nyxus-persist-login nyxus-boot-check nyxus-restore-session \
           nyxus-restore-login nyxus-overlay-unstick; do
    src="${REPO_SCRIPTS}/${s}.sh"
    if [[ -f "$src" ]] && [[ "$(readlink -f "${BIN}/${s}" 2>/dev/null)" != "$(readlink -f "$src")" ]]; then
      ln -sf "$src" "${BIN}/${s}"
      echo "[$(ts)] self-heal symlink ${BIN}/${s} -> ${src}"
    fi
  done

  # Clear stuck overlay locks from prior session
  rm -rf "${XDG_RUNTIME_DIR:-/tmp}/nyxus-overlay-shield.d" 2>/dev/null || true

  # Ensure CSS exists (offline-safe compile)
  if [[ -x "${HOME}/.config/eww/scripts/compile-eww-css.sh" ]]; then
    "${HOME}/.config/eww/scripts/compile-eww-css.sh" || true
  fi

  # Wallpaper
  if command -v nyxus-wallpaper-autostart >/dev/null 2>&1; then
    nyxus-wallpaper-autostart >>"$LOG" 2>&1 || true
  fi

  sleep 1

  # Bars — safe relaunch (compile + single daemon + 4 windows)
  if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
    nyxus-eww-launch-safe >>"$LOG" 2>&1 || true
  elif command -v nyxus-eww-launch >/dev/null 2>&1; then
    nyxus-eww-launch >>"$LOG" 2>&1 || true
  fi

  # Verify; restore from GOLD if bars still broken
  bars="$(eww active-windows 2>/dev/null | grep -cE '^bar-' || echo 0)"
  if [[ "$bars" -lt 4 ]] && command -v nyxus-restore-session >/dev/null 2>&1; then
    echo "[$(ts)] bars=$bars — restoring from GOLD-LATEST"
    nyxus-restore-session >>"$LOG" 2>&1 || true
  fi

  echo "[$(ts)] persist-login done (bars=$(eww active-windows 2>/dev/null | grep -cE '^bar-' || echo 0))"
} >>"$LOG" 2>&1

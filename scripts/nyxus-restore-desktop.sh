#!/usr/bin/env bash
# ============================================================================
# NYXUS — Desktop Restore (last-known-good)
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Rebuilds the live Hyprland/EWW desktop from the canonical repo source
# (artifacts/api-server/nyxus-scripts/). Run this when a build or agent
# run has broken the session and you need to get back to a working state.
#
#   Usage (from a clone of Nyxus-Core):
#     bash scripts/nyxus-restore-desktop.sh
#
#   Or one-shot without a clone:
#     git clone --depth 1 -b <branch> https://github.com/sierengowskisierengowski-cpu/Nyxus-Core /tmp/nyxus-restore
#     bash /tmp/nyxus-restore/scripts/nyxus-restore-desktop.sh
#
# What it does, in order:
#   1. Backs up ~/.config/{hypr,eww,dunst,rofi,wlogout,alacritty,nyxus}
#      to ~/.config/nyxus-restore-backup-<timestamp>/
#   2. Installs Hyprland config + every conf.d shard from the repo
#   3. Installs the full EWW tree (yuck modules, scss, scripts, assets)
#   4. Installs dunst / rofi / wlogout / alacritty configs
#   5. Installs stations.json + wallpaper.conf, regenerates workspaces.json
#   6. Stages every nyxus-*.png wallpaper into ~/.config/hypr/walls/
#   7. Installs helper launchers into ~/.local/bin
#   8. Applies the alien-hero wallpaper, restarts EWW, reloads Hyprland
#
# Safe to re-run any number of times. Does NOT touch /usr or system files.
# ============================================================================
set -uo pipefail

B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'; GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'
step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

if [[ $EUID -eq 0 ]]; then
  fail "run as your normal user, NOT root (this only touches ~/.config)"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
CFG="${REPO_ROOT}/artifacts/nyxus-config"

if [[ ! -d "${NS}" ]]; then
  fail "canonical source not found at ${NS} — run from a Nyxus-Core clone"
  exit 1
fi

# ── 1. backup ───────────────────────────────────────────────────────────────
step "backup current configs"
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="${HOME}/.config/nyxus-restore-backup-${TS}"
mkdir -p "${BACKUP}"
for d in hypr eww dunst rofi wlogout alacritty nyxus; do
  if [[ -d "${HOME}/.config/${d}" ]]; then
    cp -a "${HOME}/.config/${d}" "${BACKUP}/${d}"
  fi
done
ok "backed up to ${BACKUP}"

# ── 2. hyprland ─────────────────────────────────────────────────────────────
step "install Hyprland configs"
mkdir -p "${HOME}/.config/hypr/conf.d" "${HOME}/.config/hypr/walls"
# Quarantine any stray Lua config from the reverted 0.55 lua migration
# (PR #39). If present, Hyprland can load it INSTEAD OF/alongside
# hyprland.conf — its catch-all float rules crash the session when apps
# open. Move it into the backup, never leave it in ~/.config/hypr/.
for stray in "${HOME}/.config/hypr/hyprland.lua" "${HOME}/.config/hypr"/conf.d/*.lua; do
  if [[ -f "${stray}" ]]; then
    mv "${stray}" "${BACKUP}/$(basename "${stray}").quarantined"
    warn "quarantined stray lua config: ${stray} → backup"
  fi
done
install -m 0644 "${NS}/hyprland.conf"  "${HOME}/.config/hypr/hyprland.conf"
install -m 0644 "${NS}/hyprlock.conf"  "${HOME}/.config/hypr/hyprlock.conf"
install -m 0644 "${NS}/hypridle.conf"  "${HOME}/.config/hypr/hypridle.conf"
# hyprland.conf sources ./nyxus-monitors.conf (Settings auto-manages it);
# ensure an empty stub exists so a fresh install doesn't warn on a missing
# source and never clobber a user's real monitor overrides if present.
[[ -f "${HOME}/.config/hypr/nyxus-monitors.conf" ]] || \
  printf '# NYXUS monitor overrides — auto-managed by Settings\n' \
    > "${HOME}/.config/hypr/nyxus-monitors.conf"
install -m 0644 "${NS}"/nyxus-hyprland-*.conf "${HOME}/.config/hypr/conf.d/"
for shard in nyxus-stations.conf nyxus-safemode.conf nyxus-signature.conf \
             nyxus-freeform.conf nyxus-cometfire.conf; do
  if [[ -f "${NS}/${shard}" ]]; then
    install -m 0644 "${NS}/${shard}" "${HOME}/.config/hypr/conf.d/${shard}"
  fi
done
ok "hyprland.conf + $(ls "${HOME}/.config/hypr/conf.d/" | wc -l) conf.d shards"

# ── 3. eww ──────────────────────────────────────────────────────────────────
step "install EWW tree"
mkdir -p "${HOME}/.config/eww/scripts" "${HOME}/.config/eww/assets"
install -m 0644 "${NS}"/eww/*.yuck "${HOME}/.config/eww/"
# a few inline asset paths in eww.yuck are absolute — point them at the
# deploying user's home so the UFO popup / hero backdrops / saucer resolve.
[[ "${HOME}" != "/home/cosmic" ]] && \
  sed -i "s#/home/cosmic/#${HOME}/#g" "${HOME}/.config/eww/eww.yuck" 2>/dev/null || true
install -m 0644 "${NS}/eww/eww.scss" "${HOME}/.config/eww/eww.scss" 2>/dev/null || true
if [[ -f "${NS}/eww/accent.scss" ]]; then
  install -m 0644 "${NS}/eww/accent.scss" "${HOME}/.config/eww/accent.scss"
fi
if [[ -f "${NS}/eww/_nyxus_accent.scss" ]]; then
  install -m 0644 "${NS}/eww/_nyxus_accent.scss" "${HOME}/.config/eww/_nyxus_accent.scss"
fi
if [[ -f "${NS}/eww/nyxus.conf" ]]; then
  install -m 0644 "${NS}/eww/nyxus.conf" "${HOME}/.config/eww/nyxus.conf"
fi
install -m 0755 "${NS}"/eww/scripts/* "${HOME}/.config/eww/scripts/" 2>/dev/null || true
if [[ -d "${NS}/eww/assets" ]]; then
  cp -a "${NS}/eww/assets/." "${HOME}/.config/eww/assets/"
fi
# stale hand-backups confuse eww reload — they live in git history anyway
rm -f "${HOME}/.config/eww"/eww.yuck.bak* 2>/dev/null || true
ok "eww: $(ls "${HOME}/.config/eww/"*.yuck | wc -l) yuck modules, $(ls "${HOME}/.config/eww/scripts/" | wc -l) scripts"

# ── 4. dunst / rofi / wlogout / alacritty ───────────────────────────────────
step "install app configs"
mkdir -p "${HOME}/.config/dunst" "${HOME}/.config/rofi" \
         "${HOME}/.config/wlogout" "${HOME}/.config/alacritty"
install -m 0644 "${NS}/nyxus-dunstrc"       "${HOME}/.config/dunst/dunstrc"
# UFO notification icon (dunst icon_path) — keep the dunstrc icon_path + the
# bridge script's paths pointed at the deploying user's home.
install -Dm644 "${NS}/eww/assets/nyxus-notif-ufo.png" \
  "${HOME}/.local/share/nyxus/icons/nyxus-notif-ufo.png"
sed -i "s#/home/cosmic/#${HOME}/#g" "${HOME}/.config/dunst/dunstrc" 2>/dev/null || true
install -m 0644 "${NS}/rofi-config.rasi"    "${HOME}/.config/rofi/config.rasi"
install -m 0644 "${NS}/rofi-nyxus.rasi"     "${HOME}/.config/rofi/nyxus.rasi"
install -m 0644 "${NS}/rofi-startmenu.rasi" "${HOME}/.config/rofi/startmenu.rasi"
install -m 0644 "${NS}/wlogout-style.css"   "${HOME}/.config/wlogout/style.css"
install -m 0644 "${NS}/wlogout-layout"      "${HOME}/.config/wlogout/layout"
install -m 0644 "${NS}/alacritty.toml"      "${HOME}/.config/alacritty/alacritty.toml"
ok "dunst / rofi / wlogout / alacritty"

# ── 5. station matrix + wallpaper config ────────────────────────────────────
step "install station matrix + wallpaper config"
mkdir -p "${HOME}/.config/nyxus"
install -m 0644 "${CFG}/stations.json" "${HOME}/.config/nyxus/stations.json"
cat > "${HOME}/.config/nyxus/wallpaper.conf" <<EOF
WALLPAPER="nyxus-wall-alien-hero"
WALLPAPER_PATH="${HOME}/.config/hypr/walls/nyxus-wall-alien-hero.png"
EOF
ok "stations.json + wallpaper.conf (alien-hero)"

# ── 6. wallpapers ───────────────────────────────────────────────────────────
step "stage wallpapers"
install -m 0644 "${NS}"/nyxus-*.png "${HOME}/.config/hypr/walls/" 2>/dev/null || true
# the canonical wallpaper/lock art set lives under hypr-walls/
install -m 0644 "${NS}"/hypr-walls/*.png "${HOME}/.config/hypr/walls/" 2>/dev/null || true
ok "$(ls "${HOME}/.config/hypr/walls/"*.png 2>/dev/null | wc -l) wallpapers in ~/.config/hypr/walls/"

# ── 7. helper launchers ─────────────────────────────────────────────────────
step "install helper launchers → ~/.local/bin"
mkdir -p "${HOME}/.local/bin"
for h in nyxus-eww-launch nyxus-eww-launch-safe nyxus-set-wallpaper.sh \
         nyxus-set-wallpaper nyxus-apply-accent nyxus-accent-from-wallpaper \
         nyxus-sync-stations nyxus-bootstrap nyxus-wait-bootstrap \
         nyxus-session-start nyxus-security \
         nyxus-hub-apps nyxus-hub-search nyxus-nowplaying nyxus-notif-to-eww nyxus-sound \
         nyxus-sound-bake nyxus-companion \
         nyxus-sfx nyxus-soundd nyxus-sounds nyxus-sound-forge \
         nyxus-shader nyxus-plugins nyxus-living nyxus-live-wallpaper \
         nyxus-eww-cinematic nyxus-wall-cycle nyxus-wall-fx nyxus-wall-next \
         nyxus-beat nyxus-beatd nyxus-tint nyxus-tintd nyxus-lens \
         nyxus-spray nyxus-freeform nyxus-mission-control-toggle \
         nyxus-record; do
  if [[ -f "${NS}/${h}" ]]; then
    install -m 0755 "${NS}/${h}" "${HOME}/.local/bin/${h}"
  elif [[ -f "${NS}/companion/${h}" ]]; then
    install -m 0755 "${NS}/companion/${h}" "${HOME}/.local/bin/${h}"
  fi
done
# Recovery autostart hooks (referenced from hyprland.conf). These are the
# absolute-path symlinks the login-restore chain depends on; recreate the
# FULL set so a wiped ~/.local/bin can't silently break session survival.
for script in nyxus-persist-login nyxus-boot-check nyxus-overlay-unstick \
              nyxus-restore-session nyxus-restore-login; do
  src="${REPO_ROOT}/scripts/${script}.sh"
  if [[ -f "${src}" ]]; then
    ln -sf "${src}" "${HOME}/.local/bin/${script}"
  fi
done
# Wayland session entry for display managers (SDDM picks this up).
if [[ -f "${NS}/desktop-entries/nyxus-hyprland.desktop" ]]; then
  mkdir -p "${HOME}/.local/share/wayland-sessions"
  install -m 0644 "${NS}/desktop-entries/nyxus-hyprland.desktop" \
    "${HOME}/.local/share/wayland-sessions/nyxus-hyprland.desktop"
fi
ok "helpers installed"

# ── 7b. companion app + cosmic sounds ───────────────────────────────────────
step "install companion + sound theme"
mkdir -p "${HOME}/.local/share/nyxus/companion" "${HOME}/.local/share/nyxus/sounds"
if [[ -d "${NS}/companion" ]]; then
  rsync -a --delete "${NS}/companion/" "${HOME}/.local/share/nyxus/companion/"
fi
if [[ -d "${NS}/sounds" ]]; then
  rsync -a "${NS}/sounds/" "${HOME}/.local/share/nyxus/sounds/"
fi
ok "companion + sounds staged"

# ── 8. regenerate workspaces.json ───────────────────────────────────────────
step "sync stations → workspaces.json"
if command -v jq >/dev/null 2>&1; then
  "${HOME}/.local/bin/nyxus-sync-stations" && ok "workspaces.json regenerated" \
    || warn "sync-stations failed — check jq / stations.json"
else
  warn "jq not installed — skipping workspaces.json regen (pacman -S jq)"
fi

# ── 9. apply live (only if inside a Hyprland session) ───────────────────────
step "apply to live session"
if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  WALL="${HOME}/.config/hypr/walls/nyxus-wall-alien-hero.png"
  if [[ -x "${HOME}/.local/bin/nyxus-set-wallpaper.sh" && -f "${WALL}" ]]; then
    "${HOME}/.local/bin/nyxus-set-wallpaper.sh" "${WALL}" >/dev/null 2>&1 \
      && ok "wallpaper applied: alien-hero" \
      || warn "wallpaper apply failed — will land on next login"
  fi
  if [[ -x "${HOME}/.local/bin/nyxus-eww-launch-safe" ]]; then
    "${HOME}/.local/bin/nyxus-eww-launch-safe" >/dev/null 2>&1 &
    ok "EWW relaunched (single-daemon guard)"
  fi
  # Reload dunst so the freshly-installed dunstrc (incl. the EWW UFO-popup
  # bridge rule + skip_display) takes effect NOW — otherwise a running dunst
  # keeps its stale config until next login and the themed popup never fires.
  if command -v dunst >/dev/null 2>&1; then
    if pgrep -x dunst >/dev/null 2>&1; then
      killall dunst >/dev/null 2>&1 || true
      sleep 0.3
    fi
    setsid dunst >/dev/null 2>&1 &
    ok "dunst reloaded (UFO notification bridge active)"
  fi
  hyprctl reload >/dev/null 2>&1 && ok "hyprctl reload" \
    || warn "hyprctl reload failed — log out and back in"
else
  warn "not inside a Hyprland session — changes take effect at next login"
fi

printf "\n${GOLD}${B}NYXUS desktop restored.${R}\n"
printf "  backup of previous state: ${CYAN}%s${R}\n" "${BACKUP}"
printf "  if anything is still off: log out, log back in.\n\n"

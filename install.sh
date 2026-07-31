#!/usr/bin/env bash
# ============================================================================
#  NYXUS — terminal installer                        rev 2026-07-15 (RC)
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Deploys the NYXUS Hyprland desktop from this repo's canonical tree onto
#  the LIVE user surfaces — the exact same fixed state that was verified on
#  the reference machine. This kills the "fixed in repo but not on my
#  machine" class of bugs for fresh installs and re-runs alike.
#
#    ./install.sh                 # full deploy: clean user state + system phase
#    ./install.sh --check         # preview the full deploy, touch nothing
#    ./install.sh --user-only     # clean + deploy user surfaces only
#    ./install.sh --no-reload     # deploy but don't reload the running session
#
#  Idempotent and safe to re-run: only stale NYXUS-managed files are purged,
#  with backup, and user-owned data (~/.config/nyxus state, extra wallpapers in
#  ~/.config/hypr/walls/rotation, nyxus-monitors.conf) is preserved.
# ============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"

# ── ANSI (violet / magenta signature palette) ───────────────────────────────
if [[ -t 1 ]]; then
  B=$'\e[1m'; R=$'\e[0m'; DIM=$'\e[2m'
  V1=$'\e[38;5;93m'; V2=$'\e[38;5;129m'; V3=$'\e[38;5;165m'
  V4=$'\e[38;5;201m'; V5=$'\e[38;5;213m'
  MINT=$'\e[38;5;121m'; GOLD=$'\e[38;5;220m'; RED=$'\e[38;5;203m'
else
  B=""; R=""; DIM=""; V1=""; V2=""; V3=""; V4=""; V5=""; MINT=""; GOLD=""; RED=""
fi

banner() {
  printf '%s\n' \
"${V1}    ███╗   ██╗${V2}██╗   ██╗${V3}██╗  ██╗${V4}██╗   ██╗${V5}███████╗${R}" \
"${V1}    ████╗  ██║${V2}╚██╗ ██╔╝${V3}╚██╗██╔╝${V4}██║   ██║${V5}██╔════╝${R}" \
"${V1}    ██╔██╗ ██║${V2} ╚████╔╝ ${V3} ╚███╔╝ ${V4}██║   ██║${V5}███████╗${R}" \
"${V1}    ██║╚██╗██║${V2}  ╚██╔╝  ${V3} ██╔██╗ ${V4}██║   ██║${V5}╚════██║${R}" \
"${V1}    ██║ ╚████║${V2}   ██║   ${V3}██╔╝ ██╗${V4}╚██████╔╝${V5}███████║${R}" \
"${V1}    ╚═╝  ╚═══╝${V2}   ╚═╝   ${V3}╚═╝  ╚═╝${V4} ╚═════╝ ${V5}╚══════╝${R}" \
"" \
"${DIM}    ◤ ALIEN NEON · IRIDESCENT VOID ◥${R}" \
"${DIM}    silent dark Hyprland desktop · © 2026 JOSEPH A. SIERENGOWSKI${R}" \
""
}

step() { printf "\n${V4}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${MINT}✓${R}  %s\n" "$*"; }
info() { printf "  ${V5}·${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
die()  { printf "  ${RED}✗${R}  %s\n" "$*" >&2; exit 1; }

# ── options ─────────────────────────────────────────────────────────────────
CHECK=false; RELOAD=true; RUN_SYSTEM=true; KEEP_LEGACY_SESSIONS=false
for arg in "$@"; do case "$arg" in
  --check|--dry-run) CHECK=true ;;
  --no-reload)       RELOAD=false ;;
  --system)          RUN_SYSTEM=true ;;
  --user-only)       RUN_SYSTEM=false ;;
  --keep-legacy-sessions) KEEP_LEGACY_SESSIONS=true ;;
  -h|--help)         awk 'NR==1{next} /^#/ {sub(/^# ?/, ""); print; next} {exit}' "${BASH_SOURCE[0]}"; exit 0 ;;
  *) die "unknown option: $arg (try --help)" ;;
esac; done

LAUNCHERS=(
  nyxus
  nyxus-accent-from-wallpaper nyxus-apply-accent nyxus-backup nyxus-beat
  nyxus-beatd nyxus-blackarch-full nyxus-boot-check nyxus-bootstrap nyxus-companion nyxus-crash-report nyxus-drop
  nyxus-dynamic-wallpaper.sh nyxus-eww-cinematic nyxus-eww-launch
  nyxus-eww-launch-safe nyxus-freeform nyxus-gen-backdrop nyxus-ghost
  nyxus-ghost-helper nyxus-glow nyxus-graffiti-wall nyxus-hacker-mode nyxus-home
  nyxus-hotkey nyxus_hotcorners.py nyxus-hub-apps nyxus-hub-close nyxus-hub-launch
  nyxus-hub-open nyxus-hub-search nyxus-launch-bifrost nyxus-launch-meli nyxus-lens nyxus-livewall-flagship
  nyxus-livewall-generate nyxus-live-wallpaper nyxus-living nyxus-lock-art
  nyxus-lock-track nyxus-mission-control-toggle nyxus-mood nyxus-notifications
  nyxus-notif-to-eww nyxus-nowplaying nyxus-overlay-open nyxus-palette-extract nyxus-panic nyxus-stage-system-walls
  nyxus-persist-login
  nyxus-plugins nyxus-plymouth-install nyxus-postinstall nyxus-pulsed nyxus-record
  nyxus-rotate-walls
  nyxus-screensaver nyxus-security nyxus-sense nyxus-session-start nyxus-settings
  nyxus-set-wallpaper nyxus-set-wallpaper.sh nyxus-sfx nyxus-shader
  nyxus-sound nyxus-sound-bake nyxus-supernova nyxus-soundd nyxus-sound-forge nyxus-sounds
  nyxus-spray nyxus-store nyxus-sync-stations nyxus-tint nyxus-tintd
  nyxus-updater nyxus-voice nyxus-voiced nyxus-voice-install
  nyxus-voice-model nyxus-wait-bootstrap nyxus-wall-cycle nyxus-wall-fx
  nyxus-wall-next nyxus-wallpaper-autostart nyxus-weather-line nyxus-welcome nyxus-whispers sync-eww.sh
  nyxus-gamemode nyxus-focusmode
)

declare -A MANIFEST_EWW=() MANIFEST_HYPR=() MANIFEST_NYXUS=() MANIFEST_BIN=() MANIFEST_DESKTOP=()
manifest_add() {
  local map_name="$1" key="$2"
  declare -n map_ref="$map_name"
  map_ref["$key"]=1
}
manifest_has() {
  local map_name="$1" key="$2"
  declare -n map_ref="$map_name"
  [[ -n "${map_ref[$key]+x}" ]]
}
build_manifests() {
  while IFS= read -r -d '' f; do
    manifest_add MANIFEST_EWW "${f#"$NS"/eww/}"
  done < <(find "$NS/eww" -type f -print0)
  for f in hyprland.conf hypridle.conf hyprlock.conf hyprlock-accent.conf hyprpaper.conf; do
    manifest_add MANIFEST_HYPR "$f"
  done
  for f in "$NS"/nyxus-*.conf; do
    [[ -f "$f" ]] || continue
    base="$(basename "$f")"
    case "$base" in
      nyxus-monitors.conf|nyxus-voice.conf) manifest_add MANIFEST_HYPR "$base" ;;
      *)                                    manifest_add MANIFEST_HYPR "conf.d/$base" ;;
    esac
  done
  if [[ -d "$NS/hypr-walls/rotation" ]]; then
    while IFS= read -r -d '' f; do
      manifest_add MANIFEST_HYPR "walls/rotation/${f##*/}"
    done < <(find "$NS/hypr-walls/rotation" -type f -print0)
  fi
  for f in "$NS"/nyxus_*.py; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "nyxus_matrix_saver.py" ]] && continue
    manifest_add MANIFEST_NYXUS "$(basename "$f")"
  done
  for base in "${LAUNCHERS[@]}"; do manifest_add MANIFEST_BIN "$base"; done
  manifest_add MANIFEST_BIN "nyxus-start"  # deployed from nyxus-start/ sub-dir
  while IFS= read -r -d '' f; do
    manifest_add MANIFEST_DESKTOP "$(basename "$f")"
  done < <(find "$NS/desktop-entries" -maxdepth 1 -type f -name '*.desktop' -print0)
}
build_manifests

# copy helper: only writes when content differs (idempotent + fast re-runs)
CHANGED=0
place() { # place <src> <dst> [mode]
  local src="$1" dst="$2" mode="${3:-0644}"
  [[ -f "$src" ]] || { warn "missing in repo: ${src#"$REPO_ROOT"/}"; return 1; }
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then return 0; fi
  if $CHECK; then info "would update ${dst/#$HOME/\~}"; CHANGED=$((CHANGED+1)); return 0; fi
  mkdir -p "$(dirname "$dst")"
  install -m "$mode" "$src" "$dst" && CHANGED=$((CHANGED+1))
}
place_with_backup() { # place_with_backup <src> <dst> <backup-rel> [mode]
  local src="$1" dst="$2" rel="$3" mode="${4:-0644}"
  [[ -f "$src" ]] || { warn "missing in repo: ${src#"$REPO_ROOT"/}"; return 1; }
  if [[ -f "$dst" ]] && ! cmp -s "$src" "$dst"; then
    backup_move "$dst" "$rel"
  fi
  place "$src" "$dst" "$mode"
}

BACKUP_ROOT=""
BACKUP_COUNT=0
BACKUP_PREVIEW_COUNT=0
preserve_hypr_extra() {
  local rel="$1"
  case "$rel" in
    nyxus-monitors.conf|walls/rotation/*) return 0 ;;
    *)                                    return 1 ;;
  esac
}
ensure_backup_root() {
  [[ -n "$BACKUP_ROOT" ]] && return 0
  BACKUP_ROOT="${HOME}/.nyxus-backup-$(date +%Y%m%d-%H%M%S)"
  $CHECK || mkdir -p "$BACKUP_ROOT"
}
prune_empty_parent_dirs() {
  local current="$1" stop="$2"
  while [[ "$current" != "$stop" && "$current" != "/" ]]; do
    if ! rmdir "$current" 2>/dev/null; then
      if [[ ! -d "$current" ]]; then
        warn "parent directory disappeared during pruning: ${current/#$HOME/\~}"
      elif [[ -n "$(find "$current" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
        info "keeping non-empty ${current/#$HOME/\~}"
      else
        warn "could not prune empty ${current/#$HOME/\~}"
      fi
      break
    fi
    current="$(dirname "$current")"
  done
}
backup_move() { # backup_move <src> <home-relative-dest>
  local src="$1" rel="$2" dst_dir
  ensure_backup_root
  if $CHECK; then
    info "would back up ~/${rel#./}"
    BACKUP_PREVIEW_COUNT=$((BACKUP_PREVIEW_COUNT+1))
  else
    dst_dir="${BACKUP_ROOT}/$(dirname "$rel")"
    mkdir -p "$dst_dir"
    mv "$src" "${BACKUP_ROOT}/${rel}"
    BACKUP_COUNT=$((BACKUP_COUNT+1))
  fi
}
purge_unmanaged_tree() { # purge_unmanaged_tree <root> <prefix> <manifest> [mode]
  local root="$1" prefix="$2" manifest="$3" mode="${4:-generic}" path rel
  [[ -d "$root" ]] || return 0
  while IFS= read -r -d '' path; do
    rel="${path#"$root"/}"
    [[ "$mode" == "hypr" ]] && preserve_hypr_extra "$rel" && continue
    if ! manifest_has "$manifest" "$rel"; then
      backup_move "$path" "${prefix}/${rel}"
      $CHECK || prune_empty_parent_dirs "$(dirname "$path")" "$root"
    fi
  done < <(find "$root" -mindepth 1 \( -type f -o -type l \) -print0)
}
purge_unmanaged_matches() { # purge_unmanaged_matches <dir> <glob> <prefix> <manifest>
  local dir="$1" glob_pat="$2" prefix="$3" manifest="$4" path base
  [[ -d "$dir" ]] || return 0
  while IFS= read -r -d '' path; do
    base="$(basename "$path")"
    if ! manifest_has "$manifest" "$base"; then
      backup_move "$path" "${prefix}/${base}"
    fi
  done < <(find "$dir" -maxdepth 1 \( -type f -o -type l \) -name "$glob_pat" -print0)
}
VERIFY_TOTAL=0
VERIFY_MATCHED=0
VERIFY_MISMATCHES=()
verify_pair() { # verify_pair <src> <dst>
  local src="$1" dst="$2"
  VERIFY_TOTAL=$((VERIFY_TOTAL+1))
  if [[ -f "$dst" ]] && cmp -s "$src" "$dst"; then
    VERIFY_MATCHED=$((VERIFY_MATCHED+1))
  else
    VERIFY_MISMATCHES+=("${dst/#$HOME/\~}")
  fi
}

banner
$CHECK && warn "CHECK MODE — nothing will be written"

# ── 1 · dependency check ────────────────────────────────────────────────────
step "1/6 · dependency check"
[[ -d "$NS" ]] || die "run from a Nyxus-Core clone (missing artifacts/…/nyxus-scripts)"
missing=()
for c in hyprctl eww grim jq python3; do
  command -v "$c" >/dev/null 2>&1 && ok "$c $(command -v "$c")" || { missing+=("$c"); warn "$c NOT FOUND"; }
done
command -v sass >/dev/null 2>&1 || command -v npx >/dev/null 2>&1 \
  && ok "sass/npx (CSS compile)" || { missing+=(sass); warn "sass or npx NOT FOUND (eww CSS compile)"; }
if (( ${#missing[@]} )); then
  warn "install missing deps first, e.g.: sudo pacman -S --needed hyprland eww grim jq dart-sass"
  warn "continuing — configs will still be placed, some features degrade"
fi

# ── 2 · purge stale state ───────────────────────────────────────────────────
step "2/6 · purge stale NYXUS-managed state"
purge_unmanaged_tree "$HOME/.config/eww" ".config/eww" MANIFEST_EWW
purge_unmanaged_tree "$HOME/.config/hypr" ".config/hypr" MANIFEST_HYPR hypr
purge_unmanaged_tree "$HOME/.nyxus" ".nyxus" MANIFEST_NYXUS
purge_unmanaged_matches "$HOME/.local/bin" 'nyxus-*' ".local/bin" MANIFEST_BIN
purge_unmanaged_matches "$HOME/.local/share/applications" 'nyxus-*.desktop' ".local/share/applications" MANIFEST_DESKTOP
BACKUP_FOUND=$BACKUP_COUNT
$CHECK && BACKUP_FOUND=$BACKUP_PREVIEW_COUNT
if (( BACKUP_FOUND == 0 )); then
  ok "no stale NYXUS-managed files found"
else
  ok "$BACKUP_FOUND stale file(s)$($CHECK && printf ' would be') backed up before deploy"
fi

# ── 3 · deploy: live config surfaces ────────────────────────────────────────
step "3/6 · deploy configs → live surfaces"

# eww (bars, Hub, OSDs, flyouts, theme)
n=0
while IFS= read -r -d '' f; do
  rel="${f#"$NS"/eww/}"
  place "$f" "$HOME/.config/eww/$rel" && n=$((n+1)) || true
done < <(find "$NS/eww" -type f -print0)
ok "eww → ~/.config/eww  ($n files checked)"

# hyprland (core + conf.d + shaders ride along in repo hyprland tree)
for f in hyprland.conf hypridle.conf hyprlock.conf hyprlock-accent.conf hyprpaper.conf; do
  place "$NS/$f" "$HOME/.config/hypr/$f" || true
done
for f in "$NS"/nyxus-*.conf; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  case "$base" in
    nyxus-monitors.conf) dst="$HOME/.config/hypr/$base" ;;  # per-machine, but seed if absent
    nyxus-voice.conf)    dst="$HOME/.config/hypr/$base" ;;  # sourced from hypr root, not conf.d
    *)                   dst="$HOME/.config/hypr/conf.d/$base" ;;
  esac
  if [[ "$base" == nyxus-monitors.conf && -f "$dst" ]]; then continue; fi
  place "$f" "$dst" || true
done
# Hyprland `env = PATH,…` is a RAW string — $HOME does not expand and breaks
# every bare nyxus-* bind. Stamp the installing user's real home into the
# live hyprland.conf (fixes leftover `$HOME`, placeholders, or foreign homes).
if [[ -f "$HOME/.config/hypr/hyprland.conf" ]]; then
  if $CHECK; then
    info "would stamp PATH home → $HOME in ~/.config/hypr/hyprland.conf"
  else
    sed -i \
      -e "s|__NYXUS_HOME__|$HOME|g" \
      -e "s|env = PATH,\$HOME/|env = PATH,$HOME/|g" \
      "$HOME/.config/hypr/hyprland.conf"
    # Normalize any /home/<user>/ prefixes on the PATH line to this $HOME.
    # (Safe for the cosmic reference machine: /home/cosmic → /home/cosmic.)
    python3 - "$HOME" "$HOME/.config/hypr/hyprland.conf" <<'PY' || true
import re, sys
home, path = sys.argv[1], sys.argv[2]
text = open(path).read()
def fix_line(m):
    line = m.group(0)
    line = re.sub(r'/home/[^/]+/', home.rstrip('/') + '/', line)
    return line
text2, n = re.subn(r'(?m)^env = PATH,.*$', fix_line, text, count=1)
if n and text2 != text:
    open(path, 'w').write(text2)
PY
  fi
fi
ok "hyprland → ~/.config/hypr (+conf.d)"

# launcher/bin scripts → ~/.local/bin. CURATED manifest — the exact launcher
# set the reference machine runs (verified live 2026-07-15). Do NOT glob the
# whole scripts dir: it also holds assets (.tgz/.mp4/.service) that must
# never land on PATH.
n=0
for base in "${LAUNCHERS[@]}"; do
  place "$NS/$base" "$HOME/.local/bin/$base" 0755 && n=$((n+1)) || true
done
ok "launchers → ~/.local/bin  ($n scripts checked)"

# NYXUS python app suite → ~/.nyxus (+ thin launchers)
n=0
for f in "$NS"/nyxus_*.py; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  [[ "$base" == nyxus_matrix_saver.py ]] && continue  # ships to ~/.config/nyxus below
  place "$f" "$HOME/.nyxus/$base" 0755 && n=$((n+1)) || true
done
ok "app suite → ~/.nyxus  ($n apps checked)"

# nyxus-start GTK app → ~/.nyxus/nyxus-start/ + launcher → ~/.local/bin/nyxus-start
if [[ -d "$NS/nyxus-start" ]]; then
  mkdir -p "$HOME/.nyxus/nyxus-start"
  n=0
  for f in "$NS/nyxus-start"/*.py "$NS/nyxus-start/nyxus-palette.css"; do
    [[ -f "$f" ]] || continue
    place "$f" "$HOME/.nyxus/nyxus-start/$(basename "$f")" && n=$((n+1)) || true
  done
  place "$NS/nyxus-start/nyxus-start" "$HOME/.local/bin/nyxus-start" 0755 || true
  ok "nyxus-start app → ~/.nyxus/nyxus-start  ($n files) + launcher → ~/.local/bin/nyxus-start"
fi

# idle screensavers → ~/.config/nyxus/ (the path hypridle + nyxus-screensaver
# expect; see docs/THEME.md). nyxus_screensaver.py is the alien-wallpaper saver
# (default); nyxus_matrix_saver.py is the matrix-rain fallback.
place "$NS/nyxus_screensaver.py"   "$HOME/.config/nyxus/nyxus_screensaver.py"   0755 || true
place "$NS/nyxus_matrix_saver.py"  "$HOME/.config/nyxus/nyxus_matrix_saver.py"  0755 || true
ok "screensavers → ~/.config/nyxus/ (alien-wallpaper + matrix-rain)"

# canonical NYXUS runtime config bundle (stations/accent/wallpaper/profile).
# Back up user edits before overwrite so re-runs stay reversible.
NYXUS_CFG_SRC="${REPO_ROOT}/artifacts/nyxus-config"
if [[ -d "$NYXUS_CFG_SRC" ]]; then
  n=0
  for base in stations.json stations-hacker.json accent.json wallpaper.conf; do
    [[ -f "$NYXUS_CFG_SRC/$base" ]] || continue
    place_with_backup "$NYXUS_CFG_SRC/$base" \
      "$HOME/.config/nyxus/$base" \
      ".config/nyxus/$base" && n=$((n+1)) || true
  done
  if [[ -d "$NYXUS_CFG_SRC/hw_profiles" ]]; then
    while IFS= read -r -d '' f; do
      rel="${f#"$NYXUS_CFG_SRC"/}"
      place_with_backup "$f" "$HOME/.config/nyxus/$rel" ".config/nyxus/$rel" && n=$((n+1)) || true
    done < <(find "$NYXUS_CFG_SRC/hw_profiles" -type f -print0)
  fi
  if $CHECK; then
    info "would regenerate ~/.config/nyxus/workspaces.json from stations.json"
    ok "nyxus config → ~/.config/nyxus  ($n files checked)"
  elif [[ -x "$HOME/.local/bin/nyxus-sync-stations" && -f "$HOME/.config/nyxus/stations.json" ]]; then
    if "$HOME/.local/bin/nyxus-sync-stations" >/dev/null 2>&1; then
      ok "nyxus config → ~/.config/nyxus  ($n files checked) + workspaces.json regenerated"
    else
      warn "nyxus config copied but workspaces.json regen failed — check jq / stations.json"
      ok "nyxus config → ~/.config/nyxus  ($n files checked)"
    fi
  else
    ok "nyxus config → ~/.config/nyxus  ($n files checked)"
  fi
fi

# Curated wallpaper-rotation list (alien / NYXUS-HYPRLAND / sierengowski set
# that the desktop + lock + login rotate through). SEED ONLY — never clobber
# the user's edited pick list on re-run.
if [[ -f "$NS/wall-rotation.list" && ! -f "$HOME/.config/nyxus/wall-rotation.list" ]]; then
  place "$NS/wall-rotation.list" "$HOME/.config/nyxus/wall-rotation.list" || true
  ok "wall-rotation list → ~/.config/nyxus/wall-rotation.list (seeded)"
fi

# ~/.bashrc — NYXUS shell greeting (random-neon-glow line) + `glow` helper.
# SEED ONLY: never clobber a user's existing ~/.bashrc.
if [[ -f "$NS/bashrc" && ! -f "$HOME/.bashrc" ]]; then
  place "$NS/bashrc" "$HOME/.bashrc" || true
  ok "shell greeting → ~/.bashrc (seeded)"
fi

# Hyprland helper scripts → ~/.config/hypr/scripts/ (idle-glass, pulse halo,
# lens zoom, prism-pulse, daily-line). Canonical source is the ISO skel tree,
# so the installed system matches the ISO exactly. Referenced by hyprland.conf
# + conf.d shards; without these the eye-candy binds silently no-op.
HYPR_SCRIPTS_SRC="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/scripts"
if [[ -d "$HYPR_SCRIPTS_SRC" ]]; then
  n=0
  for f in "$HYPR_SCRIPTS_SRC"/*.sh; do
    [[ -f "$f" ]] || continue
    place "$f" "$HOME/.config/hypr/scripts/$(basename "$f")" 0755 && n=$((n+1)) || true
  done
  ok "hypr scripts → ~/.config/hypr/scripts  ($n scripts)"
fi

# .desktop entries (Hub tiles / launcher discover apps through these).
n=0
for f in "$NS"/desktop-entries/*.desktop; do
  [[ -f "$f" ]] || continue
  place "$f" "$HOME/.local/share/applications/$(basename "$f")" && n=$((n+1)) || true
done
ok "desktop entries → ~/.local/share/applications  ($n files checked)"

# wallpapers — full NYXUS set → ~/.config/hypr/walls (matches the ISO skel,
# which ships all of them there). Canonical source is the ISO skel tree so an
# install.sh machine matches a fresh ISO exactly. This includes the default
# wallpaper (nyxus-urban-alien) + the alien walls the screensaver, hyprlock
# and Hacker Mode reference; without it those fell back to a flat colour.
# place() is idempotent (skips unchanged), so re-runs are cheap. User-added
# wallpapers under walls/rotation/ are preserved (handled separately below).
WALLS_SRC="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/walls"
n=0
if [[ -d "$WALLS_SRC" ]]; then
  for f in "$WALLS_SRC"/*.png; do
    [[ -f "$f" ]] || continue
    place "$f" "$HOME/.config/hypr/walls/$(basename "$f")" && n=$((n+1)) || true
  done
fi
ok "wallpapers → ~/.config/hypr/walls  ($n files checked)"
# explicit user-surface mirrors for hacker-mode fallback logic
for base in nyxus-urban-alien.png nyxus-login-wall.png nyxus-desktop-hero.png; do
  [[ -f "$WALLS_SRC/$base" ]] || continue
  place "$WALLS_SRC/$base" "$HOME/.config/hypr/walls/$base" || true
done

# wallpapers (rotation set; repo files replaced, user additions kept)
n=0
for f in "$NS"/hypr-walls/rotation/*.png; do
  [[ -f "$f" ]] || continue
  dst="$HOME/.config/hypr/walls/rotation/$(basename "$f")"
  place "$f" "$dst" && n=$((n+1)) || true
done
ok "wallpaper rotation → ~/.config/hypr/walls/rotation  ($n files checked)"

# ── 4 · compile theme CSS (GTK-strict, no grey fallback) ────────────────────
step "4/6 · compile eww theme"
if $CHECK; then
  info "would run ~/.config/eww/scripts/compile-eww-css.sh"
elif [[ -x "$HOME/.config/eww/scripts/compile-eww-css.sh" ]]; then
  if "$HOME/.config/eww/scripts/compile-eww-css.sh" >/dev/null 2>&1 \
     && [[ -f "$HOME/.config/eww/eww.css" ]] \
     && ! head -1 "$HOME/.config/eww/eww.css" | grep -q '@charset'; then
    ok "eww.css compiled clean (no @charset / grey-fallback poison)"
  else
    warn "CSS compile failed — bars will use the last known-good eww.css"
  fi
else
  warn "compile-eww-css.sh not executable — skipped"
fi

# ── 5 · reload the live session (if one is running) ────────────────────────
step "5/6 · reload live session"
if $CHECK; then
  info "would reload hyprland config + relaunch bars via nyxus-eww-launch-safe"
elif ! $RELOAD; then
  info "skipped (--no-reload) — changes apply on next login"
elif [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] || hyprctl monitors >/dev/null 2>&1; then
  hyprctl reload >/dev/null 2>&1 && ok "hyprland config reloaded" || warn "hyprctl reload failed"
  if [[ -x "$HOME/.local/bin/nyxus-eww-launch-safe" ]]; then
    "$HOME/.local/bin/nyxus-eww-launch-safe" >/dev/null 2>&1 \
      && ok "eww bars relaunched (single daemon, 4 bars)" \
      || warn "bar relaunch reported issues — run nyxus-eww-launch-safe manually"
  fi
else
  info "no running Hyprland session — changes apply on next login"
fi

# ── 6 · verify + system phase ───────────────────────────────────────────────
step "6/6 · verify deploy"
while IFS= read -r -d '' f; do
  verify_pair "$f" "$HOME/.config/eww/${f#"$NS"/eww/}"
done < <(find "$NS/eww" -type f -print0)
for f in hyprland.conf hypridle.conf hyprlock.conf hyprlock-accent.conf hyprpaper.conf; do
  verify_pair "$NS/$f" "$HOME/.config/hypr/$f"
done
for f in "$NS"/nyxus-*.conf; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  [[ "$base" == "nyxus-monitors.conf" ]] && continue
  case "$base" in
    nyxus-voice.conf) verify_pair "$f" "$HOME/.config/hypr/$base" ;;
    *)                verify_pair "$f" "$HOME/.config/hypr/conf.d/$base" ;;
  esac
done
for f in "$NS"/hypr-walls/rotation/*.png; do
  [[ -f "$f" ]] || continue
  verify_pair "$f" "$HOME/.config/hypr/walls/rotation/$(basename "$f")"
done
if [[ -d "$WALLS_SRC" ]]; then
  for f in "$WALLS_SRC"/*.png; do
    [[ -f "$f" ]] || continue
    verify_pair "$f" "$HOME/.config/hypr/walls/$(basename "$f")"
  done
fi
for base in "${LAUNCHERS[@]}"; do
  [[ -f "$NS/$base" ]] || continue
  verify_pair "$NS/$base" "$HOME/.local/bin/$base"
done
# nyxus-start launcher (deployed from nyxus-start/ sub-dir)
if [[ -f "$NS/nyxus-start/nyxus-start" ]]; then
  verify_pair "$NS/nyxus-start/nyxus-start" "$HOME/.local/bin/nyxus-start"
fi
for f in "$NS"/nyxus_*.py; do
  [[ -f "$f" ]] || continue
  [[ "$(basename "$f")" == "nyxus_matrix_saver.py" ]] && continue
  verify_pair "$f" "$HOME/.nyxus/$(basename "$f")"
done
verify_pair "$NS/nyxus_matrix_saver.py" "$HOME/.config/nyxus/nyxus_matrix_saver.py"
if [[ -d "$NYXUS_CFG_SRC" ]]; then
  for base in stations.json stations-hacker.json accent.json wallpaper.conf; do
    [[ -f "$NYXUS_CFG_SRC/$base" ]] || continue
    verify_pair "$NYXUS_CFG_SRC/$base" "$HOME/.config/nyxus/$base"
  done
  if [[ -d "$NYXUS_CFG_SRC/hw_profiles" ]]; then
    while IFS= read -r -d '' f; do
      rel="${f#"$NYXUS_CFG_SRC"/}"
      verify_pair "$f" "$HOME/.config/nyxus/$rel"
    done < <(find "$NYXUS_CFG_SRC/hw_profiles" -type f -print0)
  fi
fi
for f in "$NS"/desktop-entries/*.desktop; do
  [[ -f "$f" ]] || continue
  verify_pair "$f" "$HOME/.local/share/applications/$(basename "$f")"
done

SYSTEM_ARGS=(--yes --skip-user-config)
$KEEP_LEGACY_SESSIONS && SYSTEM_ARGS+=(--keep-legacy-sessions)
if $RUN_SYSTEM; then
  step "system phase (packages / sessions / greeter)"
  if $CHECK; then
    info "dry-run preview does not require sudo authentication"
    bash "${REPO_ROOT}/scripts/nyxus-install.sh" --dry-run "${SYSTEM_ARGS[@]}" || die "system phase dry-run failed"
  else
    sudo -v || die "sudo authentication failed"
    bash "${REPO_ROOT}/scripts/nyxus-install.sh" "${SYSTEM_ARGS[@]}" || die "system phase failed"
  fi
else
  info "system phase skipped (--user-only)"
  warn "--user-only leaves system security components untouched (jeTT daemon, Bifrost, Meli/Grafana services)"
fi

if $CHECK; then
  ok "check complete — ${CHANGED} file(s) would change"
  ok "managed-file checksum verification is skipped in check mode"
else
  ok "deploy complete — ${CHANGED} file(s) updated (identical files untouched)"
  if (( VERIFY_MATCHED == VERIFY_TOTAL )); then
    ok "managed-file checksums match repo (${VERIFY_MATCHED}/${VERIFY_TOTAL})"
  else
    warn "managed-file checksum mismatches: ${VERIFY_MATCHED}/${VERIFY_TOTAL} matched repo"
    warn "mismatched paths: ${VERIFY_MISMATCHES[*]:0:8}"
  fi
fi
BACKUP_FOUND=$BACKUP_COUNT
$CHECK && BACKUP_FOUND=$BACKUP_PREVIEW_COUNT
if (( BACKUP_FOUND == 0 )); then
  info "backup: none needed (no stale NYXUS-managed files)"
else
  info "backup: ${BACKUP_ROOT}"
fi
info "surfaces: ~/.config/eww · ~/.config/hypr · ~/.local/bin · ~/.nyxus"
info "          ~/.config/nyxus (stations + wallpaper + screensavers) · ~/.local/share/applications"
printf "\n${V5}${B}  ◆ NYXUS ready.${R} ${DIM}Run ./install.sh again anytime; clean systems converge without backup churn.${R}\n\n"

#!/usr/bin/env bash
# ============================================================================
#  NYXUS — terminal installer                        rev 2026-07-15 (RC)
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Deploys the NYXUS Hyprland desktop from this repo's canonical tree onto
#  the LIVE user surfaces — the exact same fixed state that was verified on
#  the reference machine. This kills the "fixed in repo but not on my
#  machine" class of bugs for fresh installs and re-runs alike.
#
#    ./install.sh                 # user-level deploy (no sudo needed)
#    ./install.sh --check         # preview: show what would change, touch nothing
#    ./install.sh --no-reload     # deploy but don't reload the running session
#    ./install.sh --system        # ALSO run the full system installer
#                                 # (packages/greeter/kernel — needs sudo,
#                                 #  delegates to scripts/nyxus-install.sh)
#
#  Idempotent and safe to re-run: files are only replaced, never deleted;
#  your personal data (~/.config/nyxus state, notes, wallpapers you added)
#  is never touched. Non-interactive by default — no prompts.
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
"${DIM}    ◤ OBSIDIAN PRISM · IRIDESCENT VOID ◥${R}" \
"${DIM}    silent dark Hyprland desktop · © 2026 JOSEPH SIERENGOWSKI${R}" \
""
}

step() { printf "\n${V4}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${MINT}✓${R}  %s\n" "$*"; }
info() { printf "  ${V5}·${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
die()  { printf "  ${RED}✗${R}  %s\n" "$*" >&2; exit 1; }

# ── options ─────────────────────────────────────────────────────────────────
CHECK=false; RELOAD=true; SYSTEM=false
for arg in "$@"; do case "$arg" in
  --check|--dry-run) CHECK=true ;;
  --no-reload)       RELOAD=false ;;
  --system)          SYSTEM=true ;;
  -h|--help)         sed -n '3,21p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) die "unknown option: $arg (try --help)" ;;
esac; done

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

banner
$CHECK && warn "CHECK MODE — nothing will be written"

# ── 1 · dependency check ────────────────────────────────────────────────────
step "1/5 · dependency check"
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

# ── 2 · deploy: live config surfaces ────────────────────────────────────────
step "2/5 · deploy configs → live surfaces"

# eww (bars, Hub, OSDs, flyouts, theme)
n=0
while IFS= read -r -d '' f; do
  rel="${f#"$NS"/eww/}"
  place "$f" "$HOME/.config/eww/$rel" && n=$((n+1)) || true
done < <(find "$NS/eww" -type f -print0)
ok "eww → ~/.config/eww  ($n files checked)"

# hyprland (core + conf.d + shaders ride along in repo hyprland tree)
for f in hyprland.conf hypridle.conf hyprlock.conf hyprpaper.conf; do
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
ok "hyprland → ~/.config/hypr (+conf.d)"

# launcher/bin scripts → ~/.local/bin. CURATED manifest — the exact launcher
# set the reference machine runs (verified live 2026-07-15). Do NOT glob the
# whole scripts dir: it also holds assets (.tgz/.mp4/.service) that must
# never land on PATH.
LAUNCHERS=(
  nyxus-accent-from-wallpaper nyxus-apply-accent nyxus-backup nyxus-beat
  nyxus-beatd nyxus-bootstrap nyxus-companion nyxus-crash-report nyxus-drop
  nyxus-dynamic-wallpaper.sh nyxus-eww-cinematic nyxus-eww-launch
  nyxus-eww-launch-safe nyxus-freeform nyxus-gen-backdrop nyxus-home
  nyxus_hotcorners.py nyxus-hub-apps nyxus-hub-close nyxus-hub-launch
  nyxus-hub-open nyxus-hub-search nyxus-lens nyxus-livewall-flagship
  nyxus-livewall-generate nyxus-live-wallpaper nyxus-living nyxus-lock-art
  nyxus-lock-track nyxus-mission-control-toggle nyxus-notifications
  nyxus-notif-to-eww nyxus-nowplaying nyxus-palette-extract nyxus-plugins
  nyxus-plymouth-install nyxus-postinstall nyxus-pulsed nyxus-record
  nyxus-screensaver nyxus-security nyxus-session-start nyxus-settings
  nyxus-set-wallpaper nyxus-set-wallpaper.sh nyxus-sfx nyxus-shader
  nyxus-sound nyxus-sound-bake nyxus-soundd nyxus-sound-forge nyxus-sounds
  nyxus-spray nyxus-store nyxus-sync-stations nyxus-tint nyxus-tintd
  nyxus-updater nyxus-voice nyxus-voiced nyxus-voice-install
  nyxus-voice-model nyxus-wait-bootstrap nyxus-wall-cycle nyxus-wall-fx
  nyxus-wall-next nyxus-weather-line nyxus-welcome sync-eww.sh
)
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

# alien matrix-rain screensaver → ~/.config/nyxus/ (the path hypridle +
# nyxus-screensaver expect; see docs/THEME.md)
place "$NS/nyxus_matrix_saver.py" "$HOME/.config/nyxus/nyxus_matrix_saver.py" 0755 || true
ok "matrix screensaver → ~/.config/nyxus/nyxus_matrix_saver.py"

# .desktop entries (Hub tiles / launcher discover apps through these).
# SEED-IF-ABSENT: existing user entries may carry machine-local fixes
# (X-Nyxus-Override) with absolute paths — never clobber those.
n=0
for f in "$NS"/desktop-entries/*.desktop; do
  [[ -f "$f" ]] || continue
  dst="$HOME/.local/share/applications/$(basename "$f")"
  [[ -f "$dst" ]] && continue
  place "$f" "$dst" && n=$((n+1)) || true
done
ok "desktop entries seeded → ~/.local/share/applications  ($n new)"

# wallpapers (rotation set; only seeds missing files — user additions kept)
n=0
for f in "$NS"/hypr-walls/rotation/*.png; do
  [[ -f "$f" ]] || continue
  dst="$HOME/.config/hypr/walls/rotation/$(basename "$f")"
  [[ -f "$dst" ]] || { place "$f" "$dst" && n=$((n+1)) || true; }
done
ok "wallpaper rotation seeded ($n new)"

# ── 3 · compile theme CSS (GTK-strict, no grey fallback) ────────────────────
step "3/5 · compile eww theme"
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

# ── 4 · reload the live session (if one is running) ────────────────────────
step "4/5 · reload live session"
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

# ── 5 · summary ─────────────────────────────────────────────────────────────
step "5/5 · post-install summary"
if $CHECK; then
  ok "check complete — ${CHANGED} file(s) would change"
else
  ok "deploy complete — ${CHANGED} file(s) updated (identical files untouched)"
fi
info "surfaces: ~/.config/eww · ~/.config/hypr · ~/.local/bin · ~/.nyxus"
info "          ~/.config/nyxus (screensaver) · ~/.local/share/applications"
if $SYSTEM; then
  step "system installer (packages / greeter / kernel — sudo)"
  exec bash "${REPO_ROOT}/scripts/nyxus-install.sh" --yes
fi
printf "\n${V5}${B}  ◆ NYXUS ready.${R} ${DIM}Log in via 'NYXUS (Hyprland)' — or you're already home.${R}\n\n"

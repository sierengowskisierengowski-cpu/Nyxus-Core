#!/usr/bin/env bash
# ============================================================
#  NYXUS — Daily Driver live preview harness
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Provisions a SECOND, throwaway user account whose home carries the
#  urban-neon "Daily Driver" theme, so the owner can log out, pick that
#  user at the greeter, and look at the new desktop next to the real one
#  — without rebaking an ISO and without touching their own account.
#
#  WHY A SECOND ACCOUNT and not a second session entry:
#  the theme IS a set of per-user files at fixed paths under ~/.config
#  (nyxus/accent.json, nyxus/wallpaper.conf, hypr/, eww/, gtk-*). Two
#  sessions sharing one $HOME would fight over those paths, and
#  `nyxus-apply-accent` rewrites ~25 of them globally per run. A separate
#  user gets a separate ~/.config for free — genuine isolation, and the
#  primary account is unreachable from here by construction.
#
#  WHAT IT WRITES OUTSIDE THE PREVIEW HOME — the complete list:
#    /etc/passwd, /etc/shadow, /etc/group  (useradd / usermod / chpasswd)
#  That is all. No system theme file, no /etc/greetd, no /usr/share is
#  touched. See "the greeter caveat" in docs/DAILY_PREVIEW_HARNESS.md.
#
#  Usage (run from the repo, as root):
#    sudo bash scripts/nyxus-daily-preview.sh              # create / refresh
#    bash scripts/nyxus-daily-preview.sh --dry-run         # no root needed
#    sudo bash scripts/nyxus-daily-preview.sh --remove     # tear it down
#
#  Re-running is the refresh path: it re-lays the preview home from the
#  CURRENT repo contents every time, which is the whole point — the Daily
#  theme is still being authored and the owner wants to see each pass.
# ============================================================
set -euo pipefail

# ── Colours (same vocabulary as iso-builder/build-iso.sh) ────────────────
B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'
DIM=$'\e[2m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }
note() { printf "     ${DIM}%s${R}\n" "$*"; }
die()  { fail "$*"; exit 1; }

# ── Defaults ─────────────────────────────────────────────────────────────
PREVIEW_USER="nyxdaily"
PREVIEW_PASS=""            # defaults to the username; --password overrides
DRY_RUN=0
DO_REMOVE=0
ASSUME_YES=0
WANT_WHEEL=1
RUN_BOOTSTRAP=0            # default: pre-mark bootstrapped, see below

# The group set the NYXUS desktop actually needs, lifted verbatim from
# iso-builder/nyx-profile/airootfs/root/customize_airootfs.sh, which creates
# the real `nyx` user with:
#   useradd -m -G wheel,audio,video,input,storage,network,uucp -s /bin/bash nyx
# Get this wrong and the preview session comes up with no audio, no input
# devices and no GPU access, which reads as "the new theme is broken".
NYX_GROUPS=(wheel audio video input storage network uucp)

usage() {
  cat <<'EOF'
nyxus-daily-preview.sh — provision a preview account carrying the Daily theme

  sudo bash scripts/nyxus-daily-preview.sh [options]

  --user NAME        preview account name          (default: nyxdaily)
  --password PW      password set ON CREATION only (default: the username)
  --no-wheel         leave the preview account out of `wheel` (no sudo)
  --with-bootstrap   let nyxus-bootstrap run on first login (see note below)
  --dry-run          print every action, change nothing, no root required
  --remove           delete the preview account and its home
  --yes              skip the confirmation prompt on --remove
  -h, --help         this text

  Bootstrap: by default the preview home is pre-marked as bootstrapped, so
  nyxus-bootstrap no-ops. It is skipped because nyxus_install.sh calls plain
  `sudo pacman -S` in several places, and on a fingerprint-only sudo box that
  blocks on an invisible auth prompt inside the login sequence. The preview
  is for looking at the THEME; pass --with-bootstrap if you want the full
  first-boot app install to run in the preview account too.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)           PREVIEW_USER="${2:?--user needs a name}"; shift 2 ;;
    --password)       PREVIEW_PASS="${2:?--password needs a value}"; shift 2 ;;
    --no-wheel)       WANT_WHEEL=0; shift ;;
    --with-bootstrap) RUN_BOOTSTRAP=1; shift ;;
    --dry-run)        DRY_RUN=1; shift ;;
    --remove)         DO_REMOVE=1; shift ;;
    --yes|-y)         ASSUME_YES=1; shift ;;
    -h|--help)        usage; exit 0 ;;
    *)                usage >&2; die "unknown argument: $1" ;;
  esac
done

: "${PREVIEW_PASS:=${PREVIEW_USER}}"
(( WANT_WHEEL )) || NYX_GROUPS=("${NYX_GROUPS[@]/wheel}")

# `run` is the single choke point between "say it" and "do it". Every
# mutating command goes through it, so --dry-run is exhaustive by
# construction rather than by remembering to add prints.
run() {
  if (( DRY_RUN )); then
    local shown="" a
    for a in "$@"; do
      case "${a}" in
        *[[:space:]]*) shown+=" '${a}'" ;;
        *)             shown+=" ${a}"   ;;
      esac
    done
    printf "  ${GOLD}dry${R} %s\n" "${shown}"
  else
    "$@"
  fi
}

# Same as `run`, but silent under --dry-run. For bulk loops of a hundred
# near-identical installs, where printing every line buries the things that
# actually need reading. The caller prints the count instead.
runq() {
  (( DRY_RUN )) || "$@"
}

# Run a command AS the preview user, with HOME pointed at the preview home and
# a PATH that finds the preview's own tool layer first. Everything the NYXUS
# tools do is keyed off HOME, so this is how the preview account's own copies
# get used and nothing lands root-owned.
_as_preview() {
  if (( DRY_RUN )); then
    printf "  ${GOLD}dry${R} runuser -u %s -- env HOME=%s %s\n" \
           "${PREVIEW_USER}" "${PREVIEW_HOME}" "$*"
    return 0
  fi
  local env_args=(
    "HOME=${PREVIEW_HOME}"
    "USER=${PREVIEW_USER}"
    "LOGNAME=${PREVIEW_USER}"
    "PATH=${PREVIEW_HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin"
  )
  if command -v runuser >/dev/null 2>&1; then
    runuser -u "${PREVIEW_USER}" -- env "${env_args[@]}" "$@"
  else
    su -s /bin/bash "${PREVIEW_USER}" -c \
       "env $(printf '%q ' "${env_args[@]}") $(printf '%q ' "$@")"
  fi
}

# ── Repo layout ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKEL_SRC="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/etc/skel"
EDITION_SRC="${REPO_ROOT}/artifacts/nyxus-config/editions/daily"
WALLS_SRC="${REPO_ROOT}/iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus"
APPLY_ACCENT="${REPO_ROOT}/artifacts/api-server/nyxus-scripts/nyxus-apply-accent"
BOOTSTRAP_SRC="${REPO_ROOT}/artifacts/api-server/nyxus-scripts/nyxus-bootstrap"

# The four walls approved 2026-08-01 (product brief §4). They ship from the
# profile; the preview account needs them reachable from its own home
# because this machine's /usr/share/backgrounds/nyxus predates them.
DAILY_WALLS=(
  nyxus-urban-flower-wall
  nyxus-urban-flower-concrete
  nyxus-urban-astronaut-moonwalk
  nyxus-hero-cosmic
)

# ── Who is asking ────────────────────────────────────────────────────────
INVOKER="${SUDO_USER:-${USER:-${LOGNAME:-root}}}"
INVOKER_HOME="$(getent passwd "${INVOKER}" 2>/dev/null | cut -d: -f6 || true)"

printf "\n${B}${PURPLE}NYXUS — Daily Driver preview harness${R}\n"
printf "${DIM}  repo      %s${R}\n" "${REPO_ROOT}"
printf "${DIM}  invoked by %s${R}\n" "${INVOKER}"
(( DRY_RUN )) && printf "${GOLD}  DRY RUN — nothing will be changed${R}\n"

# ════════════════════════════════════════════════════════════════════════
#  GUARDS — the primary account must be unreachable from this script
# ════════════════════════════════════════════════════════════════════════
step "guards"

# 1. Never the invoker, never nyx, never root, never a system account.
[[ "${PREVIEW_USER}" == "root" ]] && die "refusing: target account is root"
[[ "${PREVIEW_USER}" == "nyx"  ]] && die "refusing: 'nyx' is the NYXUS primary account, not a preview account"
if [[ "${PREVIEW_USER}" == "${INVOKER}" ]]; then
  die "refusing: target account '${PREVIEW_USER}' is the account invoking this script"
fi

TARGET_EXISTS=0
TARGET_UID=""
PREVIEW_HOME="/home/${PREVIEW_USER}"
if getent passwd "${PREVIEW_USER}" >/dev/null 2>&1; then
  TARGET_EXISTS=1
  TARGET_UID="$(getent passwd "${PREVIEW_USER}" | cut -d: -f3)"
  PREVIEW_HOME="$(getent passwd "${PREVIEW_USER}" | cut -d: -f6)"
  # 2. uid 1000 is the primary desktop user on every NYXUS install, and
  #    anything below 1000 is a system account. Neither is a preview target.
  [[ "${TARGET_UID}" == "1000" ]] && die "refusing: '${PREVIEW_USER}' is uid 1000 — that is the primary desktop account"
  (( TARGET_UID < 1000 ))         && die "refusing: '${PREVIEW_USER}' is uid ${TARGET_UID} — a system account"
  if (( DO_REMOVE )); then
    ok "account '${PREVIEW_USER}' exists (uid ${TARGET_UID}, home ${PREVIEW_HOME})"
  else
    ok "account '${PREVIEW_USER}' exists (uid ${TARGET_UID}, home ${PREVIEW_HOME}) — this run REFRESHES it"
  fi
elif (( DO_REMOVE )); then
  ok "account '${PREVIEW_USER}' does not exist"
else
  ok "account '${PREVIEW_USER}' does not exist — this run CREATES it"
fi

# 3. The home must be a plain per-user home, and must not be anybody else's.
case "${PREVIEW_HOME}" in
  /home/*/*|/home/) die "refusing: '${PREVIEW_HOME}' is not a top-level home directory" ;;
  /home/?*)         : ;;
  *)                die "refusing: home '${PREVIEW_HOME}' is not under /home — this script only writes inside a preview home" ;;
esac
[[ "${PREVIEW_HOME}" == "${INVOKER_HOME}" ]] && die "refusing: '${PREVIEW_HOME}' is the invoking user's home"
[[ "${PREVIEW_HOME}" == "/home/nyx"      ]] && die "refusing: '${PREVIEW_HOME}' is the NYXUS primary home"
if [[ "${REPO_ROOT}" == "${PREVIEW_HOME}"* ]]; then
  die "refusing: the repo lives inside '${PREVIEW_HOME}' — provisioning would overwrite it"
fi
# Any OTHER account claiming this home means we picked a name that collides.
COLLIDER="$(getent passwd | awk -F: -v h="${PREVIEW_HOME}" -v u="${PREVIEW_USER}" '$6==h && $1!=u {print $1}' | head -1)"
[[ -n "${COLLIDER}" ]] && die "refusing: '${PREVIEW_HOME}' is also the home of account '${COLLIDER}'"
ok "preview home ${PREVIEW_HOME} is safe to write"

# 4. Root, unless we are only talking about it.
if (( ! DRY_RUN )) && [[ ${EUID} -ne 0 ]]; then
  fail "this needs root (it creates an account). Run:"
  printf "\n      ${B}sudo bash %s/scripts/nyxus-daily-preview.sh${R}\n\n" "${REPO_ROOT}"
  note "or preview the plan with no privileges at all:"
  printf "      ${B}bash %s/scripts/nyxus-daily-preview.sh --dry-run${R}\n\n" "${REPO_ROOT}"
  exit 1
fi
(( DRY_RUN )) || ok "running as root"

# ════════════════════════════════════════════════════════════════════════
#  REMOVE
# ════════════════════════════════════════════════════════════════════════
if (( DO_REMOVE )); then
  step "remove preview account '${PREVIEW_USER}'"
  if (( ! TARGET_EXISTS )); then
    ok "no such account — nothing to remove"
    if [[ -d "${PREVIEW_HOME}" ]]; then
      warn "but ${PREVIEW_HOME} still exists (orphan home)"
      run rm -rf -- "${PREVIEW_HOME}"
    fi
    exit 0
  fi
  warn "this deletes the account AND ${PREVIEW_HOME} (everything in it)"
  if (( ! ASSUME_YES )) && (( ! DRY_RUN )); then
    read -r -p "  type the account name to confirm: " _confirm
    [[ "${_confirm}" == "${PREVIEW_USER}" ]] || die "not confirmed — nothing removed"
  fi
  if command -v loginctl >/dev/null 2>&1; then
    run loginctl terminate-user "${PREVIEW_USER}" || true
  fi
  run pkill -KILL -u "${PREVIEW_USER}" || true
  run userdel -r "${PREVIEW_USER}"
  # userdel -r leaves the home behind if anything in it was still open.
  if (( ! DRY_RUN )) && [[ -d "${PREVIEW_HOME}" ]]; then
    warn "userdel left ${PREVIEW_HOME} behind — removing it"
    rm -rf -- "${PREVIEW_HOME}"
  fi
  ok "preview account removed"
  exit 0
fi

# ════════════════════════════════════════════════════════════════════════
#  PRE-FLIGHT — every repo path this script depends on
# ════════════════════════════════════════════════════════════════════════
step "check repo sources"

[[ -d "${SKEL_SRC}"    ]] || die "missing shared skel: ${SKEL_SRC}"
[[ -d "${EDITION_SRC}" ]] || die "missing daily edition dir: ${EDITION_SRC}"
[[ -d "${WALLS_SRC}"   ]] || die "missing wallpaper source: ${WALLS_SRC}"
ok "skel            ${SKEL_SRC}"
ok "daily edition   ${EDITION_SRC}"
ok "wallpapers      ${WALLS_SRC}"

SKEL_ACCENT="${SKEL_SRC}/.config/nyxus/accent.json"
[[ -r "${SKEL_ACCENT}" ]] || die "missing canonical accent.json: ${SKEL_ACCENT}"

for _w in "${DAILY_WALLS[@]}"; do
  if [[ -r "${WALLS_SRC}/${_w}.png" ]]; then
    ok "wall            ${_w}.png"
  else
    warn "wall ${_w}.png is NOT in the profile — the preview will fall back for it"
  fi
done

HAVE_JQ=0; command -v jq      >/dev/null 2>&1 && HAVE_JQ=1
HAVE_PY=0; command -v python3 >/dev/null 2>&1 && HAVE_PY=1
(( HAVE_JQ )) || warn "jq is not installed — accent.json cannot be merged or applied"
(( HAVE_PY )) || warn "python3 is not installed — the accent re-skin pass will be skipped"

# ════════════════════════════════════════════════════════════════════════
#  ACCOUNT
# ════════════════════════════════════════════════════════════════════════
step "preview account '${PREVIEW_USER}'"

# Only ask for groups that actually exist on THIS machine. A missing group
# makes useradd fail outright, which would abort the whole run over
# something cosmetic (e.g. `uucp` absent on a non-Arch host).
GROUPS_WANTED=()
for g in "${NYX_GROUPS[@]}"; do
  [[ -n "${g}" ]] || continue
  if getent group "${g}" >/dev/null 2>&1; then
    GROUPS_WANTED+=("${g}")
  else
    warn "group '${g}' does not exist on this machine — skipping it"
  fi
done
GROUP_CSV="$(IFS=,; echo "${GROUPS_WANTED[*]}")"
ok "groups: ${GROUP_CSV}"
(( WANT_WHEEL )) || note "wheel omitted (--no-wheel): the preview account will have no sudo"

if (( ! TARGET_EXISTS )); then
  run useradd -m -d "${PREVIEW_HOME}" -s /bin/bash -c "NYXUS Daily preview" \
      -G "${GROUP_CSV}" "${PREVIEW_USER}"
  if (( DRY_RUN )); then
    printf "  ${GOLD}dry${R}  echo '%s:%s' | chpasswd\n" "${PREVIEW_USER}" "${PREVIEW_PASS}"
  else
    echo "${PREVIEW_USER}:${PREVIEW_PASS}" | chpasswd
  fi
  ok "created — login ${PREVIEW_USER} / ${PREVIEW_PASS}"
else
  # Idempotent top-up: add only the memberships that are missing.
  CURRENT_GROUPS="$(id -nG "${PREVIEW_USER}" 2>/dev/null || echo "")"
  MISSING=()
  for g in "${GROUPS_WANTED[@]}"; do
    [[ " ${CURRENT_GROUPS} " == *" ${g} "* ]] || MISSING+=("${g}")
  done
  if (( ${#MISSING[@]} )); then
    run usermod -aG "$(IFS=,; echo "${MISSING[*]}")" "${PREVIEW_USER}"
    ok "added missing groups: ${MISSING[*]}"
  else
    ok "group memberships already correct"
  fi
  # A half-provisioned account with a locked password cannot reach the
  # greeter, and the failure looks like "the theme broke login".
  PW_STATE="$(passwd -S "${PREVIEW_USER}" 2>/dev/null | awk '{print $2}' || echo "?")"
  if [[ "${PW_STATE}" == "L" || "${PW_STATE}" == "NP" ]]; then
    warn "password was ${PW_STATE} (unusable) — setting it so the greeter can accept a login"
    if (( DRY_RUN )); then
      printf "  ${GOLD}dry${R}  echo '%s:%s' | chpasswd\n" "${PREVIEW_USER}" "${PREVIEW_PASS}"
    else
      echo "${PREVIEW_USER}:${PREVIEW_PASS}" | chpasswd
    fi
  else
    ok "password already set (unchanged by a refresh)"
  fi
fi

if command -v loginctl >/dev/null 2>&1 && \
   loginctl list-sessions --no-legend 2>/dev/null | grep -qw "${PREVIEW_USER}"; then
  warn "'${PREVIEW_USER}' has a live session — log it out before trusting what you see,"
  note "a running Hyprland holds the old config in memory"
fi

# ════════════════════════════════════════════════════════════════════════
#  HOME — shared skel first, Daily edition on top
# ════════════════════════════════════════════════════════════════════════
step "lay the shared skel into ${PREVIEW_HOME}"

note "this OVERWRITES the preview home's config from the repo — that is the refresh"
run install -d -m 0700 "${PREVIEW_HOME}"
run cp -aT "${SKEL_SRC}" "${PREVIEW_HOME}"
ok "skel copied ($(find "${SKEL_SRC}" -type f | wc -l) files)"

# The accent engine keeps a pristine "canonical prism" snapshot of every
# consumer file under accent-baseline/. A stale one from a previous run
# would be re-rendered over the fresh skel and silently reinstate the old
# theme, so it goes before anything is applied.
if [[ -e "${PREVIEW_HOME}/.config/nyxus/accent-baseline" ]]; then
  run rm -rf -- "${PREVIEW_HOME}/.config/nyxus/accent-baseline"
  ok "dropped the stale accent baseline"
fi

step "overlay the Daily edition"

# Mapping is data-driven so that files a sibling agent adds under
# editions/daily/ later are either picked up automatically (known names,
# directories) or reported loudly (unknown names) rather than ignored.
declare -A EDITION_MAP=(
  ["wallpaper.conf"]=".config/nyxus/wallpaper.conf"
  ["wallpaper.json"]=".config/nyxus/wallpaper.json"
  ["wall-rotation.list"]=".config/nyxus/wall-rotation.list"
  ["livewall.conf"]=".config/nyxus/livewall.conf"
  ["wallfx.conf"]=".config/nyxus/wallfx.conf"
  ["stations.json"]=".config/nyxus/stations.json"
  ["stations-hacker.json"]=".config/nyxus/stations-hacker.json"
  ["hyprlock-accent.conf"]=".config/hypr/hyprlock-accent.conf"
  ["hyprlock.conf"]=".config/hypr/hyprlock.conf"
)
# Directories under editions/daily/ overlay onto ~/.config/<same name>/.
EDITION_DIRS=(eww hypr nyxus gtk-3.0 gtk-4.0 rofi dunst swaync wlogout)

# accent.json is merged, not copied — see the accent step below.
# regreet.css is deliberately NOT installed — it is /etc/greetd, system-wide.
EDITION_SPECIAL=(accent.json regreet.css)

DEFERRED_ACCENT_SHARD=""

shopt -s nullglob dotglob
for src in "${EDITION_SRC}"/*; do
  name="$(basename "${src}")"

  if [[ -d "${src}" ]]; then
    matched=0
    for d in "${EDITION_DIRS[@]}"; do
      [[ "${name}" == "${d}" ]] || continue
      run install -d -m 0755 "${PREVIEW_HOME}/.config/${name}"
      run cp -a "${src}/." "${PREVIEW_HOME}/.config/${name}/"
      ok "${name}/ → ~/.config/${name}/"
      matched=1; break
    done
    (( matched )) || warn "editions/daily/${name}/ is a directory this script does not know — NOT staged"
    continue
  fi

  special=0
  for s in "${EDITION_SPECIAL[@]}"; do
    if [[ "${name}" == "${s}" ]]; then special=1; fi
  done
  (( special )) && continue

  dest="${EDITION_MAP[${name}]:-}"
  if [[ -z "${dest}" ]]; then
    warn "editions/daily/${name} is new to this script — NOT staged"
    note "add it to EDITION_MAP in scripts/nyxus-daily-preview.sh"
    continue
  fi
  # hyprlock-accent.conf is regenerated by nyxus-apply-accent, so the
  # edition's copy has to land AFTER the accent pass or it gets clobbered.
  if [[ "${name}" == "hyprlock-accent.conf" ]]; then
    DEFERRED_ACCENT_SHARD="${src}"
    ok "${name} → deferred until after the accent pass"
    continue
  fi
  run install -Dm0644 "${src}" "${PREVIEW_HOME}/${dest}"
  ok "${name} → ~/${dest}"
done
shopt -u nullglob dotglob

# regreet.css: staged for reference only, never applied. Installing it would
# mean writing /etc/greetd/regreet.css, which is system-wide and would repaint
# the owner's own login screen — the exact blast radius this harness exists
# to avoid.
if [[ -r "${EDITION_SRC}/regreet.css" ]]; then
  run install -Dm0644 "${EDITION_SRC}/regreet.css" \
      "${PREVIEW_HOME}/.config/nyxus/daily-preview/regreet.css"
  warn "regreet.css staged as REFERENCE ONLY at ~/.config/nyxus/daily-preview/"
  note "the greeter is /etc/greetd/regreet.css — system-wide, so a preview account cannot theme it"
else
  note "no regreet.css in the edition dir yet — nothing to stage"
fi

# ════════════════════════════════════════════════════════════════════════
#  WALLPAPERS — make every referenced path resolve inside the preview home
# ════════════════════════════════════════════════════════════════════════
step "wallpapers"

WALLS_HOME="${PREVIEW_HOME}/.config/hypr/walls"
run install -d -m 0755 "${WALLS_HOME}"
for w in "${DAILY_WALLS[@]}"; do
  if (( ! DRY_RUN )) && [[ -r "${WALLS_HOME}/${w}.png" ]]; then
    ok "${w}.png already in the preview home"
    continue
  fi
  if [[ -r "${WALLS_SRC}/${w}.png" ]]; then
    run install -m0644 "${WALLS_SRC}/${w}.png" "${WALLS_HOME}/${w}.png"
    ok "${w}.png → ~/.config/hypr/walls/"
  else
    warn "${w}.png missing from the profile — skipped"
  fi
done

# The edition files point at /usr/share/backgrounds/nyxus/<slug>.png, which
# is where a BAKED Daily ISO puts them. On a machine running an older build
# those files do not exist, and nyxus-wallpaper-autostart silently falls back
# to nyxus-nebula-01.png — i.e. the preview would come up wearing the wrong
# wallpaper and look like the theme failed. Repoint only the paths that do
# not resolve, and only to a copy we just proved is there.
if (( ! DRY_RUN )); then
  for f in "${PREVIEW_HOME}/.config/nyxus/wallpaper.conf" \
           "${PREVIEW_HOME}/.config/nyxus/wallpaper.json"; do
    [[ -f "${f}" ]] || continue
    while read -r sys_path; do
      [[ -n "${sys_path}" ]] || continue
      [[ -r "${sys_path}" ]] && continue
      slug="$(basename "${sys_path}" .png)"
      [[ -r "${WALLS_HOME}/${slug}.png" ]] || continue
      sed -i "s|${sys_path}|${WALLS_HOME}/${slug}.png|g" "${f}"
      ok "$(basename "${f}"): ${slug} repointed into the preview home"
    done < <(grep -o '/usr/share/backgrounds/nyxus/[A-Za-z0-9._-]*\.png' "${f}" | sort -u)
  done
else
  printf "  ${GOLD}dry${R}  repoint any unresolvable /usr/share/backgrounds/nyxus/*.png\n"
  printf "        ${DIM}in wallpaper.conf + wallpaper.json to %s/${R}\n" "${WALLS_HOME}"
fi

# ════════════════════════════════════════════════════════════════════════
#  TOOL LAYER — the preview account gets its OWN copy of the NYXUS tools
# ════════════════════════════════════════════════════════════════════════
# WHY THIS EXISTS (measured 2026-08-02): the first preview login came up as a
# bare desktop — wallpaper and accent right, no NYXUS shell. The cause was not
# the theme. On this machine the tool layer is installed into the OWNER's home:
# 164 nyxus-* commands in /home/cosmic/.local/bin against 56 in /usr/local/bin,
# and /home/cosmic is 0700. nyxus-session-start happens to be one of the ones
# in /usr/local/bin, which is why the session started at all — but nearly
# everything it launches afterwards to build the desktop lived behind a 0700
# directory belonging to another user, so the shell never assembled. It is also
# why the accent pass hit "Permission denied" when it ran as the preview user.
#
# The fix is not to relax anyone's permissions. It is to give the preview
# account its own copy from the repo, which is what a real Daily ISO does for
# its user anyway. Nothing here reads another user's home.
#
# EVERY FILE SET BELOW IS DERIVED FROM AN EXISTING DEFINITION IN THE REPO,
# parsed at run time. A second hand-maintained list that drifts from the
# installers is a failure mode this project has already paid for twice —
# verify-profile gate 13pg exists because install.sh and nyxus_install.sh had
# silently diverged in both directions. This script adds no third list.
step "NYXUS tool layer"

NS_SRC="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
HOME_PKG_SRC="${REPO_ROOT}/artifacts/nyxus-home/src"
BUILD_ISO="${REPO_ROOT}/iso-builder/build-iso.sh"
PBIN="${PREVIEW_HOME}/.local/bin"
PNYX="${PREVIEW_HOME}/.nyxus"
PAPPS="${PREVIEW_HOME}/.local/share/applications"

[[ -d "${NS_SRC}" ]] || die "missing tool source: ${NS_SRC}"

# ~/.local/bin is what the desktop actually reaches for: the skel .bashrc
# prepends it, and hyprland.conf's exec-once/bind lines export
# PATH="$HOME/.local/bin:/usr/local/bin:$PATH" before calling these by name.
run install -d -m 0755 "${PBIN}" "${PNYX}" "${PAPPS}"

# A shebang or an ELF header means the file is meant to be executed. This
# project once shipped 116 executables at mode 644, so the bit is decided by
# looking at the file, never by assuming.
_exec_payload() {
  local magic
  magic="$(head -c4 "$1" 2>/dev/null | od -An -tx1 2>/dev/null | tr -d ' \n')"
  [[ "${magic}" == 2321* || "${magic}" == 7f454c46* ]]
}

# Pull a bash array literal out of a script by name. Same idea as
# verify-profile gate 13pg's parser, in awk so it needs nothing extra.
_parse_array() {
  awk -v want="$2" '
    $0 ~ "^" want "=\\(" { f = 1; next }
    f && /^\)/           { exit }
    f                    { sub(/#.*/, ""); print }
  ' "$1"
}

# ── 1. Launchers → ~/.local/bin ─────────────────────────────────────────
# Source of truth: the LAUNCHERS array in nyxus_install.sh, which is the
# offline/ISO deploy path — i.e. exactly the set a Daily ISO user would get.
LAUNCHERS=()
if [[ -r "${NS_SRC}/nyxus_install.sh" ]]; then
  mapfile -t LAUNCHERS < <(_parse_array "${NS_SRC}/nyxus_install.sh" LAUNCHERS \
                           | tr -s ' \t' '\n\n' | sed '/^$/d')
fi
if (( ${#LAUNCHERS[@]} == 0 )); then
  die "could not parse LAUNCHERS out of ${NS_SRC}/nyxus_install.sh — refusing to guess the tool set"
fi

# install.sh (the dev-machine deploy path) carries the same array and gate
# 13pg fails the build if they differ. If they differ HERE, the gate is red
# and the preview would be a coin-flip between two tool sets — say so.
if [[ -r "${REPO_ROOT}/install.sh" ]]; then
  _drift="$(diff <(printf '%s\n' "${LAUNCHERS[@]}" | sort) \
                 <(_parse_array "${REPO_ROOT}/install.sh" LAUNCHERS \
                   | tr -s ' \t' '\n\n' | sed '/^$/d' | sort) || true)"
  if [[ -n "${_drift}" ]]; then
    warn "install.sh and nyxus_install.sh LAUNCHERS disagree — verify-profile gate 13pg is red"
    note "using the nyxus_install.sh (ISO) set; fix the drift before trusting this preview"
  fi
fi

# Track what has been put on the preview's PATH, so later steps never shadow
# an earlier one and --dry-run reports the same counts a real run produces.
declare -A INSTALLED_BIN=()

_lnch_ok=0; _lnch_miss=()
for _l in "${LAUNCHERS[@]}"; do
  if [[ -f "${NS_SRC}/${_l}" ]]; then
    runq install -Dm0755 "${NS_SRC}/${_l}" "${PBIN}/${_l}"
    INSTALLED_BIN["${_l}"]=1
    _lnch_ok=$((_lnch_ok + 1))
  else
    _lnch_miss+=("${_l}")
  fi
done
ok "launchers: ${_lnch_ok}/${#LAUNCHERS[@]} → ~/.local/bin (mode 0755)"
if (( ${#_lnch_miss[@]} )); then
  warn "unresolved in nyxus-scripts: ${_lnch_miss[*]}"
  note "these are named by the installer but not present in the repo — they will be missing in the preview"
fi

# ── 2. GTK app wrappers → ~/.local/bin ──────────────────────────────────
# The bake generates a one-line wrapper per entry of APPS_LIST in
# build-iso.sh (Settings, Control, Launcher, Store, Terminal, …). Those are
# NOT in LAUNCHERS, so without this the preview has the reactive layer but
# none of the actual apps. Parsed from build-iso.sh rather than retyped; the
# only change is where the module is looked up, because /opt/nyxus is outside
# the preview home and this script does not write there.
_write_app_wrapper() {
  local bin="$1" mod="$2"
  if (( ! DRY_RUN )); then
    cat > "${PBIN}/${bin}" <<WRAPPER
#!/usr/bin/env bash
# NYXUS ${bin} — generated by nyxus-daily-preview.sh for the preview account.
# Resolution order mirrors nyxus-screensaver: the user's own copy first, then
# the system one, so this works whether or not /opt/nyxus is populated.
for _p in "\${HOME}/.nyxus/${mod}" "/opt/nyxus/${mod}"; do
  [ -f "\${_p}" ] && exec python3 "\${_p}" "\$@"
done
echo "${bin}: ${mod} not found in ~/.nyxus or /opt/nyxus" >&2
exit 1
WRAPPER
    chmod 0755 "${PBIN}/${bin}"
  fi
  INSTALLED_BIN["${bin}"]=1
}

_apps_n=0
if [[ -r "${BUILD_ISO}" ]]; then
  while IFS= read -r _entry; do
    [[ -n "${_entry}" ]] || continue
    _mod="${_entry%%:*}"
    [[ -n "${_mod}" ]] || continue
    if [[ "${_mod}" == "sysmon_gtk" ]]; then _bin="nyxus-sysmon"; else _bin="nyxus-${_mod//_/-}"; fi
    [[ -n "${INSTALLED_BIN[${_bin}]:-}" ]] && continue
    _write_app_wrapper "${_bin}" "nyxus_${_mod}.py"
    _apps_n=$((_apps_n + 1))
  done < <(_parse_array "${BUILD_ISO}" APPS_LIST | tr -d '"' | sed 's/^[[:space:]]*//;/^$/d')
  ok "GTK app wrappers: ${_apps_n} written from build-iso.sh APPS_LIST"
else
  warn "build-iso.sh unreadable — the GTK app wrappers (Settings, Control, Store, …) are NOT installed"
fi

# ── 2c. Package apps → ~/.nyxus/<pkg> (+ their launcher) ─────────────────
# nyxus-panel and nyxus-start ship as directories inside nyxus-scripts, each
# carrying its own launcher; nyxus-home's canonical source is
# artifacts/nyxus-home/src (see docs/NYXUS_BUILD.md and nyxus-backport-live.sh).
# The launchers exec "$HOME/.nyxus/<pkg>/main.py", so the package has to be in
# the preview's own ~/.nyxus or the window opens and paints nothing.
_install_pkg() {
  local name="$1" src="$2"
  [[ -d "${src}" ]] || { warn "package ${name}: no source at ${src} — skipped"; return 0; }
  run install -d -m 0755 "${PNYX}/${name}"
  run cp -a "${src}/." "${PNYX}/${name}/"
  # The in-package launcher (if any) belongs on PATH, not in the package.
  if [[ -f "${src}/${name}" ]]; then
    run install -Dm0755 "${src}/${name}" "${PBIN}/${name}"
    INSTALLED_BIN["${name}"]=1
  fi
  ok "package ${name} → ~/.nyxus/${name}/"
}
_install_pkg nyxus-panel "${NS_SRC}/nyxus-panel"
_install_pkg nyxus-start "${NS_SRC}/nyxus-start"
_install_pkg nyxus-home  "${HOME_PKG_SRC}"
if [[ -d "${HOME_PKG_SRC}" && ! -f "${HOME_PKG_SRC}/nyxus-home" && -f "${NS_SRC}/nyxus-home" ]]; then
  note "nyxus-home's launcher comes from nyxus-scripts (already in LAUNCHERS)"
fi

# ── 2d. Coverage backstop — everything hyprland.conf actually calls ─────
# The two lists above are what the installers deploy. What decides whether the
# desktop ASSEMBLES is narrower and more specific: the set of commands
# hyprland.conf's exec-once and bind lines invoke. Anything in there that is
# not reachable is a feature that silently never starts, with no error
# anywhere — the exact failure the first preview login showed. So: read the
# shipped hyprland.conf, and for every nyxus-* command it names that is still
# unreachable, either install it or generate its wrapper. Anything that can be
# satisfied neither way is reported, because an unreachable name here is a
# real hole and the owner should not have to discover it by looking at a
# desktop that half-appeared.
_HYPR_SRC="${NS_SRC}/hyprland.conf"
_bs_n=0; _bs_none=()
if [[ -r "${_HYPR_SRC}" ]]; then
  while IFS= read -r _n; do
    [[ -n "${_n}" ]] || continue
    [[ -n "${INSTALLED_BIN[${_n}]:-}" ]] && continue
    # Already reachable system-wide as a root-owned copy: leave it alone
    # rather than putting a user-writable shadow of it earlier on PATH.
    [[ -x "/usr/local/bin/${_n}" || -x "/usr/bin/${_n}" ]] && continue
    if [[ -f "${NS_SRC}/${_n}" ]] && _exec_payload "${NS_SRC}/${_n}"; then
      runq install -Dm0755 "${NS_SRC}/${_n}" "${PBIN}/${_n}"
      INSTALLED_BIN["${_n}"]=1
      ok "backstop: ${_n} (called by hyprland.conf, was unreachable)"
      _bs_n=$((_bs_n + 1))
      continue
    fi
    # hyprland.conf calls its own shards by absolute path out of
    # ~/.config/hypr/scripts, which the skel copy already delivered.
    [[ -f "${NS_SRC}/hypr/scripts/${_n}" ]] && continue
    _mod="nyxus_${_n#nyxus-}"; _mod="${_mod//-/_}.py"
    if [[ -f "${NS_SRC}/${_mod}" ]]; then
      _write_app_wrapper "${_n}" "${_mod}"
      ok "backstop: ${_n} → ${_mod} wrapper (called by hyprland.conf)"
      _bs_n=$((_bs_n + 1))
      continue
    fi
    _bs_none+=("${_n}")
  done < <(grep -oE '\bnyxus-[a-z0-9][a-z0-9._-]*' "${_HYPR_SRC}" \
           | sed 's/\.$//' \
           | grep -vE '\.(conf|service|desktop|log|png|json|css|scss|list|toml)$' \
           | sort -u)
  ok "coverage backstop: ${_bs_n} added from hyprland.conf"
  if (( ${#_bs_none[@]} )); then
    note "named in hyprland.conf but not resolvable to a tool: ${_bs_none[*]}"
    note "(eww window names such as nyxus-hub / nyxus-eww land here too — not necessarily a problem)"
  fi
else
  warn "no hyprland.conf in nyxus-scripts — skipping the coverage backstop"
fi

# ── 3. Python module layer → ~/.nyxus ───────────────────────────────────
# The bake installs NS/nyxus_*.py into /opt/nyxus and gives each user a
# ~/.nyxus full of per-file symlinks to it. The preview cannot write /opt, so
# it gets real copies in the same place instead — same import surface, since
# these modules import each other as siblings (nyxus_chrome, nyxus_cosmic_bg
# and friends) and every launcher resolves them through ~/.nyxus.
_mods_n=0
shopt -s nullglob
_MODULES=("${NS_SRC}"/nyxus_*.py)
for _extra in nyxus-security-daemon.py nyxus-crash-report.py nyxus-palette.css; do
  [[ -f "${NS_SRC}/${_extra}" ]] && _MODULES+=("${NS_SRC}/${_extra}")
done
shopt -u nullglob
for _m in "${_MODULES[@]}"; do
  if _exec_payload "${_m}"; then _mode=0755; else _mode=0644; fi
  runq install -Dm"${_mode}" "${_m}" "${PNYX}/$(basename "${_m}")"
  _mods_n=$((_mods_n + 1))
done
if [[ -f "${NS_SRC}/desktop/nyxus_desktop.py" ]]; then
  run install -Dm0755 "${NS_SRC}/desktop/nyxus_desktop.py" "${PNYX}/desktop/nyxus_desktop.py"
  _mods_n=$((_mods_n + 1))
fi
ok "python modules: ${_mods_n} → ~/.nyxus (exec bit set by shebang/ELF, not assumed)"

# ── 5. Desktop entries + app art ────────────────────────────────────────
# 42 nyxus .desktop files are already system-wide on this machine, but the
# curated set in the repo is larger and is what the bake ships. App windows
# also read their splat backgrounds out of ~/.nyxus/backgrounds (nyxus_install.sh
# "App Backgrounds"), and without them the GTK apps render on flat black.
if [[ -d "${NS_SRC}/desktop-entries" ]]; then
  run install -d -m 0755 "${PAPPS}"
  run cp -a "${NS_SRC}/desktop-entries/." "${PAPPS}/"
  ok "desktop entries → ~/.local/share/applications/"
fi
shopt -s nullglob
_BGS=("${NS_SRC}"/nyxus-bg-*.png)
shopt -u nullglob
if (( ${#_BGS[@]} )); then
  run install -d -m 0755 "${PNYX}/backgrounds"
  for _bg in "${_BGS[@]}"; do
    runq install -m0644 "${_bg}" "${PNYX}/backgrounds/$(basename "${_bg}")"
  done
  ok "app backgrounds: ${#_BGS[@]} → ~/.nyxus/backgrounds/"
fi

# ════════════════════════════════════════════════════════════════════════
#  OWNERSHIP — must happen BEFORE the accent pass
# ════════════════════════════════════════════════════════════════════════
# `cp -a` from the repo preserves the repo's ownership, so everything staged
# above currently belongs to whoever owns the checkout. The accent pass below
# runs AS the preview user and rewrites ~25 files in place; against a
# root/checkout-owned tree every one of those writes is EACCES. Hand the home
# over first, then re-run it at the end for the few files written after.
step "ownership"
run chown -R "${PREVIEW_USER}:${PREVIEW_USER}" "${PREVIEW_HOME}"
run chmod 0700 "${PREVIEW_HOME}"
ok "${PREVIEW_HOME} handed to ${PREVIEW_USER} before the accent pass"

# ════════════════════════════════════════════════════════════════════════
#  ACCENT — merge the Daily preset in, then let the real engine re-skin
# ════════════════════════════════════════════════════════════════════════
step "accent"

DAILY_ACCENT="${EDITION_SRC}/accent.json"
PREVIEW_ACCENT="${PREVIEW_HOME}/.config/nyxus/accent.json"
DAILY_PRESET=""

if [[ ! -r "${DAILY_ACCENT}" ]]; then
  warn "no accent.json in the edition dir — the preview keeps the shared alien palette"
elif (( ! HAVE_JQ )); then
  warn "jq missing — copying the edition accent.json verbatim, no re-skin"
  run install -Dm0644 "${DAILY_ACCENT}" "${PREVIEW_ACCENT}"
else
  DAILY_PRESET="$(jq -r '.active // empty' "${DAILY_ACCENT}")"
  [[ -n "${DAILY_PRESET}" ]] || die "editions/daily/accent.json has no .active preset"
  ok "daily preset: ${DAILY_PRESET}"

  # nyxus-apply-accent renders every consumer file FROM a canonical `prism`
  # baseline, so `prism` must still be present in the preview's accent.json
  # or the re-skin pass dies on an empty colour. Merge the edition on top of
  # the shared file (jq `*` is a recursive merge) and hold `.active` at
  # prism, which is what the freshly-copied skel files are actually coloured
  # in. The apply run below then moves it to the daily preset for real.
  if (( DRY_RUN )); then
    printf "  ${GOLD}dry${R}  jq -s '(.[0] * .[1]) | .active=\"prism\"' skel/accent.json editions/daily/accent.json\n"
    printf "        ${DIM}→ %s${R}\n" "${PREVIEW_ACCENT}"
  else
    _tmp="$(mktemp)"
    jq -s '(.[0] * .[1]) | .active = "prism"' "${SKEL_ACCENT}" "${DAILY_ACCENT}" > "${_tmp}"
    install -Dm0644 "${_tmp}" "${PREVIEW_ACCENT}"
    rm -f "${_tmp}"
    ok "accent.json merged (prism baseline + ${DAILY_PRESET})"
  fi

  # Run the preview account's OWN copy, installed by the tool-layer step and
  # owned by it. The first version of this script ran the one in the repo,
  # under /home/cosmic at 0700 — which is precisely the permission wall this
  # whole change is about, and it failed there with EACCES.
  ACCENT_BIN="${PBIN}/nyxus-apply-accent"
  if (( ! DRY_RUN )) && [[ ! -x "${ACCENT_BIN}" ]]; then
    warn "the preview has no nyxus-apply-accent — falling back to the repo copy"
    ACCENT_BIN="${APPLY_ACCENT}"
    [[ -r "${ACCENT_BIN}" ]] || ACCENT_BIN="$(command -v nyxus-apply-accent 2>/dev/null || true)"
  fi
  if [[ -z "${ACCENT_BIN}" ]]; then
    warn "nyxus-apply-accent not found — eww/GTK/hyprlock keep the alien colours"
  elif (( ! HAVE_PY )); then
    warn "python3 missing — skipping the re-skin pass"
  else
    _as_preview bash "${ACCENT_BIN}" "${DAILY_PRESET}" \
      || warn "nyxus-apply-accent exited non-zero — check the colours in the session"
    (( DRY_RUN )) || ok "re-skinned the preview home to '${DAILY_PRESET}'"
  fi
fi

# The edition's own hyprlock shard, if it exists, is authored art and beats
# the generated one — so it lands last.
if [[ -n "${DEFERRED_ACCENT_SHARD}" ]]; then
  run install -Dm0644 "${DEFERRED_ACCENT_SHARD}" \
      "${PREVIEW_HOME}/.config/hypr/hyprlock-accent.conf"
  ok "hyprlock-accent.conf → ~/.config/hypr/ (edition copy wins)"
fi

# ════════════════════════════════════════════════════════════════════════
#  APP ICONS
# ════════════════════════════════════════════════════════════════════════
# The .desktop files name io.nyxus.* icons that are painted, not shipped —
# nyxus_install.sh runs this generator and it writes into
# ~/.local/share/icons/hicolor. There are none system-wide on this machine, so
# without it every NYXUS app shows a generic placeholder in the launcher.
# Best-effort: it needs pycairo, and a missing icon is cosmetic.
step "app icons"
if [[ -f "${PNYX}/nyxus_gen_icons.py" ]] || (( DRY_RUN )); then
  if _as_preview python3 "${PNYX}/nyxus_gen_icons.py" >/dev/null 2>&1; then
    if (( DRY_RUN )); then
      ok "would paint the io.nyxus.* icons into ~/.local/share/icons/"
    else
      ok "icons painted: $(find "${PREVIEW_HOME}/.local/share/icons" -name 'io.nyxus.*.png' 2>/dev/null | wc -l)"
    fi
  else
    warn "icon generation failed (usually missing python-cairo) — apps will show generic icons"
  fi
else
  warn "nyxus_gen_icons.py not in the preview home — apps will show generic icons"
fi

# ════════════════════════════════════════════════════════════════════════
#  FIRST-BOOT BOOTSTRAP
# ════════════════════════════════════════════════════════════════════════
step "first-boot bootstrap"

if (( RUN_BOOTSTRAP )); then
  run rm -f -- "${PREVIEW_HOME}/.nyxus/.bootstrapped"
  warn "nyxus-bootstrap WILL run at first login (--with-bootstrap)"
  note "it calls plain 'sudo pacman -S'; on a fingerprint-only sudo box that can stall the login"
else
  BOOTSTRAP_VERSION=""
  for b in "${BOOTSTRAP_SRC}" /usr/local/bin/nyxus-bootstrap; do
    [[ -r "${b}" ]] || continue
    BOOTSTRAP_VERSION="$(sed -n 's/^BOOTSTRAP_VERSION="\(.*\)"$/\1/p' "${b}" | head -1)"
    [[ -n "${BOOTSTRAP_VERSION}" ]] && break
  done
  if [[ -z "${BOOTSTRAP_VERSION}" ]]; then
    warn "could not read BOOTSTRAP_VERSION — bootstrap will run at first login"
  else
    run install -d -m 0755 "${PREVIEW_HOME}/.nyxus"
    if (( DRY_RUN )); then
      printf "  ${GOLD}dry${R}  echo '%s' > %s/.nyxus/.bootstrapped\n" \
             "${BOOTSTRAP_VERSION}" "${PREVIEW_HOME}"
    else
      printf '%s\n' "${BOOTSTRAP_VERSION}" > "${PREVIEW_HOME}/.nyxus/.bootstrapped"
    fi
    ok "pre-marked bootstrapped at ${BOOTSTRAP_VERSION} (no app install on login)"
    note "pass --with-bootstrap if you want the full first-boot install in the preview too"
  fi
fi

# ════════════════════════════════════════════════════════════════════════
#  OWNERSHIP
# ════════════════════════════════════════════════════════════════════════
step "ownership (final)"
run chown -R "${PREVIEW_USER}:${PREVIEW_USER}" "${PREVIEW_HOME}"
run chmod 0700 "${PREVIEW_HOME}"
ok "${PREVIEW_HOME} is owned by ${PREVIEW_USER}, mode 0700"

# ════════════════════════════════════════════════════════════════════════
#  SUMMARY
# ════════════════════════════════════════════════════════════════════════
step "done"
printf "  ${B}log out${R}, then at the greeter choose user ${B}%s${R}" "${PREVIEW_USER}"
(( TARGET_EXISTS )) || printf " (password ${B}%s${R})" "${PREVIEW_PASS}"
printf ", session ${B}NYXUS (Hyprland)${R}.\n"
printf "  Your own account is untouched — log back into ${B}%s${R} to return.\n" "${INVOKER}"
printf "\n  ${GOLD}Known limitation:${R} the greeter itself is /etc/greetd/regreet.css —\n"
printf "  system-wide, and drawn BEFORE you pick a user. The ${B}login screen stays\n"
printf "  alien${R} no matter which account you choose. Only the desktop after login\n"
printf "  changes. That is expected, not a bug. See docs/DAILY_PREVIEW_HARNESS.md.\n"
printf "\n  Refresh after we change the theme:  ${B}sudo bash %s/scripts/nyxus-daily-preview.sh${R}\n" "${REPO_ROOT}"
printf "  Remove it entirely:                ${B}sudo bash %s/scripts/nyxus-daily-preview.sh --remove${R}\n\n" "${REPO_ROOT}"

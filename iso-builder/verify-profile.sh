#!/usr/bin/env bash
# ============================================================================
#  iso-builder/verify-profile.sh                          rev 2026-05-13 r1
#
#  Pre-flight linter for the NYX archiso profile. Runs locally (no root,
#  no mkarchiso, no chroot) so contributors and CI can sanity-check the
#  profile before kicking off a 15-minute bake.
#
#  Checks (each emits exactly one line, prefixed [OK]/[WARN]/[FAIL]):
#    1. profiledef.sh   — sourceable, declares iso_name + iso_label
#    2. packages.x86_64 — exists, non-empty, no duplicate package names
#    3. pacman.conf     — exists, references core + extra repos
#    4. customize_airootfs.sh — bash -n parses, executable bit set
#    5. all bash scripts under airootfs/usr/local/bin parse with bash -n
#    6. all python files under airootfs/opt/nyxus parse with py_compile
#    7. all .desktop files validate with desktop-file-validate (if present)
#    8. calamares settings.conf + each module yaml is valid YAML
#    9. polkit policies are well-formed XML (xmllint, if present)
#   10. SDDM theme metadata.desktop + Main.qml present
#   11. plymouth nyxus.plymouth + nyxus.script present
#   12. grub theme theme.txt present
#   13. firstboot.d scripts are executable
#   14. mksquashfs is on PATH for an actual bake (warn-only)
#
#  Exit code: 0 if no [FAIL] lines were emitted, 1 otherwise.
#
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE="${HERE}/nyx-profile"
AIROOT="${PROFILE}/airootfs"
NS="${HERE}/../artifacts/api-server/nyxus-scripts"

FAIL=0
ok()   { printf '[ \033[1;32mOK\033[0m  ] %s\n' "$*"; }
warn() { printf '[\033[1;33mWARN\033[0m ] %s\n' "$*"; }
fail() { printf '[\033[1;31mFAIL\033[0m ] %s\n' "$*"; FAIL=1; }
hd()   { printf '\n\033[1;35m── %s ──\033[0m\n' "$*"; }

[[ -d "${PROFILE}" ]] || { fail "missing profile dir: ${PROFILE}"; exit 1; }

# ── 1. profiledef ──────────────────────────────────────────────────────
hd "1. profiledef.sh"
PD="${PROFILE}/profiledef.sh"
if [[ ! -f "${PD}" ]]; then
  fail "missing profiledef.sh"
else
  if ! bash -n "${PD}" 2>/tmp/nyx-profiledef.err; then
    fail "profiledef.sh syntax error: $(tr '\n' ' ' </tmp/nyx-profiledef.err)"
  else
    # NOTE: profiledef.sh uses bash associative-array syntax for
    # file_permissions=(...) which mkarchiso evaluates in its own
    # `declare -A`-prepared context. Sourcing it here without that
    # context produces a false-positive syntax error, so we grep for
    # the required keys instead.
    if grep -Eq '^[[:space:]]*iso_name=' "${PD}" \
       && grep -Eq '^[[:space:]]*iso_label=' "${PD}"; then
      ok "profiledef.sh declares iso_name + iso_label"
    else
      fail "profiledef.sh missing iso_name or iso_label"
    fi
  fi
fi

# ── 2. packages.x86_64 ─────────────────────────────────────────────────
hd "2. packages.x86_64"
PK="${PROFILE}/packages.x86_64"
if [[ ! -f "${PK}" ]]; then
  fail "missing packages.x86_64"
else
  TOTAL=$(grep -cv '^\s*\(#\|$\)' "${PK}" || true)
  if (( TOTAL == 0 )); then
    fail "packages.x86_64 is empty"
  else
    DUPES=$(grep -v '^\s*\(#\|$\)' "${PK}" | sort | uniq -d)
    if [[ -n "${DUPES}" ]]; then
      warn "duplicate packages: $(echo "${DUPES}" | tr '\n' ' ')"
    fi
    UNIQUE=$(grep -v '^\s*\(#\|$\)' "${PK}" | sort -u | wc -l)
    ok "packages.x86_64: ${TOTAL} entries, ${UNIQUE} unique"
  fi
fi

# ── 3. pacman.conf ─────────────────────────────────────────────────────
hd "3. pacman.conf"
PC="${PROFILE}/pacman.conf"
if [[ ! -f "${PC}" ]]; then
  warn "no profile-local pacman.conf (will use host /etc/pacman.conf)"
else
  if grep -q '^\[core\]' "${PC}" && grep -q '^\[extra\]' "${PC}"; then
    ok "pacman.conf references [core] + [extra]"
  else
    fail "pacman.conf missing [core] or [extra] repo section"
  fi
fi

# ── 4. customize_airootfs.sh ───────────────────────────────────────────
hd "4. customize_airootfs.sh"
CZ="${AIROOT}/root/customize_airootfs.sh"
if [[ ! -f "${CZ}" ]]; then
  fail "missing customize_airootfs.sh"
else
  if bash -n "${CZ}" 2>/tmp/nyx-cz.err; then
    ok "customize_airootfs.sh parses (bash -n)"
  else
    fail "customize_airootfs.sh syntax error: $(tr '\n' ' ' </tmp/nyx-cz.err)"
  fi
  [[ -x "${CZ}" ]] && ok "customize_airootfs.sh is executable" \
                   || warn "customize_airootfs.sh is not +x (mkarchiso will chmod it)"
fi

# ── 5. all /usr/local/bin scripts parse ───────────────────────────────
hd "5. /usr/local/bin shell scripts"
COUNT=0; BAD=0
if [[ -d "${AIROOT}/usr/local/bin" ]]; then
  while IFS= read -r -d '' s; do
    COUNT=$((COUNT+1))
    if head -1 "$s" | grep -q '^#!.*bash\|^#!.*sh'; then
      bash -n "$s" 2>/dev/null || { fail "bad shell: $s"; BAD=$((BAD+1)); }
    fi
  done < <(find "${AIROOT}/usr/local/bin" -maxdepth 1 -type f -print0)
  (( BAD == 0 )) && ok "all ${COUNT} /usr/local/bin scripts parse"
fi

# ── 6. /opt/nyxus python ──────────────────────────────────────────────
hd "6. /opt/nyxus python files"
if command -v python3 >/dev/null; then
  PYDIR="${AIROOT}/opt/nyxus"
  if [[ -d "${PYDIR}" ]]; then
    PCOUNT=0; PBAD=0
    while IFS= read -r -d '' p; do
      PCOUNT=$((PCOUNT+1))
      if ! python3 -m py_compile "$p" 2>/tmp/nyx-py.err; then
        fail "py_compile failed: $p — $(tr '\n' ' ' </tmp/nyx-py.err)"
        PBAD=$((PBAD+1))
      fi
    done < <(find "${PYDIR}" -maxdepth 1 -name '*.py' -print0)
    (( PBAD == 0 )) && ok "py_compile ✓ for ${PCOUNT} files"
  else
    warn "/opt/nyxus does not yet exist in airootfs (build-iso.sh installs it)"
  fi
else
  warn "python3 not available; skipping py_compile checks"
fi

# ── 7. .desktop files ─────────────────────────────────────────────────
hd "7. .desktop entries"
DCOUNT=0; DBAD=0
if [[ -d "${AIROOT}/usr/share/applications" ]]; then
  if command -v desktop-file-validate >/dev/null; then
    while IFS= read -r -d '' d; do
      DCOUNT=$((DCOUNT+1))
      desktop-file-validate "$d" >/dev/null 2>/tmp/nyx-d.err \
        || { warn "desktop-file-validate: $d — $(head -1 /tmp/nyx-d.err)"; DBAD=$((DBAD+1)); }
    done < <(find "${AIROOT}/usr/share/applications" -maxdepth 1 -name '*.desktop' -print0)
    ok "desktop-file-validate: ${DCOUNT} files (${DBAD} warnings)"
  else
    warn "desktop-file-validate not available; skipping"
  fi

  # NYXUS desktop-entry source parity (source-of-truth lives in nyxus-scripts/)
  # Session-selector entries (DesktopNames=) are installed to
  # usr/share/wayland-sessions/ by build-iso.sh, not usr/share/applications/
  # (desktop-file-validate rejects DesktopNames on a Type=Application entry
  # outside a session directory), so they are excluded from this parity set.
  SRC_DESK="${NS}/desktop-entries"
  ISO_DESK="${AIROOT}/usr/share/applications"
  if [[ -d "${SRC_DESK}" ]]; then
    src_list="$(grep -EL '^DesktopNames=' "${SRC_DESK}"/nyxus-*.desktop 2>/dev/null | xargs -n1 basename | sort)"
    iso_list="$(find "${ISO_DESK}" -maxdepth 1 -name 'nyxus-*.desktop' -printf '%f\n' | sort)"
    if [[ "${src_list}" != "${iso_list}" ]]; then
      fail "desktop parity mismatch between nyxus-scripts/desktop-entries and airootfs/usr/share/applications"
    else
      ok "desktop parity: nyxus-scripts/desktop-entries ↔ airootfs/usr/share/applications"
    fi
  fi
fi

# ── 8. calamares yaml ─────────────────────────────────────────────────
hd "8. calamares modules"
CALCONF="${AIROOT}/etc/calamares/settings.conf"
if [[ -f "${CALCONF}" ]]; then
  ok "settings.conf present"
  if command -v python3 >/dev/null; then
    python3 - "$CALCONF" <<'PYEOF' && ok "settings.conf parses as YAML" \
                                    || fail "settings.conf YAML invalid"
import sys
try:
    import yaml
except ImportError:
    print("PyYAML not available — skipping deep YAML check"); sys.exit(0)
yaml.safe_load(open(sys.argv[1]))
PYEOF
  fi
  for m in "${AIROOT}/etc/calamares/modules"/*.conf; do
    [[ -f "$m" ]] || continue
    if command -v python3 >/dev/null; then
      python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1]))' "$m" \
        2>/tmp/nyx-cal.err \
        || warn "yaml: $(basename "$m") — $(head -1 /tmp/nyx-cal.err)"
    fi
  done
  if [[ -f "${AIROOT}/etc/calamares/modules/timezone.conf" ]]; then
    if grep -Eq '^[[:space:]]*-[[:space:]]*timezone([[:space:]]|$)' "${CALCONF}"; then
      ok "calamares timezone module wired in settings.conf"
    else
      fail "calamares timezone.conf exists but timezone module is not referenced in settings.conf"
    fi
  fi
  ok "calamares modules scanned"
else
  warn "no calamares settings.conf (installer flow will be welcome→finished)"
fi

# ── 9. polkit policies ────────────────────────────────────────────────
hd "9. polkit policies"
PCOUNT=0
if [[ -d "${AIROOT}/usr/share/polkit-1/actions" ]]; then
  if command -v xmllint >/dev/null; then
    PBAD=0
    while IFS= read -r -d '' x; do
      PCOUNT=$((PCOUNT+1))
      xmllint --noout "$x" 2>/tmp/nyx-x.err \
        || { fail "polkit XML: $(basename "$x") — $(head -1 /tmp/nyx-x.err)"; PBAD=$((PBAD+1)); }
    done < <(find "${AIROOT}/usr/share/polkit-1/actions" -maxdepth 1 -name '*.policy' -print0)
    (( PBAD == 0 )) && ok "${PCOUNT} polkit policies validate as XML"
  else
    warn "xmllint not available; skipping XML validation"
  fi

  SRC_POL="${NS}/polkit-policies"
  ISO_POL="${AIROOT}/usr/share/polkit-1/actions"
  if [[ -d "${SRC_POL}" ]]; then
    src_pol="$(find "${SRC_POL}" -maxdepth 1 -name 'com.nyxus.*.policy' -printf '%f\n' | sort)"
    iso_pol="$(find "${ISO_POL}" -maxdepth 1 -name 'com.nyxus.*.policy' -printf '%f\n' | sort)"
    if [[ "${src_pol}" != "${iso_pol}" ]]; then
      fail "polkit parity mismatch between nyxus-scripts/polkit-policies and airootfs actions"
    else
      ok "polkit parity: nyxus-scripts/polkit-policies ↔ airootfs actions"
    fi
  fi
fi

# ── 10. SDDM theme ────────────────────────────────────────────────────
hd "10. SDDM theme"
ST="${AIROOT}/usr/share/sddm/themes/nyxus"
if [[ -f "${ST}/Main.qml" && -f "${ST}/metadata.desktop" ]]; then
  ok "SDDM nyxus theme: Main.qml + metadata.desktop present"
else
  fail "SDDM nyxus theme incomplete: missing Main.qml or metadata.desktop"
fi

# ── 11. plymouth ──────────────────────────────────────────────────────
hd "11. plymouth theme"
PT="${AIROOT}/usr/share/plymouth/themes/nyxus"
if [[ -f "${PT}/nyxus.plymouth" && -f "${PT}/nyxus.script" ]]; then
  ok "plymouth nyxus theme present"
else
  fail "plymouth nyxus theme incomplete"
fi

# ── 12. grub theme ────────────────────────────────────────────────────
hd "12. grub theme"
GT="${AIROOT}/usr/share/grub/themes/nyxus"
if [[ -f "${GT}/theme.txt" ]]; then
  ok "grub nyxus theme.txt present"
else
  fail "grub nyxus theme.txt missing"
fi

# ── 13. firstboot.d ───────────────────────────────────────────────────
hd "13. firstboot.d"
FB="${AIROOT}/etc/nyxus-firstboot.d"
if [[ -d "${FB}" ]]; then
  NX=$(find "${FB}" -maxdepth 1 -name '*.sh' ! -perm -u+x | wc -l)
  TOT=$(find "${FB}" -maxdepth 1 -name '*.sh' | wc -l)
  if (( NX > 0 )); then
    fail "${NX}/${TOT} firstboot.d scripts are not executable"
  else
    ok "${TOT} firstboot.d scripts are executable"
  fi
fi

# ── 13b. NYXUS-Dark icon theme ────────────────────────────────────────
hd "13b. NYXUS-Dark icon theme"
ICON_ROOT="${AIROOT}/usr/share/icons/NYXUS-Dark"
if [[ -d "${ICON_ROOT}" ]]; then
  if [[ -f "${ICON_ROOT}/index.theme" ]]; then
    ok "NYXUS-Dark/index.theme present"
  else
    fail "NYXUS-Dark/index.theme missing"
  fi
  ICON_COUNT=$(find "${ICON_ROOT}/scalable" -name '*.svg' 2>/dev/null | wc -l)
  if (( ICON_COUNT >= 30 )); then
    ok "NYXUS-Dark has ${ICON_COUNT} svg icons"
  else
    fail "NYXUS-Dark has only ${ICON_COUNT} svg icons (expected >=30)"
  fi
  for f in "${AIROOT}/etc/skel/.config/gtk-3.0/settings.ini" \
           "${AIROOT}/etc/skel/.config/gtk-4.0/settings.ini"; do
    if grep -q '^gtk-icon-theme-name=NYXUS-Dark$' "$f" 2>/dev/null; then
      ok "$(basename "$(dirname "$f")")/settings.ini -> NYXUS-Dark"
    else
      fail "$(basename "$(dirname "$f")")/settings.ini does not select NYXUS-Dark"
    fi
  done
else
  fail "NYXUS-Dark icon theme dir missing"
fi

# ── 13c. NYXUS wallpaper pack ─────────────────────────────────────────
hd "13c. NYXUS wallpaper pack"
WP_DIR="${AIROOT}/usr/share/backgrounds/nyxus"
WP_SVG=$(find "${WP_DIR}" -maxdepth 1 -name '*.svg' 2>/dev/null | wc -l)
WP_PNG=$(find "${WP_DIR}" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
WP_COUNT=$((WP_SVG + WP_PNG))
if (( WP_COUNT >= 50 )); then
  ok "${WP_COUNT} wallpapers shipped (${WP_SVG} svg + ${WP_PNG} png)"
else
  fail "only ${WP_COUNT} wallpapers (expected >=50)"
fi
if [[ -f "${WP_DIR}/manifest.tsv" ]]; then
  ok "manifest.tsv present"
  # Strict TSV: every non-empty line must be exactly slug<TAB>display, both non-empty.
  MAN_BAD=$(awk -F'\t' 'NF>0 && (NF!=2 || $1=="" || $2=="")' "${WP_DIR}/manifest.tsv" | wc -l)
  if (( MAN_BAD == 0 )); then
    ok "manifest.tsv is well-formed (slug<TAB>display)"
  else
    fail "manifest.tsv has ${MAN_BAD} malformed line(s)"
  fi
  MAN_SLUGS=$(awk -F'\t' 'NF>0{print $1}' "${WP_DIR}/manifest.tsv" | sort -u | wc -l)
  MAN_LINES=$(grep -c . "${WP_DIR}/manifest.tsv")
  if (( MAN_SLUGS == MAN_LINES )); then
    ok "manifest slugs are unique (${MAN_SLUGS})"
  else
    fail "manifest has duplicate slugs (${MAN_LINES} lines, ${MAN_SLUGS} unique)"
  fi
  # Exact 1:1 parity: every manifest slug resolves to a shipped file (.png or .svg),
  # and every shipped file has a manifest entry.
  PARITY_FAIL=0
  while IFS=$'\t' read -r slug _; do
    [[ -z "${slug}" ]] && continue
    if [[ ! -f "${WP_DIR}/${slug}.png" && ! -f "${WP_DIR}/${slug}.svg" ]]; then
      PARITY_FAIL=$((PARITY_FAIL+1))
    fi
  done < "${WP_DIR}/manifest.tsv"
  if (( PARITY_FAIL == 0 )); then
    ok "every manifest slug resolves to a shipped wallpaper"
  else
    fail "${PARITY_FAIL} manifest slug(s) have no matching .png/.svg"
  fi
  ORPHAN=0
  for f in "${WP_DIR}"/*.png "${WP_DIR}"/*.svg; do
    [[ -f "${f}" ]] || continue
    base=$(basename "${f}"); slug=${base%.*}
    grep -qP "^${slug}\t" "${WP_DIR}/manifest.tsv" || ORPHAN=$((ORPHAN+1))
  done
  if (( ORPHAN == 0 )); then
    ok "no orphan wallpaper files (every file has a manifest entry)"
  else
    fail "${ORPHAN} wallpaper file(s) missing from manifest"
  fi
else
  fail "manifest.tsv missing"
fi

# ── 13c-rot. every wall-rotation.list entry is actually STAGEABLE ──────
# The bake wipes skel/.config/hypr (taking walls/rotation/ with it) and stages
# wallpapers from NS. It used to glob only NS's ROOT, so all 27 nyxus-rot-*.png
# — which live in NS/hypr-walls/rotation/ — were absent from every ISO: the
# ambient rotation silently cycled 5 of its 32 images. This derives the
# requirement from wall-rotation.list itself rather than from a whitelist, so
# adding art to the list cannot outrun the bake again.
ROT_LIST="${NS}/wall-rotation.list"
if [[ -f "${ROT_LIST}" ]]; then
  ROT_MISS=0; ROT_TOTAL=0
  while read -r _slug; do
    [[ -z "${_slug}" || "${_slug}" == \#* ]] && continue
    _b="$(basename "${_slug}" .png).png"
    ROT_TOTAL=$((ROT_TOTAL+1))
    if [[ ! -f "${NS}/${_b}" && ! -f "${NS}/hypr-walls/rotation/${_b}" \
       && ! -f "${NS}/hypr-walls/${_b}" ]]; then
      ROT_MISS=$((ROT_MISS+1))
      warn "  rotation wallpaper has no source in NS: ${_b}"
    fi
  done < "${ROT_LIST}"
  if (( ROT_MISS == 0 )); then
    ok "all ${ROT_TOTAL} wall-rotation.list wallpapers have a stageable source"
  else
    fail "${ROT_MISS}/${ROT_TOTAL} wall-rotation.list wallpapers are not stageable"
  fi
else
  warn "wall-rotation.list absent — rotation set unverified"
fi

# ── 13c-eww. the eww wipe restores every top-level NS/eww file ────────
# `rm -rf skel/.config/eww` deletes the whole tree; anything the bake does not
# explicitly restage simply is not on the ISO. cava.conf (the visualizer +
# CAVA_BASS feed), _nyxus_accent.scss (imported by eww.scss.source) and
# nyxus-palette.css were all lost this way. build-iso.sh now has a catch-all
# loop; this asserts it stays effective.
if [[ -d "${NS}/eww" ]]; then
  if grep -q 'for _ef in "\${NS}"/eww/\*' "${HERE}/build-iso.sh"; then
    ok "bake restages every top-level NS/eww file (catch-all present)"
  else
    fail "build-iso.sh lost the NS/eww catch-all — new eww files will vanish at bake"
  fi
  for _need in cava.conf _nyxus_accent.scss nyxus-palette.css; do
    if [[ -f "${NS}/eww/${_need}" ]]; then
      ok "eww support file present in NS: ${_need}"
    else
      fail "eww support file MISSING from NS: ${_need}"
    fi
  done
fi
WP_CONF="${AIROOT}/etc/skel/.config/nyxus/wallpaper.conf"
if [[ -f "${WP_CONF}" ]]; then
  # Runtime schema: WALLPAPER="slug" + WALLPAPER_PATH="/abs/path" (consumed by
  # nyxus-wallpaper-autostart and nyxus_wallpaper_studio.py).
  WP_DEFAULT=$(grep -oP '^WALLPAPER_PATH="?\K[^"]+' "${WP_CONF}" | head -1)
  WP_SLUG=$(grep -oP '^WALLPAPER="?\K[^"]+' "${WP_CONF}" | head -1)
else
  WP_DEFAULT=""; WP_SLUG=""
fi
SDDM_BG="${AIROOT}/usr/share/sddm/themes/nyxus/backgrounds"
SDDM_PNG=$(find "${SDDM_BG}" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
# The greeter ships a CURATED set of alien hero backgrounds (see HANDOFF.md
# "SDDM greeter = urban-alien heroes"), not the full wallpaper pack. Require
# the mirror to be non-empty AND to contain the default hero, so the login
# screen always has its alien art — without demanding all ${WP_PNG} wallpapers.
if (( SDDM_PNG >= 1 )) && [[ -n "${WP_SLUG}" && -f "${SDDM_BG}/${WP_SLUG}.png" ]]; then
  ok "${SDDM_PNG} alien hero background(s) mirrored to SDDM greeter (incl. default '${WP_SLUG}')"
else
  fail "SDDM greeter backgrounds: have ${SDDM_PNG}, need >=1 incl. default hero '${WP_SLUG}.png'"
fi
if [[ -f "${WP_CONF}" ]]; then
  # WALLPAPER_PATH may be either a system-wide path (e.g.
  # /usr/share/backgrounds/nyxus/<slug>.png — user-agnostic, the current
  # canonical form) or a per-user runtime path under the live user's $HOME
  # (e.g. /home/<user>/... — populated from /etc/skel at first login, so it
  # does not exist in the build-time airootfs). Resolve both against airootfs:
  #   /home/<user>/REST  -> /etc/skel/REST
  #   /anything/else     -> checked as-is under airootfs
  if [[ "${WP_DEFAULT}" == /home/* ]]; then
    WP_DEFAULT_REL="${WP_DEFAULT#/home/}"          # user/REST...
    WP_DEFAULT_CHECK="/etc/skel/${WP_DEFAULT_REL#*/}"
  else
    WP_DEFAULT_CHECK="${WP_DEFAULT}"
  fi
  if [[ -n "${WP_DEFAULT}" && -f "${AIROOT}${WP_DEFAULT_CHECK}" ]]; then
    ok "default wallpaper present: ${WP_DEFAULT}"
  else
    fail "default WALLPAPER_PATH invalid or missing: '${WP_DEFAULT}'"
  fi
  if [[ -n "${WP_SLUG}" ]] && grep -qP "^${WP_SLUG}\t" "${WP_DIR}/manifest.tsv"; then
    ok "default WALLPAPER slug listed in manifest: ${WP_SLUG}"
  else
    fail "default WALLPAPER slug missing or not in manifest: '${WP_SLUG}'"
  fi
else
  fail "wallpaper.conf missing"
fi
[[ -x "${AIROOT}/usr/local/bin/nyxus-set-wallpaper" ]] \
  && ok "nyxus-set-wallpaper present + executable" \
  || fail "nyxus-set-wallpaper missing/not-exec"
[[ -x "${AIROOT}/usr/local/bin/nyxus-wallpaper-autostart" ]] \
  && ok "nyxus-wallpaper-autostart present + executable" \
  || fail "nyxus-wallpaper-autostart missing/not-exec"
[[ -f "${AIROOT}/opt/nyxus/nyxus_wallpaper_studio.py" ]] \
  && ok "nyxus_wallpaper_studio.py module present" \
  || fail "wallpaper studio module missing"

# ── 13d. NYXUS Aurora cursor theme ────────────────────────────────────
hd "13d. NYXUS Aurora cursor theme"
CT_DIR="${AIROOT}/usr/share/icons/NYXUS-Aurora"
[[ -f "${CT_DIR}/manifest.hl" ]] && ok "manifest.hl present" || fail "manifest.hl missing"
[[ -f "${CT_DIR}/index.theme" ]] && ok "XCursor index.theme present" || fail "index.theme missing"
CT_SHAPES=$(find "${CT_DIR}/hyprcursors" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
if (( CT_SHAPES >= 12 )); then
  ok "${CT_SHAPES} cursor shapes shipped"
else
  fail "only ${CT_SHAPES} cursor shapes (expected >=12)"
fi
grep -q "HYPRCURSOR_THEME,NYXUS-Aurora" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "Hyprland HYPRCURSOR_THEME wired" \
  || fail "Hyprland HYPRCURSOR_THEME not set"
grep -q "gtk-cursor-theme-name=NYXUS-Aurora" "${AIROOT}/etc/skel/.config/gtk-3.0/settings.ini" \
  && ok "GTK3 cursor wired" || fail "GTK3 cursor not wired"
grep -q "gtk-cursor-theme-name=NYXUS-Aurora" "${AIROOT}/etc/skel/.config/gtk-4.0/settings.ini" \
  && ok "GTK4 cursor wired" || fail "GTK4 cursor not wired"
grep -q "hyprctl setcursor NYXUS-Aurora" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "cursor setcursor wired in user session" \
  || fail "cursor setcursor not wired in hyprland exec-once"

# ── 13e. NYXUS Game Mode + Focus Mode ─────────────────────────────────
hd "13e. NYXUS Game Mode + Focus Mode"
[[ -x "${AIROOT}/usr/local/bin/nyxus-gamemode" ]] \
  && ok "nyxus-gamemode present + executable" \
  || fail "nyxus-gamemode missing/not-exec"
[[ -x "${AIROOT}/usr/local/bin/nyxus-focusmode" ]] \
  && ok "nyxus-focusmode present + executable" \
  || fail "nyxus-focusmode missing/not-exec"
[[ -f "${AIROOT}/etc/polkit-1/rules.d/50-nyxus-cpupower.rules" ]] \
  && ok "cpupower polkit rule present" \
  || fail "cpupower polkit rule missing"
grep -q "nyxus-gamemode toggle" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "Game Mode hotkey bound" || fail "Game Mode hotkey missing"
grep -q "nyxus-focusmode toggle" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "Focus Mode hotkey bound" || fail "Focus Mode hotkey missing"

# ── 13f. NYXUS workspace names + per-workspace wallpapers ─────────────
hd "13f. NYXUS workspaces"
[[ -f "${AIROOT}/etc/skel/.config/nyxus/stations.json" ]] \
  && ok "stations.json shipped" || fail "stations.json missing"
[[ -f "${AIROOT}/etc/skel/.config/nyxus/stations-hacker.json" ]] \
  && ok "stations-hacker.json shipped" || fail "stations-hacker.json missing"
[[ -f "${AIROOT}/etc/skel/.config/nyxus/workspaces.json" ]] \
  && ok "workspaces.json shipped" || fail "workspaces.json missing"
[[ -x "${AIROOT}/usr/local/bin/nyxus-workspace-wallpaperd" ]] \
  && ok "ws wallpaper daemon present + executable" \
  || fail "ws wallpaper daemon missing/not-exec"
[[ -f "${AIROOT}/etc/skel/.config/systemd/user/nyxus-ws-wallpaperd.service" ]] \
  && ok "ws wallpaper systemd unit present" \
  || fail "ws wallpaper systemd unit missing"
WS_MAIN="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
WS_STATIONS="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-stations.conf"
if [[ -f "${WS_STATIONS}" ]]; then
  WS_NAMES=$(grep -Ec '^workspace = [0-9]+,' "${WS_STATIONS}")
else
  WS_NAMES=$(grep -Ec '^workspace = [0-9]+,' "${WS_MAIN}")
fi
if (( WS_NAMES >= 10 )); then
  ok "${WS_NAMES} named workspaces declared"
else
  fail "only ${WS_NAMES} named workspaces (expected 10)"
fi

# ── 13g. NYXUS first-run welcome tour ─────────────────────────────────
hd "13g. NYXUS welcome tour"
[[ -f "${AIROOT}/opt/nyxus/nyxus_welcome.py" ]] \
  && ok "nyxus_welcome.py present" || fail "nyxus_welcome.py missing"
grep -q "/usr/local/bin/nyxus-welcome" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "welcome auto-launch wired in user session" \
  || fail "welcome auto-launch not wired in hyprland exec-once"

# ── 13h. NYXUS Battery Health + Network Usage + Store ─────────────────
hd "13h. NYXUS Battery / Network / Store"
[[ -f "${AIROOT}/opt/nyxus/nyxus_battery.py" ]]  && ok "battery module present"  || fail "battery module missing"
[[ -f "${AIROOT}/opt/nyxus/nyxus_netusage.py" ]] && ok "netusage module present" || fail "netusage module missing"
[[ -f "${AIROOT}/opt/nyxus/nyxus_store.py" ]]    && ok "store module present"    || fail "store module missing"
[[ -x "${AIROOT}/usr/local/bin/nyxus-store-install" ]] \
  && ok "nyxus-store-install present + executable" \
  || fail "nyxus-store-install missing/not-exec"
[[ -f "${AIROOT}/etc/skel/.config/nyxus/store-catalog.json" ]] \
  && ok "store catalog shipped" || fail "store catalog missing"

# ── 13i. NYXUS theming engine (accent picker) ─────────────────────────
hd "13i. NYXUS theming engine"
[[ -x "${AIROOT}/usr/local/bin/nyxus-apply-accent" ]] \
  && ok "nyxus-apply-accent present + executable" \
  || fail "nyxus-apply-accent missing/not-exec"
[[ -f "${AIROOT}/etc/skel/.config/nyxus/accent.json" ]] \
  && ok "accent.json shipped" || fail "accent.json missing"

# ── 13j. NYXUS bar plugin API ─────────────────────────────────────────
hd "13j. NYXUS bar plugin API"
[[ -x "${AIROOT}/usr/local/bin/nyxus-bar-plugins" ]] \
  && ok "nyxus-bar-plugins loader present + executable" \
  || fail "nyxus-bar-plugins loader missing/not-exec"
[[ -d "${AIROOT}/etc/skel/.config/nyxus/plugins" ]] \
  && ok "user plugin dir shipped" || fail "user plugin dir missing"
EX_DIR="${AIROOT}/usr/share/nyxus/plugins/example-quote"
[[ -f "${EX_DIR}/manifest.json" && -f "${EX_DIR}/widget.yuck" ]] \
  && ok "example plugin shipped" || fail "example plugin missing"

# ── 13k. Tier A polish (Plymouth/GRUB/Sync/KDE Connect/EQ) ────────────
hd "13k. Tier A · Plymouth + GRUB + Sync + KDE Connect + EQ"
# Plymouth HOOK must precede autodetect for kms early splash to work.
if grep -Eq '^HOOKS=\([^)]*\budev\s+plymouth\b' "${AIROOT}/etc/mkinitcpio.conf"; then
  ok "plymouth HOOK inserted in mkinitcpio.conf"
else
  fail "plymouth HOOK missing from mkinitcpio.conf HOOKS=(...)"
fi
# GRUB theme — theme.txt + ALL pixmaps it references.
GTH="${AIROOT}/usr/share/grub/themes/nyxus"
[[ -f "${GTH}/theme.txt" ]] && ok "grub theme.txt present" \
  || fail "grub theme.txt missing"
[[ -s "${GTH}/background.png" ]] && ok "grub background.png present" \
  || fail "grub background.png missing (run scripts/generate-grub-theme.py)"
for pm in select_c.png select_e.png select_w.png \
          terminal_box_c.png terminal_box_n.png terminal_box_s.png \
          terminal_box_e.png terminal_box_w.png \
          terminal_box_ne.png terminal_box_nw.png \
          terminal_box_se.png terminal_box_sw.png; do
  [[ -s "${GTH}/${pm}" ]] || fail "grub pixmap missing: ${pm}"
done
ok "grub pixmaps complete (12 files)"
# /etc/default/grub references our theme + splash cmdline.
GD="${AIROOT}/etc/default/grub"
if [[ -f "${GD}" ]] && grep -q 'GRUB_THEME=.*nyxus' "${GD}" \
   && grep -q 'splash' "${GD}"; then
  ok "/etc/default/grub wired to nyxus theme + splash cmdline"
else
  fail "/etc/default/grub missing or not wired (theme + splash)"
fi
# NYXUS Sync — nyxus-account helper exists + parses + supports CLI flags.
NA="${AIROOT}/usr/local/bin/nyxus-account"
if [[ -x "${NA}" ]] && bash -n "${NA}" 2>/dev/null \
   && grep -q -- '--push' "${NA}" && grep -q -- '--pull' "${NA}"; then
  ok "nyxus-account helper present + parses + supports --push/--pull"
else
  fail "nyxus-account helper missing/broken (SyncPage will dangle)"
fi
# KDE Connect package + autostart.
grep -Eq '^kdeconnect$' "${PROFILE}/packages.x86_64" \
  && ok "kdeconnect in packages.x86_64" \
  || fail "kdeconnect not in packages.x86_64"
grep -q 'kdeconnect-indicator' "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "kdeconnect-indicator autostart wired" \
  || fail "kdeconnect-indicator autostart missing in hyprland.conf"
# EasyEffects package + presets + autostart.
grep -Eq '^easyeffects$' "${PROFILE}/packages.x86_64" \
  && ok "easyeffects in packages.x86_64" \
  || fail "easyeffects not in packages.x86_64"
EE_DIR="${AIROOT}/etc/skel/.config/easyeffects/output"
COUNT=0
[[ -d "${EE_DIR}" ]] && COUNT=$(ls "${EE_DIR}"/*.json 2>/dev/null | wc -l)
if (( COUNT >= 3 )); then
  ok "easyeffects presets shipped (${COUNT} files)"
else
  fail "easyeffects presets missing (have ${COUNT}, need >=3)"
fi
grep -q 'easyeffects --gapplication-service' \
  "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
  && ok "easyeffects autostart wired" \
  || fail "easyeffects autostart missing in hyprland.conf"

# ── 13l. Tier B (Virt / Containers / Kernel / Gaming / Editors) ──────
hd "13l. Tier B · Virt + Containers + Kernel + Gaming + Editors"
# NOTE (rev 2026-07-23): linux-lts / linux-zen / linux-hardened were dropped —
# NYXUS ships the Kage Ryu kernel as primary with stock `linux` as rescue only
# (see packages.x86_64 "NYXUS Kernel policy"). Do not re-add them here.
for pkg in qemu-desktop libvirt virt-manager virt-viewer edk2-ovmf swtpm \
           buildah skopeo distrobox \
           steam mangohud \
           code helix micro gnome-text-editor; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done
for h in nyxus-virt-setup nyxus-distrobox-helper \
         nyxus-kernel-switch nyxus-protonup; do
  HP="${AIROOT}/usr/local/bin/${h}"
  if [[ -x "${HP}" ]] && bash -n "${HP}" 2>/dev/null; then
    ok "${h} present + parses"
  else
    fail "${h} missing/not-executable/bad"
  fi
done
# Settings page registration: every Tier B key must be in PAGE_CLASSES
# AND in SECTIONS AND have a glyph.
NSS="${NS}/nyxus_settings.py"
for key in virt containers kernel gaming editors; do
  grep -q "\"${key}\":" "${NSS}" \
    && ok "Settings: ${key} registered" \
    || fail "Settings: ${key} not registered"
done

# ── 13m. Tier C (USB / Secure Boot / VPN / DoH / MAC) ────────────────
hd "13m. Tier C · USB firewall + SecBoot + VPN + DoH + MAC random"
for pkg in usbguard wireguard-tools openvpn networkmanager-openvpn \
           networkmanager-strongswan sbctl tpm2-tools macchanger \
           dnscrypt-proxy; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done
for h in nyxus-usbguard-helper nyxus-secboot nyxus-vpn nyxus-doh \
         nyxus-mac-randomize; do
  HP="${AIROOT}/usr/local/bin/${h}"
  if [[ -x "${HP}" ]] && bash -n "${HP}" 2>/dev/null; then
    ok "${h} present + parses"
  else
    fail "${h} missing/not-executable/bad"
  fi
done
# usbguard ships PERMISSIVE — verify safe defaults so user doesn't get locked out
UG_CONF="${AIROOT}/etc/usbguard/usbguard-daemon.conf"
if [[ -f "${UG_CONF}" ]] \
   && grep -q '^PresentDevicePolicy=allow' "${UG_CONF}" \
   && grep -q '^ImplicitPolicyTarget=allow' "${UG_CONF}"; then
  ok "usbguard ships permissive (PresentDevicePolicy=allow)"
else
  fail "usbguard daemon.conf missing or not permissive (lockout risk!)"
fi
[[ -f "${AIROOT}/etc/usbguard/rules.conf" ]] \
  && ok "usbguard rules.conf present (empty by design)" \
  || fail "usbguard rules.conf missing"
for key in usb_firewall secboot vpn doh mac_random; do
  grep -q "\"${key}\":" "${NS}/nyxus_settings.py" \
    && ok "Settings: ${key} registered" \
    || fail "Settings: ${key} not registered"
done

# ── 13n. Settings Completeness Standard (rev 2026-05-14) ────────────
hd "13n. Settings Completeness · Dock/Wallpaper/ThemePacks/Clipboard/Record/Assistant"
# Required helpers for the 6 new pages.
for h in nyxus-clipboard; do
  HP="${AIROOT}/usr/local/bin/${h}"
  if [[ -x "${HP}" ]] && bash -n "${HP}" 2>/dev/null; then
    ok "${h} present + parses"
  else
    fail "${h} missing/not-executable/bad"
  fi
done
# Backing tools (already required elsewhere; checked here so a regression
# in packages.x86_64 surfaces in the right section).
for pkg in cliphist wl-clipboard wf-recorder grim slurp; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done
# Every new section key is registered in PAGE_CLASSES.
for key in dock wallpaper themepacks clipboard record assistant; do
  grep -q "\"${key}\":" "${NS}/nyxus_settings.py" \
    && ok "Settings: ${key} registered" \
    || fail "Settings: ${key} not registered"
done
# Standard-footer foundation must be present in nyxus_settings.py.
for sym in make_keybinds_group make_reset_group make_advanced_group \
           _append_standard_footer; do
  grep -q "${sym}" "${NS}/nyxus_settings.py" \
    && ok "Standard footer: ${sym} present" \
    || fail "Standard footer: ${sym} missing"
done

# ── 13o. Tier 1 · Welcome / Onboarding wizard (rev 2026-05-14) ──────
hd "13o. Tier 1 · Welcome wizard"
# Wizard implementation (Python GTK4) must be present + parse.
WW_IMPL="${AIROOT}/opt/nyxus/nyxus_welcome.py"
if [[ -f "${WW_IMPL}" ]] && python3 -c "import ast; ast.parse(open('${WW_IMPL}').read())" 2>/dev/null; then
  ok "wizard impl present + parses (/opt/nyxus/nyxus_welcome.py)"
else
  fail "wizard impl missing or unparseable: ${WW_IMPL}"
fi
# Launcher binary must be present + executable + bash-clean.
WW_BIN="${AIROOT}/usr/local/bin/nyxus-welcome"
if [[ -x "${WW_BIN}" ]] && bash -n "${WW_BIN}" 2>/dev/null; then
  ok "nyxus-welcome launcher present + parses"
else
  fail "nyxus-welcome launcher missing/not-executable/bad: ${WW_BIN}"
fi
# Application .desktop entry must be present and point to nyxus-welcome.
WW_DSK="${AIROOT}/usr/share/applications/nyxus-welcome.desktop"
if [[ -f "${WW_DSK}" ]] && grep -q "^Exec=nyxus-welcome" "${WW_DSK}"; then
  ok "nyxus-welcome.desktop present + Exec wired"
else
  fail "nyxus-welcome.desktop missing or Exec= wrong: ${WW_DSK}"
fi
# First-boot autostart entry shipped via /etc/skel.
WW_AS="${AIROOT}/etc/skel/.config/autostart/nyxus-welcome.desktop"
if [[ -f "${WW_AS}" ]] && grep -q "^Exec=nyxus-welcome" "${WW_AS}"; then
  ok "first-boot autostart entry present"
else
  fail "first-boot autostart entry missing: ${WW_AS}"
fi
# Settings hub must register the welcome page.
if grep -q '"welcome":' "${NS}/nyxus_settings.py" \
   && grep -q "^class WelcomePage(SectionPage)" "${NS}/nyxus_settings.py"; then
  ok "Settings: welcome registered + WelcomePage class present"
else
  fail "Settings: welcome not registered or WelcomePage class missing"
fi
# Required runtime packages for the wizard backend (gtk4, libadwaita,
# python-gobject) — already in packages.x86_64 for the wallpaper studio,
# pinned here so a regression surfaces in this section.
for pkg in gtk4 libadwaita python-gobject; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

# ── 13p. Tier 1 · Login Screen / SDDM theme (rev 2026-05-14) ────────
hd "13p. Tier 1 · Login Screen (SDDM)"
# nyxus-loginscreen helper
LS_BIN="${AIROOT}/usr/local/bin/nyxus-loginscreen"
if [[ -x "${LS_BIN}" ]] && bash -n "${LS_BIN}" 2>/dev/null; then
  ok "nyxus-loginscreen helper present + parses"
else
  fail "nyxus-loginscreen helper missing/not-executable/bad: ${LS_BIN}"
fi
# Polkit policy
LS_POL="${AIROOT}/usr/share/polkit-1/actions/com.nyxus.loginscreen.policy"
if [[ -f "${LS_POL}" ]] \
   && grep -q "com.nyxus.loginscreen.write" "${LS_POL}"; then
  ok "polkit policy: com.nyxus.loginscreen.policy present"
else
  fail "polkit policy missing: ${LS_POL}"
fi
# Defaults file (used by `reset`)
LS_DEF="${AIROOT}/usr/share/nyxus/sddm.defaults.conf"
if [[ -f "${LS_DEF}" ]] && grep -q "^\[Theme\]" "${LS_DEF}"; then
  ok "sddm defaults file present"
else
  fail "sddm defaults file missing: ${LS_DEF}"
fi
# SDDM theme assets (existing)
LS_THEME="${AIROOT}/usr/share/sddm/themes/nyxus"
for f in Main.qml theme.conf metadata.desktop background.png; do
  if [[ -f "${LS_THEME}/${f}" ]]; then
    ok "sddm theme asset: ${f}"
  else
    fail "sddm theme missing: ${LS_THEME}/${f}"
  fi
done
# At least one background pack image
BG_COUNT=$(find "${LS_THEME}/backgrounds" -maxdepth 1 -type f \
            \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \
               -o -iname '*.webp' \) 2>/dev/null | wc -l)
if (( BG_COUNT >= 1 )); then
  ok "sddm background pack: ${BG_COUNT} images"
else
  fail "sddm background pack empty: ${LS_THEME}/backgrounds/"
fi
# Settings hub registration
if grep -q '"loginscreen":' "${NS}/nyxus_settings.py" \
   && grep -q "^class LoginScreenPage(SectionPage)" "${NS}/nyxus_settings.py"; then
  ok "Settings: loginscreen registered + LoginScreenPage class present"
else
  fail "Settings: loginscreen not registered or LoginScreenPage missing"
fi
# Required runtime packages — greetd + tuigreet (display manager for live ISO).
# rev 2026-07-16: the bare `tuigreet` package name does not resolve in Arch
# repos (only `greetd-tuigreet` does — confirmed via `pacman -Si tuigreet`
# failing during the real bake). packages.x86_64 was fixed to only list
# `greetd-tuigreet`; update this check to match instead of a name that was
# never actually installable.
for pkg in greetd greetd-tuigreet; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done
# Ensure SDDM is not present (greetd is the sole display manager).
if grep -Eq "^sddm\$" "${PROFILE}/packages.x86_64"; then
  fail "conflicting package: sddm must not be listed when greetd is chosen"
else
  ok "sddm absent (greetd is sole display manager)"
fi
# greetd config.toml must be present.
GREETD_CONF="${AIROOT}/etc/greetd/config.toml"
if [[ -f "${GREETD_CONF}" ]]; then
  ok "greetd config.toml present"
else
  fail "greetd config.toml missing: ${GREETD_CONF}"
fi

# ── 13q. Tier 1 · Plymouth boot splash (rev 2026-05-14) ────────────
hd "13q. Tier 1 · Plymouth boot splash"
PL_BIN="${AIROOT}/usr/local/bin/nyxus-plymouth"
if [[ -x "${PL_BIN}" ]] && bash -n "${PL_BIN}" 2>/dev/null; then
  ok "nyxus-plymouth helper present + parses"
else
  fail "nyxus-plymouth helper missing/not-executable/bad: ${PL_BIN}"
fi
PL_POL="${AIROOT}/usr/share/polkit-1/actions/com.nyxus.plymouth.policy"
if [[ -f "${PL_POL}" ]] \
   && grep -q "com.nyxus.plymouth.set-theme" "${PL_POL}"; then
  ok "polkit policy: com.nyxus.plymouth.policy present"
else
  fail "polkit policy missing: ${PL_POL}"
fi
PL_THEME="${AIROOT}/usr/share/plymouth/themes/nyxus"
for f in nyxus.plymouth nyxus.script background.png saucer.png beam.png; do
  if [[ -f "${PL_THEME}/${f}" ]]; then
    ok "plymouth theme asset: ${f}"
  else
    fail "plymouth theme missing: ${PL_THEME}/${f}"
  fi
done
# Manifest sanity: ModuleName=script + ScriptFile points to nyxus.script
if grep -q '^ModuleName=script' "${PL_THEME}/nyxus.plymouth" \
   && grep -q 'ScriptFile=.*nyxus.script' "${PL_THEME}/nyxus.plymouth"; then
  ok "plymouth manifest references script module + nyxus.script"
else
  fail "plymouth manifest malformed: ${PL_THEME}/nyxus.plymouth"
fi
# Plymouth Script lint: catch invented syntax (C-style ternary,
# arity-mismatched SetUpdateStatusFunction handler) — these silently
# degrade to fallback behavior at boot, so guard them at build time.
# Strip comment lines first (Plymouth Script comments start with `#`),
# then look for `<expr> ? <expr> : <expr>` patterns. We tolerate `?:`
# inside string literals by requiring at least one identifier-like
# character before the `?`.
if sed -E 's/[[:space:]]*#.*$//' "${PL_THEME}/nyxus.script" \
     | grep -E '[A-Za-z0-9_)][[:space:]]*\?[^?:]+:[^=]' >/dev/null; then
  fail "plymouth script uses C-style ternary — Plymouth Script does not support \`?:\`"
else
  ok "plymouth script: no ternary"
fi
if grep -qE 'SetUpdateStatusFunction *\( *progress_callback' \
     "${PL_THEME}/nyxus.script"; then
  fail "plymouth script: SetUpdateStatusFunction wired to (duration,progress) callback — wrong arity"
else
  ok "plymouth script: SetUpdateStatusFunction handler arity sound"
fi
# Pkexec safety lint for nyxus-loginscreen — never `bash -c` interpolated user paths.
if grep -nE "pkexec[^#]*bash -c[^|]*\\\$\\{" \
     "${AIROOT}/usr/local/bin/nyxus-loginscreen" >/dev/null; then
  fail "nyxus-loginscreen still has pkexec bash -c with shell interpolation"
else
  ok "nyxus-loginscreen: no pkexec shell-interpolation injection"
fi
# Settings hub registration
if grep -q '"plymouth":' "${NS}/nyxus_settings.py" \
   && grep -q "^class PlymouthPage(SectionPage)" "${NS}/nyxus_settings.py"; then
  ok "Settings: plymouth registered + PlymouthPage class present"
else
  fail "Settings: plymouth not registered or PlymouthPage missing"
fi
# Required runtime packages
for pkg in plymouth mkinitcpio; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

# ── 13r. Tier 1 · Sound Pack (rev 2026-05-14) ──────────────────────
hd "13r. Tier 1 · Sound Pack"
SD_BIN="${AIROOT}/usr/local/bin/nyxus-sound"
if [[ -x "${SD_BIN}" ]] && bash -n "${SD_BIN}" 2>/dev/null; then
  ok "nyxus-sound helper present + parses"
else
  fail "nyxus-sound helper missing/not-executable/bad: ${SD_BIN}"
fi
SD_POL="${AIROOT}/usr/share/polkit-1/actions/com.nyxus.sound.policy"
SD_SYSDEF="${AIROOT}/usr/local/libexec/nyxus-sound-system-default"
if [[ -f "${SD_POL}" ]] \
   && grep -q "com.nyxus.sound.set-system-default" "${SD_POL}"; then
  ok "polkit policy: com.nyxus.sound.policy present"
else
  fail "polkit policy missing: ${SD_POL}"
fi
# Polkit must target the dedicated root helper, NOT a generic shell
# (architect blocker: previously bound to /usr/bin/env bash -c).
if grep -q "exec.path.*nyxus-sound-system-default" "${SD_POL}"; then
  ok "polkit policy narrowly targets dedicated helper"
else
  fail "polkit policy must target /usr/local/libexec/nyxus-sound-system-default"
fi
# Dedicated root helper must exist + parse + reject arguments
if [[ -x "${SD_SYSDEF}" ]] && bash -n "${SD_SYSDEF}" 2>/dev/null \
   && grep -q "this helper takes no arguments" "${SD_SYSDEF}"; then
  ok "system-default helper present + parses + rejects args"
else
  fail "system-default helper missing/invalid: ${SD_SYSDEF}"
fi
# nyxus-sound must call into the dedicated helper, not ad-hoc shell
if grep -q '/usr/local/libexec/nyxus-sound-system-default' "${SD_BIN}" \
   && ! grep -q 'pkexec /usr/bin/env' "${SD_BIN}"; then
  ok "nyxus-sound delegates set-system-default to root helper"
else
  fail "nyxus-sound still uses pkexec env shell pattern"
fi
SD_THEME="${AIROOT}/usr/share/sounds/nyxus"
if [[ -f "${SD_THEME}/index.theme" ]] \
   && grep -q '^\[Sound Theme\]' "${SD_THEME}/index.theme" \
   && grep -q '^Inherits=freedesktop' "${SD_THEME}/index.theme"; then
  ok "sound theme manifest present + valid"
else
  fail "sound theme manifest missing/invalid: ${SD_THEME}/index.theme"
fi
# Required event coverage — every NYXUS event must exist as a real
# WAV file (no zero-byte files, no fake silence).
SD_EVENTS=(
  service-login service-logout screen-locked screen-unlocked
  message complete dialog-error dialog-warning dialog-information
  audio-volume-change power-plug power-unplug
  device-added device-removed bell-terminal
)
SD_FAILED=0
for evt in "${SD_EVENTS[@]}"; do
  f="${SD_THEME}/stereo/${evt}.wav"
  if [[ -f "${f}" ]] && (( $(stat -c%s "${f}") > 1024 )); then
    :
  else
    fail "sound event missing or empty: ${f}"
    SD_FAILED=1
  fi
done
(( SD_FAILED == 0 )) && ok "all 15 NYXUS sound events present (>1KB each)"
# WAV header sanity: every file must start with RIFF/WAVE
for f in "${SD_THEME}"/stereo/*.wav; do
  head -c 12 "${f}" | grep -q 'WAVE' \
    || { fail "not a valid WAV: ${f}"; SD_FAILED=1; }
done
(( SD_FAILED == 0 )) && ok "all WAV headers valid (RIFF/WAVE)"
# Settings hub registration
if grep -q '"sounds":' "${NS}/nyxus_settings.py" \
   && grep -q "^class SoundsPage(SectionPage)" "${NS}/nyxus_settings.py"; then
  ok "Settings: sounds registered + SoundsPage class present"
else
  fail "Settings: sounds not registered or SoundsPage missing"
fi
# Required runtime packages
for pkg in libcanberra sound-theme-freedesktop pipewire-pulse; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

# ── 13s. Tier 1 · Calamares Branding (rev 2026-05-14) ───────────────
hd "13s. Tier 1 · Calamares Branding"
CAL_BRAND="${AIROOT}/etc/calamares/branding/nyxus"
CAL_SETTINGS="${AIROOT}/etc/calamares/settings.conf"
CAL_LAUNCHER="${AIROOT}/usr/share/applications/install-nyxus.desktop"
CAL_DESKTOP="${AIROOT}/etc/skel/Desktop/install-nyxus.desktop"

[[ -f "${CAL_BRAND}/branding.desc" ]] \
  && ok "calamares: branding.desc present" \
  || fail "calamares: branding.desc missing"
grep -q '^componentName: nyxus' "${CAL_BRAND}/branding.desc" 2>/dev/null \
  && ok "calamares: componentName=nyxus" \
  || fail "calamares: componentName not 'nyxus'"
# ALIEN NEON palette lock: canonical cool-white text token must be present
grep -qi '#eef2fa' "${CAL_BRAND}/branding.desc" \
  && ok "calamares: ALIEN NEON text #eef2fa present" \
  || fail "calamares: ALIEN NEON text #eef2fa missing"

[[ -f "${CAL_BRAND}/show.qml" ]] \
  && ok "calamares: show.qml slideshow present" \
  || fail "calamares: show.qml missing"
# Slideshow sanity — must import QtQuick and define slides array
grep -q 'import QtQuick' "${CAL_BRAND}/show.qml" 2>/dev/null \
  && ok "calamares: show.qml imports QtQuick" \
  || fail "calamares: show.qml missing QtQuick import"
grep -q 'readonly property var slides' "${CAL_BRAND}/show.qml" 2>/dev/null \
  && ok "calamares: slideshow has slides[] array" \
  || fail "calamares: slideshow missing slides[] array"

[[ -f "${CAL_BRAND}/logo.png" ]] && (( $(stat -c%s "${CAL_BRAND}/logo.png") > 256 )) \
  && ok "calamares: logo.png present (>256B)" \
  || fail "calamares: logo.png missing/empty"
[[ -f "${CAL_BRAND}/welcome.png" ]] && (( $(stat -c%s "${CAL_BRAND}/welcome.png") > 256 )) \
  && ok "calamares: welcome.png present (>256B)" \
  || fail "calamares: welcome.png missing/empty"

[[ -f "${CAL_SETTINGS}" ]] \
  && grep -q '^branding: nyxus' "${CAL_SETTINGS}" \
  && ok "calamares: settings.conf points to branding=nyxus" \
  || fail "calamares: settings.conf missing or wrong branding"

# Required module configs (skip only 'summary' / 'mount' / 'umount' /
# 'unpackfs' / 'machineid' / 'localecfg'; 'partition' is required in this
# profile even though some installers treat it as a built-in/zero-config
# module).
for m in welcome locale timezone keyboard partition users \
         fstab displaymanager networkcfg hwclock \
         services-systemd grubcfg bootloader \
         packages shellprocess finished; do
  [[ -f "${AIROOT}/etc/calamares/modules/${m}.conf" ]] \
    || fail "calamares: missing module config ${m}.conf"
done

# Required modules must be wired in settings.conf
for m in welcome locale timezone keyboard partition users \
         fstab displaymanager networkcfg hwclock \
         services-systemd grubcfg bootloader \
         packages shellprocess finished; do
  # Match YAML list items like "- module" and "- module   # inline comment"
  grep -Eq "^[[:space:]]*-[[:space:]]*${m}([[:space:]]*(#.*)?)?$" "${CAL_SETTINGS}" \
    && ok "calamares: module '${m}' wired in settings.conf" \
    || fail "calamares: module '${m}' missing from settings.conf"
done

# Launcher (.desktop) — both system-wide and live-session desktop copy
if [[ -f "${CAL_LAUNCHER}" ]] \
   && grep -q '^Exec=pkexec calamares' "${CAL_LAUNCHER}" \
   && grep -q '^TryExec=calamares' "${CAL_LAUNCHER}"; then
  ok "calamares: install-nyxus.desktop launcher (system) valid"
else
  fail "calamares: install-nyxus.desktop launcher missing/wrong Exec"
fi
if [[ -f "${CAL_DESKTOP}" ]] \
   && grep -q '^Exec=pkexec calamares' "${CAL_DESKTOP}"; then
  ok "calamares: live-session desktop launcher present"
else
  fail "calamares: live-session desktop launcher missing"
fi
if [[ -f "${AIROOT}/etc/calamares/modules/shellprocess.conf" ]] \
   && grep -q 'rm -f /etc/sddm.conf.d/00-nyxus-live.conf' "${AIROOT}/etc/calamares/modules/shellprocess.conf"; then
  ok "calamares: shellprocess removes live-only sddm autologin override"
else
  fail "calamares: shellprocess must remove /etc/sddm.conf.d/00-nyxus-live.conf"
fi

# Calamares installation validation (Arch package or AUR build path):
# Calamares may be installed from repos OR built from AUR in customize_airootfs.sh.
# Matches either "_aur_build calamares" helpers or direct "yay/paru -S ... calamares" installs.
CALAMARES_AUR_PATTERN='(_aur_build[[:space:]]+calamares|((yay|paru)[[:space:]]+-S([^#\n]*[[:space:]])?calamares))([[:space:]]|$)'
if grep -qE '^calamares$' "${PROFILE}/packages.x86_64"; then
  ok "package: calamares"
elif [[ -f "${AIROOT}/root/customize_airootfs.sh" ]] \
     && grep -Eq "${CALAMARES_AUR_PATTERN}" "${AIROOT}/root/customize_airootfs.sh"; then
  ok "calamares built from AUR via customize_airootfs.sh"
else
  fail "calamares not in packages.x86_64 and not built in customize_airootfs.sh"
fi
# ckbcomp package was removed from official Arch repos; ensure we don't
# carry a hardcoded runtime dependency on it in shipped Calamares configs.
# Include *.desc because Calamares branding metadata lives in branding.desc.
if [[ -d "${AIROOT}/etc/calamares" ]] \
   && grep -rlq --include='*.conf' --include='*.desc' --include='*.qml' '\bckbcomp\b' "${AIROOT}/etc/calamares"; then
  fail "calamares config still references ckbcomp directly"
else
  ok "calamares config has no direct ckbcomp dependency"
fi

# ── 13t. Tier 1 · GRUB Theme (rev 2026-05-14) ──────────────────────
hd "13t. Tier 1 · GRUB Theme"
GRUB_THEME_DIR="${AIROOT}/usr/share/grub/themes/nyxus"
GRUB_DEFAULT="${AIROOT}/etc/default/grub"

if [[ -f "${GRUB_THEME_DIR}/theme.txt" ]] \
   && grep -q '^desktop-image:' "${GRUB_THEME_DIR}/theme.txt" \
   && grep -q 'boot_menu' "${GRUB_THEME_DIR}/theme.txt"; then
  ok "GRUB: theme.txt valid (desktop-image + boot_menu)"
else
  fail "GRUB: theme.txt missing/incomplete"
fi
grep -qi '#eef2fa' "${GRUB_THEME_DIR}/theme.txt" 2>/dev/null \
  && ok "GRUB: ALIEN NEON text #eef2fa present" \
  || fail "GRUB: ALIEN NEON text #eef2fa missing from theme.txt"

# Required theme assets
for f in background.png select_c.png select_e.png select_w.png \
         terminal_box_c.png terminal_box_n.png terminal_box_s.png \
         terminal_box_e.png terminal_box_w.png \
         terminal_box_ne.png terminal_box_nw.png \
         terminal_box_se.png terminal_box_sw.png; do
  if [[ -f "${GRUB_THEME_DIR}/${f}" ]] \
     && head -c 8 "${GRUB_THEME_DIR}/${f}" | grep -q $'\x89PNG'; then
    :
  else
    fail "GRUB asset missing/not-PNG: ${f}"
  fi
done
ok "GRUB: all 13 theme assets present + valid PNG"

if [[ -f "${GRUB_DEFAULT}" ]] \
   && grep -q '^GRUB_THEME=.*nyxus/theme.txt' "${GRUB_DEFAULT}" \
   && grep -q 'splash' "${GRUB_DEFAULT}"; then
  ok "GRUB: /etc/default/grub references nyxus theme + splash"
else
  fail "GRUB: /etc/default/grub missing theme/splash"
fi

# Calamares must propagate the theme to installed systems
if grep -q 'GRUB_THEME.*nyxus' \
   "${AIROOT}/etc/calamares/modules/grubcfg.conf" 2>/dev/null; then
  ok "GRUB: calamares grubcfg propagates nyxus theme to install"
else
  fail "GRUB: calamares grubcfg does not propagate theme"
fi

grep -Eq '^grub$' "${PROFILE}/packages.x86_64" \
  && ok "package: grub" \
  || fail "missing package: grub"

# ── 13u. Tier 1 · Notification Toasts (rev 2026-05-14) ─────────────
hd "13u. Tier 1 · Notification Toasts"
DUNST_RC="${AIROOT}/etc/skel/.config/dunst/dunstrc"
SWAYNC_CSS="${AIROOT}/etc/skel/.config/swaync/style.css"

if [[ -f "${DUNST_RC}" ]] \
   && grep -q '^\[urgency_low\]'      "${DUNST_RC}" \
   && grep -q '^\[urgency_normal\]'   "${DUNST_RC}" \
   && grep -q '^\[urgency_critical\]' "${DUNST_RC}"; then
  ok "dunst: dunstrc present with all 3 urgency sections"
else
  fail "dunst: dunstrc missing or incomplete"
fi
grep -qi '#eef2fa' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: ALIEN NEON text #eef2fa present" \
  || fail "dunst: ALIEN NEON text #eef2fa missing"
grep -qi 'font *= *Inter' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: Inter font set" \
  || fail "dunst: Inter font not set"
grep -qi 'corner_radius = 3' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: 3px corners applied" \
  || fail "dunst: corner_radius not locked to 3"
grep -qi 'background *= *\"#05060af7\"' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: glass background rgba(5,6,10,0.97) applied" \
  || fail "dunst: glass background missing"

if [[ -f "${SWAYNC_CSS}" ]] \
   && grep -q '\.notification' "${SWAYNC_CSS}" \
   && grep -q '\.control-center' "${SWAYNC_CSS}"; then
  ok "swaync: style.css present with .notification + .control-center"
else
  fail "swaync: style.css missing or incomplete"
fi
grep -qi '#eef2fa' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: ALIEN NEON text #eef2fa present" \
  || fail "swaync: ALIEN NEON text #eef2fa missing"
grep -qi 'font-family: \"Inter\"' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: Inter font set" \
  || fail "swaync: Inter font missing"
grep -qi 'border-radius: 3px' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: 3px corners applied" \
  || fail "swaync: border-radius not locked to 3px"

for pkg in dunst swaync; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

# ── 13v. ALIEN NEON palette/token compliance (chrome configs) ────────────────
hd "13v. ALIEN NEON palette/token compliance"
CHROME_SCAN=(
  "${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
  "${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-general.conf"
  "${AIROOT}/etc/skel/.config/dunst/dunstrc"
  "${AIROOT}/etc/skel/.config/alacritty/alacritty.toml"
  "${AIROOT}/etc/skel/.config/rofi/config.rasi"
  "${AIROOT}/etc/skel/.config/rofi/nyxus.rasi"
  "${AIROOT}/etc/skel/.config/rofi/startmenu.rasi"
  "${AIROOT}/etc/skel/.config/swaync/style.css"
)
# Old / drift palette hexes that must NEVER appear in chrome configs. The
# canonical ALIEN NEON colors (#7d3dff violet, #2bd2ff cyan, …) are ALLOWED
# and are intentionally NOT listed here. (A global palette find/replace once
# corrupted this list by rewriting the old violet/cyan hexes to the canonical
# ones, which turned this compliance check into a check that banned ALIEN
# NEON — do not reintroduce canonical colors below.)
FORBIDDEN_PATTERN='#(C084FC|7C3AED|5B21B6|a78bfa|a06bff|f4ead5|3ad8ff|06b6d4|0ea5e9|dc2626|ef4444)([^0-9a-fA-F]|$)|splat-pink|splat-purple|DARK MIRROR'
if grep -RIniE "${FORBIDDEN_PATTERN}" "${CHROME_SCAN[@]}" >/tmp/verify-profile-forbidden.out 2>/dev/null; then
  fail "chrome configs contain forbidden ALIEN NEON colors/tokens (see /tmp/verify-profile-forbidden.out)"
else
  ok "chrome configs: forbidden ALIEN NEON colors/tokens absent"
fi

# ── 13w. bake will actually SHIP everything hyprland.conf depends on ────────
# WHY THIS EXISTS (2026-07-28): build-iso.sh does `rm -rf skel/.config/hypr`
# and repopulates it from NS using a hand-maintained whitelist. Committing a
# shard in airootfs is therefore NOT enough to ship it — twice now a shard was
# committed, sourced, and silently deleted at bake:
#   2026-07-24  nyxus-arsenal-apps.conf  (W6)
#   2026-07-27  nyxus-consoles.conf      -> the shipped 2026.07.27 ISO booted
#                                          into Hyprland's "source= ... found
#                                          no match" banner at line 592
# The same hole swallowed nyxus-home-deck, the socket2 watcher that maps every
# station to its eww window, so that ISO showed HOME/START pills that switched
# to permanently empty workspaces.
#
# So do NOT check the whitelist. DERIVE the requirement from hyprland.conf and
# fail if the bake cannot satisfy it. A new shard or exec-once needs no edit
# here — it is caught automatically.
hd "13w. bake ships every sourced shard + exec-once binary"

HYPR_CONF="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
BUILD_SH="${HERE}/build-iso.sh"

if [[ ! -r "${HYPR_CONF}" ]]; then
  fail "cannot read ${HYPR_CONF}"
else
  # ── every `source =` shard must be committed, present in NS, identical in
  #    both, and reachable by one of build-iso.sh's copy rules.
  _n_shards=0
  while read -r _shard; do
    [[ -z "${_shard}" ]] && continue
    _n_shards=$((_n_shards + 1))
    _committed="${AIROOT}/etc/skel/.config/hypr/conf.d/${_shard}"
    _ns="${NS}/${_shard}"

    if [[ ! -f "${_committed}" ]]; then
      fail "sourced shard not committed in airootfs: conf.d/${_shard}"
      continue
    fi
    if [[ ! -f "${_ns}" ]]; then
      fail "sourced shard missing from NS (bake repopulates from NS, so the ISO will not have it): ${_shard}"
      continue
    fi
    if ! cmp -s "${_committed}" "${_ns}"; then
      fail "sourced shard DRIFTED between NS and airootfs — the bake ships the NS copy: ${_shard}"
      continue
    fi
    # reachable by the nyxus-hyprland-*.conf glob, or named in the shard loop?
    if [[ "${_shard}" == nyxus-hyprland-*.conf ]] || grep -qF "${_shard}" "${BUILD_SH}"; then
      ok "shard ships: ${_shard}"
    else
      fail "sourced shard is NOT in build-iso.sh's copy list — it will be wiped at bake: ${_shard}"
    fi
  done < <(grep -oE 'source *= *~?/?[^ ]*conf\.d/[A-Za-z0-9._-]+\.conf' "${HYPR_CONF}" \
             | sed 's|.*/||' | sort -u)
  ok "checked ${_n_shards} sourced conf.d shard(s)"

  # ── every nyxus-* binary an exec-once invokes must land in airootfs. It may
  #    be committed directly, installed from NS, or generated by a heredoc —
  #    all three are fine, absence is not. `.service` units are excluded here
  #    and checked separately below (they are systemd units, not binaries).
  while read -r _bin; do
    [[ -z "${_bin}" ]] && continue
    if [[ -e "${AIROOT}/usr/local/bin/${_bin}" ]] || [[ -e "${AIROOT}/usr/bin/${_bin}" ]]; then
      ok "exec-once binary committed: ${_bin}"
    elif grep -qE "(LBIN|local/bin)[^\"']*/?${_bin}\"?$|/${_bin}\"" "${BUILD_SH}"; then
      ok "exec-once binary staged at bake: ${_bin}"
    else
      fail "hyprland.conf exec-once's '${_bin}' but the bake never stages it — it will be 'command not found' on the ISO"
    fi
  done < <(grep -E '^\s*exec-once' "${HYPR_CONF}" \
             | sed 's/nyxus-[a-z0-9-]*\.service//g' \
             | grep -oE '\bnyxus-[a-z0-9-]+' | sort -u)

  # ── every `systemctl --user start X.service` needs the unit in skel AND the
  #    payload the unit's ExecStart points at. A shipped unit whose ExecStart
  #    target is absent fails silently at login, which is indistinguishable
  #    from "the feature was never wired up".
  _UNIT_DIR="${AIROOT}/etc/skel/.config/systemd/user"
  while read -r _unit; do
    [[ -z "${_unit}" ]] && continue
    if [[ ! -f "${_UNIT_DIR}/${_unit}" ]]; then
      fail "hyprland.conf starts ${_unit} but the unit is not in skel systemd/user"
      continue
    fi
    # Resolve what ExecStart actually runs. Take the LAST absolute path on the
    # line, not the first: `ExecStart=/usr/bin/python3 /opt/nyxus/nyxus_qsd.py`
    # would otherwise "verify" that python3 exists, which proves nothing about
    # whether the daemon's own script got staged.
    _payload="$(grep -m1 '^ExecStart=' "${_UNIT_DIR}/${_unit}" \
                  | sed 's/^ExecStart=//' | tr ' ' '\n' \
                  | grep -E '^/(opt|usr|home)/' | tail -1)"
    _pbase="$(basename "${_payload}")"
    if [[ -z "${_payload}" ]]; then
      ok "unit ships: ${_unit}"
    elif [[ -e "${AIROOT}${_payload}" ]] \
         || [[ -f "${NS}/${_pbase}" ]] \
         || grep -qF "${_pbase}" "${BUILD_SH}"; then
      # present in airootfs, or in NS (the bake glob-copies NS/nyxus_*.py into
      # /opt/nyxus), or named explicitly in build-iso.sh
      ok "unit ships + payload staged: ${_unit} -> ${_payload}"
    else
      fail "${_unit} ExecStart=${_payload} but the bake never stages that payload"
    fi
  done < <(grep -E '^\s*exec-once' "${HYPR_CONF}" \
             | grep -oE 'nyxus-[a-z0-9-]+\.service' | sort -u)
fi

# ── the station matrix ships from a THIRD tree, not from skel ───────────────
# artifacts/nyxus-config/ overwrites skel/.config/nyxus/stations*.json at bake
# (build-iso.sh NYXUS_CFG). So a fix applied only to the committed skel copy is
# silently discarded — which is how stations-hacker.json kept 9=BLAST / 10=EDGE
# after the Jul 27 rename, and why a single hacker-mode flip reverted station
# identity on a machine that looked correct in git.
NYXCFG="${HERE}/../artifacts/nyxus-config"
for _j in stations.json stations-hacker.json; do
  if [[ ! -f "${NYXCFG}/${_j}" ]]; then
    warn "artifacts/nyxus-config/${_j} absent — bake will ship whatever is in skel"
  elif ! cmp -s "${NYXCFG}/${_j}" "${AIROOT}/etc/skel/.config/nyxus/${_j}"; then
    fail "${_j} DRIFTED between artifacts/nyxus-config and skel — the bake ships the nyxus-config copy"
  else
    ok "station matrix in sync: ${_j}"
  fi
done

# Station identity must not change between the normal and hacker matrices.
# Hacker mode themes wallpaper and launch commands, NOT which station is which.
if [[ -f "${NYXCFG}/stations.json" && -f "${NYXCFG}/stations-hacker.json" ]] \
   && command -v jq >/dev/null 2>&1; then
  if diff -q <(jq -r '.stations[]|"\(.id) \(.name)"' "${NYXCFG}/stations.json" 2>/dev/null) \
             <(jq -r '.stations[]|"\(.id) \(.name)"' "${NYXCFG}/stations-hacker.json" 2>/dev/null) \
             >/dev/null 2>&1; then
    ok "station identity identical in normal + hacker matrices"
  else
    fail "station names differ between stations.json and stations-hacker.json — a hacker-mode flip will silently rename stations"
  fi
fi

# ── 13y. reactive bus: producers are actually STARTED + threat chain ──
# The whole reactive layer shipped with NOTHING starting nyxus-sense, so
# sense.json was never written, nyxus-mood never pushed SENSE, and the bars sat
# on a defvar default forever. The consumers were fine; the producer was never
# launched. This gate asserts each link of the chain exists AND is wired,
# because "the script is committed" was never the part that was broken.
hd "13y. reactive bus + threat signal"
HYPRCONF="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
EWWY="${AIROOT}/etc/skel/.config/eww/eww.yuck"
EWWCSS="${AIROOT}/etc/skel/.config/eww/eww.css"

if grep -q 'conf\.d/nyxus-reactive\.conf' "${HYPRCONF}"; then
  ok "nyxus-reactive.conf is sourced by hyprland.conf"
else
  fail "nyxus-reactive.conf NOT sourced - the reactive bus never starts"
fi

for _d in nyxus-sense nyxus-mood nyxus-threatd; do
  if grep -rqs "${_d} start" "${AIROOT}/etc/skel/.config/hypr/"; then
    ok "producer autostarted: ${_d}"
  else
    fail "producer NEVER started: ${_d} (nothing in hypr config launches it)"
  fi
done

for _d in nyxus-sense nyxus-mood nyxus-threatd; do
  if [[ -x "${AIROOT}/usr/local/bin/${_d}" ]]; then
    if python3 -c "import ast;ast.parse(open('${AIROOT}/usr/local/bin/${_d}').read())" 2>/dev/null; then
      ok "producer ships + parses: ${_d}"
    else
      fail "producer ships but FAILS to parse: ${_d}"
    fi
  else
    fail "producer missing or not executable: /usr/local/bin/${_d}"
  fi
done

if grep -q 'THREAT=' "${AIROOT}/usr/local/bin/nyxus-threatd" 2>/dev/null; then
  ok "threatd pushes the THREAT defvar to eww"
else
  fail "threatd does not push THREAT - the bars would never see a threat level"
fi
if grep -q '(defvar THREAT ' "${EWWY}"; then
  ok "eww declares the THREAT defvar"
else
  fail "eww has no THREAT defvar - threatd's push would be dropped"
fi
if grep -q 'ws-threat-' "${EWWY}"; then
  ok "eww renders threat state (ws-threat-* on the GHOST pill)"
else
  fail "no widget consumes THREAT - the signal would be invisible"
fi

_MISSING_CSS=0
for _c in ws-threat-watch ws-threat-alert ws-threat-breach ws-threat-blind; do
  grep -q "\.${_c}" "${EWWCSS}" || { warn "  threat class has no CSS rule: .${_c}"; _MISSING_CSS=1; }
done
if (( _MISSING_CSS == 0 )); then
  ok "all 4 threat classes have CSS in eww.css"
else
  fail "a threat class the yuck emits has no rule in eww.css"
fi

# The threat classes are APPENDED to .ws-pill-<hue>; equal specificity means
# source order decides. Above the hue rules they do nothing.
_LAST_PILL=$(grep -nE '^\.ws-pill[a-z0-9-]*(:[a-z-]+)?[[:space:]]*\{' "${EWWCSS}" | tail -1 | cut -d: -f1)
_FIRST_THREAT=$(grep -nE '^\.ws-threat-' "${EWWCSS}" | head -1 | cut -d: -f1)
if [[ -n "${_LAST_PILL}" && -n "${_FIRST_THREAT}" ]] && (( _FIRST_THREAT > _LAST_PILL )); then
  ok "threat rules sit AFTER every .ws-pill rule (line ${_FIRST_THREAT} > ${_LAST_PILL})"
else
  fail "threat CSS is above a .ws-pill rule - equal specificity means it is dead"
fi

# jq's `//` treats false as empty, so a boolean defaulting to TRUE cannot use it.
# Getting this wrong reports blind=true even when the bus said false, inverting
# the one field that exists to prevent a misreport.
if grep -q 'threat_blind:  (if (.threat.blind == null)' \
        "${AIROOT}/etc/skel/.config/eww/scripts/sense-poll.sh" 2>/dev/null; then
  ok "sense-poll.sh null-checks threat_blind (jq // would invert it)"
else
  warn "sense-poll.sh threat_blind may be using jq // (false // true == true)"
fi


# ── 13x. Hyprland version guard (hyprlang removal + build-host skew) ────────
# TWO REAL PROBLEMS, both found 2026-07-28:
#
# 1. hyprlang is being REMOVED. Lua configs landed in 0.55 and upstream said
#    the old .conf syntax survives "1-2 releases" after that, i.e. gone at
#    ~0.57. NYXUS is hyprland.conf + 17 hyprlang shards, and three of those
#    shards are GENERATED at runtime (nyxus-hacker-mode, nyxus-freeform,
#    Settings). So the first bake that pulls 0.57 produces an ISO where the
#    entire desktop config silently stops loading - no bars, no keybinds, no
#    stations. That must never happen by accident, so it is a hard FAIL.
#
# 2. BUILD-HOST SKEW. The bake installs Hyprland from the Arch repos at bake
#    time, so the ISO can ship a different version than the box the config was
#    developed and "verified live" on. The 2026.07.27 ISO shipped 0.56.1 while
#    the builder box ran 0.55.4 - which is exactly why `hyprctl configerrors`
#    was clean here and the ISO showed an error banner. Warn loudly, because
#    "I tested it live" means very little across a version gap.
#
# Override for a deliberate experiment: NYX_ALLOW_HYPRLAND=1
hd "13x. Hyprland version guard"

_hypr_avail="$(pacman -Si hyprland 2>/dev/null | awk -F': ' '/^Version/{print $2; exit}')"
_hypr_host="$(pacman -Q hyprland 2>/dev/null | awk '{print $2}')"

if [[ -z "${_hypr_avail}" ]]; then
  warn "cannot query the hyprland version from the repos (offline?) — guard skipped"
else
  _hv="${_hypr_avail%%-*}"
  _maj="${_hv%%.*}"; _rest="${_hv#*.}"; _min="${_rest%%.*}"
  printf '        repos offer hyprland %s   build host has %s\n' "${_hypr_avail}" "${_hypr_host:-none}"

  if [[ "${_maj}" == "0" ]] && (( ${_min:-0} >= 57 )) && [[ "${NYX_ALLOW_HYPRLAND:-0}" != "1" ]]; then
    fail "hyprland ${_hypr_avail} DROPS hyprlang — this profile's hyprland.conf + 17 shards would not load AT ALL"
    fail "  migrate the config to Lua first (see HANDOFF 'hyprlang is being REMOVED'),"
    fail "  or bake deliberately with NYX_ALLOW_HYPRLAND=1 if you know why"
  elif [[ "${_maj}" == "0" ]] && (( ${_min:-0} >= 57 )); then
    warn "hyprland ${_hypr_avail} drops hyprlang — proceeding only because NYX_ALLOW_HYPRLAND=1"
  else
    ok "hyprland ${_hypr_avail} still supports hyprlang (.conf)"
  fi

  if [[ -n "${_hypr_host}" && "${_hypr_host}" != "${_hypr_avail}" ]]; then
    warn "VERSION SKEW: the ISO will ship ${_hypr_avail} but this box runs ${_hypr_host}"
    warn "  config verified live here is NOT verified against what boots — update the host or pin the ISO"
  elif [[ -n "${_hypr_host}" ]]; then
    ok "build host matches what the ISO will ship (${_hypr_host})"
  fi
fi

# ── 13z. shipped configs must not reach a tool through ~/.local/bin ─────────
# WHY THIS EXISTS (2026-07-30): the owner kept flashing a freshly baked stick
# and seeing "the old desktop". The ISO was correct every single time — the
# build stamp, /etc/skel, /home/nyx and /opt/nyxus-cache were byte-identical to
# HEAD. What was wrong was the PATH the configs used to reach their own tools.
#
# /home/nyx/.local/bin ships EMPTY (nothing stages into it), yet the hypr
# configs invoked 21 distinct nyxus tools by the hardcoded path
# `~/.local/bin/<tool>`. On THIS builder box ~/.local/bin holds all 21, so every
# one of them worked when a change was "verified live" here — and every one was
# dead on the stick. That silently killed the living/reflex layer
# (nyxus-living -> pulsed), nyxus-soundd, `nyxus-shader restore`, ~20 flair
# keybinds, the three headline reactive features (whispers / supernova /
# graffiti wall) and all five hyprlock widgets (weather, lock art, track
# chip+title+artist) — i.e. exactly the "none of my improvements are there"
# symptom, on every bake.
#
# Gate 13w does NOT catch this: it reads only hyprland.conf (never the conf.d
# shards), and it asserts the binary SHIPS, not that the config's path to it
# RESOLVES. Every one of these tools is in /usr/local/bin, which is on the
# default PATH, so the correct and only portable form is the bare command name.
hd "13z. no shipped config reaches a tool through ~/.local/bin"

_lb_fail=0; _lb_warn=0; _lb_files=0
_LB_RE='(~|\$HOME|\$\{HOME\})/\.local/bin/'

while IFS= read -r _cfg; do
  [[ -r "${_cfg}" ]] || continue
  _lb_files=$((_lb_files + 1))
  _rel="${_cfg#"${HERE}/"}"
  while IFS= read -r _hit; do
    [[ -z "${_hit}" ]] && continue
    _ln="${_hit%%:*}"; _txt="${_hit#*:}"
    # Strip a leading comment marker so a commented-out directive is still
    # recognised as a directive (and flagged before someone uncomments it).
    _bare="$(printf '%s' "${_txt}" | sed 's/^[[:space:]]*#*[[:space:]]*//')"
    # Prose that merely mentions the path is fine; only lines that RUN
    # something matter (hypr binds/execs + hyprlock text/reload_cmd).
    printf '%s' "${_bare}" \
      | grep -qE '^(bind[a-z]*|exec-once|exec|text|reload_cmd)[[:space:]]*=' \
      || continue
    _tool="$(printf '%s' "${_txt}" | grep -oE "${_LB_RE}[A-Za-z0-9_.-]+" \
               | head -1 | sed 's|.*/||')"
    if printf '%s' "${_txt}" | grep -qE '^[[:space:]]*#'; then
      warn "${_rel}:${_ln} commented directive still uses ~/.local/bin/${_tool} — dead if uncommented"
      _lb_warn=$((_lb_warn + 1))
    elif [[ -e "${AIROOT}/usr/local/bin/${_tool}" ]]; then
      fail "${_rel}:${_ln} runs '${_tool}' via ~/.local/bin — EMPTY on the ISO. Use the bare name; it ships in /usr/local/bin"
      _lb_fail=$((_lb_fail + 1))
    else
      fail "${_rel}:${_ln} runs '${_tool}' via ~/.local/bin — EMPTY on the ISO, and '${_tool}' is not in /usr/local/bin either"
      _lb_fail=$((_lb_fail + 1))
    fi
  done < <(grep -nE "${_LB_RE}" "${_cfg}" 2>/dev/null)
done < <({
  find "${AIROOT}/etc/skel/.config/hypr" -maxdepth 2 -name '*.conf' 2>/dev/null
  # The bake repopulates skel from NS, so the NS copies are what actually ship.
  find "${NS}" -maxdepth 1 \( -name 'hypr*.conf' -o -name 'nyxus-*.conf' \) 2>/dev/null
} | sort -u)

if (( _lb_fail == 0 )); then
  ok "checked ${_lb_files} shipped hypr config(s) — none reach a tool through ~/.local/bin"
fi
(( _lb_warn > 0 )) \
  && warn "${_lb_warn} commented directive(s) still carry the ~/.local/bin prefix"

# The premise above, asserted rather than assumed: if a future bake ever DOES
# stage a populated ~/.local/bin into skel, this gate's reasoning changes and
# whoever did that should see this note fire.
_SKEL_LB="${AIROOT}/etc/skel/.local/bin"
if [[ -d "${_SKEL_LB}" ]] && [[ -n "$(ls -A "${_SKEL_LB}" 2>/dev/null)" ]]; then
  warn "skel/.local/bin is NOT empty ($(ls -A "${_SKEL_LB}" | wc -l) entries) — re-read gate 13z's premise"
else
  ok "skel/.local/bin is empty/absent — bare command names are the only portable form"
fi

# ── 13aa. ~/.local/bin OUTSIDE the hypr configs ───────────────────────────────
# Gate 13z covers hyprland.conf / hyprlock.conf / the conf.d shards. The same
# bug class lives in every OTHER shipped config that names an executable, and
# two real instances were found there on 2026-07-30 after 13z was already green:
#
#   skel/.config/dunst/dunstrc  -> script = /home/nyx/.local/bin/nyxus-notif-to-eww
#   skel/.config/eww/scripts/hotkey-record.sh -> exec "${HOME}/.local/bin/nyxus-hotkey"
#
# The dunst one was the worse of the two: that rule also sets skip_display=true,
# so dunst suppressed its own popup AND the eww bridge could not start —
# notifications were swallowed entirely on the stick, which is also why nothing
# ever surfaced an error toast for any of the other broken features.
hd "13aa. dead ~/.local/bin paths outside the hypr configs"
_aa_fail=0; _aa_files=0
_AA_RE='(\$\{?HOME\}?|~|/home/[a-z][a-z0-9_-]*)/\.local/bin/'
while IFS= read -r _f; do
  [[ -f "${_f}" ]] || continue
  _aa_files=$((_aa_files + 1))
  _rel="${_f#"${HERE}/"}"
  while IFS= read -r _hit; do
    [[ -z "${_hit}" ]] && continue
    _ln="${_hit%%:*}"; _txt="${_hit#*:}"
    # Comments and prose are fine; only lines that actually name an executable
    # matter. Skip anything whose first non-space char starts a comment.
    printf '%s' "${_txt}" | grep -qE '^[[:space:]]*(#|//|\*)' && continue
    _tool="$(printf '%s' "${_txt}" | grep -oE "${_AA_RE}[A-Za-z0-9_.-]+" \
               | head -1 | sed 's|.*/||')"
    [[ -z "${_tool}" ]] && continue
    if [[ -e "${AIROOT}/usr/local/bin/${_tool}" ]]; then
      fail "${_rel}:${_ln} reaches '${_tool}' through ~/.local/bin — EMPTY on the ISO. It ships in /usr/local/bin; use the bare name (or the absolute /usr/local/bin path where PATH is not guaranteed, e.g. dunstrc)"
      _aa_fail=$((_aa_fail + 1))
    else
      warn "${_rel}:${_ln} reaches '${_tool}' through ~/.local/bin, and '${_tool}' is not in /usr/local/bin either — that feature cannot work on the ISO at all"
    fi
  done < <(grep -nE "${_AA_RE}" "${_f}" 2>/dev/null)
done < <({
  # Everything under skel that can name a program, minus the hypr tree that
  # gate 13z already owns.
  find "${AIROOT}/etc/skel/.config" -type f \
       \( -name '*.sh' -o -name '*.conf' -o -name '*.yuck' -o -name '*rc' \
          -o -name '*.py' -o -name '*.json' -o -name '*.desktop' \) 2>/dev/null \
    | grep -v '/\.config/hypr/'
  # ...and the NS originals the bake actually repopulates skel FROM.
  find "${NS}/eww" -type f 2>/dev/null
  ls "${NS}"/nyxus-dunstrc "${NS}"/nyxus-rofi* "${NS}"/nyxus-wlogout* 2>/dev/null
} | sort -u)
(( _aa_fail == 0 )) \
  && ok "checked ${_aa_files} shipped config(s) outside hypr — none reach a tool through ~/.local/bin"

# ── 13ab. every shipped station launch resolves to something on the ISO ──────
# 2026-07-30: stations FORGE and CORE shipped `on-created-empty:cursor` and
# `on-created-empty:thunar`. NEITHER binary is in the image (`cursor` is not
# packaged for Arch at all; `thunar` was never in packages.x86_64) — so
# clicking those two station pills genuinely did nothing, with no error and
# nothing in the journal. `btop` was the same story from the other direction:
# the profile ships THREE btop themes plus btop.conf into skel and four launch
# paths fall back to it, and btop itself was not in packages.x86_64.
#
# Rule enforced: the LAST fallback in every launch chain must resolve, because
# that is the only branch the ISO is guaranteed to reach. Unresolvable EARLIER
# branches are fine by design (that is what `command -v` guards are for) but
# are reported as warnings so a silently-never-taken branch is visible.
hd "13ab. station on-created-empty targets exist on the ISO"
_STATIONS_JSON="${HERE}/../artifacts/nyxus-config/stations.json"
if [[ -r "${_STATIONS_JSON}" ]] && command -v jq >/dev/null 2>&1; then
  _PKGS="${PROFILE}/packages.x86_64"
  _ab_fail=0; _ab_n=0
  # A command resolves if it ships as a nyxus tool, is a listed package (the
  # pkg name matches the binary for every launcher used here), or is a shell
  # builtin/coreutil that is always present.
  _resolves() {
    local c="$1"
    [[ -e "${AIROOT}/usr/local/bin/${c}" ]] && return 0
    [[ -e "${AIROOT}/usr/bin/${c}" ]]       && return 0
    grep -qxF "${c}" "${_PKGS}" 2>/dev/null && return 0
    case "${c}" in sh|bash|exec|true|echo|cd|python3|env) return 0 ;; esac
    return 1
  }
  while IFS=$'\t' read -r _id _name _launch; do
    [[ -n "${_launch}" ]] || continue
    _ab_n=$((_ab_n + 1))
    # Pull out every candidate program in the chain, in order: the words that
    # follow `exec`/`command -v`, plus the leading word of the whole launch.
    mapfile -t _cands < <(
      printf '%s\n' "${_launch}" \
        | grep -oE '(command -v|exec) +[A-Za-z0-9_.-]+' \
        | awk '{print $NF}'
      printf '%s\n' "${_launch}" | awk '{print $1}'
    )
    # De-dup while preserving order; drop the sh/exec noise words.
    _chain=(); for _c in "${_cands[@]}"; do
      case "${_c}" in sh|exec|""|-*) continue ;; esac
      [[ " ${_chain[*]} " == *" ${_c} "* ]] || _chain+=("${_c}")
    done
    (( ${#_chain[@]} )) || continue
    _last="${_chain[-1]}"
    for _c in "${_chain[@]}"; do
      _resolves "${_c}" && continue
      if [[ "${_c}" == "${_last}" ]]; then
        fail "station ${_id} (${_name}): last-resort launch '${_c}' is NOT on the ISO — this station opens NOTHING. Add it to packages.x86_64 or append a fallback that does resolve"
        _ab_fail=$((_ab_fail + 1))
      else
        warn "station ${_id} (${_name}): '${_c}' is not on the ISO — that branch never fires (guarded, so not fatal)"
      fi
    done
  done < <(jq -r '.stations[] | [(.id|tostring), .name, (.launch // "")] | @tsv' "${_STATIONS_JSON}")
  (( _ab_fail == 0 )) \
    && ok "all ${_ab_n} station launch chains end in a program the ISO actually installs"

  # The shipped conf.d snapshot is regenerated from this JSON by
  # nyxus-hacker-mode, so the two must agree or the first mode flip silently
  # changes what the stations do.
  _SNAP="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-stations.conf"
  _drift=0
  while IFS=$'\t' read -r _id _launch; do
    [[ -n "${_launch}" ]] || continue
    grep -qF "workspace = ${_id}, persistent:true, defaultName:" "${_SNAP}" 2>/dev/null || continue
    grep -qF "on-created-empty:${_launch}" "${_SNAP}" 2>/dev/null \
      || { warn "nyxus-stations.conf station ${_id} has drifted from stations.json — the first hacker-mode flip will rewrite it"; _drift=$((_drift + 1)); }
  done < <(jq -r '.stations[] | [(.id|tostring), (.launch // "")] | @tsv' "${_STATIONS_JSON}")
  (( _drift == 0 )) && ok "nyxus-stations.conf snapshot matches stations.json (a hacker-mode flip is a no-op)"
else
  warn "stations.json unreadable or jq missing — skipped station launch check"
fi

# ── 13ac. nothing avoidable sits between plymouth and the greeter ────────────
# The 2026.07.27 ISO took 102s from splash to login. HANDOFF blamed
# nyxus-firstboot.service being Type=oneshot on multi-user.target; that fix DID
# ship in 07.29 and the owner reported no change, because it was only part of
# the picture. systemd.target(5): "Target units will automatically complement
# all configured dependencies of type Wants= or Requires= with dependencies of
# type After=" — so multi-user.target waits for EVERYTHING enabled into it, and
# graphical.target is Requires=+After= multi-user.target with greetd behind it.
# Each assertion below removes one measured item from that path.
hd "13ac. splash → greeter critical path"
_FB_UNIT="${AIROOT}/etc/systemd/system/nyxus-firstboot.service"
if grep -qE '^Type=simple' "${_FB_UNIT}" 2>/dev/null; then
  ok "nyxus-firstboot.service is Type=simple (does not hold multi-user.target open)"
else
  fail "nyxus-firstboot.service is not Type=simple — a oneshot here blocks multi-user.target, and graphical.target/greetd sit behind it"
fi

_HP_FRAG="${AIROOT}/etc/nyxus-firstboot.d/06-honeypot-stack.sh"
if grep -q '/run/archiso' "${_HP_FRAG}" 2>/dev/null; then
  ok "06-honeypot-stack.sh skips live media (no ~1GB docker load in front of the greeter)"
else
  fail "06-honeypot-stack.sh has no live-media guard — it will docker-load ~1GB off the USB on every live boot"
fi

_HPFW="${AIROOT}/usr/lib/systemd/system/nyxus-honeypot-firewall.service"
if grep -q 'ConditionPathExists=!/run/archiso' "${_HPFW}" 2>/dev/null; then
  ok "nyxus-honeypot-firewall.service skips live media (does not force a full dockerd start before login)"
else
  fail "nyxus-honeypot-firewall.service runs on live media: Requires=+After=docker.service and WantedBy=multi-user.target means dockerd must fully start before the greeter, to lock down containers that the live-media guard already skipped"
fi

_CUST="${AIROOT}/root/customize_airootfs.sh"
if grep -qE '^\s*systemctl disable NetworkManager-wait-online\.service' "${_CUST}" 2>/dev/null; then
  ok "NetworkManager-wait-online.service is disabled (docker/ollama no longer wait up to 60s for a network the live stick has not configured)"
else
  fail "customize_airootfs.sh does not disable NetworkManager-wait-online.service — 'systemctl enable NetworkManager' pulls it in, and docker.service + ollama.service are both After=network-online.target AND WantedBy=multi-user.target"
fi

# ── 13ad. squashfs compressor ────────────────────────────────────────────────
# Measured on this image's own content (2140MB of /usr/bin + /usr/lib/systemd,
# single-threaded, warm cache so only decode cost is compared):
#   xz  -Xbcj x86 -b 1M -Xdict-size 1M  ->  647.0 MB, 29.5s  ( 72 MB/s)
#   zstd -Xcompression-level 19 -b 1M   ->  716.7 MB,  3.9s  (549 MB/s)
# squashfs inflates a WHOLE 1MiB block to serve one 4KiB read, so under xz every
# cold file touch costs ~14.5ms of CPU. A desktop session start touches
# thousands of them. This is a WARN, not a FAIL — xz is a legitimate choice if
# ISO size ever matters more than live-session speed.
hd "13ad. squashfs compressor"
_COMPLINE="$(grep -E '^airootfs_image_tool_options=' "${PROFILE}/profiledef.sh" 2>/dev/null)"
case "${_COMPLINE}" in
  *"'zstd'"*) ok "airootfs squashfs uses zstd (~7.6x faster cold reads than xz on this content)" ;;
  *"'xz'"*)   warn "airootfs squashfs uses xz — ~7.6x slower cold reads for ~10.8% less size. Deliberate? bake with NYX_SQUASH_COMP to be explicit" ;;
  "")         fail "profiledef.sh has no airootfs_image_tool_options line" ;;
  *)          warn "unrecognised squashfs compressor: ${_COMPLINE}" ;;
esac

# ── 13ae. layerrule catch-all must not sit below the explicit rules ──────────
# Hyprland applies layerrules in file order, LAST match wins. The
# `^(nyxus.*)$` catch-all in nyxus-hyprland-layerblur.conf calls itself a
# catch-all "for future surfaces", but it shipped BELOW every explicit
# per-namespace rule, so it was really a global override that silently ate
# them. docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md §7.4 warns about exactly
# this ("the catch-all can undo `blur off`") and the frosted rectangular
# "shadow box" behind the bars was fought twice partly because of it.
# Moved to the top on 2026-07-30. This gate keeps it there.
hd "13ae. layer-blur catch-all is a floor, not an override"
_LB="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-layerblur.conf"
if [[ -r "${_LB}" ]]; then
  _catch="$(grep -nE '^layerrule = .*match:namespace \^\(nyxus\.\*\)\$' "${_LB}" \
              | tail -1 | cut -d: -f1)"
  _lastspecific="$(grep -nE '^layerrule = .*match:namespace nyxus-' "${_LB}" \
                     | tail -1 | cut -d: -f1)"
  if [[ -z "${_catch}" ]]; then
    warn "no ^(nyxus.*)$ catch-all in nyxus-hyprland-layerblur.conf — new eww surfaces will ship with no blur rule at all"
  elif [[ -z "${_lastspecific}" ]]; then
    warn "nyxus-hyprland-layerblur.conf has a catch-all but no explicit nyxus-* rules"
  elif (( _catch < _lastspecific )); then
    ok "catch-all at line ${_catch} precedes the last explicit nyxus-* rule (line ${_lastspecific}) — explicit rules win"
  else
    fail "the ^(nyxus.*)\$ catch-all is at line ${_catch}, BELOW the last explicit nyxus-* rule (line ${_lastspecific}). Hyprland's last-match-wins means the catch-all overrides every per-namespace rule in this file, including any 'blur off'. Move the catch-all above them"
  fi

  # Every eww namespace that is not the catch-all itself should have its own
  # rule now that the catch-all is only a floor.
  _EWWDIR="${AIROOT}/etc/skel/.config/eww"
  _missing=0
  while IFS= read -r _ns; do
    [[ -n "${_ns}" ]] || continue
    grep -qE "^layerrule = .*match:namespace ${_ns}\$" "${_LB}" && continue
    warn "eww namespace '${_ns}' has no explicit layerrule — it only gets the catch-all floor"
    _missing=$((_missing + 1))
  done < <(grep -rhoE ':namespace "nyxus-[a-z0-9-]+"' "${_EWWDIR}" 2>/dev/null \
             | sed -E 's/.*"(nyxus-[a-z0-9-]+)"/\1/' | sort -u)
  (( _missing == 0 )) && ok "every declared eww namespace has an explicit layerrule"
else
  fail "nyxus-hyprland-layerblur.conf is not in skel conf.d"
fi

# ── 13af. no `set -u` script dies on an unset session variable ───────────────
# nyxus-home-deck, nyxus-soundd and nyxus-tintd all ran `set -u` and then
# built their Hyprland socket path from a BARE ${XDG_RUNTIME_DIR} and
# ${HYPRLAND_INSTANCE_SIGNATURE}. In each of the three the immediately
# preceding line already used ${XDG_RUNTIME_DIR:-/tmp} — the author knew it
# could be unset and the guard just never reached the next line. Unset either
# variable and bash aborts the whole script with "unbound variable", so
# nyxus-home-deck did its one startup sync and then died: the station decks
# worked exactly once and then no station ever opened anything again, silently.
hd "13af. set -u scripts guard session env vars"
_af_fail=0; _af_n=0
while IFS= read -r _s; do
  [[ -f "${_s}" ]] || continue
  grep -qE '^set -[a-z]*u' "${_s}" || continue
  _af_n=$((_af_n + 1))
  while IFS= read -r _hit; do
    [[ -z "${_hit}" ]] && continue
    _ln="${_hit%%:*}"; _txt="${_hit#*:}"
    printf '%s' "${_txt}" | grep -qE '^[[:space:]]*#' && continue
    _var="$(printf '%s' "${_txt}" \
              | grep -oE '\$\{(XDG_RUNTIME_DIR|HYPRLAND_INSTANCE_SIGNATURE)\}' \
              | head -1 | tr -d '${}')"
    [[ -z "${_var}" ]] && continue
    # Most of these scripts open with
    #   export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    # which makes every later bare use safe. Only flag a variable that is
    # never given a default anywhere in the file.
    grep -qE "^[[:space:]]*(export[[:space:]]+)?${_var}=\"?\\\$\{${_var}:-" "${_s}" && continue
    fail "$(basename "${_s}"):${_ln} uses bare \${${_var}} under 'set -u' and never defaults it — if the session does not export it the script aborts on this line with 'unbound variable', before any of its own error handling runs. Either add \${${_var}:-<fallback>} here or hoist an 'export ${_var}=\"\${${_var}:-...}\"' to the top like nyxus-eww-launch-safe does"
    _af_fail=$((_af_fail + 1))
  done < <(grep -nE '\$\{(XDG_RUNTIME_DIR|HYPRLAND_INSTANCE_SIGNATURE)\}[^:]' "${_s}" 2>/dev/null)
done < <(find "${NS}" -maxdepth 1 -type f ! -name '*.conf' ! -name '*.md' \
              ! -name '*.json' ! -name '*.css' 2>/dev/null | sort)
(( _af_fail == 0 )) \
  && ok "checked ${_af_n} 'set -u' script(s) — all session env vars are guarded"

# ── 13ag. no shipped surface dispatches `workspace name:0` ───────────────────
# Hyprland resolves a NUMERIC `name:0` into the SPECIAL workspace range
# (id -1337) — a hidden overlay you cannot see. The HOME station was fixed to
# `name:HOME` in nyxus-stations-named.conf on 2026-07-26 and the reason is
# written out in that file's header, but three call sites kept the old form
# and were only found on 2026-07-30:
#
#   eww.yuck hub_home_pill        -> the Hub's own HOME pill went nowhere
#   nyxus-hub-search "home|dash"  -> same, from the Hub search box
#   stations-hacker.json .home    -> HOME broke on the first hacker-mode flip
#
# All three are inside the Hub or its data, which is a large part of why the
# Hub read as "nothing in here works".
hd "13ag. nothing dispatches the hidden special workspace (name:0)"
_ag_fail=0; _ag_n=0
while IFS= read -r _f; do
  [[ -f "${_f}" ]] || continue
  _ag_n=$((_ag_n + 1))
  _rel="${_f#"${HERE}/../"}"
  while IFS= read -r _hit; do
    [[ -z "${_hit}" ]] && continue
    _ln="${_hit%%:*}"; _txt="${_hit#*:}"
    # Comments (including the ones explaining this very rule) are fine.
    printf '%s' "${_txt}" | grep -qE '^[[:space:]]*(#|;;|//)' && continue
    fail "${_rel}:${_ln} dispatches 'name:0' — Hyprland reads a numeric name:0 as the SPECIAL workspace (id -1337), a hidden overlay, so this jumps somewhere invisible. Use 'name:HOME'"
    _ag_fail=$((_ag_fail + 1))
  done < <(grep -nE '(workspace[ ,]+name:0|"hypr"[[:space:]]*:[[:space:]]*"name:0")([^0-9]|$)' \
             "${_f}" 2>/dev/null)
done < <({
  find "${NS}" "${HERE}/../artifacts/nyxus-config" -type f \
       \( -name '*.yuck' -o -name '*.json' -o -name '*.conf' -o -name '*.sh' \) 2>/dev/null
  find "${NS}" -maxdepth 1 -type f ! -name '*.*' 2>/dev/null
  find "${AIROOT}/etc/skel/.config" "${AIROOT}/usr/local/bin" -type f 2>/dev/null
} | sort -u)
(( _ag_fail == 0 )) \
  && ok "checked ${_ag_n} shipped file(s) — none dispatch the hidden name:0 workspace"

# ── 13ua. URBAN-ALIEN idle/login/power surfaces stay urban-alien ─────────────
# e5c381d1 (2026-07-24) pinned the login screen, the lock screen and the idle
# screensaver to nyxus-urban-alien, and af1acb85 (2026-07-25) gave wlogout the
# same hero as its canvas. Every one of those is a one-line path in a file the
# bake reads from a DIFFERENT tree than the one you probably edited, and one of
# them (wlogout) was being silently reverted at RUNTIME by nyxus-gen-backdrop.
# This gate asserts the whole chain, on both surfaces the bake reads, so
# "urban-alien everywhere" cannot quietly decay back into stock art again.
hd "13ua. urban-alien login / lock / screensaver / power surfaces"
_UA_SYS="/usr/share/backgrounds/nyxus/nyxus-urban-alien.png"
_ua_fail=0
_uafail() { fail "$*"; _ua_fail=$((_ua_fail + 1)); }

# The art itself must ship, or every pin below silently falls back.
[[ -s "${AIROOT}${_UA_SYS}" ]] \
  || _uafail "${_UA_SYS} is not in the airootfs — hyprlock, the greeter, the screensaver and wlogout all resolve to this exact system path and every one of them falls back to flat ink without it"

# hyprlock (lock / re-login) background is the pinned system hero, not the
# retired rotating ~/.cache/nyxus/lock-wall.png.
for _f in "${NS}/hyprlock.conf" "${AIROOT}/etc/skel/.config/hypr/hyprlock.conf"; do
  if [[ -r "${_f}" ]]; then
    grep -qE "^[[:space:]]*path[[:space:]]*=[[:space:]]*${_UA_SYS}[[:space:]]*$" "${_f}" \
      || _uafail "$(basename "$(dirname "${_f}")")/$(basename "${_f}"): hyprlock background is not pinned to ${_UA_SYS}"
  else
    _uafail "missing ${_f}"
  fi
done

# The greeter copies the hero into the greeter-writable regreet cache on every
# start. regreet reads /var/cache/regreet/nyxus-login-bg.png, NOT the seed in
# /etc/greetd, so this copy is the only thing that makes the login screen
# urban-alien.
for _f in "${NS}/greetd/nyxus-greeter" "${AIROOT}/usr/local/bin/nyxus-greeter"; do
  if [[ -r "${_f}" ]]; then
    grep -q 'nyxus-urban-alien.png' "${_f}" \
      || _uafail "$(basename "${_f}") does not pin the login background to nyxus-urban-alien"
  else
    _uafail "missing ${_f}"
  fi
done
# ...and the dirs it writes into must be pre-created + chowned to `greeter` at
# bake, because greeter cannot mkdir under root-owned /var/lib and /var/cache.
grep -q 'chown.*greeter.*/var/cache/regreet\|/var/cache/regreet' \
     "${AIROOT}/root/customize_airootfs.sh" 2>/dev/null \
  || _uafail "customize_airootfs.sh no longer provisions /var/cache/regreet — the greeter runs unprivileged and every cp into it will silently no-op, leaving the login screen with no background at all"

# The screensaver launcher must run the urban-alien saver, not the retired
# matrix-rain one, and must pin the wall it renders.
for _f in "${NS}/nyxus-screensaver" "${AIROOT}/usr/local/bin/nyxus-screensaver"; do
  if [[ -r "${_f}" ]]; then
    grep -q 'nyxus_screensaver\.py' "${_f}" \
      || _uafail "$(basename "${_f}") does not launch nyxus_screensaver.py (the urban-alien saver)"
    # prose comments about the retired saver are fine; a live line is not.
    grep -vE '^[[:space:]]*#' "${_f}" | grep -q 'nyxus_matrix_saver' \
      && _uafail "$(basename "${_f}") still launches nyxus_matrix_saver.py — that is the superseded matrix-rain effect the owner did not want; the urban-alien saver is canonical"
    grep -q "NYXUS_SCREENSAVER_WALL=.*nyxus-urban-alien.png" "${_f}" \
      || _uafail "$(basename "${_f}") does not pin NYXUS_SCREENSAVER_WALL to the urban-alien hero"
  else
    _uafail "missing ${_f}"
  fi
done
# The saver payload has to actually ship. skel/.config/nyxus is NOT in the
# bake's wipe list, so an unstaged payload survives by accident — until
# somebody edits the NS copy and wonders why the stick never changes.
[[ -s "${AIROOT}/etc/skel/.config/nyxus/nyxus_screensaver.py" ]] \
  || _uafail "nyxus_screensaver.py is not in skel/.config/nyxus — hypridle launches it by absolute \$HOME path and gets nothing"
grep -q 'nyxus_screensaver.py' "${HERE}/build-iso.sh" \
  || _uafail "build-iso.sh does not stage nyxus_screensaver.py from NS into skel — the shipped saver would be whatever is committed in airootfs, not the source of truth"

# hypridle is the only thing that drives any of it.
for _f in "${NS}/hypridle.conf" "${AIROOT}/etc/skel/.config/hypr/hypridle.conf"; do
  if [[ -r "${_f}" ]]; then
    grep -q 'nyxus-screensaver' "${_f}" \
      || _uafail "$(basename "$(dirname "${_f}")")/hypridle.conf never launches nyxus-screensaver — the idle screen is dead no matter how good the saver is"
    grep -q 'loginctl lock-session' "${_f}" \
      || _uafail "$(basename "$(dirname "${_f}")")/hypridle.conf never locks the session — idle would never reach hyprlock"
  else
    _uafail "missing ${_f}"
  fi
done
grep -qE '^exec-once = hypridle$' "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" 2>/dev/null \
  || _uafail "hyprland.conf does not exec-once hypridle — nothing starts the idle pipeline, so neither the screensaver nor the 10-minute lock ever fires"

# wlogout — the urban-alien canvas, and the runtime rewriter that used to eat it.
for _f in "${NS}/wlogout-style.css" "${AIROOT}/etc/skel/.config/wlogout/style.css"; do
  if [[ -r "${_f}" ]]; then
    grep -q "url(\"${_UA_SYS}\")" "${_f}" \
      || _uafail "$(basename "${_f}") lost the urban-alien canvas (background-image: url(\"${_UA_SYS}\"))"
  else
    _uafail "missing ${_f}"
  fi
done
for _f in "${NS}/nyxus-gen-backdrop" "${AIROOT}/usr/local/bin/nyxus-gen-backdrop"; do
  if [[ -r "${_f}" ]]; then
    if grep -qF "r'background-image:\\s*url\\(\"[^\"]+\"\\)\\s*;'" "${_f}"; then
      _uafail "$(basename "${_f}") rewrites the FIRST background-image in wlogout/style.css whatever it points at. nyxus-set-wallpaper calls this on every wallpaper change — including the one at login and on every station switch — so the pinned urban-alien canvas is replaced by a 42px-blurred derivative within seconds of every boot. Scope the regex to starfall-backdrop.png"
    else
      grep -q 'starfall-backdrop\\.png' "${_f}" \
        || warn "$(basename "${_f}") no longer scopes its wlogout rewrite to starfall-backdrop.png — check it cannot clobber a pinned hero"
    fi
  else
    _uafail "missing ${_f}"
  fi
done

# NS is the source of truth and the bake copies it over skel; any drift here
# means the file you read in one tree is not the file that boots.
for _pair in \
  "hyprlock.conf:etc/skel/.config/hypr/hyprlock.conf" \
  "hypridle.conf:etc/skel/.config/hypr/hypridle.conf" \
  "nyxus-screensaver:usr/local/bin/nyxus-screensaver" \
  "nyxus_screensaver.py:etc/skel/.config/nyxus/nyxus_screensaver.py" \
  "nyxus-gen-backdrop:usr/local/bin/nyxus-gen-backdrop" \
  "wlogout-style.css:etc/skel/.config/wlogout/style.css" \
  "greetd/nyxus-greeter:usr/local/bin/nyxus-greeter" ; do
  _src="${NS}/${_pair%%:*}"; _dst="${AIROOT}/${_pair#*:}"
  [[ -r "${_src}" && -r "${_dst}" ]] || continue
  cmp -s "${_src}" "${_dst}" \
    || _uafail "${_pair%%:*} differs between nyxus-scripts (source of truth) and airootfs — the bake installs the NS copy, so the airootfs edit ships nothing"
done

(( _ua_fail == 0 )) \
  && ok "urban-alien is pinned end to end: greeter -> hyprlock -> screensaver -> wlogout, on both trees the bake reads"

# ── 13ub. the urban-alien surfaces stay LOOKABLE, not just pinned ────────────
# 13ua proves the hero is wired up. It says nothing about whether you can see
# it, and on 2026-07-30 the owner's answer to all three was "no": the greeter
# card sat across the alien's legs, the Super+Escape overlay buried the mural
# under a 0.76/0.82 scrim, and the app-menu power window had no art at all.
# Each fix is a single number or a single block that a later edit can quietly
# undo, so each gets an assertion.
hd "13ub. urban-alien surfaces are actually visible (card placement, scrim, art)"
_ub_fail=0
_ubfail() { fail "$*"; _ub_fail=$((_ub_fail + 1)); }

# (a) The login card must clear the centre-composed alien. nyxus-urban-alien is
#     NOT the left-weighted art these margins were written for: at Cover on
#     1920x1080 the figure spans x~460..1550, so the old margin-left of 720px
#     put the card straight through it.
for _f in "${NS}/greetd/regreet.css" "${AIROOT}/etc/greetd/regreet.css"; do
  if [[ -r "${_f}" ]]; then
    _ml="$(grep -oE '^[[:space:]]*margin-left:[[:space:]]*[0-9]+px;' "${_f}" \
             | head -1 | grep -oE '[0-9]+')"
    if [[ -z "${_ml}" ]]; then
      _ubfail "$(basename "$(dirname "${_f}")")/regreet.css: the login frame has no plain \`margin-left: <n>px;\` line. nyxus-greeter rescales the card for the detected panel by rewriting that exact line — without it every screen gets the 1920x1080 numbers, and a narrower panel pushes the card off the edge where the operator cannot type a password"
    elif (( _ml < 1200 )); then
      _ubfail "$(basename "$(dirname "${_f}")")/regreet.css: login card margin-left is ${_ml}px. Anything below ~1200 lands it on the alien in nyxus-urban-alien.png (the figure runs to x~1550 at Cover on 1920x1080) — that is the 'old login screen' the owner reported. 1360px parks it in the starfield right of the sneaker"
    fi
  else
    _ubfail "missing ${_f}"
  fi
done
# ...and the greeter has to do the rescale, or those absolute pixels are a
# lockout waiting for the first non-1080p panel.
for _f in "${NS}/greetd/nyxus-greeter" "${AIROOT}/usr/local/bin/nyxus-greeter"; do
  [[ -r "${_f}" ]] || continue
  grep -q 'REGREET_STYLE' "${_f}" \
    || _ubfail "$(basename "${_f}") no longer generates a per-panel stylesheet (REGREET_STYLE). regreet.css positions the card in ABSOLUTE pixels tuned for 1920 wide; on a 1366x768 laptop those margins push the login card off screen"
done
# regreet's config + stylesheet have to actually be installed from NS. They were
# not, for the whole life of the file: NS carried a full copy that nothing ever
# staged, so editing the source of truth shipped nothing.
grep -q 'regreet.css' "${HERE}/build-iso.sh" \
  || _ubfail "build-iso.sh does not stage greetd/regreet.css from NS — the login screen would ship whatever is committed under airootfs, not the source of truth"
for _pair in "greetd/regreet.css:etc/greetd/regreet.css" \
             "greetd/regreet.toml:etc/greetd/regreet.toml" ; do
  _src="${NS}/${_pair%%:*}"; _dst="${AIROOT}/${_pair#*:}"
  [[ -r "${_src}" && -r "${_dst}" ]] || continue
  cmp -s "${_src}" "${_dst}" \
    || _ubfail "${_pair%%:*} differs between nyxus-scripts (source of truth) and airootfs"
done

# (b) The Super+Escape overlay's scrim. Above ~0.70 the ufo-shop mural is a
#     smudge; the card and buttons carry their own fills, so lowering it costs
#     no label contrast (measured 18.5:1 white / 11.5:1 grey at 0.52/0.60 over
#     the brightest 1% of the art).
#     Read the whole `(defwindow powermenu …)` form, not a fixed line window.
#     The first cut of this used `grep -A4` and a later commit added two comment
#     lines inside the block, which pushed the value out of the window and
#     failed a tree that was actually correct — i.e. it was asserting "do not
#     comment here". Slurp from the defwindow line to the next top-level `(def`
#     form so comments and blank lines anywhere inside are irrelevant.
for _f in "${NS}/eww/eww.yuck" "${AIROOT}/etc/skel/.config/eww/eww.yuck"; do
  [[ -r "${_f}" ]] || continue
  _sc="$(awk '/^\(defwindow powermenu([[:space:]]|$)/ { f = 1 }
              f && /^\(def/ && ++n > 1        { exit }
              f                               { print }' "${_f}" \
           | grep -oE 'linear-gradient\([[:space:]]*rgba\([[:space:]]*5,[[:space:]]*1,[[:space:]]*13,[[:space:]]*[0-9.]+' \
           | head -1 | grep -oE '[0-9]+\.[0-9]+$')"
  if [[ -z "${_sc}" ]]; then
    _ubfail "$(basename "${_f}"): the powermenu window no longer scrims the hero with linear-gradient(rgba(5,1,13,..)) — check the NYXUS · POWER overlay still shows the ufo-shop art"
  elif awk -v v="${_sc}" 'BEGIN{exit !(v > 0.70)}'; then
    _ubfail "$(basename "${_f}"): NYXUS · POWER scrim is back to ${_sc}. The owner asked to SEE the graffiti; 0.76 was the value that hid it, and the power labels do not depend on this number because .powermenu-root and .power-btn stack their own fills"
  fi
done

# (c) The standalone GTK power window — same menu, reached from the app menu
#     instead of the keybind — was the last flat power surface.
for _f in "${NS}/nyxus_powermenu.py" "${AIROOT}/opt/nyxus/nyxus_powermenu.py"; do
  [[ -r "${_f}" ]] || continue
  grep -q 'nyxus-urban-alien.png' "${_f}" \
    || _ubfail "$(basename "${_f}") lost its urban-alien wall — the app-menu power window falls back to flat ink while the keybind overlay, hyprlock, the greeter and the screensaver all wear the hero"
  grep -q 'set_measure_overlay' "${_f}" \
    || _ubfail "$(basename "${_f}") drops set_measure_overlay: the Gtk.Picture backdrop is set_can_shrink(True) and asks for no size, so the window collapses to set_default_size and clips the outer tiles and the ESC hint off the edge"
done

(( _ub_fail == 0 )) \
  && ok "the hero is visible on all three power/login surfaces, and the greeter scales its card to the panel"

# ── 13uc. every wallpaper a config names has a source the BAKE can reach ─────
# The wallpaper staging glob is `install "${NS}"/nyxus-*.png`, which only sees
# the ROOT of nyxus-scripts. Walls that live one directory down in
# nyxus-scripts/hypr-walls/ are invisible to it — that is the same bug the
# 2026-07-29 fix patched for hypr-walls/rotation/, and it was still true for
# nyxus-urban-alien-mono.png, the wallpaper stations-hacker.json puts on ALL
# TEN stations. It shipped anyway, because usr/share/backgrounds/nyxus is not
# in the bake's wipe list and a committed copy sat there — so hacker mode
# looked fine while the file had no source of truth the bake would ever read.
# skel/.config/hypr IS wiped, so that surface simply lost it.
#
# Assert the property that actually matters: for every wallpaper NAME any
# shipped config references, some file the staging globs reach must exist.
hd "13uc. every configured wallpaper has a source the bake stages"
_uc_fail=0
_uc_names="$( { for _j in "${NYXCFG}/stations.json" "${NYXCFG}/stations-hacker.json" \
                          "${NYXCFG}/wallpaper.json"; do
                  [[ -r "${_j}" ]] && grep -oE '"[A-Za-z0-9_.-]+\.png"' "${_j}" | tr -d '"'
                done
                if [[ -r "${NS}/wall-rotation.list" ]]; then
                  grep -vE '^[[:space:]]*(#|$)' "${NS}/wall-rotation.list" \
                    | sed -E 's#.*/##; s/[[:space:]]*$//; /\.png$/! s/$/.png/'
                fi
              } | sort -u )"
_uc_n=0
while IFS= read -r _w; do
  [[ -n "${_w}" ]] || continue
  _uc_n=$((_uc_n + 1))
  # the two globs build-iso.sh actually installs from
  [[ -f "${NS}/${_w}" || -f "${NS}/hypr-walls/rotation/${_w}" ]] && continue
  if [[ -f "${NS}/hypr-walls/${_w}" ]]; then
    fail "${_w} is referenced by a shipped config and exists at nyxus-scripts/hypr-walls/${_w}, but the bake only globs nyxus-scripts/*.png and hypr-walls/rotation/*.png — nothing stages it. Move it to the root of nyxus-scripts"
  else
    fail "${_w} is referenced by a shipped config and has NO source anywhere under nyxus-scripts — it can only ship as a committed airootfs blob, which skel/.config/hypr does not keep because the bake wipes that tree"
  fi
  _uc_fail=$((_uc_fail + 1))
done <<< "${_uc_names}"
(( _uc_fail == 0 )) \
  && ok "all ${_uc_n} configured wallpapers resolve to a file the bake installs"

# ── 13ud. no shipped consumer names a wallpaper that does not exist ──────────
# 13uc checks the STAGING half: a wallpaper a config names must have a source
# the bake installs. This is the REFERENCE half, and it is the one that bites
# when art is *removed* rather than added. On 2026-07-30 five images were
# dropped (a VectorStock-watermarked mural, plus graffiti-space, demon,
# login-stars and rot-black-void) and between them they were named in eleven
# places nobody would think to grep: the station and workspace matrices, three
# wall-rotation lists, nyxus-rotate-walls' built-in FALLBACK array,
# nyxus-graffiti-wall's BASE_SRC, the screensaver's candidate chain,
# nyxus-livewall-generate's no-config default, nyxus_install.sh's _soft_wall
# list, nyxus_chrome's app-background pool, and two SDDM installers.
#
# A dangling wallpaper reference never errors. It falls through to a black
# desktop, a blank lock surface, or flat cream behind every app window — which
# is precisely the silent-failure shape this project keeps re-shipping.
hd "13ud. every wallpaper a shipped consumer names actually exists"
_ud_fail=0; _ud_refs=0
# Names produced at RUNTIME rather than shipped as art. These are supposed to
# be absent from the source tree; flagging them would train people to ignore
# this gate.
_UD_RUNTIME='nyxus-login-bg|nyxus-lock-wall|nyxus-wallpaper|nyxus-graffiti-memory|nyxus-live-|nyxus-collage-|nyxus-livewall-flagship'
_UD_CONSUMERS=(
  "${NS}/nyxus-rotate-walls"            "${NS}/nyxus-graffiti-wall"
  "${NS}/nyxus-livewall-generate"       "${NS}/nyxus_screensaver.py"
  "${NS}/nyxus_chrome.py"               "${NS}/nyxus_install.sh"
  "${NS}/wall-rotation.list"            "${NS}/sddm-theme/install.sh"
  "${NYXCFG}/stations.json"             "${NYXCFG}/stations-hacker.json"
  "${NYXCFG}/workspaces.json"           "${NYXCFG}/wallpaper.json"
  "${AIROOT}/etc/skel/.config/nyxus/stations.json"
  "${AIROOT}/etc/skel/.config/nyxus/workspaces.json"
  "${AIROOT}/etc/skel/.config/nyxus/wallpaper.json"
  "${AIROOT}/etc/skel/.config/nyxus/wall-rotation.list"
  "${AIROOT}/usr/share/nyxus/wall-rotation.list"
  "${AIROOT}/usr/share/backgrounds/nyxus/manifest.tsv"
)
for _ud_f in "${_UD_CONSUMERS[@]}"; do
  [[ -r "${_ud_f}" ]] || continue
  # A wall-rotation.list stores bare slugs; everything else writes the filename.
  # Strip comments first so a line explaining a REMOVED image is not read as a
  # reference to it — that would make the gate impossible to ever satisfy.
  while IFS= read -r _ud_w; do
    [[ -n "${_ud_w}" ]] || continue
    printf '%s' "${_ud_w}" | grep -qE "^(${_UD_RUNTIME})" && continue
    _ud_refs=$((_ud_refs + 1))
    [[ -f "${NS}/${_ud_w}.png" || -f "${NS}/hypr-walls/rotation/${_ud_w}.png" ]] && continue
    fail "${_ud_f##*/} references the wallpaper '${_ud_w}', which exists nowhere the bake stages from. A missing wall does not error — it renders as a black desktop, a blank lock surface, or flat cream behind an app window"
    _ud_fail=$((_ud_fail + 1))
  done < <(sed -E 's/(^|[[:space:]])#.*$//; s@^[[:space:]]*(//|;;).*$@@' "${_ud_f}" \
             | grep -oE 'nyxus-[a-z0-9][a-z0-9-]*\.png' | sed 's/\.png$//' | sort -u
             if [[ "${_ud_f}" == *wall-rotation.list ]]; then
               # NOTE: `tr -d '[:space:]'` here would delete the NEWLINES too and
               # hand the loop all 29 slugs concatenated into one word, which is
               # how this gate first shipped: it reported a single impossible
               # filename instead of checking anything. Strip per line.
               sed -E 's/#.*$//' "${_ud_f}" | grep -oE '^[[:space:]]*nyxus-[a-z0-9-]+' | sed 's/[[:space:]]//g' | sort -u
             fi)
done
(( _ud_fail == 0 )) \
  && ok "checked ${_ud_refs} wallpaper reference(s) across ${#_UD_CONSUMERS[@]} shipped consumers — none dangle"

# ── 13ah. eww handlers must fit inside eww's run_command budget ──────────────
# eww runs every :onclick/:onchange as `/bin/sh -c <cmd>` and SIGKILLs that
# shell after :timeout, which DEFAULTS TO 200 MILLISECONDS (crates/eww
# widgets/mod.rs run_command(), identical in 0.5.0 and 0.6.0). Anything
# sequenced after a slow FOREGROUND command therefore never runs at all.
#
# `nyxus-hub-close` measured 231ms-3723ms on a live session on 2026-07-30 —
# it is a bash script that makes half a dozen eww socket round-trips and can
# relaunch four bars. Six shipped handlers were written `nyxus-hub-close; X`,
# so X was killed before it started. That is why every NYXUS Power action
# (Shutdown / Restart / Suspend / Logout / Lock) "did nothing but close the
# menu", and why the powermenu's own Cancel button did nothing at all.
#
# The fix is to background the WHOLE thing — `(nyxus-hub-close; X) &` — which
# is what the hub tiles already did correctly. This gate keeps it that way.
hd "13ah. eww onclick handlers survive the 200ms run_command budget"
_ah_slow='nyxus-hub-close|nyxus-hub-open|nyxus-eww-launch-safe|nyxus-eww-launch|nyxus-panic'
_ah_fail=0; _ah_files=0
while IFS= read -r _y; do
  [[ -f "${_y}" ]] || continue
  _ah_files=$((_ah_files + 1))
  while IFS= read -r _hit; do
    [[ -z "${_hit}" ]] && continue
    _ln="${_hit%%:*}"; _txt="${_hit#*:}"
    # the handler's command string, i.e. what eww hands to `sh -c`
    _cmd="$(printf '%s' "${_txt}" \
              | sed -nE 's/.*:on(click|middleclick|rightclick|change|hover)[[:space:]]+"([^"]*)".*/\2/p')"
    [[ -z "${_cmd}" ]] && continue
    printf '%s' "${_cmd}" | grep -qE "(${_ah_slow})" || continue
    # SAFE: the whole command is one detached subshell, so sh exits at once.
    printf '%s' "${_cmd}" | grep -qE '^\(.*\)[[:space:]]*&$' && continue
    # Otherwise every slow command must itself be detached: split the handler
    # on the shell separators and require the segment that holds a slow
    # command to end in `&`. `hyprctl dispatch ...; nyxus-hub-close &` is fine
    # (hyprctl is fast and nyxus-hub-close is backgrounded); the reverse is not.
    _stranded=""
    while IFS= read -r _seg; do
      printf '%s' "${_seg}" | grep -qE "(${_ah_slow})" || continue
      printf '%s' "${_seg}" | grep -qE '&[[:space:]]*$' && continue
      _stranded="${_seg#"${_seg%%[![:space:]]*}"}"
      break
    done < <(printf '%s' "${_cmd}" | sed -E 's/(&&|\|\||;)/\n/g')
    [[ -z "${_stranded}" ]] && continue
    fail "$(basename "${_y}"):${_ln} leaves \`${_stranded}\` in the FOREGROUND of \`${_cmd}\`. eww SIGKILLs the handler shell after 200ms (its run_command default) and nyxus-hub-close alone measured 231ms-3.7s, so nothing sequenced after it ever runs. Background the whole handler instead: \"(${_cmd}) &\" with the inner & removed"
    _ah_fail=$((_ah_fail + 1))
  done < <(grep -nE ':on(click|middleclick|rightclick|change|hover)[[:space:]]+"' "${_y}" 2>/dev/null)
done < <({ find "${NS}/eww" -maxdepth 1 -name '*.yuck'; \
           find "${AIROOT}/etc/skel/.config/eww" -maxdepth 1 -name '*.yuck'; } 2>/dev/null | sort)
(( _ah_fail == 0 )) \
  && ok "checked ${_ah_files} yuck file(s) — no handler strands its action behind a slow foreground command"

# ── 13ai. no fullscreen input surface on the OVERLAY layer ───────────────────
# HANDOFF Section 7: a fullscreen wlr-layer-shell surface on the OVERLAY layer
# with no input region sits above EVERYTHING and swallows every pointer event
# on the desktop. This was observed again live on 2026-07-30 — an unrelated
# fullscreen OVERLAY probe was up and made every click on every other surface
# vanish, including clicks on windows that were plainly visible.
#
# eww maps :stacking "overlay" -> OVERLAY and "fg" -> TOP. A fullscreen menu
# belongs on TOP: it still covers ordinary windows, but OSDs, notifications
# and hyprlock stay reachable above it, so the session can always talk to the
# user and the screen can always be locked.
hd "13ai. no fullscreen eww window sits on the OVERLAY layer"
_ai_fail=0; _ai_n=0
for _yuck in "${NS}/eww/eww.yuck" "${AIROOT}/etc/skel/.config/eww/eww.yuck"; do
  [[ -r "${_yuck}" ]] || continue
  _ai_n=$((_ai_n + 1))
  # defwindow blocks are separated by blank lines; pull name + stacking + size
  while IFS='|' read -r _win _stack _geo; do
    [[ -n "${_win}" ]] || continue
    [[ "${_stack}" == "overlay" ]] || continue
    [[ "${_geo}" == *'width "100%"'* && "${_geo}" == *'height "100%"'* ]] || continue
    # screensaver is the one surface that genuinely has to outrank everything,
    # including notifications and OSDs — it is not a menu, it carries no
    # control the user has to reach, and any input dismisses it.
    if [[ "${_win}" == "screensaver" ]]; then
      ok "defwindow ${_win} stays on OVERLAY on purpose (nothing may draw over the screensaver)"
      continue
    fi
    fail "$(basename "${_yuck}"): defwindow ${_win} is 100%x100% AND :stacking \"overlay\" — a fullscreen OVERLAY-layer surface eats every pointer event on the desktop and nothing (not even an OSD or hyprlock) can appear above it. Use :stacking \"fg\" unless it also carries an empty input region"
    _ai_fail=$((_ai_fail + 1))
  done < <(awk '
    /^\(defwindow /            { name=$2; stack=""; geo=""; want=1 }
    want && /:stacking[[:space:]]*"/ { s=$0; sub(/.*:stacking[[:space:]]*"/,"",s); sub(/".*/,"",s); stack=s }
    want && /:geometry/        { geo=geo $0 }
    want && /^$/               { if (name != "") print name "|" stack "|" geo; want=0; name="" }
    END                        { if (want && name != "") print name "|" stack "|" geo }
  ' "${_yuck}")
done
(( _ai_fail == 0 && _ai_n > 0 )) \
  && ok "checked ${_ai_n} eww config(s) — no fullscreen window claims the OVERLAY layer"

# ── 13aj. the bars keep their blur alpha-clip (shadow-box guard) ─────────────
# The frosted rectangular "shadow box" behind the bars is what the bars look
# like with NO alpha clip. Demonstrated live on 2026-07-30 by A/B-ing
# `hyprctl keyword layerrule 'ignore_alpha <v>, match:namespace nyxus-bar-*'`
# on a running session: at 0.0 the wallpaper behind each cluster and behind
# the whole left rail turns into a solid frosted slab; at 0.2, 0.45 and 0.6 it
# is crisp and only the pills carry frost. So the shipped value is already
# right and the bug is the rule going MISSING, not the number being wrong.
#
# The window/bar roots are `background: transparent` (alpha 0) and the pill
# fills are rgba(8,3,16,0.55) / rgba(24,10,44,0.62), so any threshold strictly
# between 0 and 0.55 clips the bleed and keeps the frost. Above 0.55 the pills
# lose their frost too, which is the other half of what the owner asked for.
hd "13aj. bar blur keeps an alpha clip below the pill fill"
_LBS="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-layerblur.conf"
_PILL_MIN="0.55"     # lowest pill background-color alpha in eww.css
if [[ -r "${_LBS}" ]]; then
  _aj_fail=0
  for _ns in nyxus-bar-top nyxus-bar-bottom nyxus-bar-left nyxus-bar-right; do
    _v="$(grep -E "^layerrule = ignore_alpha [0-9.]+, match:namespace ${_ns}\$" "${_LBS}" \
            | tail -1 | sed -E 's/^layerrule = ignore_alpha ([0-9.]+),.*/\1/')"
    if [[ -z "${_v}" ]]; then
      fail "${_ns} has no ignore_alpha layerrule — with blur on and no alpha clip the bar renders as a frosted rectangular slab (the 'shadow box'). Add: layerrule = ignore_alpha 0.2, match:namespace ${_ns}"
      _aj_fail=$((_aj_fail + 1)); continue
    fi
    if awk -v v="${_v}" 'BEGIN{exit !(v <= 0)}'; then
      fail "${_ns} has ignore_alpha ${_v} — 0 clips nothing, so the blur bleeds into the fully transparent parts of the bar and paints the shadow box"
      _aj_fail=$((_aj_fail + 1))
    elif awk -v v="${_v}" -v p="${_PILL_MIN}" 'BEGIN{exit !(v >= p)}'; then
      fail "${_ns} has ignore_alpha ${_v}, which is >= the ${_PILL_MIN} alpha of the pill fills — that clips the pills themselves and the frost disappears along with the box. Keep it strictly between 0 and ${_PILL_MIN}"
      _aj_fail=$((_aj_fail + 1))
    fi
  done
  (( _aj_fail == 0 )) \
    && ok "all four bars clip blur below the ${_PILL_MIN} pill alpha — frost on the pills, no slab behind them"
else
  fail "nyxus-hyprland-layerblur.conf is not in skel conf.d"
fi

# ── 13ak. no shipping config has an unread twin under nyxus-scripts/hypr ─────
# The bake reads Hyprland shards from the ROOT of nyxus-scripts:
#   build-iso.sh:  install "${NS}"/nyxus-hyprland-*.conf  and  "${NS}/${_shard}"
# It never looks in nyxus-scripts/hypr/conf.d/. That directory nevertheless
# held copies of nyxus-hyprland-layerblur.conf and nyxus-stations.conf, and
# both had drifted from the real ones — the layerblur twin was still the
# pre-2026-07-30 ordering. An agent grepping for "layerblur" finds the twin
# first, because its path looks canonical, edits it, verifies nothing, and
# ships nothing. This is the single most repeated bug on this project, so it
# gets a gate rather than another paragraph in HANDOFF.
hd "13ak. no unread duplicate Hyprland shards under nyxus-scripts/hypr"
_ak_fail=0; _ak_dir="${NS}/hypr/conf.d"
if [[ -d "${_ak_dir}" ]]; then
  while IFS= read -r _dup; do
    [[ -n "${_dup}" ]] || continue
    _b="$(basename "${_dup}")"
    if [[ -f "${NS}/${_b}" ]]; then
      fail "${_dup#${NS}/} is a copy of ${_b}, which the bake actually installs from ${NS}/${_b}. Nothing reads nyxus-scripts/hypr/conf.d/ — delete the copy so the next edit cannot land in a file that ships nothing"
    else
      fail "${_dup#${NS}/} lives in a directory the bake never reads (build-iso.sh installs shards from the root of nyxus-scripts). Move it to ${NS}/${_b} and add it to the shard list, or delete it"
    fi
    _ak_fail=$((_ak_fail + 1))
  done < <(find "${_ak_dir}" -maxdepth 1 -name '*.conf' 2>/dev/null | sort)
fi
# Same trap, wider net (2026-08-01): artifacts/nyxus-home/config/hyprland.conf
# was a whole second hyprland.conf that nothing staged — a snapshot left behind
# by nyxus-backport-live.sh. It had drifted badly (still opened the orphaned
# `cheatsheet` window, still dispatched `name:0`, still launched nyxus-start)
# and it is the first hit for anyone grepping the repo for a bind. Only two
# copies of hyprland.conf may exist: the source the bake reads, and the skel
# copy it installs to.
_ak_repo="$(cd "${HERE}/.." && pwd)"
_ak_ok_src="$(cd "${NS}" && pwd)/hyprland.conf"
_ak_ok_skel="$(cd "${AIROOT}" && pwd)/etc/skel/.config/hypr/hyprland.conf"
_ak_hypr=()
while IFS= read -r _h; do _ak_hypr+=("${_h}"); done < <(
  find "${_ak_repo}" -name 'hyprland.conf' -not -path '*/node_modules/*' \
       -not -path '*/.git/*' 2>/dev/null | sort)
for _h in "${_ak_hypr[@]}"; do
  case "${_h}" in
    "${_ak_ok_src}"|"${_ak_ok_skel}") ;;
    *)
      fail "${_h#${_ak_repo}/} is a third copy of hyprland.conf that nothing stages. The bake installs artifacts/api-server/nyxus-scripts/hyprland.conf into etc/skel; any other copy is a decoy that will collect edits and ship nothing"
      _ak_fail=$((_ak_fail + 1))
      ;;
  esac
done

(( _ak_fail == 0 )) \
  && ok "no decoy Hyprland shards or stray hyprland.conf copies (${#_ak_hypr[@]} found, both expected)"

# ── 13pa. fullscreen eww overlays must be TOP-anchored, not centred ──────────
# An eww window is non-exclusive (exclusive_zone 0), so wlr-layer-shell lays it
# out inside the monitor's USABLE area — what is left after the bars' exclusive
# zones — and with no anchor Hyprland CENTRES it there:
#     y = reserved_top + (usable_h - requested_h) / 2
# Measured live 2026-07-30, 1920x1080, reserved [0,40,0,158] (usable 882):
#     anchor "center"      -> y = -59, bottom edge 1021  → 59px of bare desktop
#                             showing under NYXUS Power / the Hub / every
#                             fullscreen overlay
#     anchor "top center"  -> y = 40,  bottom edge 1120  → bottom always covered
# The overlay-shield defpoll does eventually hide the bars, after which the
# surface snaps to y=0 — but it is a 2-SECOND poll, so "center" showed the strip
# for the first ~2s of every single open. Top-anchoring is correct in both
# phases and depends on no timing at all, so that is what is asserted here.
# This also cannot be fixed with an exclusive-zone setting: eww's `:exclusive`
# is a bool and only ever selects 0 or auto, never the -1 that would make
# Hyprland use the full monitor as the bounds.
hd "13pa. fullscreen eww overlays are top-anchored (no bottom desktop strip)"
_pa_fail=0; _pa_seen=0
_PA_TREES=("${NS}/eww" "${AIROOT}/etc/skel/.config/eww")
for _pa_dir in "${_PA_TREES[@]}"; do
  [[ -d "${_pa_dir}" ]] || { fail "13pa: eww tree missing: ${_pa_dir}"; _pa_fail=$((_pa_fail+1)); continue; }
  while IFS= read -r _pa_f; do
    [[ -n "${_pa_f}" ]] || continue
    # Every geometry that asks for the whole screen must anchor to an edge.
    while IFS= read -r _pa_line; do
      [[ -n "${_pa_line}" ]] || continue
      _pa_seen=$((_pa_seen+1))
      _pa_no="${_pa_line%%:*}"
      fail "13pa: ${_pa_f#${HERE}/../}:${_pa_no} declares a 100%x100% eww window with :anchor \"center\". A non-exclusive layer surface is centred inside the USABLE area, so at reserved [0,40,0,158] it lands at y=-59 and leaves a 59px strip of live desktop along the bottom edge. Use :anchor \"top center\""
      _pa_fail=$((_pa_fail+1))
    done < <(grep -n ':height "100%" :anchor "center"' "${_pa_f}" 2>/dev/null)
  done < <(find "${_pa_dir}" -maxdepth 1 -name '*.yuck' 2>/dev/null | sort)
done
# The bake copies NS/eww/*.yuck into skel, so a fix applied to one tree only
# still ships the bug. Assert the two trees agree.
for _pa_f in "${NS}"/eww/*.yuck; do
  [[ -f "${_pa_f}" ]] || continue
  _pa_b="$(basename "${_pa_f}")"
  _pa_s="${AIROOT}/etc/skel/.config/eww/${_pa_b}"
  if [[ ! -f "${_pa_s}" ]]; then
    fail "13pa: ${_pa_b} exists in nyxus-scripts/eww but not in skel — the bake would ship no copy of it"
    _pa_fail=$((_pa_fail+1))
  elif ! cmp -s "${_pa_f}" "${_pa_s}"; then
    fail "13pa: ${_pa_b} has drifted between nyxus-scripts/eww (source of truth) and skel. Copy NS -> skel"
    _pa_fail=$((_pa_fail+1))
  fi
done
(( _pa_fail == 0 )) \
  && ok "no centred fullscreen eww window on either tree; NS/eww *.yuck == skel"

# ── 13pb. the screensavers must be able to actually go fullscreen ────────────
# Hyprland refuses to fullscreen a PINNED window (pin implies floating), so a
# `pin on` rule silently defeats the `fullscreen on` sitting next to it. Both
# savers carried both rules, so neither ever went fullscreen. Measured live
# 2026-07-30 on Hyprland 0.55.4:
#     with `pin on`    -> at [0,-59] 1920x1080, fullscreen 0, pinned true
#     without          -> at [0,0]   1920x1080, fullscreen 2
# The -59 is the same arithmetic as 13pa: a 1080-tall window centred in the
# 882px the bars leave. The alien saver was worse still — it does not size
# itself, so it mapped as a 900x650 card floating in the middle of the desktop.
hd "13pb. screensaver window rules can reach fullscreen (no pin conflict)"
_pb_fail=0
_PB_CLASSES=("com\\.nyxus\\.matrixsaver" "app\\.nyxus\\.Screensaver")
for _pb_f in "${NS}/nyxus-hyprland-rules.conf" \
             "${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-rules.conf"; do
  if [[ ! -r "${_pb_f}" ]]; then
    fail "13pb: cannot read ${_pb_f}"; _pb_fail=$((_pb_fail+1)); continue
  fi
  # The class patterns in these rules contain literal backslashes, so match
  # them as FIXED strings. Comment lines are stripped first, because a
  # commented-out directive is inert and the file documents the trap in prose.
  _pb_live="$(grep -v '^[[:space:]]*#' "${_pb_f}")"
  for _pb_c in "${_PB_CLASSES[@]}"; do
    if printf '%s\n' "${_pb_live}" \
         | grep -Fq "windowrule = pin on, match:class ^(${_pb_c})\$"; then
      fail "13pb: ${_pb_f#${HERE}/../} pins ${_pb_c//\\/}. Hyprland will not fullscreen a pinned window, so this silently cancels the fullscreen rule beside it and the saver maps as a floating window with live desktop around it. Remove the pin"
      _pb_fail=$((_pb_fail+1))
    fi
    if ! printf '%s\n' "${_pb_live}" \
         | grep -Fq "windowrule = fullscreen on, match:class ^(${_pb_c})\$"; then
      fail "13pb: ${_pb_f#${HERE}/../} has no 'fullscreen on' rule for ${_pb_c//\\/} — the idle screen will not cover the display"
      _pb_fail=$((_pb_fail+1))
    fi
  done
done
# The payload's own belt-and-braces: fullscreen() called in __init__ runs before
# the wayland surface exists and wlroots drops it, so it must be re-asserted
# after present(). nyxus_matrix_saver.py already did this; the alien saver did
# not. Checked on all three trees the bake reads.
for _pb_p in "${NS}/nyxus_screensaver.py" \
             "${AIROOT}/etc/skel/.config/nyxus/nyxus_screensaver.py" \
             "${AIROOT}/opt/nyxus/nyxus_screensaver.py"; do
  if [[ ! -r "${_pb_p}" ]]; then
    fail "13pb: nyxus_screensaver.py missing at ${_pb_p#${HERE}/../}"; _pb_fail=$((_pb_fail+1)); continue
  fi
  if ! grep -q 'GLib.idle_add(win.fullscreen)' "${_pb_p}"; then
    fail "13pb: ${_pb_p#${HERE}/../} never re-asserts fullscreen after present(). The fullscreen() in __init__ is issued before the surface is mapped and wlroots ignores it; add GLib.idle_add(win.fullscreen) after win.present() the way nyxus_matrix_saver.py does"
    _pb_fail=$((_pb_fail+1))
  fi
done
(( _pb_fail == 0 )) \
  && ok "both savers can reach fullscreen (no pin conflict) and the payload re-asserts it after map"

# ── 13pg. the two installer allowlists agree, and every name resolves ────────
# install.sh (dev/repo deploy) and nyxus_install.sh (offline/ISO deploy) each
# carry an explicit LAUNCHERS array. They are supposed to be the same list.
# They were not: eight names in one, two in the other, so which tools you ended
# up with depended on which installer ran. Two of the names also pointed at
# symlinks that dangled on every machine but the author's, so they deployed
# nothing at all.
hd "13pg. installer allowlists agree and resolve"
if ! command -v python3 >/dev/null 2>&1; then
  warn "13pg: python3 not available — allowlist check skipped"
else
  _pg_out="$(python3 - "${HERE}/.." <<'PYEOF'
import re, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
ns = root / "artifacts/api-server/nyxus-scripts"

def launchers(path):
    m = re.search(r"^LAUNCHERS=\((.*?)^\)",
                  Path(path).read_text(encoding="utf-8"), re.S | re.M)
    if not m:
        return None
    return set(re.sub(r"#.*", "", m.group(1)).split())

a = launchers(root / "install.sh")
b = launchers(ns / "nyxus_install.sh")
if a is None or b is None:
    print("SKIP could not parse a LAUNCHERS array")
    raise SystemExit(0)

for name in sorted(a - b):
    print(f"DIFF {name} is in install.sh but not nyxus_install.sh")
for name in sorted(b - a):
    print(f"DIFF {name} is in nyxus_install.sh but not install.sh")
for name in sorted(a | b):
    p = ns / name
    if not p.exists():
        target = f" -> {p.readlink()}" if p.is_symlink() else ""
        print(f"DANGLING {name} is allowlisted but does not resolve under "
              f"nyxus-scripts{target}")
PYEOF
)"
  if grep -q '^SKIP' <<<"${_pg_out}"; then
    warn "13pg: $(sed -n 's/^SKIP //p' <<<"${_pg_out}")"
  elif [[ -z "${_pg_out}" ]]; then
    ok "13pg: both installer allowlists match and every entry resolves"
  else
    while IFS= read -r _pg_line; do
      [[ -n "${_pg_line}" ]] && fail "13pg: ${_pg_line#* }"
    done <<<"${_pg_out}"
  fi
fi

# Nothing under nyxus-scripts may be a symlink that does not resolve. build-iso
# copies this tree into the ISO's offline cache; a link pointing outside the
# repo lands on the stick as a dead file.
_pg_broken=0
while IFS= read -r _bl; do
  [[ -n "${_bl}" ]] || continue
  fail "13pg: ${_bl#${HERE}/../} is a broken symlink -> $(readlink "${_bl}")"
  _pg_broken=$((_pg_broken + 1))
done < <(find "${NS}" -type l ! -exec test -e {} \; -print 2>/dev/null)
(( _pg_broken == 0 )) && ok "13pg: no dangling symlinks under nyxus-scripts"

# ── 13pf. no FORBIDDEN palette hex in a shipped NYXUS surface ────────────────
# nyxus_palette.FORBIDDEN is the banned list, and assert_no_forbidden() exists
# so an app can check its own CSS — but nothing checked the tree, so banned
# colours lived on for months in places nobody re-read: the icon and cursor
# generators (which bake into the shipped icon theme), the wallpaper and GRUB
# theme generators, and all six Vite web apps.
#
# Scope is NYXUS chrome only. Arsenal / Bifrost / Meli / GodsApp / the Forge
# tools carry their own palettes and are explicitly out of scope per
# docs/DESIGN_CONTRACT.md, and the FORBIDDEN tuple itself obviously contains
# the strings it bans.
hd "13pf. no forbidden palette colours in shipped surfaces"
if ! command -v python3 >/dev/null 2>&1; then
  warn "13pf: python3 not available — palette scan skipped"
else
  _pf_out="$(python3 - "${HERE}/.." <<'PYEOF'
import re, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
palette = root / "artifacts/api-server/nyxus-scripts/nyxus_palette.py"
src = palette.read_text(encoding="utf-8")
block = re.search(r"FORBIDDEN\s*=\s*\((.*?)\n\)", src, re.S)
if not block:
    print("SKIP could not parse FORBIDDEN from nyxus_palette.py")
    raise SystemExit(0)
banned = {h.lower() for h in re.findall(r'"(#[0-9a-fA-F]{6})"', block.group(1))}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv",
    "opt/arsenal", "opt/meli", "opt/honeypot", "usr/lib/bifrost",
    "opt/nyxus-intel", "opt/nyxus-intel-bundle", "attached_assets",
    "docs",                     # documents the banned palettes on purpose
    "accent-baseline",          # per-machine cache, gitignored
}
EXTS = {".css", ".scss", ".py", ".ts", ".tsx", ".conf", ".rasi", ".toml",
        ".yuck", ".txt", ".json", ".theme", ".qml", ".sh"}

hits = []
for p in root.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in EXTS:
        continue
    rel = p.relative_to(root).as_posix()
    if any(s in rel for s in SKIP_DIRS):
        continue
    if p.name == "nyxus_palette.py":
        continue            # defines the list
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").lower().splitlines()
    except OSError:
        continue
    # Prose is allowed to name a banned colour — most of the notes explaining
    # WHY something is banned have to quote it. Only flag a hex that survives
    # into the code part of its line.
    for line in lines:
        if not any(h in line for h in banned):
            continue
        code = line
        for marker in ("#", "//", "/*", "*", "--"):
            idx = code.find(marker)
            # A CSS/py hex literal starts with '#', so only treat '#' as a
            # comment marker when what follows it is not a hex colour.
            if marker == "#":
                while idx != -1 and re.match(r"#[0-9a-f]{3,8}\b", code[idx:]):
                    idx = code.find("#", idx + 1)
            if idx != -1:
                code = code[:idx]
        for h in banned:
            if h in code:
                hits.append((rel, h))

for rel, h in sorted(set(hits)):
    print(f"HIT {h} {rel}")
PYEOF
)"
  if grep -q '^SKIP' <<<"${_pf_out}"; then
    warn "13pf: $(sed -n 's/^SKIP //p' <<<"${_pf_out}")"
  elif [[ -z "${_pf_out}" ]]; then
    ok "13pf: no forbidden palette colour in any shipped NYXUS surface"
  else
    while IFS= read -r _pf_line; do
      [[ -n "${_pf_line}" ]] || continue
      set -- ${_pf_line}
      fail "13pf: forbidden colour $2 in $3 — use a nyxus_palette constant"
    done <<<"${_pf_out}"
  fi
fi

# ── 13pc. every executable in airootfs is in file_permissions ────────────────
# archiso copies airootfs with --no-preserve=mode, so an executable missing
# from profiledef.sh's file_permissions ships 644 and silently cannot run. The
# 2026-07-31 ISO shipped 116 of them that way, including the ARSENAL and MESH
# station launchers and every eww/hypr script. The array is derived now, not
# hand-maintained — this gate is what catches a stale checkout.
hd "13pc. file_permissions covers every executable"
if ! command -v python3 >/dev/null 2>&1; then
  warn "13pc: python3 not available — cannot verify file_permissions"
elif python3 "${HERE}/regen-file-permissions.py" --profile "${PROFILE}" --check >/tmp/nyx-fileperm.out 2>&1; then
  ok "13pc: file_permissions matches the airootfs ($(grep -c '\]="0:0:755"' "${PROFILE}/profiledef.sh") executables)"
else
  while IFS= read -r _fp_line; do
    [[ -n "${_fp_line}" ]] && fail "13pc: ${_fp_line#\[FAIL\] }"
  done < <(grep '^\[FAIL\]' /tmp/nyx-fileperm.out)
  fail "13pc: run iso-builder/regen-file-permissions.py and commit the result"
fi

# ── 13pd. every boot path the profile ships sets cow_spacesize ───────────────
# FS-01: without it archiso uses a 256M overlay, /etc/skel alone is ~162 MB,
# and the live session hits a full disk minutes after first login. Only the
# configs consumed by this profile's bootmodes are checked — nyx-profile has no
# efiboot/ on purpose, because mkarchiso reads that only for systemd-boot.
hd "13pd. cow_spacesize on every boot path"
_cow_fail=0
_cow_seen=0
for _cow_f in "${PROFILE}/syslinux/syslinux.cfg" "${PROFILE}/grub/grub.cfg"; do
  [[ -f "${_cow_f}" ]] || continue
  while IFS= read -r _cow_line; do
    _cow_seen=$((_cow_seen+1))
    if [[ "${_cow_line}" != *cow_spacesize=* ]]; then
      fail "13pd: ${_cow_f#${HERE}/} boots without cow_spacesize: ${_cow_line# }"
      _cow_fail=$((_cow_fail+1))
    fi
  done < <(grep -E '^\s*(APPEND|linux)\s' "${_cow_f}" | grep 'archisobasedir=')
done
if (( _cow_seen == 0 )); then
  fail "13pd: found no bootable entries in syslinux.cfg / grub.cfg to check"
elif (( _cow_fail == 0 )); then
  ok "13pd: all ${_cow_seen} boot entries set cow_spacesize"
fi

# BIOS needs a UI directive or syslinux ignores every MENU line and draws
# nothing — B-02, which made the safe/no-KMS and rescue kernels unreachable.
if [[ -f "${PROFILE}/syslinux/syslinux.cfg" ]]; then
  if grep -Eq '^\s*UI\s+(vesa)?menu\.c32' "${PROFILE}/syslinux/syslinux.cfg"; then
    ok "13pd: syslinux.cfg declares a UI module (the BIOS menu will draw)"
  else
    fail "13pd: syslinux.cfg has no 'UI menu.c32' / 'UI vesamenu.c32' — syslinux ignores every MENU directive without one and renders no menu at all"
  fi
fi

# ── 13pe. GRUB theme boxes have all nine slices ──────────────────────────────
# B-03: a `foo_*.png` box makes GRUB look for nine slices and silently skip the
# missing ones. Shipping only select_c/_e/_w — and pointing terminal-box at
# that same prefix — is why the UEFI menu drew a background and nothing else.
hd "13pe. GRUB theme nine-slice completeness"
_slice_fail=0
_slice_themes=0
while IFS= read -r _theme; do
  _slice_themes=$((_slice_themes+1))
  _tdir="$(dirname "${_theme}")"
  while IFS= read -r _prefix; do
    for _s in c n s e w nw ne sw se; do
      if [[ ! -f "${_tdir}/${_prefix}_${_s}.png" ]]; then
        fail "13pe: ${_theme#${HERE}/} references ${_prefix}_*.png but ${_prefix}_${_s}.png is missing"
        _slice_fail=$((_slice_fail+1))
      fi
    done
  done < <(grep -oE '"[a-z_]+_\*\.png"' "${_theme}" | tr -d '"' | sed 's/_\*\.png$//' | sort -u)
done < <(find "${PROFILE}" -path '*/themes/nyxus/theme.txt' 2>/dev/null)
if (( _slice_themes == 0 )); then
  warn "13pe: no GRUB theme.txt found under the profile"
elif (( _slice_fail == 0 )); then
  ok "13pe: ${_slice_themes} GRUB theme(s) — every referenced box has all nine slices"
fi

# ── 14. mksquashfs ────────────────────────────────────────────────────
hd "14. mksquashfs"
command -v mksquashfs >/dev/null \
  && ok "mksquashfs available ($(mksquashfs -version | head -1))" \
  || warn "mksquashfs not on PATH (host can't bake; CI is fine)"

# ── final ─────────────────────────────────────────────────────────────
echo
if (( FAIL == 0 )); then
  printf '\033[1;32m✓ verify-profile passed.\033[0m\n'
  exit 0
else
  printf '\033[1;31m✗ verify-profile FAILED.\033[0m\n'
  exit 1
fi

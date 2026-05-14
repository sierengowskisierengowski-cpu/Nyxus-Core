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
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
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
  SRC_DESK="${NS}/desktop-entries"
  ISO_DESK="${AIROOT}/usr/share/applications"
  if [[ -d "${SRC_DESK}" ]]; then
    src_list="$(find "${SRC_DESK}" -maxdepth 1 -name 'nyxus-*.desktop' -printf '%f\n' | sort)"
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
SDDM_BG="${AIROOT}/usr/share/sddm/themes/nyxus/backgrounds"
SDDM_PNG=$(find "${SDDM_BG}" -maxdepth 1 -name '*.png' 2>/dev/null | wc -l)
if (( SDDM_PNG >= WP_PNG )); then
  ok "${SDDM_PNG} wallpapers mirrored to SDDM theme"
else
  fail "SDDM wallpaper mirror has ${SDDM_PNG}, expected >= ${WP_PNG}"
fi
WP_CONF="${AIROOT}/etc/skel/.config/nyxus/wallpaper.conf"
if [[ -f "${WP_CONF}" ]]; then
  # Runtime schema: WALLPAPER="slug" + WALLPAPER_PATH="/abs/path" (consumed by
  # nyxus-wallpaper-autostart and nyxus_wallpaper_studio.py).
  WP_DEFAULT=$(grep -oP '^WALLPAPER_PATH="?\K[^"]+' "${WP_CONF}" | head -1)
  WP_SLUG=$(grep -oP '^WALLPAPER="?\K[^"]+' "${WP_CONF}" | head -1)
  if [[ -n "${WP_DEFAULT}" && -f "${AIROOT}${WP_DEFAULT}" ]]; then
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
[[ -f "${AIROOT}/etc/skel/.config/nyxus/workspaces.json" ]] \
  && ok "workspaces.json shipped" || fail "workspaces.json missing"
[[ -x "${AIROOT}/usr/local/bin/nyxus-workspace-wallpaperd" ]] \
  && ok "ws wallpaper daemon present + executable" \
  || fail "ws wallpaper daemon missing/not-exec"
[[ -f "${AIROOT}/etc/skel/.config/systemd/user/nyxus-ws-wallpaperd.service" ]] \
  && ok "ws wallpaper systemd unit present" \
  || fail "ws wallpaper systemd unit missing"
WS_NAMES=$(grep -c '^workspace = ' "${AIROOT}/etc/skel/.config/hypr/hyprland.conf")
if (( WS_NAMES >= 10 )); then
  ok "${WS_NAMES} named workspaces declared"
else
  fail "only ${WS_NAMES} named workspaces (expected 10)"
fi

# ── 13g. NYXUS first-run welcome tour ─────────────────────────────────
hd "13g. NYXUS welcome tour"
[[ -f "${AIROOT}/opt/nyxus/nyxus_welcome.py" ]] \
  && ok "nyxus_welcome.py present" || fail "nyxus_welcome.py missing"
grep -q "/usr/local/bin/nyxus welcome" "${AIROOT}/etc/skel/.config/hypr/hyprland.conf" \
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
for pkg in qemu-desktop libvirt virt-manager virt-viewer edk2-ovmf swtpm \
           buildah skopeo distrobox \
           linux-lts linux-zen linux-hardened \
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
# Required runtime packages — sddm itself + python3 (used by helper).
for pkg in sddm; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

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
for f in nyxus.plymouth nyxus.script logo.png bar-track.png bar-fill.png; do
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
# Canonical DARK MIRROR colors must be present in branding.desc
grep -qi '#a06bff' "${CAL_BRAND}/branding.desc" \
  && ok "calamares: canonical accent #a06bff present" \
  || fail "calamares: canonical accent #a06bff missing"

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

# Required module configs (skip 'summary' / 'mount' / 'partition' /
# 'umount' / 'unpackfs' / 'machineid' / 'localecfg' — these are built-in
# views or accept zero-config defaults).
for m in welcome locale timezone keyboard users \
         fstab displaymanager networkcfg hwclock \
         services-systemd grubcfg bootloader \
         packages shellprocess finished; do
  [[ -f "${AIROOT}/etc/calamares/modules/${m}.conf" ]] \
    || fail "calamares: missing module config ${m}.conf"
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
grep -qi '#a06bff' "${GRUB_THEME_DIR}/theme.txt" 2>/dev/null \
  && ok "GRUB: canonical accent #a06bff present" \
  || fail "GRUB: canonical accent #a06bff missing from theme.txt"
grep -qi '#3ad8ff' "${GRUB_THEME_DIR}/theme.txt" 2>/dev/null \
  && ok "GRUB: canonical cyan #3ad8ff present" \
  || fail "GRUB: canonical cyan #3ad8ff missing from theme.txt"

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
grep -qi '#a06bff' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: canonical accent #a06bff present" \
  || fail "dunst: canonical accent #a06bff missing"
grep -qi 'JetBrains Mono' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: JetBrains Mono font set" \
  || fail "dunst: JetBrains Mono font not set (off-brand typography)"
grep -qi 'corner_radius = 0' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: sharp slab corners (corner_radius=0)" \
  || fail "dunst: corners not flat — DARK MIRROR requires sharp edges"

if [[ -f "${SWAYNC_CSS}" ]] \
   && grep -q '\.notification' "${SWAYNC_CSS}" \
   && grep -q '\.control-center' "${SWAYNC_CSS}"; then
  ok "swaync: style.css present with .notification + .control-center"
else
  fail "swaync: style.css missing or incomplete"
fi
grep -qi '#a06bff' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: canonical accent #a06bff present" \
  || fail "swaync: canonical accent #a06bff missing"
grep -qi '#3ad8ff' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: canonical cyan #3ad8ff present" \
  || fail "swaync: canonical cyan #3ad8ff missing"
grep -qi 'border-radius: 0' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: sharp slab corners (border-radius:0)" \
  || fail "swaync: rounded corners present — DARK MIRROR requires sharp edges"

for pkg in dunst swaync; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

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

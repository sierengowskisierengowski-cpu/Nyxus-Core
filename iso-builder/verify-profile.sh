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
# Active theme is `nyxus-void` (DARKSIDE rev5). The legacy `nyxus` theme
# (full DARK MIRROR purple+cyan) was retired in Sprint E.
hd "11. plymouth theme"
PT="${AIROOT}/usr/share/plymouth/themes/nyxus-void"
if [[ -f "${PT}/nyxus-void.plymouth" && -f "${PT}/nyxus-void.script" ]]; then
  ok "plymouth nyxus-void (DARKSIDE rev5) theme present"
else
  fail "plymouth nyxus-void theme incomplete"
fi
# Make sure the legacy DARK MIRROR theme stays purged
if [[ -d "${AIROOT}/usr/share/plymouth/themes/nyxus" ]]; then
  fail "legacy plymouth nyxus theme dir reappeared (must stay PURGED)"
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
    # Sprint J rev r16: default GTK icon theme is now NYXUS-Glyph;
    # NYXUS-Dark remains a valid fallback (inherited by NYXUS-Glyph).
    if grep -Eq '^gtk-icon-theme-name=NYXUS-(Glyph|Dark)$' "$f" 2>/dev/null; then
      ok "$(basename "$(dirname "$f")")/settings.ini -> $(grep -E '^gtk-icon-theme-name=' "$f" | cut -d= -f2)"
    else
      fail "$(basename "$(dirname "$f")")/settings.ini does not select NYXUS-Glyph or NYXUS-Dark"
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
# Active plymouth theme is `nyxus-void` (DARKSIDE rev5). Sprint E retired
# the legacy `nyxus` theme dir (full DARK MIRROR purple+cyan progress bar).
PL_THEME="${AIROOT}/usr/share/plymouth/themes/nyxus-void"
for f in nyxus-void.plymouth nyxus-void.script background.png; do
  if [[ -f "${PL_THEME}/${f}" ]]; then
    ok "plymouth theme asset: ${f}"
  else
    fail "plymouth theme missing: ${PL_THEME}/${f}"
  fi
done
# Manifest sanity: ModuleName=script + ScriptFile points to nyxus-void.script
if grep -q '^ModuleName=script' "${PL_THEME}/nyxus-void.plymouth" \
   && grep -q 'ScriptFile=.*nyxus-void.script' "${PL_THEME}/nyxus-void.plymouth"; then
  ok "plymouth manifest references script module + nyxus-void.script"
else
  fail "plymouth manifest malformed: ${PL_THEME}/nyxus-void.plymouth"
fi
# Plymouth Script lint: nyxus-void uses // C++-style comments, so the
# ternary check needs to strip those (and `#` legacy) before scanning.
if sed -E 's|//.*$||; s|[[:space:]]*#.*$||' "${PL_THEME}/nyxus-void.script" \
     | grep -E '[A-Za-z0-9_)][[:space:]]*\?[^?:]+:[^=]' >/dev/null; then
  fail "plymouth script uses C-style ternary — Plymouth Script does not support \`?:\`"
else
  ok "plymouth script: no ternary"
fi
if grep -qE 'SetUpdateStatusFunction *\( *progress_callback' \
     "${PL_THEME}/nyxus-void.script"; then
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
for pkg in libcanberra libcanberra-pulse sound-theme-freedesktop pipewire-pulse; do
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
# rev r15 — canonical CREAM (#f4ead5) accent must be present in branding.desc
grep -qi '#f4ead5' "${CAL_BRAND}/branding.desc" \
  && ok "calamares: canonical CREAM accent #f4ead5 present (rev r15)" \
  || fail "calamares: canonical CREAM accent #f4ead5 missing (rev r15)"
# Banned palette literals must NOT appear (rev r15 brand contract)
if grep -qiE '#a06bff|#3ad8ff|#d4b87a|#ff4d6b' "${CAL_BRAND}/branding.desc"; then
  fail "calamares: branding.desc still contains banned palette literal (rev r15)"
else
  ok "calamares: zero banned palette literals (rev r15)"
fi

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

# Required Arch packages
for pkg in calamares ckbcomp; do
  grep -Eq "^${pkg}\$" "${PROFILE}/packages.x86_64" \
    && ok "package: ${pkg}" \
    || fail "missing package: ${pkg}"
done

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
grep -qi '#f4ead5' "${GRUB_THEME_DIR}/theme.txt" 2>/dev/null \
  && ok "GRUB: canonical CREAM #f4ead5 present (rev r15)" \
  || fail "GRUB: canonical CREAM #f4ead5 missing from theme.txt (rev r15)"
if grep -qiE '#a06bff|#3ad8ff|#d4b87a|#ff4d6b' "${GRUB_THEME_DIR}/theme.txt" 2>/dev/null; then
  fail "GRUB: theme.txt still contains banned palette literal (rev r15)"
else
  ok "GRUB: zero banned palette literals in theme.txt (rev r15)"
fi

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
grep -qi '#f4ead5' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: canonical CREAM accent #f4ead5 present (rev r15)" \
  || fail "dunst: canonical CREAM accent #f4ead5 missing (rev r15)"
if grep -qiE '#a06bff|#3ad8ff|#d4b87a|#ff4d6b' "${DUNST_RC}" 2>/dev/null; then
  fail "dunst: dunstrc still contains banned palette literal (rev r15)"
else
  ok "dunst: zero banned palette literals (rev r15)"
fi
grep -qi 'JetBrains Mono' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: JetBrains Mono font set" \
  || fail "dunst: JetBrains Mono font not set (off-brand typography)"
grep -qiE 'corner_radius[[:space:]]*=[[:space:]]*3' "${DUNST_RC}" 2>/dev/null \
  && ok "dunst: 3px corners (rev r15 spec)" \
  || fail "dunst: corner_radius not 3 (rev r15 requires 3px corners, not sharp slab)"

if [[ -f "${SWAYNC_CSS}" ]] \
   && grep -q '\.notification' "${SWAYNC_CSS}" \
   && grep -q '\.control-center' "${SWAYNC_CSS}"; then
  ok "swaync: style.css present with .notification + .control-center"
else
  fail "swaync: style.css missing or incomplete"
fi
grep -qi '#f4ead5' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: canonical CREAM accent #f4ead5 present (rev r15)" \
  || fail "swaync: canonical CREAM accent #f4ead5 missing (rev r15)"
if grep -qiE '#a06bff|#3ad8ff|#d4b87a|#ff4d6b' "${SWAYNC_CSS}" 2>/dev/null; then
  fail "swaync: style.css still contains banned palette literal (rev r15)"
else
  ok "swaync: zero banned palette literals (rev r15)"
fi
grep -qE 'border-radius:[[:space:]]*3px' "${SWAYNC_CSS}" 2>/dev/null \
  && ok "swaync: 3px corners (rev r15 spec)" \
  || fail "swaync: border-radius not 3px (rev r15 requires 3px corners, not sharp slab)"

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

# ── 13v. Tier 1 · Brand Contract (rev r15 — 2026-05-14) ────────────
# Locks the DARK MIRROR rev r15 contract:
#   • CREAM (#f4ead5) is the only warm accent
#   • Caveat + Inter + JetBrains Mono Nerd Font is the type system
#   • 3px corners (near-sharp) on every surface
#   • Banned palette literals (purple #a06bff, cyan #3ad8ff,
#     gold #d4b87a, strobe red #ff4d6b) must not appear anywhere
#     in airootfs CSS / SCSS / SVG / QML / JSON / Python / config.
#   • Intelligent window sizing: nyxus_chrome.py must not clamp
#     set_default_size; each app declares its own intelligent default.
hd "13v. Tier 1 · Brand Contract (rev r15)"

# Banned palette literals — hex AND rgba() equivalents — across BOTH
# the airootfs surface and the artifacts/api-server/nyxus-scripts source
# of truth (both are part of the shipped contract).
BANNED_HEX='#a06bff|#3ad8ff|#d4b87a|#8b6f3a|#8a6f3a|#e8c66b|#ff4d6b|#ff4d6d|#bf5cff|#ffd700|#7B5EA7'
BANNED_RGBA='rgba\(\s*160\s*,\s*107\s*,\s*255|rgba\(\s*58\s*,\s*216\s*,\s*255|rgba\(\s*212\s*,\s*184\s*,\s*122|rgba\(\s*255\s*,\s*77\s*,\s*107|rgba\(\s*123\s*,\s*94\s*,\s*167'
BANNED_PATTERN="${BANNED_HEX}|${BANNED_RGBA}"

HITS_FILE="$(mktemp)"
# airootfs (installed surface) — exclude nothing here, contract is total.
grep -rEli --include='*.css' --include='*.scss' --include='*.qml' --include='*.svg' \
     --include='*.desc' --include='*.json' --include='*.txt' --include='*.cfg' \
     --include='*.md' --include='dunstrc' --include='*.py' \
     "${BANNED_PATTERN}" "${AIROOT}" >> "${HITS_FILE}" 2>/dev/null || true

# artifacts source — exclude nyxus_palette.py (legitimately holds the
# FORBIDDEN test data) and any cached/__pycache__ output.
ART_SRC="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts"
if [[ -d "${ART_SRC}" ]]; then
  grep -rEli --include='*.css' --include='*.scss' --include='*.py' \
       --exclude='nyxus_palette.py' \
       --exclude-dir='__pycache__' \
       "${BANNED_PATTERN}" "${ART_SRC}" >> "${HITS_FILE}" 2>/dev/null || true
fi

if [[ -s "${HITS_FILE}" ]]; then
  fail "rev r15: $(wc -l < "${HITS_FILE}") files contain banned palette literals — see ${HITS_FILE}"
else
  ok "rev r15: zero banned palette literals across airootfs + artifacts source"
  rm -f "${HITS_FILE}"
fi

# Cream accent must be present in the canonical palette.css mirror.
NYXUS_PAL="${AIROOT}/usr/share/nyxus/css/nyxus-palette.css"
if [[ -f "${NYXUS_PAL}" ]]; then
  grep -qi '#f4ead5' "${NYXUS_PAL}" \
    && ok "palette.css: CREAM #f4ead5 defined" \
    || fail "palette.css: CREAM #f4ead5 missing — rev r15 contract broken"
  grep -qE '@define-color\s+(nyx-)?cream' "${NYXUS_PAL}" \
    && ok "palette.css: @define-color cream alias present" \
    || fail "palette.css: @define-color cream alias missing"
fi

# Type system — Caveat must be bundled OR scheduled for bundling.
CAVEAT_DIR="${AIROOT}/usr/share/fonts/nyxus-display"
if [[ -d "${CAVEAT_DIR}" ]]; then
  if [[ -f "${CAVEAT_DIR}/Caveat-Regular.ttf" ]]; then
    ok "fonts: Caveat-Regular.ttf bundled"
  elif [[ -f "${CAVEAT_DIR}/Caveat-Regular.ttf.placeholder" ]]; then
    warn "fonts: Caveat-Regular.ttf placeholder present (build host must drop real OFL binary)"
  else
    fail "fonts: Caveat-Regular.ttf missing AND no placeholder — rev r15 type system broken"
  fi
else
  fail "fonts: ${CAVEAT_DIR} missing — Caveat font dir required"
fi
grep -Eq '^inter-font$' "${PROFILE}/packages.x86_64" \
  && ok "fonts: inter-font package present" \
  || fail "fonts: inter-font package missing — rev r15 body font"
grep -Eq '^ttf-jetbrains-mono-nerd$' "${PROFILE}/packages.x86_64" \
  && ok "fonts: ttf-jetbrains-mono-nerd present" \
  || fail "fonts: ttf-jetbrains-mono-nerd missing — rev r15 mono font"

# 3px radius — near-sharp corners must be the default in palette.css.
if [[ -f "${NYXUS_PAL}" ]]; then
  grep -Eq 'radius[-_]?(card|tight|input|pill)?:?\s*3px' "${NYXUS_PAL}" \
    && ok "palette.css: 3px radius defined" \
    || fail "palette.css: 3px radius missing (rev r15 near-sharp corners)"
fi

# Intelligent window sizing — chrome must NOT clamp set_default_size.
# A clamp is detectable by the literal "min(int(w)" pattern coupled with
# NYXUS_MAX_DEFAULT_W <= 1024 (rev r13 used 700). rev r15 uses 2400.
# Check both the installed location AND the artifacts source of truth.
CHROME_PY="${AIROOT}/opt/nyxus/nyxus_chrome.py"
[[ -f "${CHROME_PY}" ]] || CHROME_PY="${ART_SRC}/nyxus_chrome.py"
if [[ -f "${CHROME_PY}" ]]; then
  if grep -Eq 'NYXUS_MAX_DEFAULT_W\s*=\s*[0-9]+' "${CHROME_PY}"; then
    cap=$(grep -Eo 'NYXUS_MAX_DEFAULT_W\s*=\s*[0-9]+' "${CHROME_PY}" | head -1 | grep -Eo '[0-9]+')
    if (( cap >= 2000 )); then
      ok "chrome: set_default_size ceiling = ${cap} (rev r15 honors per-app defaults)"
    else
      fail "chrome: set_default_size ceiling = ${cap} — rev r15 requires >= 2000 (no clamping)"
    fi
  else
    fail "chrome: NYXUS_MAX_DEFAULT_W not declared"
  fi
  grep -q 'INTELLIGENT DEFAULTS' "${CHROME_PY}" \
    && ok "chrome: rev r15 INTELLIGENT DEFAULTS policy block present" \
    || fail "chrome: rev r15 INTELLIGENT DEFAULTS policy block missing"
  grep -q '_nyxus_fixed_layout' "${CHROME_PY}" \
    && ok "chrome: _nyxus_fixed_layout opt-out implemented" \
    || fail "chrome: _nyxus_fixed_layout opt-out missing"
fi

# Intelligent default-size table — each app must declare a sensible
# default for its content. Failures here mean the app would feel wrong
# at first launch (terminal too narrow, file manager too small, etc).
# Format: <file>:<expected_min_w>:<expected_min_h>:<role>
INTELLIGENT_TABLE=(
  "nyxus_terminal.py:900:600:terminal — comfortable code/log reading"
  "nyxus_files.py:1024:640:file manager — wider for browsing"
  "nyxus_notepad.py:1024:640:notepad — writing-friendly width"
  "nyxus_settings.py:1100:680:settings — standard system-settings size"
  "nyxus_security.py:1100:680:security center — standard system-settings size"
  "nyxus_control.py:1024:640:control center — wider for tiles"
  "nyxus_sysmon_gtk.py:1024:640:system monitor — wider for graphs"
)
for entry in "${INTELLIGENT_TABLE[@]}"; do
  IFS=':' read -r fname min_w min_h role <<< "${entry}"
  fpath="${ART_SRC}/${fname}"
  if [[ -f "${fpath}" ]]; then
    # rev r15 — robust main-window detection:
    #   1. If the file declares WIN_W/WIN_H constants, prefer those
    #      (the main window is the one that uses set_default_size(WIN_W,WIN_H)).
    #   2. Otherwise pick the LARGEST set_default_size(N,N) call —
    #      the main window is almost always the biggest, while small
    #      numeric defaults (e.g. 540x420) are dialog children.
    w=""; h=""
    if grep -qE '^WIN_W\s*=' "${fpath}"; then
      w=$(grep -oE '^WIN_W\s*=\s*[0-9]+' "${fpath}" | head -1 | grep -oE '[0-9]+' | head -1)
      h=$(grep -oE '^WIN_H\s*=\s*[0-9]+' "${fpath}" | head -1 | grep -oE '[0-9]+' | head -1)
    elif grep -qE 'WIN_W,\s*WIN_H\s*=\s*[0-9]+,\s*[0-9]+' "${fpath}"; then
      pair=$(grep -oE 'WIN_W,\s*WIN_H\s*=\s*[0-9]+,\s*[0-9]+' "${fpath}" | head -1)
      w=$(echo "${pair}" | grep -oE '[0-9]+' | head -1)
      h=$(echo "${pair}" | grep -oE '[0-9]+' | tail -1)
    fi
    if [[ -z "${w}" || -z "${h}" ]]; then
      # Largest set_default_size(N,N) — sort by width desc, take winner.
      best=$(grep -oE 'set_default_size\([0-9]+,\s*[0-9]+\)' "${fpath}" \
        | awk -F'[(),]' '{print $2"x"$3}' \
        | sort -t'x' -k1,1nr -k2,2nr | head -1)
      if [[ -n "${best}" ]]; then
        w="${best%x*}"; h="${best#*x}"
        w="${w// /}"; h="${h// /}"
      fi
    fi
    if [[ -n "${w}" && -n "${h}" ]]; then
      if (( w >= min_w )) && (( h >= min_h )); then
        ok "intelligent-default ${fname}: ${w}x${h} >= ${min_w}x${min_h} (${role})"
      else
        fail "intelligent-default ${fname}: ${w}x${h} TOO SMALL — needs >= ${min_w}x${min_h} (${role})"
      fi
    else
      warn "intelligent-default ${fname}: could not parse default size"
    fi
  fi
done



# ── 13w. Tier 1 · Real-OS Desktop Contract (rev r15 — 2026-05-14) ──
# Locks the Sprint B "Real-OS desktop" requirements so the system feels
# natural to anyone coming from Windows or macOS:
#   • Desktop right-click context menu (Change Wallpaper, New Folder,
#     New File, Open Terminal Here, Display Settings, Refresh)
#   • Title-bar right-click window menu (Move, Resize, Minimize,
#     Maximize, Close)
#   • Every NYXUS app opens floating + draggable + resizable
#   • chrome.py auto-installs a HeaderBar on plain Gtk.Window /
#     Gtk.ApplicationWindow that lack one
hd "13w. Tier 1 · Real-OS Desktop Contract (rev r15)"

# (a) nyxus-context-menu.sh exists, executable, has all 6 entries.
CTX="${AIROOT}/usr/local/bin/nyxus-context-menu.sh"
if [[ -x "${CTX}" ]]; then
  ok "context-menu: nyxus-context-menu.sh present + executable"
  for entry in "Change Wallpaper" "New Folder" "New File" "Open Terminal" "Display Settings" "Refresh"; do
    if grep -q "${entry}" "${CTX}"; then
      ok "context-menu: entry present — ${entry}"
    else
      fail "context-menu: missing entry — ${entry}"
    fi
  done
else
  fail "context-menu: ${CTX} missing or not executable"
fi

# (b) nyxus-window-menu.sh exists, executable, has all 5 entries.
WM="${AIROOT}/usr/local/bin/nyxus-window-menu.sh"
if [[ -x "${WM}" ]]; then
  ok "window-menu: nyxus-window-menu.sh present + executable"
  for entry in "Move" "Resize" "Minimize" "Maximize" "Close"; do
    if grep -qE "[\"' ]${entry}[\"' ]" "${WM}"; then
      ok "window-menu: entry present — ${entry}"
    else
      fail "window-menu: missing entry — ${entry}"
    fi
  done
  grep -q "hyprctl" "${WM}" \
    && ok "window-menu: dispatches via hyprctl" \
    || fail "window-menu: missing hyprctl dispatch"
else
  fail "window-menu: ${WM} missing or not executable"
fi

# (c) Hyprland windowrules — NYXUS apps must float + center.
WRULE="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-windowrules.conf"
if [[ -f "${WRULE}" ]]; then
  ok "windowrules: nyxus-windowrules.conf present"
  grep -qE 'windowrulev2 = float, *class:\^\(nyxus' "${WRULE}" \
    && ok "windowrules: NYXUS apps float by default" \
    || fail "windowrules: NYXUS apps not set to float"
  grep -qE 'windowrulev2 = center' "${WRULE}" \
    && ok "windowrules: NYXUS apps center on open" \
    || fail "windowrules: NYXUS apps not centered on open"
  grep -q 'ALT,.*F4.*killactive' "${WRULE}" \
    && ok "windowrules: ALT+F4 close binding (Windows-style)" \
    || fail "windowrules: ALT+F4 close binding missing"
  grep -qE 'SUPER,.*M.*fullscreen.*1' "${WRULE}" \
    && ok "windowrules: SUPER+M maximize binding (macOS-style)" \
    || fail "windowrules: SUPER+M maximize binding missing"
else
  fail "windowrules: ${WRULE} missing"
fi

# (d) chrome.py installs a HeaderBar + double-click + right-click handlers.
if [[ -f "${CHROME_PY}" ]]; then
  grep -q 'def _ensure_titlebar' "${CHROME_PY}" \
    && ok "chrome: _ensure_titlebar() helper installed" \
    || fail "chrome: _ensure_titlebar() helper missing — windows won't be draggable"
  grep -q 'def _attach_titlebar_handlers' "${CHROME_PY}" \
    && ok "chrome: _attach_titlebar_handlers() (double-click + RMB) present" \
    || fail "chrome: title-bar handlers missing"
  grep -q 'window.maximize\|is_maximized' "${CHROME_PY}" \
    && ok "chrome: double-click toggles maximize" \
    || fail "chrome: double-click maximize logic missing"
  grep -q 'nyxus-window-menu' "${CHROME_PY}" \
    && ok "chrome: title-bar RMB invokes nyxus-window-menu.sh" \
    || fail "chrome: title-bar RMB → nyxus-window-menu wiring missing"
fi

# (e) Desktop right-click is wired in nyxus_desktop.py.
DESK="${AIROOT}/opt/nyxus/desktop/nyxus_desktop.py"
[[ -f "${DESK}" ]] || DESK="${ART_SRC}/desktop/nyxus_desktop.py"
if [[ -f "${DESK}" ]]; then
  grep -q "BUTTON_SECONDARY" "${DESK}" \
    && ok "desktop: BUTTON_SECONDARY (right-click) handler wired" \
    || fail "desktop: right-click handler missing in nyxus_desktop.py"
  grep -q "nyxus-context-menu" "${DESK}" \
    && ok "desktop: invokes nyxus-context-menu.sh on right-click" \
    || fail "desktop: nyxus-context-menu.sh dispatch missing"
fi


# ── 13x. Sprint C · Top 3 Apps full Build Standard (rev r15 — 2026-05-14) ──
# Software Center · NYXUS Capture · Notification Center must each ship with:
#   1. .desktop entry whose Exec= path actually exists in airootfs
#   2. Hyprland keybind in skel/.config/hypr/hyprland.conf
#   3. SectionDef + PAGE_CLASSES registration in nyxus_settings.py
#   4. Notification Center drawer mode + matching windowrule
echo
echo "── 13x. Sprint C · Top 3 Apps full Build Standard ─────────────────"

SPRINT_C_HYPR="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
SPRINT_C_RULES="${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-windowrules.conf"
SPRINT_C_SETTINGS="${ART_SRC}/nyxus_settings.py"
SPRINT_C_NOTIF="${AIROOT}/opt/nyxus/nyxus_settings_notifications.py"

# (a) .desktop entries + their Exec= targets exist
for spec in \
    "nyxus-software.desktop|opt/nyxus/nyxus_store.py|software" \
    "nyxus-capture.desktop|opt/nyxus/nyxus_screenshot.py|capture" \
    "nyxus-notification-center.desktop|opt/nyxus/nyxus_settings_notifications.py|notif_center"; do
  IFS='|' read -r dfile target key <<< "${spec}"
  dpath="${AIROOT}/usr/share/applications/${dfile}"
  if [[ -f "${dpath}" ]]; then
    ok "Sprint C: ${dfile} present"
    if [[ -f "${AIROOT}/${target}" ]]; then
      ok "Sprint C: Exec target /${target} exists in airootfs"
    else
      fail "Sprint C: ${dfile} references /${target} but file is missing"
    fi
  else
    fail "Sprint C: ${dfile} missing from /usr/share/applications/"
  fi
done

# (b) Hyprland binds present (Super+Shift+A → software, Super+Shift+S
#     → capture, Super+N → notif drawer)
if [[ -f "${SPRINT_C_HYPR}" ]]; then
  grep -qE '^bind = \$mod SHIFT, A,.*nyxus_store' "${SPRINT_C_HYPR}" \
    && ok "Sprint C: Super+Shift+A → nyxus_store bind present" \
    || fail "Sprint C: Super+Shift+A → nyxus_store bind missing"
  grep -qE '^bind = \$mod SHIFT, S,.*nyxus_screenshot' "${SPRINT_C_HYPR}" \
    && ok "Sprint C: Super+Shift+S → nyxus_screenshot bind present" \
    || fail "Sprint C: Super+Shift+S → nyxus_screenshot bind missing"
  grep -qE '^bind = \$mod, +N,.*nyxus_settings_notifications.*--drawer' "${SPRINT_C_HYPR}" \
    && ok "Sprint C: Super+N → notification drawer bind present" \
    || fail "Sprint C: Super+N → notification drawer bind missing"
else
  fail "Sprint C: ${SPRINT_C_HYPR} missing — cannot verify keybinds"
fi

# (c) Notification Center drawer mode wired in standalone main()
if [[ -f "${SPRINT_C_NOTIF}" ]]; then
  grep -q '"--drawer" in sys.argv' "${SPRINT_C_NOTIF}" \
    && ok "Sprint C: notif center main() handles --drawer flag" \
    || fail "Sprint C: notif center main() missing --drawer handling"
  grep -q 'Gtk4LayerShell' "${SPRINT_C_NOTIF}" \
    && ok "Sprint C: notif drawer attempts gtk4-layer-shell anchoring" \
    || fail "Sprint C: notif drawer missing layer-shell anchor"
fi

# (d) Drawer windowrule fallback present
if [[ -f "${SPRINT_C_RULES}" ]]; then
  grep -qE '^windowrulev2 = float,.*class:\^\(com\\\.nyxus\\\.notifications\)\$' "${SPRINT_C_RULES}" \
    && ok "Sprint C: drawer fallback windowrule (float) present" \
    || fail "Sprint C: drawer fallback windowrule (float) missing"
  grep -qE '^windowrulev2 = move .*class:\^\(com\\\.nyxus\\\.notifications\)\$' "${SPRINT_C_RULES}" \
    && ok "Sprint C: drawer fallback windowrule (right-edge move) present" \
    || fail "Sprint C: drawer fallback windowrule (move) missing"
fi

# (e) Three settings hub pages registered (SectionDef + PAGE_CLASSES + glyph)
if [[ -f "${SPRINT_C_SETTINGS}" ]]; then
  for key in software capture notif_center; do
    grep -qE "^[[:space:]]*SectionDef\(\"${key}\"," "${SPRINT_C_SETTINGS}" \
      && ok "Sprint C: SectionDef('${key}') registered" \
      || fail "Sprint C: SectionDef('${key}') missing from SECTIONS tuple"
    grep -qE "^[[:space:]]*\"${key}\":[[:space:]]+(Software|Capture|NotifCenter)Page," \
         "${SPRINT_C_SETTINGS}" \
      && ok "Sprint C: PAGE_CLASSES['${key}'] wired to its page class" \
      || fail "Sprint C: PAGE_CLASSES['${key}'] missing or wrong class"
    grep -qE "^[[:space:]]*\"${key}\":[[:space:]]+\"\\\\u" "${SPRINT_C_SETTINGS}" \
      && ok "Sprint C: glyph icon for '${key}' present" \
      || fail "Sprint C: glyph icon for '${key}' missing from glyph map"
  done

  # 6-section Build Standard: General + Appearance + Behavior present
  # in each new page. (Keybinds + Reset + Advanced are auto-injected
  # by SectionPage's footer — guaranteed structurally.)
  for cls in SoftwarePage CapturePage NotifCenterPage; do
    cls_block=$(awk -v c="${cls}" '
      $0 ~ "^class " c "\\(SectionPage\\):" { in_cls = 1; print; next }
      in_cls && /^class / { in_cls = 0 }
      in_cls { print }
    ' "${SPRINT_C_SETTINGS}")
    fails=0
    for needed in "title=\"General\"" "title=\"Appearance\"" "title=\"Behavior\""; do
      grep -qF "${needed}" <<< "${cls_block}" || fails=1
    done
    if (( fails == 0 )); then
      ok "Sprint C: ${cls} ships General+Appearance+Behavior groups"
    else
      fail "Sprint C: ${cls} missing one of General/Appearance/Behavior"
    fi

    # NYXUS Build Standard: no stub markers in shipped page code
    if grep -qE "TODO|FIXME|placeholder|coming soon|not implemented" \
         <<< "${cls_block}"; then
      fail "Sprint C: ${cls} contains stub markers (TODO/FIXME/placeholder)"
    else
      ok "Sprint C: ${cls} has no stub markers"
    fi
  done
fi

# ══════════════════════════════════════════════════════════════════════
# §14x — Sprint D: brand asset library + chrome redesign (rev r15)
# ----------------------------------------------------------------------
# Asserts the locked rev r15 cream brand is consistently applied across
# every chrome surface (SDDM, hyprlock, EWW bar, GTK theme, icons),
# and that no purple/Dark-Mirror residue from earlier specs survives.
# ══════════════════════════════════════════════════════════════════════

# (a) Brand asset library exists with all four marks + wordmark + README
SPRINT_D_BRAND="${PROFILE}/airootfs/usr/share/nyxus/brand"
if [[ -d "${SPRINT_D_BRAND}" ]]; then
  for mark in eclipse.svg eclipse-cream.svg constellation-n.svg \
              eye-of-nyx.svg wordmark-nyxus.svg README.md; do
    [[ -f "${SPRINT_D_BRAND}/${mark}" ]] \
      && ok "Sprint D: brand asset ${mark} present" \
      || fail "Sprint D: brand asset ${mark} missing"
  done
else
  fail "Sprint D: brand asset directory ${SPRINT_D_BRAND} missing"
fi

# Render script exists and is executable. PROFILE is iso-builder/nyx-profile,
# so the script lives one level up at ../scripts/render-brand-pngs.sh.
SPRINT_D_RENDER="${PROFILE}/../scripts/render-brand-pngs.sh"
if [[ -x "${SPRINT_D_RENDER}" ]]; then
  ok "Sprint D: brand PNG renderer is executable"
else
  fail "Sprint D: brand PNG renderer missing or not executable"
fi

# build-iso.sh invokes the renderer
SPRINT_D_BUILD="${PROFILE}/../build-iso.sh"
if [[ -f "${SPRINT_D_BUILD}" ]] && grep -q 'render-brand-pngs.sh' "${SPRINT_D_BUILD}"; then
  ok "Sprint D: build-iso.sh wires the brand PNG renderer"
else
  fail "Sprint D: build-iso.sh does NOT invoke render-brand-pngs.sh"
fi

# (b₀) SDDM tarball is the BUILD-TIME source of truth — build-iso.sh
# extracts it over airootfs at line 339. If the tarball still ships the
# old DARK MIRROR purple Main.qml, the airootfs r3 file gets clobbered
# at bake time and the live ISO ships the wrong greeter regardless of
# what verify-profile says about the airootfs source. Assert the tarball
# itself contains the r3 cream content.
SPRINT_D_SDDM_TGZ="${PROFILE}/../../artifacts/api-server/nyxus-scripts/nyxus-sddm-theme.tar.gz"
if [[ -f "${SPRINT_D_SDDM_TGZ}" ]]; then
  # Tarball stores paths with leading "./" — try both forms.
  tarball_qml="$(tar -xzOf "${SPRINT_D_SDDM_TGZ}" ./Main.qml 2>/dev/null \
                 || tar -xzOf "${SPRINT_D_SDDM_TGZ}" Main.qml 2>/dev/null \
                 || echo "")"
  if grep -q '#f4ead5' <<< "${tarball_qml}"; then
    ok "Sprint D: SDDM tarball Main.qml is cream r3 (won't clobber)"
  else
    fail "Sprint D: SDDM tarball Main.qml is STALE — will clobber r3 at bake time"
  fi
  if grep -q 'DARK MIRROR' <<< "${tarball_qml}"; then
    fail "Sprint D: SDDM tarball Main.qml still contains DARK MIRROR branding"
  else
    ok "Sprint D: SDDM tarball Main.qml DARK MIRROR purged"
  fi
  if tar -tzf "${SPRINT_D_SDDM_TGZ}" 2>/dev/null | grep -q '^\./eclipse\.png$'; then
    ok "Sprint D: SDDM tarball bundles eclipse.png (self-contained mark)"
  else
    fail "Sprint D: SDDM tarball missing bundled eclipse.png"
  fi
else
  fail "Sprint D: SDDM tarball ${SPRINT_D_SDDM_TGZ} missing"
fi

# Hyprlock NS source must also be the cream r3 — build-iso.sh installs
# it from artifacts/api-server/nyxus-scripts/hyprlock.conf, clobbering
# the airootfs version if the NS source still says DARK MIRROR.
SPRINT_D_HYPRLOCK_NS="${PROFILE}/../../artifacts/api-server/nyxus-scripts/hyprlock.conf"
if [[ -f "${SPRINT_D_HYPRLOCK_NS}" ]]; then
  if grep -q 'DARK MIRROR' "${SPRINT_D_HYPRLOCK_NS}"; then
    fail "Sprint D: NS hyprlock.conf still STALE DARK MIRROR — will clobber r3"
  else
    ok "Sprint D: NS hyprlock.conf is r3 cream (won't clobber airootfs)"
  fi
fi

# (b) SDDM r3: cream accent, Eclipse mark, no purple, no ◤ X ◥, no dup clock
SPRINT_D_SDDM="${PROFILE}/airootfs/usr/share/sddm/themes/nyxus/Main.qml"
if [[ -f "${SPRINT_D_SDDM}" ]]; then
  grep -q '#f4ead5' "${SPRINT_D_SDDM}" \
    && ok "Sprint D: SDDM uses cream accent (#f4ead5)" \
    || fail "Sprint D: SDDM missing cream accent"
  grep -qE 'eclipse\.(svg|png)' "${SPRINT_D_SDDM}" \
    && ok "Sprint D: SDDM references Eclipse mark" \
    || fail "Sprint D: SDDM does NOT reference Eclipse mark"
  if grep -qE 'C084FC|c084fc|7C3AED|5B21B6' "${SPRINT_D_SDDM}"; then
    fail "Sprint D: SDDM still contains purple accent residue"
  else
    ok "Sprint D: SDDM purple residue purged"
  fi
  if grep -qF '◤ X ◥' "${SPRINT_D_SDDM}"; then
    fail "Sprint D: SDDM still contains deprecated ◤ X ◥ glyph"
  else
    ok "Sprint D: SDDM ◤ X ◥ glyph purged"
  fi
  if grep -q 'DARK MIRROR' "${SPRINT_D_SDDM}"; then
    fail "Sprint D: SDDM still contains Dark Mirror legacy branding"
  else
    ok "Sprint D: SDDM Dark Mirror branding purged"
  fi
  # Single clock: exactly one Qt.formatDateTime that emits HH:mm
  clock_count=$(grep -cE 'Qt\.formatDateTime.*HH:mm' "${SPRINT_D_SDDM}" || true)
  if (( clock_count == 1 )); then
    ok "Sprint D: SDDM has exactly one HH:mm clock (no dup)"
  else
    fail "Sprint D: SDDM has ${clock_count} HH:mm clocks (must be 1)"
  fi
else
  fail "Sprint D: SDDM Main.qml missing"
fi

# (c) Hyprlock r3: cream, Eclipse PNG via image{}, 3px rounding, no purple
SPRINT_D_HYPRLOCK="${PROFILE}/airootfs/etc/skel/.config/hypr/hyprlock.conf"
if [[ -f "${SPRINT_D_HYPRLOCK}" ]]; then
  grep -q '244, 234, 213' "${SPRINT_D_HYPRLOCK}" \
    && ok "Sprint D: hyprlock uses cream accent (rgba 244,234,213)" \
    || fail "Sprint D: hyprlock missing cream accent"
  grep -q 'eclipse-128.png' "${SPRINT_D_HYPRLOCK}" \
    && ok "Sprint D: hyprlock references Eclipse PNG mark" \
    || fail "Sprint D: hyprlock does NOT reference Eclipse PNG mark"
  grep -qE '^[[:space:]]*rounding[[:space:]]*=[[:space:]]*3' "${SPRINT_D_HYPRLOCK}" \
    && ok "Sprint D: hyprlock input rounding = 3 (brand spec)" \
    || fail "Sprint D: hyprlock input rounding not 3"
  if grep -qE '192,\s*132,\s*252' "${SPRINT_D_HYPRLOCK}"; then
    fail "Sprint D: hyprlock still contains purple residue (192,132,252)"
  else
    ok "Sprint D: hyprlock purple residue purged"
  fi
  if grep -qF '◤ X ◥' "${SPRINT_D_HYPRLOCK}"; then
    fail "Sprint D: hyprlock still contains deprecated ◤ X ◥ glyph"
  else
    ok "Sprint D: hyprlock ◤ X ◥ glyph purged"
  fi
else
  fail "Sprint D: hyprlock.conf missing"
fi

# (d) EWW bar: slim (min-height 32) + cream + glass
SPRINT_D_EWW_SCSS="${PROFILE}/airootfs/etc/skel/.config/eww/eww.scss"
SPRINT_D_EWW_YUCK="${PROFILE}/airootfs/etc/skel/.config/eww/eww.yuck"
if [[ -f "${SPRINT_D_EWW_SCSS}" ]]; then
  grep -qE '\.bar-bottom \{ padding: 4px 12px; min-height: 32px; \}' \
       "${SPRINT_D_EWW_SCSS}" \
    && ok "Sprint D: EWW bar-bottom is slim (32px)" \
    || fail "Sprint D: EWW bar-bottom not slimmed to 32px"
  grep -q '#f4ead5' "${SPRINT_D_EWW_SCSS}" \
    && ok "Sprint D: EWW bar uses cream accent" \
    || fail "Sprint D: EWW bar missing cream accent"
fi
if [[ -f "${SPRINT_D_EWW_YUCK}" ]]; then
  grep -q ':height "40px"' "${SPRINT_D_EWW_YUCK}" \
    && ok "Sprint D: EWW bar-bottom window is 40px (down from 56)" \
    || fail "Sprint D: EWW bar-bottom window not 40px"
fi

# (e) NYXUS-Dark GTK theme is no longer empty
SPRINT_D_GTK_THEME="${PROFILE}/airootfs/usr/share/themes/NYXUS-Dark"
if [[ -d "${SPRINT_D_GTK_THEME}" ]]; then
  for f in index.theme gtk-3.0/gtk.css gtk-4.0/gtk.css; do
    [[ -f "${SPRINT_D_GTK_THEME}/${f}" ]] \
      && ok "Sprint D: NYXUS-Dark/${f} exists" \
      || fail "Sprint D: NYXUS-Dark/${f} missing"
  done
fi

# Skel-level user overlays so cream applies even when env forces Adwaita
for f in gtk-3.0/gtk.css gtk-4.0/gtk.css; do
  p="${PROFILE}/airootfs/etc/skel/.config/${f}"
  if [[ -f "${p}" ]] && grep -q '#f4ead5' "${p}"; then
    ok "Sprint D: skel ${f} ships cream-accent overlay"
  else
    fail "Sprint D: skel ${f} missing or lacks cream overlay"
  fi
done

# (f) Icon theme dirs exist for every Directories= entry in index.theme
SPRINT_D_ICONS="${PROFILE}/airootfs/usr/share/icons/NYXUS-Dark"
if [[ -f "${SPRINT_D_ICONS}/index.theme" ]]; then
  for d in scalable/apps scalable/places scalable/devices scalable/status \
           scalable/actions symbolic/apps; do
    if [[ -d "${SPRINT_D_ICONS}/${d}" ]]; then
      ok "Sprint D: icon theme dir ${d} exists"
    else
      fail "Sprint D: icon theme dir ${d} missing (declared in index.theme)"
    fi
  done
fi


# ──────────────────────────────────────────────────────────────────────
# §15x · Sprint E — Total Identity assertions
#   Every brand surface checked here. Drift = FAIL.
# ──────────────────────────────────────────────────────────────────────
hd "§15x  Sprint E — Total Identity"

ICN_DIR="${AIROOT}/usr/share/icons/NYXUS-Dark/scalable/apps"
DESK_DIR="${AIROOT}/usr/share/applications"

# (a) all 12 NYXUS app icons present
for app in nyxus-settings nyxus-store nyxus-capture nyxus-notification-center \
           nyxus-sysmon nyxus-notepad nyxus-stickies nyxus-widgets \
           nyxus-ghost-auth nyxus-files nyxus-terminal nyxus-browser; do
  if [[ -f "${ICN_DIR}/${app}.svg" ]]; then
    ok "Sprint E: app icon ${app}.svg present"
  else
    fail "Sprint E: app icon ${app}.svg MISSING"
  fi
done

# (b) every nyxus-NAME icon must use the chassis (radial bg + cream ring)
for f in "${ICN_DIR}"/nyxus-*.svg; do
  [[ -f "$f" ]] || continue
  bn=$(basename "$f")
  if ! grep -q 'radialGradient' "$f"; then
    fail "Sprint E: ${bn} missing radialGradient chassis"
  fi
  if ! grep -q '#f4ead5' "$f"; then
    fail "Sprint E: ${bn} missing cream #f4ead5 (off-brand)"
  fi
done

# (c) .desktop entries point at the brand icons (sample of must-haves)
declare -A WANT=(
  [nyxus-capture.desktop]=nyxus-capture
  [nyxus-files.desktop]=nyxus-files
  [nyxus-notepad.desktop]=nyxus-notepad
  [nyxus-notification-center.desktop]=nyxus-notification-center
  [nyxus-stickies.desktop]=nyxus-stickies
  [nyxus-store.desktop]=nyxus-store
  [nyxus-sysmon-gtk.desktop]=nyxus-sysmon
  [nyxus-terminal.desktop]=nyxus-terminal
)
for d in "${!WANT[@]}"; do
  p="${DESK_DIR}/${d}"
  [[ -f "$p" ]] || { warn "Sprint E: ${d} not present (skipped)"; continue; }
  got=$(grep -m1 -E '^Icon=' "$p" | cut -d= -f2)
  if [[ "$got" == "${WANT[$d]}" ]]; then
    ok "Sprint E: ${d} → Icon=${WANT[$d]}"
  else
    fail "Sprint E: ${d} Icon=${got} (expected ${WANT[$d]})"
  fi
done

# (d) swaync style.css — cream + 3px + glass + no DARK MIRROR
SWAY="${AIROOT}/etc/skel/.config/swaync/style.css"
if [[ -f "$SWAY" ]]; then
  grep -q '#f4ead5'            "$SWAY" && ok "Sprint E: swaync uses cream #f4ead5" \
                                       || fail "Sprint E: swaync missing cream"
  grep -q 'border-radius: 3px' "$SWAY" && ok "Sprint E: swaync uses 3px corners" \
                                       || fail "Sprint E: swaync NOT 3px corners"
  if grep -qiE 'dark[ _]mirror|splat-' "$SWAY"; then
    fail "Sprint E: swaync still references legacy DARK MIRROR / splat-*"
  else
    ok "Sprint E: swaync free of legacy DARK MIRROR / splat residue"
  fi
  if grep -qE 'C084FC|c084fc|7C3AED|a06bff|3ad8ff|06b6d4' "$SWAY"; then
    fail "Sprint E: swaync still has forbidden purple/cyan hex"
  else
    ok "Sprint E: swaync free of forbidden purple/cyan"
  fi
fi

# (e) rofi nyxus.rasi — cream + 3px + no splat-* + no purple
ROFI="${AIROOT}/etc/skel/.config/rofi/nyxus.rasi"
if [[ -f "$ROFI" ]]; then
  grep -q '#f4ead5'            "$ROFI" && ok "Sprint E: rofi uses cream #f4ead5" \
                                       || fail "Sprint E: rofi missing cream"
  grep -q 'border-radius:    3px' "$ROFI" && ok "Sprint E: rofi uses 3px corners" \
                                          || fail "Sprint E: rofi NOT 3px corners"
  if grep -qE 'splat-|purple wash|C084FC|c084fc|a06bff|3ad8ff' "$ROFI"; then
    fail "Sprint E: rofi still has splat-* / purple residue"
  else
    ok "Sprint E: rofi clean of splat-* / purple residue"
  fi
fi

# (f) GTK depth pass — both gtk-3 and gtk-4 must have ≥10 depth occurrences
G3="${AIROOT}/usr/share/themes/NYXUS-Dark/gtk-3.0"
G4="${AIROOT}/usr/share/themes/NYXUS-Dark/gtk-4.0"
G3CNT=$(grep -hcE 'box-shadow|linear-gradient|outline:|transition' "${G3}/gtk.css" "${G3}/nyxus-depth.css" 2>/dev/null | awk '{s+=$1} END{print s+0}')
G4CNT=$(grep -cE 'box-shadow|linear-gradient|outline:|transition' "${G4}/gtk.css" 2>/dev/null)
if (( G3CNT >= 10 )); then ok "Sprint E: gtk-3.0 depth=${G3CNT} (≥10)"; else fail "Sprint E: gtk-3.0 depth=${G3CNT} (<10)"; fi
if (( G4CNT >= 10 )); then ok "Sprint E: gtk-4.0 depth=${G4CNT} (≥10)"; else fail "Sprint E: gtk-4.0 depth=${G4CNT} (<10)"; fi
[[ -f "${G3}/nyxus-depth.css" ]] && ok "Sprint E: gtk-3.0/nyxus-depth.css present" \
                                 || fail "Sprint E: gtk-3.0/nyxus-depth.css missing"

# (g) hyprland active border is cream, not pure white
HYP="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
if grep -qE 'col\.active_border\s*=\s*rgba\(f4ead5' "$HYP"; then
  ok "Sprint E: hyprland col.active_border is cream f4ead5"
elif grep -qE 'col\.active_border\s*=\s*rgba\(ffffff' "$HYP"; then
  fail "Sprint E: hyprland col.active_border still pure white"
else
  warn "Sprint E: hyprland border colour unverified"
fi

# (h) legacy plymouth nyxus theme PURGED (active is nyxus-void)
if [[ -d "${AIROOT}/usr/share/plymouth/themes/nyxus" ]]; then
  fail "Sprint E: legacy plymouth nyxus dir still present (must be PURGED — active is nyxus-void)"
else
  ok "Sprint E: legacy plymouth nyxus PURGED"
fi
[[ -f "${AIROOT}/usr/share/plymouth/themes/nyxus-void/nyxus-void.script" ]] \
  && ok "Sprint E: plymouth nyxus-void DARKSIDE theme present" \
  || fail "Sprint E: plymouth nyxus-void script MISSING"

# (i) GRUB theme rebrand — no false "purple+cyan" comment, no DARK MIRROR label
GRUB="${AIROOT}/usr/share/grub/themes/nyxus/theme.txt"
if [[ -f "$GRUB" ]]; then
  # Sprint G: only inspect ACTIVE config (non-comment lines). The Sprint G
  # rebrand comment legitimately mentions the old palette to explain what
  # was removed, which used to trip this check.
  if grep -vE '^\s*#|^\s*$' "$GRUB" | grep -qiE 'purple|cyan|DARK MIRROR'; then
    fail "Sprint E: GRUB theme.txt still references DARK MIRROR / purple / cyan in ACTIVE config"
  else
    ok "Sprint E: GRUB theme.txt rebranded clean"
  fi
fi

# (j) MOTD branded with Eclipse + no DARK MIRROR
MOTD="${AIROOT}/etc/motd"
if [[ -f "$MOTD" ]]; then
  if grep -qE 'DARK MIRROR' "$MOTD"; then
    fail "Sprint E: /etc/motd still says DARK MIRROR"
  else
    ok "Sprint E: /etc/motd rebranded"
  fi
  grep -q 'Darkside' "$MOTD" && ok "Sprint E: /etc/motd has Darkside tagline" || warn "Sprint E: /etc/motd missing Darkside tagline"
fi

# (k) fontconfig — Inter+JBM+Caveat locked
FC="${AIROOT}/etc/fonts/conf.d/75-nyxus.conf"
if [[ -f "$FC" ]]; then
  ok "Sprint E: fontconfig 75-nyxus.conf present"
  grep -q 'Inter'                   "$FC" && ok "Sprint E: fontconfig pins Inter"     || fail "Sprint E: fontconfig missing Inter"
  grep -q 'JetBrainsMono Nerd Font' "$FC" && ok "Sprint E: fontconfig pins JBM Nerd"  || fail "Sprint E: fontconfig missing JBM Nerd"
  grep -q 'Caveat'                  "$FC" && ok "Sprint E: fontconfig pins Caveat"    || fail "Sprint E: fontconfig missing Caveat"
else
  fail "Sprint E: fontconfig 75-nyxus.conf MISSING"
fi

# (l) cursor X11 fallback — NYXUS-Aurora cursors/default symlink present
CUR="${AIROOT}/usr/share/icons/NYXUS-Aurora/cursors/default"
if [[ -L "$CUR" || -e "$CUR" ]]; then
  ok "Sprint E: NYXUS-Aurora cursors/default fallback present (X11 apps get branded cursor)"
else
  warn "Sprint E: NYXUS-Aurora cursors/default fallback missing (X11 apps fall back to white)"
fi

# ──────────────────────────────────────────────────────────────────────
# §15y — Sprint E pipeline guards (artifact source-of-truth)
# ──────────────────────────────────────────────────────────────────────
# build-iso.sh stages several runtime configs from
# `artifacts/api-server/nyxus-scripts/` INTO `airootfs/` at bake time.
# That means an in-spec airootfs/ tree is NOT enough — if the artifact
# source-of-truth file is legacy, it overwrites the airootfs version
# and silently reverts brand identity on a real ISO build.
# These guards lock the upstream copies to the same r15 spec.
section "§15y — Sprint E source-of-truth guards (artifacts/api-server/nyxus-scripts)"
NS_SRC="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/artifacts/api-server/nyxus-scripts"
if [[ -d "$NS_SRC" ]]; then
  # rofi
  R="$NS_SRC/rofi-nyxus.rasi"
  if [[ -f "$R" ]]; then
    grep -q 'splat-purple' "$R" && fail "Sprint E src: rofi-nyxus.rasi still references splat-purple" \
      || ok "Sprint E src: rofi-nyxus.rasi free of splat-purple"
    grep -qi 'purple wash\|dark mirror' "$R" && fail "Sprint E src: rofi-nyxus.rasi has DARK MIRROR / purple wash text" \
      || ok "Sprint E src: rofi-nyxus.rasi clean of legacy brand text"
    grep -q 'f4ead5' "$R" && ok "Sprint E src: rofi-nyxus.rasi uses cream f4ead5" \
      || fail "Sprint E src: rofi-nyxus.rasi missing cream accent"
  else
    fail "Sprint E src: $R MISSING (build-iso.sh will fail)"
  fi
  # hyprland
  H="$NS_SRC/hyprland.conf"
  if [[ -f "$H" ]]; then
    # Sprint K-A rev r16 pivot: active border now leads with copper
    # #b8865a as the dominant 1st stop, cream as a softer 2nd stop.
    # Either is acceptable as "off white/cyan/purple"; the K-A guard
    # in §15ad+§15ae asserts copper specifically.
    grep -qE 'col\.active_border\s*=\s*rgba\((f4ead5|b8865a)' "$H" \
      && ok "Sprint E src: hyprland.conf col.active_border = cream-or-copper (rev r16 ok)" \
      || fail "Sprint E src: hyprland.conf col.active_border NOT cream f4ead5 or copper b8865a"
    grep -qE 'col\.active_border\s*=\s*rgba\(ffffff' "$H" \
      && fail "Sprint E src: hyprland.conf still has white border (will overwrite cream airootfs at bake)" \
      || ok "Sprint E src: hyprland.conf free of legacy white border"
  else
    fail "Sprint E src: $H MISSING"
  fi
  # dunst
  D="$NS_SRC/nyxus-dunstrc"
  if [[ -f "$D" ]]; then
    if grep -qE '^\s*corner_radius\s*=\s*3\b' "$D"; then
      ok "Sprint E src: nyxus-dunstrc corner_radius = 3 (rev r15)"
    else
      fail "Sprint E src: nyxus-dunstrc corner_radius != 3 (sharp slab violates rev r15)"
    fi
  else
    fail "Sprint E src: $D MISSING"
  fi
  # desktop entries — must use Icon=nyxus-* (not generic Papirus fallbacks)
  if [[ -d "$NS_SRC/desktop-entries" ]]; then
    BAD_ICONS=0
    for d in "$NS_SRC"/desktop-entries/nyxus-{capture,files,notepad,notes,notification-center,screenshot,stickies,store,software,sysmon-gtk,terminal}.desktop; do
      [[ -f "$d" ]] || continue
      if ! grep -qE '^Icon=nyxus-' "$d"; then
        fail "Sprint E src: $(basename "$d") Icon= is not branded nyxus-*"
        BAD_ICONS=$((BAD_ICONS+1))
      fi
    done
    (( BAD_ICONS == 0 )) && ok "Sprint E src: all 11 promoted .desktop entries use Icon=nyxus-*"
  else
    fail "Sprint E src: $NS_SRC/desktop-entries dir MISSING"
  fi
else
  warn "Sprint E src: $NS_SRC dir not found — skipping pipeline guards"
fi

# ──────────────────────────────────────────────────────────────────────
# §15z — Sprint F premium-pass assertions
# ──────────────────────────────────────────────────────────────────────
# Premium polish: Calamares slideshow rev r15, Fastfetch branded, Qt
# platform integration via Kvantum, scratchpads + HyprExpo bind +
# borders-plus-plus shard, source-of-truth promotion guards.
section "§15z — Sprint F premium polish (calamares · fastfetch · Qt · plugins)"

# (a) Calamares slideshow & branding — DARK MIRROR codename retired,
#     no cyan #e8edf5 (rev r15 forbids cyan).
QML="${AIROOT}/etc/calamares/branding/nyxus/show.qml"
DESC="${AIROOT}/etc/calamares/branding/nyxus/branding.desc"
if [[ -f "$QML" ]]; then
  grep -qi 'DARK MIRROR'  "$QML" && fail "Sprint F: show.qml still has DARK MIRROR text" \
    || ok "Sprint F: show.qml clean of DARK MIRROR codename"
  grep -qi 'e8edf5'       "$QML" && fail "Sprint F: show.qml still uses cyan e8edf5 (rev r15 violation)" \
    || ok "Sprint F: show.qml uses cream-only palette (no cyan)"
  grep -q  'Inter'        "$QML" && ok "Sprint F: show.qml uses Inter typography" \
    || warn "Sprint F: show.qml missing Inter font reference"
  grep -q  '◐'            "$QML" && ok "Sprint F: show.qml has Eclipse mark" \
    || warn "Sprint F: show.qml missing Eclipse glyph"
else
  fail "Sprint F: $QML MISSING"
fi
if [[ -f "$DESC" ]]; then
  grep -qi 'DARK MIRROR'  "$DESC" && fail "Sprint F: branding.desc still references DARK MIRROR" \
    || ok "Sprint F: branding.desc clean of DARK MIRROR"
  grep -qE 'versionedName:\s*"NYXUS 2026\.05"' "$DESC" \
    && ok "Sprint F: branding.desc versionedName clean" \
    || fail "Sprint F: branding.desc versionedName not clean"
else
  fail "Sprint F: $DESC MISSING"
fi

# (b) Fastfetch — branded config + Eclipse ASCII art shipped
FF="${AIROOT}/etc/skel/.config/fastfetch/config.jsonc"
ASCII="${AIROOT}/usr/share/nyxus/brand/ascii/eclipse.txt"
if [[ -f "$FF" ]]; then
  ok "Sprint F: fastfetch config.jsonc present"
  grep -q 'NYXUS' "$FF" && ok "Sprint F: fastfetch shows NYXUS branding (hides Arch)" \
    || fail "Sprint F: fastfetch config doesn't brand as NYXUS"
else
  fail "Sprint F: fastfetch config.jsonc MISSING"
fi
[[ -f "$ASCII" ]] && ok "Sprint F: Eclipse ASCII art shipped" \
  || fail "Sprint F: Eclipse ASCII art MISSING ($ASCII)"

# (c) Qt platform integration — Kvantum theme + qt5ct/qt6ct + env vars
KV="${AIROOT}/usr/share/Kvantum/NYXUS"
[[ -f "$KV/NYXUS.kvconfig" ]] && ok "Sprint F: Kvantum NYXUS theme kvconfig present" \
  || fail "Sprint F: Kvantum NYXUS.kvconfig MISSING"
[[ -f "$KV/NYXUS.svg" ]]      && ok "Sprint F: Kvantum NYXUS theme svg present" \
  || fail "Sprint F: Kvantum NYXUS.svg MISSING"
[[ -f "${AIROOT}/etc/skel/.config/Kvantum/kvantum.kvconfig" ]] \
  && ok "Sprint F: skel Kvantum theme = NYXUS" \
  || fail "Sprint F: skel Kvantum theme pin MISSING"
[[ -f "${AIROOT}/etc/skel/.config/qt5ct/qt5ct.conf" ]] \
  && ok "Sprint F: qt5ct config shipped (Kvantum routed)" \
  || fail "Sprint F: qt5ct config MISSING"
[[ -f "${AIROOT}/etc/skel/.config/qt6ct/qt6ct.conf" ]] \
  && ok "Sprint F: qt6ct config shipped (Kvantum routed)" \
  || fail "Sprint F: qt6ct config MISSING"

ENVF="${AIROOT}/etc/environment"
if [[ -f "$ENVF" ]]; then
  grep -q 'QT_QPA_PLATFORMTHEME=qt5ct' "$ENVF" \
    && ok "Sprint F: /etc/environment routes Qt to qt5ct" \
    || fail "Sprint F: /etc/environment QT_QPA_PLATFORMTHEME not set"
  grep -q 'QT_STYLE_OVERRIDE=kvantum' "$ENVF" \
    && ok "Sprint F: /etc/environment overrides Qt style to kvantum" \
    || fail "Sprint F: /etc/environment QT_STYLE_OVERRIDE not set"
  grep -q 'XCURSOR_THEME=NYXUS-Aurora' "$ENVF" \
    && ok "Sprint F: /etc/environment pins NYXUS-Aurora cursor system-wide" \
    || fail "Sprint F: /etc/environment cursor pin MISSING"
  grep -q 'GTK_THEME=NYXUS-Dark' "$ENVF" \
    && ok "Sprint F: /etc/environment pins NYXUS-Dark GTK theme" \
    || fail "Sprint F: /etc/environment GTK theme pin MISSING"
else
  fail "Sprint F: /etc/environment MISSING"
fi

# (d) Hyprland premium polish — special blur + scratchpads + plugin shard
HC="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
if [[ -f "$HC" ]]; then
  grep -qE '^\s*special\s*=\s*true' "$HC" \
    && ok "Sprint F: hyprland blur 'special = true' (special workspaces blurred)" \
    || fail "Sprint F: hyprland special-workspace blur not enabled"
  grep -qE 'togglespecialworkspace, term' "$HC" \
    && ok "Sprint F: hyprland scratchpad term keybind present" \
    || fail "Sprint F: hyprland scratchpad term keybind MISSING"
  grep -q 'hyprexpo:expo, toggle' "$HC" \
    && ok "Sprint F: hyprland HyprExpo overview keybind present" \
    || fail "Sprint F: hyprland HyprExpo keybind MISSING"
  grep -q 'nyxus-hyprland-plugins.conf' "$HC" \
    && ok "Sprint F: hyprland sources plugins shard" \
    || fail "Sprint F: hyprland plugin shard not sourced"
  # Border colors must NOT use the deprecated cyan-grey gradient
  if grep -qE 'col\.active_border.*e8edf5' "$HC"; then
    fail "Sprint F: hyprland border still uses deprecated cyan-grey e8edf5"
  else
    ok "Sprint F: hyprland border free of cyan-grey (cream-only gradient)"
  fi
fi
[[ -f "${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-plugins.conf" ]] \
  && ok "Sprint F: nyxus-hyprland-plugins.conf shard shipped" \
  || fail "Sprint F: plugins shard MISSING"

# (e) hyprpm plugin builder — user-session unit (NOT system firstboot)
# rev2: original draft put this at /etc/nyxus-firstboot.d/15-hyprpm-plugins.sh
# but that runs as root before any Hyprland session exists, so hyprctl is
# unreachable and the orchestrator's marker prevents retry. Architect review
# caught it. Now lives at /usr/local/bin/nyxus-hyprpm-plugins triggered by
# user systemd unit. Guard against the broken pattern returning.
LEGACY="${AIROOT}/etc/nyxus-firstboot.d/15-hyprpm-plugins.sh"
[[ -e "$LEGACY" ]] && fail "Sprint F rev2: legacy firstboot hyprpm script reappeared at $LEGACY (must be user-service)" \
  || ok "Sprint F rev2: legacy /etc/nyxus-firstboot.d/15-hyprpm-plugins.sh purged"

HPM_BIN="${AIROOT}/usr/local/bin/nyxus-hyprpm-plugins"
HPM_SVC="${AIROOT}/etc/skel/.config/systemd/user/nyxus-hyprpm-plugins.service"
if [[ -x "$HPM_BIN" ]]; then
  ok "Sprint F rev2: nyxus-hyprpm-plugins binary present + executable"
  grep -q 'borders-plus-plus' "$HPM_BIN" && ok "Sprint F: builder installs borders-plus-plus" \
    || fail "Sprint F: builder doesn't install borders-plus-plus"
  grep -q 'hyprexpo' "$HPM_BIN" && ok "Sprint F: builder installs hyprexpo" \
    || fail "Sprint F: builder doesn't install hyprexpo"
  # Sentinel-on-full-success policy must be enforced
  grep -q 'ok_bpp == 1 && ok_expo == 1' "$HPM_BIN" \
    && ok "Sprint F rev2: sentinel only writes on FULL plugin success (architect fix)" \
    || fail "Sprint F rev2: sentinel policy regression — must require both plugins"
  # User-context check (HYPRLAND_INSTANCE_SIGNATURE) must be present
  grep -q 'HYPRLAND_INSTANCE_SIGNATURE' "$HPM_BIN" \
    && ok "Sprint F rev2: builder verifies user-session context" \
    || fail "Sprint F rev2: builder doesn't check Hyprland session"
else
  fail "Sprint F rev2: hyprpm builder MISSING or not +x ($HPM_BIN)"
fi
if [[ -f "$HPM_SVC" ]]; then
  ok "Sprint F rev2: user systemd unit shipped"
  grep -q 'WantedBy=graphical-session.target' "$HPM_SVC" \
    && ok "Sprint F rev2: user unit hooks graphical-session.target" \
    || fail "Sprint F rev2: user unit missing graphical-session hook"
  grep -q 'ConditionPathExists=!.*plugins.done' "$HPM_SVC" \
    && ok "Sprint F rev2: user unit gated on sentinel" \
    || fail "Sprint F rev2: user unit missing sentinel gate"
else
  fail "Sprint F rev2: user systemd unit MISSING ($HPM_SVC)"
fi
# Hyprland.conf must trigger the user service via exec-once
grep -q 'systemctl --user start nyxus-hyprpm-plugins' "$HC" \
  && ok "Sprint F rev2: hyprland.conf exec-once triggers plugin builder" \
  || fail "Sprint F rev2: hyprland.conf doesn't start plugin builder service"

# (e2) Scratchpad keybinds must use SUPER+ALT zone (no collision with eww
# dashboard $mod+grave or notification drawer $mod+N)
if grep -qE '^bind\s+= \$mod,\s+grave,\s+togglespecialworkspace' "$HC"; then
  fail "Sprint F rev2: \$mod+grave scratchpad bind COLLIDES with eww dashboard"
else
  ok "Sprint F rev2: scratchpad bind moved off \$mod+grave (no eww collision)"
fi
if grep -qE 'bind\s+= \$mod ALT, T,\s+togglespecialworkspace' "$HC"; then
  ok "Sprint F rev2: term scratchpad → SUPER+ALT+T (collision-free)"
else
  fail "Sprint F rev2: term scratchpad bind missing or in wrong zone"
fi
if grep -qE 'bind\s+= \$mod ALT, P,\s+togglespecialworkspace' "$HC"; then
  ok "Sprint F rev2: notes scratchpad → SUPER+ALT+P (collision-free)"
else
  fail "Sprint F rev2: notes scratchpad bind missing or in wrong zone"
fi
# HyprExpo bind must live in shard (not main config) per architect feedback
if grep -qE 'bind\s+= \$mod,\s+F1,\s+hyprexpo' "$HC"; then
  fail "Sprint F rev2: HyprExpo bind still in main hyprland.conf (must be in shard)"
else
  ok "Sprint F rev2: HyprExpo bind moved out of main config"
fi
if grep -q 'hyprexpo:expo' "${AIROOT}/etc/skel/.config/hypr/conf.d/nyxus-hyprland-plugins.conf"; then
  ok "Sprint F rev2: HyprExpo bind in plugin shard (gates with plugin presence)"
else
  fail "Sprint F rev2: HyprExpo bind missing from plugin shard"
fi

# (f) Packages — kvantum + qt5ct + qt6ct must be in packages.x86_64
PKGS="$(dirname "${AIROOT}")/packages.x86_64"
for pkg in kvantum qt5ct qt6ct; do
  grep -qE "^${pkg}$" "$PKGS" \
    && ok "Sprint F: package shipped: $pkg" \
    || fail "Sprint F: package MISSING from packages.x86_64: $pkg"
done

# (g) Source-of-truth re-promotion (Sprint F edits to hyprland.conf must
#     also be in artifact source — see §15y for rationale).
NS_SRC="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}/artifacts/api-server/nyxus-scripts"
if [[ -f "$NS_SRC/hyprland.conf" ]]; then
  if grep -qE '^\s*special\s*=\s*true' "$NS_SRC/hyprland.conf"; then
    ok "Sprint F src: hyprland.conf source has special blur (Sprint F promoted)"
  else
    fail "Sprint F src: hyprland.conf source missing special blur — Sprint F NOT promoted (will revert at bake)"
  fi
  if grep -q 'nyxus-hyprland-plugins.conf' "$NS_SRC/hyprland.conf"; then
    ok "Sprint F src: hyprland.conf source sources plugins shard"
  else
    fail "Sprint F src: hyprland.conf source missing plugins shard source"
  fi
fi
[[ -f "$NS_SRC/nyxus-hyprland-plugins.conf" ]] \
  && ok "Sprint F src: nyxus-hyprland-plugins.conf in artifact source-of-truth" \
  || fail "Sprint F src: nyxus-hyprland-plugins.conf NOT promoted to artifact source"

# (g2) Calamares artifact source-of-truth — was stale "NYXUS 1.0 (Dark Mirror)"
# pre-rev2. Architect review flagged drift risk. Re-promoted; guard here
# prevents future regression.
CAL_SRC="$NS_SRC/calamares/branding/nyxus"
if [[ -d "$CAL_SRC" ]]; then
  if [[ -f "$CAL_SRC/branding.desc" ]]; then
    grep -qi 'DARK MIRROR' "$CAL_SRC/branding.desc" \
      && fail "Sprint F src: calamares branding.desc artifact source still has DARK MIRROR (drift)" \
      || ok "Sprint F src: calamares branding.desc artifact source clean"
    grep -qE 'versionedName:\s*"NYXUS 2026\.05"' "$CAL_SRC/branding.desc" \
      && ok "Sprint F src: calamares versionedName synced to airootfs" \
      || fail "Sprint F src: calamares versionedName drifted from airootfs"
  fi
  if [[ -f "$CAL_SRC/show.qml" ]] && [[ -f "${AIROOT}/etc/calamares/branding/nyxus/show.qml" ]]; then
    if cmp -s "$CAL_SRC/show.qml" "${AIROOT}/etc/calamares/branding/nyxus/show.qml"; then
      ok "Sprint F src: calamares show.qml in sync with airootfs"
    else
      fail "Sprint F src: calamares show.qml DRIFTED — re-promote to artifact source"
    fi
  fi
fi

# (h) /etc/environment Qt6 trade-off documented (architect feedback)
if grep -q 'Note on Qt5 vs Qt6 routing' "$ENVF"; then
  ok "Sprint F rev2: /etc/environment documents Qt6 routing trade-off"
else
  fail "Sprint F rev2: /etc/environment missing Qt6 trade-off comment"
fi

# ──────────────────────────────────────────────────────────────────────
# §15aa — Sprint G round-1 (palette violations + wallpaper rotation)
# ──────────────────────────────────────────────────────────────────────
# Sprint E shipped brand cohesion but TWO surfaces escaped the palette
# audit: dunstrc (every notification — purple #1f1b2c, banned cyan
# #e8edf5, banned red #f87171) and grub theme.txt (purple-grey
# #7b7390 + purple-white #e9e5f2 + cyan #e8edf5). Sprint G round-1
# fixes both + hooks the dynamic time-of-day wallpaper rotator that
# was orphaned in artifact source for ~3 sessions.
section "§15aa — Sprint G round-1 (locked-palette compliance + wallpaper)"

# (a) dunstrc — non-comment lines must contain no banned colors
DRC="${AIROOT}/etc/skel/.config/dunst/dunstrc"
if [[ -f "$DRC" ]]; then
  # Strip comments + blank lines, then look for banned hexes
  banned=$(grep -vE '^\s*#|^\s*$' "$DRC" | grep -ioE '#(1f1b2c|0a0a14|7b7390|e9e5f2|e8edf5|f87171)' | sort -u | tr '\n' ' ')
  if [[ -n "$banned" ]]; then
    fail "Sprint G: dunstrc has banned rev r15 colors in active config: $banned"
  else
    ok "Sprint G: dunstrc active config uses only locked rev r15 palette"
  fi
  grep -qE 'frame_color\s*=\s*"#f4ead5"' "$DRC" \
    && ok "Sprint G: dunstrc uses cream frame for normal urgency" \
    || fail "Sprint G: dunstrc normal urgency missing cream frame"
  # Sprint K-A rev r16 pivot: critical urgency frame moved from cream-bright
  # #fff8e0 to copper #b8865a so it stands distinct from normal cream-framed
  # alerts WITHOUT resorting to red. Either is acceptable as "off red"; the
  # K-A-specific guard in §15ad asserts copper specifically.
  grep -qE 'frame_color\s*=\s*"(#fff8e0|#b8865a)"' "$DRC" \
    && ok "Sprint G: dunstrc critical urgency frame is off-red (cream-bright or copper)" \
    || fail "Sprint G: dunstrc critical urgency not converted off red"
  grep -qE 'frame_width\s*=\s*3' "$DRC" \
    && ok "Sprint G: dunstrc critical urgency thicker frame (visual hierarchy w/o red)" \
    || warn "Sprint G: dunstrc critical thicker frame not present"
  grep -q 'JetBrainsMono Nerd Font' "$DRC" \
    && ok "Sprint G: dunstrc uses NYXUS canonical font (JBM Nerd)" \
    || warn "Sprint G: dunstrc not using JBM Nerd Font"
fi

# (b) GRUB theme.txt — non-comment palette compliance
GTX="${AIROOT}/usr/share/grub/themes/nyxus/theme.txt"
if [[ -f "$GTX" ]]; then
  banned=$(grep -vE '^\s*#|^\s*$' "$GTX" | grep -ioE '#(7b7390|e9e5f2|e8edf5|0a0a14|1a1a28)' | sort -u | tr '\n' ' ')
  if [[ -n "$banned" ]]; then
    fail "Sprint G: grub theme.txt has banned rev r15 colors in active config: $banned"
  else
    ok "Sprint G: grub theme.txt uses only locked rev r15 palette"
  fi
  grep -qE 'item_color\s*=\s*"#f4ead5"' "$GTX" \
    && ok "Sprint G: grub menu item color = cream (was purple-white)" \
    || fail "Sprint G: grub menu item color not cream"
fi

# (c) Wallpaper rotation infrastructure hooked end-to-end
WP_SH="${AIROOT}/etc/skel/.local/bin/nyxus-dynamic-wallpaper.sh"
WP_SVC="${AIROOT}/etc/skel/.config/systemd/user/nyxus-dynamic-wallpaper.service"
WP_TMR="${AIROOT}/etc/skel/.config/systemd/user/nyxus-dynamic-wallpaper.timer"
WP_LNK="${AIROOT}/etc/skel/.config/systemd/user/timers.target.wants/nyxus-dynamic-wallpaper.timer"
[[ -x "$WP_SH" ]]  && ok "Sprint G: dynamic-wallpaper.sh shipped + executable" \
                   || fail "Sprint G: dynamic-wallpaper.sh missing or not +x"
[[ -f "$WP_SVC" ]] && ok "Sprint G: dynamic-wallpaper.service shipped" \
                   || fail "Sprint G: dynamic-wallpaper.service missing"
[[ -f "$WP_TMR" ]] && ok "Sprint G: dynamic-wallpaper.timer shipped" \
                   || fail "Sprint G: dynamic-wallpaper.timer missing"
[[ -L "$WP_LNK" ]] && ok "Sprint G: timer auto-enabled via skel symlink" \
                   || fail "Sprint G: timer NOT enabled (no timers.target.wants symlink)"

# (d) Wallpaper count sanity — 94 was the baseline
WP_COUNT=$(ls "${AIROOT}/usr/share/backgrounds/nyxus/" 2>/dev/null | wc -l)
if (( WP_COUNT >= 90 )); then
  ok "Sprint G: wallpaper library populated ($WP_COUNT files)"
else
  warn "Sprint G: wallpaper library shrunk ($WP_COUNT files, baseline 94)"
fi

# (e) Sprint G round-2: BROAD palette compliance across UI configs.
# Architect findings: dunst+grub were only 2 of 9 violating files. eww,
# alacritty, rofi (nyxus + startmenu), wlogout, swaync all shipped
# active uses of #e8edf5 (cyan) and/or #f87171 (red). All converted to
# cream variants in round-2.
ROUND2_FILES=(
  "${AIROOT}/etc/skel/.config/eww/eww.scss"
  "${AIROOT}/etc/skel/.config/alacritty/alacritty.toml"
  "${AIROOT}/etc/skel/.config/rofi/nyxus.rasi"
  "${AIROOT}/etc/skel/.config/rofi/startmenu.rasi"
  "${AIROOT}/etc/skel/.config/wlogout/style.css"
  "${AIROOT}/etc/skel/.config/swaync/style.css"
)
r2_violations=0
for f in "${ROUND2_FILES[@]}"; do
  [[ ! -f "$f" ]] && continue
  # Strip line/block comments (//, #, /*, *, --) then look for banned hexes
  banned=$(grep -vE '^\s*(//|#|/\*|\*|--)' "$f" 2>/dev/null | grep -ioE '#(7b7390|e9e5f2|e8edf5|1f1b2c|f87171)' | sort -u | tr '\n' ' ')
  if [[ -n "$banned" ]]; then
    fail "Sprint G round-2: $(basename "$f") still has active banned hex: $banned"
    r2_violations=$((r2_violations + 1))
  fi
done
if (( r2_violations == 0 )); then
  ok "Sprint G round-2: all 6 UI surfaces (eww/alacritty/rofi×2/wlogout/swaync) clean of banned palette"
fi

# (f) accent.json — aurora (default) preset must be rev r15 compliant.
# Other presets (ember/verdant/violet/rose/ice/noir) are intentional
# alternate themes the user can opt into via Quick Settings — leave them.
ACC="${AIROOT}/etc/skel/.config/nyxus/accent.json"
if [[ -f "$ACC" ]]; then
  aurora_banned=$(grep -A1 '"aurora"' "$ACC" | grep -ioE '#(7b7390|e9e5f2|e8edf5|1f1b2c|f87171)' | sort -u | tr '\n' ' ')
  if [[ -n "$aurora_banned" ]]; then
    fail "Sprint G round-2: accent.json default 'aurora' preset has banned hex: $aurora_banned"
  else
    ok "Sprint G round-2: accent.json 'aurora' default preset rev r15 compliant"
  fi
fi

# (g) dynamic-wallpaper.sh hardened with graphical-session guard
WP_SH_SRC="${REPO_ROOT:-$PWD}/../artifacts/api-server/nyxus-scripts/nyxus-dynamic-wallpaper.sh"
[[ -f "$WP_SH" ]] && grep -q 'no graphical session yet' "$WP_SH" \
  && ok "Sprint G round-2: dynamic-wallpaper.sh has session-readiness guard (no early-boot race)" \
  || warn "Sprint G round-2: dynamic-wallpaper.sh missing graphical-session guard"

# (h) Sprint G round-3: visual target reference image LOCKED.
# User-provided canonical brand image (eclipse + cream halo + reflection)
# must ship with the OS as a brand asset and live in docs/brand for
# every future sprint to reference.
ECLIPSE_OS="${AIROOT}/usr/share/backgrounds/nyxus/nyxus-eclipse-reference.png"
ECLIPSE_DOCS="${REPO_ROOT:-$PWD/..}/docs/brand/nyxus-eclipse-reference.png"
ECLIPSE_DOCS_REL="../docs/brand/nyxus-eclipse-reference.png"
[[ -f "$ECLIPSE_OS" ]] \
  && ok "Sprint G round-3: visual target ships in /usr/share/backgrounds/nyxus/" \
  || fail "Sprint G round-3: visual target reference image missing from OS assets"
[[ -f "$ECLIPSE_DOCS" || -f "$ECLIPSE_DOCS_REL" ]] \
  && ok "Sprint G round-3: visual target pinned in docs/brand/ (survives ISO rebuilds)" \
  || fail "Sprint G round-3: visual target missing from docs/brand/"
[[ -f "${REPO_ROOT:-$PWD/..}/docs/brand/VISUAL-TARGET.md" || -f "../docs/brand/VISUAL-TARGET.md" ]] \
  && ok "Sprint G round-3: VISUAL-TARGET.md doc present (rules every future sprint follows)" \
  || warn "Sprint G round-3: VISUAL-TARGET.md missing"

# ── §15ab Sprint I: Brand-moment polish (login + welcome + Plymouth) ──
# Sprint I matches docs/brand/nyxus-desktop-target.png — slim top bar +
# right sidebar + eclipse wallpaper as hero + pure black surround.

# (i) SDDM login uses the locked plinth-eclipse background (image 2)
SDDM_BG="${AIROOT}/usr/share/sddm/themes/nyxus/background.png"
SDDM_QML="${AIROOT}/usr/share/sddm/themes/nyxus/Main.qml"
[[ -f "$SDDM_BG" ]] \
  && ok "Sprint I: SDDM background.png present (eclipse plinth scene)" \
  || fail "Sprint I: SDDM background.png missing"
[[ -f "$SDDM_QML" ]] && ! grep -q '"#f87171"' "$SDDM_QML" \
  && ok "Sprint I: SDDM Main.qml has no banned red (#f87171 purged)" \
  || fail "Sprint I: SDDM Main.qml still references banned red #f87171"
[[ -f "$SDDM_QML" ]] && grep -q 'source: "background.png"' "$SDDM_QML" \
  && ok "Sprint I: SDDM Main.qml shows background.png (eclipse visible behind veil)" \
  || warn "Sprint I: SDDM Main.qml may be hiding background.png with opaque overlay"

# (j) Eclipse Horizon default wallpaper present + manifested + mirrored
EH="${AIROOT}/usr/share/backgrounds/nyxus/nyxus-eclipse-horizon.png"
EH_SDDM="${AIROOT}/usr/share/sddm/themes/nyxus/backgrounds/nyxus-eclipse-horizon.png"
[[ -f "$EH" ]] \
  && ok "Sprint I: Eclipse Horizon wallpaper present (default desktop bg)" \
  || fail "Sprint I: Eclipse Horizon wallpaper missing"
[[ -f "$EH_SDDM" ]] \
  && ok "Sprint I: Eclipse Horizon mirrored to SDDM backgrounds dir" \
  || fail "Sprint I: Eclipse Horizon not mirrored to SDDM backgrounds"
grep -qP '^nyxus-eclipse-horizon\t' "${AIROOT}/usr/share/backgrounds/nyxus/manifest.tsv" \
  && ok "Sprint I: Eclipse Horizon registered in wallpaper manifest" \
  || fail "Sprint I: Eclipse Horizon missing from wallpaper manifest"

# (k) Wallpaper autostart promotes Eclipse Horizon to DEFAULT
WAS="${AIROOT}/usr/local/bin/nyxus-wallpaper-autostart"
[[ -f "$WAS" ]] && grep -q 'DEFAULT="/usr/share/backgrounds/nyxus/nyxus-eclipse-horizon.png"' "$WAS" \
  && ok "Sprint I: nyxus-wallpaper-autostart DEFAULT is Eclipse Horizon" \
  || fail "Sprint I: nyxus-wallpaper-autostart DEFAULT not set to Eclipse Horizon"

# (l) Plymouth uses the new Eclipse Horizon brand image + on-brand copy
PLY_SCRIPT="${AIROOT}/usr/share/plymouth/themes/nyxus-void/nyxus-void.script"
[[ -f "$PLY_SCRIPT" ]] && ! grep -qiE 'darkside|DARKSIDE' "$PLY_SCRIPT" \
  && ok "Sprint I: Plymouth script purged of off-brand 'DARKSIDE' copy" \
  || fail "Sprint I: Plymouth script still contains DARKSIDE references"
[[ -f "$PLY_SCRIPT" ]] && grep -q 'E C L I P S E' "$PLY_SCRIPT" \
  && ok "Sprint I: Plymouth script displays on-brand 'ECLIPSE · OS' subtitle" \
  || fail "Sprint I: Plymouth script missing ECLIPSE subtitle"
[[ -f "$PLY_SCRIPT" ]] && grep -q 'pupil.x = screen.w \* 0.50' "$PLY_SCRIPT" \
  && ok "Sprint I: Plymouth disc anchor updated for Eclipse Horizon bg" \
  || warn "Sprint I: Plymouth disc anchor may be misaligned with new bg"

# (m) Welcome wizard rebrand sweep — no banned colors / no Mirror branding
WP="${AIROOT}/opt/nyxus/nyxus_welcome.py"
WP_SRC="${REPO_ROOT:-$PWD/..}/artifacts/api-server/nyxus-scripts/nyxus_welcome.py"
[[ -f "$WP_SRC" ]] || WP_SRC="../artifacts/api-server/nyxus-scripts/nyxus_welcome.py"
for target in "$WP" "$WP_SRC"; do
  [[ -f "$target" ]] || continue
  banned=$(grep -cE '#e8edf5|#d96b6b|232,237,245|232, 237, 245|Mirror White|DARK MIRROR|DARK · MIRROR' "$target" || true)
  if [[ "$banned" == "0" ]]; then
    ok "Sprint I: welcome wizard ($(basename $(dirname $target))) rev r15-eclipse compliant"
  else
    fail "Sprint I: welcome wizard ($(basename $(dirname $target))) still has $banned banned token(s)"
  fi
done
[[ -f "$WP" ]] && grep -q 'r15-eclipse' "$WP" \
  && ok "Sprint I: welcome wizard rev stamp updated to r15-eclipse" \
  || fail "Sprint I: welcome wizard rev stamp not updated"

# (n) eww source-vs-airootfs drift resolved (slim Eclipse desktop layout)
EWW_SRC="${REPO_ROOT:-$PWD/..}/artifacts/api-server/nyxus-scripts/eww/eww.yuck"
[[ -f "$EWW_SRC" ]] || EWW_SRC="../artifacts/api-server/nyxus-scripts/eww/eww.yuck"
EWW_AIR="${AIROOT}/etc/skel/.config/eww/eww.yuck"
[[ -f "$EWW_SRC" ]] && grep -q ':y "8" :width "96%" :height "40px"' "$EWW_SRC" \
  && ok "Sprint I: eww source has slim bar-bottom (40px y:8 96%) — drift resolved" \
  || fail "Sprint I: eww source still has pre-Sprint-I bar-bottom values"
[[ -f "$EWW_SRC" ]] && grep -q ':height "26px" :anchor "top center"' "$EWW_SRC" \
  && ok "Sprint I: eww source has slim bar-top (26px) — drift resolved" \
  || fail "Sprint I: eww source still has pre-Sprint-I bar-top values"
if [[ -f "$EWW_SRC" && -f "$EWW_AIR" ]] && diff -q "$EWW_SRC" "$EWW_AIR" >/dev/null; then
  ok "Sprint I: eww source ↔ airootfs are byte-identical (no drift)"
else
  fail "Sprint I: eww source and airootfs disagree (build-iso would silently revert)"
fi

# (o) Default open-list = "bar-top bar-right" (Eclipse desktop layout)
EWW_CONF_SRC="${REPO_ROOT:-$PWD/..}/artifacts/api-server/nyxus-scripts/eww/nyxus.conf"
[[ -f "$EWW_CONF_SRC" ]] || EWW_CONF_SRC="../artifacts/api-server/nyxus-scripts/eww/nyxus.conf"
[[ -f "$EWW_CONF_SRC" ]] && grep -q 'NYXUS_EWW_BARS="bar-top bar-right"' "$EWW_CONF_SRC" \
  && ok "Sprint I: default bar layout is 'bar-top bar-right' (Eclipse desktop)" \
  || fail "Sprint I: default bar layout not set to slim Eclipse desktop"

# (p) Desktop UI target reference image pinned in docs/brand
DT="${REPO_ROOT:-$PWD/..}/docs/brand/nyxus-desktop-target.png"
[[ -f "$DT" ]] || DT="../docs/brand/nyxus-desktop-target.png"
[[ -f "$DT" ]] \
  && ok "Sprint I: desktop UI target image pinned in docs/brand/" \
  || fail "Sprint I: desktop UI target image missing from docs/brand/"

# (q) No "DARK MIRROR" runtime strings in EWW user-visible surfaces
#     (caught by Sprint I architect review — ticker initial payload + screensaver label
#     would otherwise greet the user with off-brand wordmark on every boot).
EWW_TREE_SRC="${REPO_ROOT:-$PWD/..}/artifacts/api-server/nyxus-scripts/eww"
[[ -d "$EWW_TREE_SRC" ]] || EWW_TREE_SRC="../artifacts/api-server/nyxus-scripts/eww"
EWW_TREE_AIR="${AIROOT}/etc/skel/.config/eww"
for tree in "$EWW_TREE_SRC" "$EWW_TREE_AIR"; do
  [[ -d "$tree" ]] || continue
  hits=$(grep -rcE 'DARK MIRROR|DARK · MIRROR' "$tree" 2>/dev/null | grep -vE ':0$' | wc -l)
  if [[ "$hits" == "0" ]]; then
    ok "Sprint I: EWW tree at $(basename $(dirname $tree))/$(basename $tree) has no DARK MIRROR runtime strings"
  else
    fail "Sprint I: EWW tree at $(basename $(dirname $tree))/$(basename $tree) still has DARK MIRROR strings ($hits file(s))"
  fi
done

# (r) nyxus-eww-launch fallback BARS only references defined windows
#     (architect caught airootfs fallback referencing nonexistent 'dock' window —
#     missing-config users would have launcher exit non-zero on first run).
LAUNCH_SRC="${REPO_ROOT:-$PWD/..}/artifacts/api-server/nyxus-scripts/nyxus-eww-launch"
[[ -f "$LAUNCH_SRC" ]] || LAUNCH_SRC="../artifacts/api-server/nyxus-scripts/nyxus-eww-launch"
LAUNCH_AIR="${AIROOT}/usr/local/bin/nyxus-eww-launch"
for f in "$LAUNCH_SRC" "$LAUNCH_AIR"; do
  [[ -f "$f" ]] || continue
  if grep -q 'NYXUS_EWW_BARS:-bar-top bar-right}' "$f"; then
    ok "Sprint I: nyxus-eww-launch ($(basename $(dirname $f))) fallback = Eclipse desktop layout"
  else
    fail "Sprint I: nyxus-eww-launch ($(basename $(dirname $f))) fallback not 'bar-top bar-right'"
  fi
  if ! grep -qE 'NYXUS_EWW_BARS:-[^}]*\bdock\b' "$f"; then
    ok "Sprint I: nyxus-eww-launch ($(basename $(dirname $f))) fallback has no phantom 'dock' window"
  else
    fail "Sprint I: nyxus-eww-launch ($(basename $(dirname $f))) fallback references undefined 'dock' window"
  fi
done

# ── §15ac Sprint J: Copper accent + thin-ring eclipse + NYXUS-Glyph icon pack (rev r16 — 2026-05-14) ──
# Sprint J introduces the SECOND canonical accent (copper #b8865a) and the
# SECOND canonical brand mark (thin-ring eclipse) without disturbing the
# locked primaries (cream #f4ead5 + filled-disc Eclipse). It also ships
# the NYXUS-Glyph icon theme — the unified black-puck + thin-copper-ring
# + cream-glyph contract for every shipped NYXUS app — and switches the
# default GTK icon theme to it.
hd "§15ac Sprint J — Copper accent + thin-ring + NYXUS-Glyph (rev r16)"

# (a) Copper token defined in eww source AND mirrored to airootfs
for f in "$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/eww/eww.scss" \
         "${AIROOT}/etc/skel/.config/eww/eww.scss"; do
  if grep -q '^\$copper:[[:space:]]*#b8865a;' "$f" 2>/dev/null; then
    ok "Sprint J: \$copper #b8865a token present in $(basename $(dirname $f))/eww.scss"
  else
    fail "Sprint J: \$copper #b8865a token MISSING from $f"
  fi
done

# (b) accent.json registers 'copper' preset with primary=#b8865a
ACC="${AIROOT}/etc/skel/.config/nyxus/accent.json"
if grep -Eq '"copper"[[:space:]]*:[[:space:]]*\{[^}]*"primary"[[:space:]]*:[[:space:]]*"#b8865a"' "$ACC"; then
  ok "Sprint J: accent.json registers 'copper' preset (#b8865a)"
else
  fail "Sprint J: accent.json missing 'copper' preset with #b8865a primary"
fi

# (c) welcome wizard ACCENTS list includes Copper
WW="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/nyxus_welcome.py"
if grep -Eq '\("Copper",[[:space:]]*"#b8865a"\)' "$WW"; then
  ok "Sprint J: nyxus_welcome ACCENTS list includes Copper #b8865a"
else
  fail "Sprint J: nyxus_welcome ACCENTS list missing Copper preset"
fi

# (d) NYXUS-Glyph icon theme installed
GLYPH="${AIROOT}/usr/share/icons/NYXUS-Glyph"
if [[ -f "${GLYPH}/index.theme" ]] && grep -q '^Name=NYXUS-Glyph' "${GLYPH}/index.theme"; then
  ok "Sprint J: NYXUS-Glyph icon theme index.theme present"
else
  fail "Sprint J: NYXUS-Glyph icon theme index.theme missing or malformed"
fi

# (e) Every required app icon is shipped as a puck-and-ring SVG
for app in nyxus-settings nyxus-notepad nyxus-stickies nyxus-sysmon nyxus-widgets \
           nyxus-files nyxus-store nyxus-capture nyxus-notification-center nyxus-ghost-auth; do
  ICON="${GLYPH}/scalable/apps/${app}.svg"
  if [[ ! -f "${ICON}" ]]; then
    fail "Sprint J: NYXUS-Glyph missing icon ${app}.svg"; continue
  fi
  # Each icon must contain: black puck (radial gradient), copper ring (#b8865a), cream glyph stroke (#f4ead5)
  if grep -q '#b8865a' "${ICON}" && grep -q '#f4ead5' "${ICON}" && grep -q 'radialGradient' "${ICON}"; then
    ok "Sprint J: NYXUS-Glyph ${app}.svg = puck + copper ring + cream glyph"
  else
    fail "Sprint J: NYXUS-Glyph ${app}.svg missing required elements (puck/copper/cream)"
  fi
done

# (f) Thin-ring eclipse mark shipped as places/ glyph
if [[ -f "${GLYPH}/scalable/places/nyxus-eclipse-thinring.svg" ]]; then
  ok "Sprint J: thin-ring eclipse mark (places/nyxus-eclipse-thinring.svg) shipped"
else
  fail "Sprint J: thin-ring eclipse mark SVG missing from NYXUS-Glyph/scalable/places"
fi

# (g) GTK 3 + 4 default icon theme switched to NYXUS-Glyph
for v in 3.0 4.0; do
  GTK="${AIROOT}/etc/skel/.config/gtk-${v}/settings.ini"
  if grep -q '^gtk-icon-theme-name=NYXUS-Glyph$' "$GTK"; then
    ok "Sprint J: GTK ${v} default icon theme = NYXUS-Glyph"
  else
    fail "Sprint J: GTK ${v} default icon theme is NOT NYXUS-Glyph (settings.ini drift)"
  fi
done

# (h) Eclipse Flare wallpaper staged + manifest entry
FLARE="${AIROOT}/usr/share/backgrounds/nyxus/nyxus-eclipse-flare.png"
if [[ -f "${FLARE}" ]] && grep -q '^nyxus-eclipse-flare' "${AIROOT}/usr/share/backgrounds/nyxus/manifest.tsv"; then
  ok "Sprint J: nyxus-eclipse-flare.png wallpaper staged + manifest entry present"
else
  fail "Sprint J: nyxus-eclipse-flare wallpaper missing or unmanifested"
fi

# (i) Brand reference images committed to docs/brand
for ref in nyxus-eclipse-thinring-mark nyxus-icon-style-reference nyxus-icon-grid-reference; do
  if [[ -f "$(dirname "${PROFILE}")/../docs/brand/${ref}.png" ]]; then
    ok "Sprint J: docs/brand/${ref}.png brand reference pinned"
  else
    fail "Sprint J: docs/brand/${ref}.png brand reference missing"
  fi
done

# (k) Live-runtime drift: opt/nyxus/nyxus_welcome.py is the file the user
#     actually executes; it MUST contain Copper too, not just the artifact source.
SHIP_WW="${AIROOT}/opt/nyxus/nyxus_welcome.py"
if grep -Eq '\("Copper",[[:space:]]*"#b8865a"\)' "${SHIP_WW}"; then
  ok "Sprint J: SHIPPED welcome wizard (/opt/nyxus/nyxus_welcome.py) has Copper preset"
else
  fail "Sprint J: SHIPPED welcome wizard MISSING Copper — artifact source drift not synced to /opt/nyxus"
fi

# (l) Three additional NYXUS-Glyph icons that .desktop entries reference
for app in nyxus nyxus-terminal nyxus-browser; do
  ICON="${GLYPH}/scalable/apps/${app}.svg"
  if [[ -f "${ICON}" ]] && grep -q '#b8865a' "${ICON}" && grep -q 'radialGradient' "${ICON}"; then
    ok "Sprint J: NYXUS-Glyph ${app}.svg shipped (puck + copper ring)"
  else
    fail "Sprint J: NYXUS-Glyph ${app}.svg missing or non-conforming"
  fi
done

# (m) Accent pipeline integrity: nyxus-apply-accent must write the SCSS
#     fragment that eww.scss actually @imports (_nyxus_accent.scss), and
#     must accept the 2-hex form that nyxus_settings.py invokes it with.
APPLY="${AIROOT}/usr/local/bin/nyxus-apply-accent"
if grep -q 'EWW_OUT="\${HOME}/\.config/eww/_nyxus_accent\.scss"' "${APPLY}"; then
  ok "Sprint J: nyxus-apply-accent writes _nyxus_accent.scss (matches eww @import target)"
else
  fail "Sprint J: nyxus-apply-accent output filename does NOT match eww @import target — accent picker silently broken"
fi
if grep -q 'set -- "_custom"' "${APPLY}" && grep -q '\$# -eq 2' "${APPLY}"; then
  ok "Sprint J: nyxus-apply-accent accepts 2-hex form (matches Settings → Appearance call signature)"
else
  fail "Sprint J: nyxus-apply-accent rejects 2-hex form — Settings accent picker non-functional"
fi

# (j) Copper hex MUST NOT have been added to the banned list (sanity guard).
# Look only at the BANNED_HEX line itself, not the whole script — every
# copper guard above naturally contains "#b8865a" and would false-positive.
if grep -E '^BANNED_HEX=' "${0}" | grep -q 'b8865a'; then
  fail "Sprint J: copper #b8865a was added to BANNED_HEX — that's a contradiction with the rev r16 contract"
else
  ok "Sprint J: copper #b8865a is NOT in the banned palette list (correct)"
fi

# ── §15ad Sprint K-A: copper goes live (rev r16 — 2026-05-14) ────────
# Sprint J shipped the copper TOKEN. Sprint K-A actually USES it on
# the 5 highest-visibility surfaces so the second accent is not just
# a value in a config file but something the user can see when they
# focus a window, lock the screen, get a critical alert, drag a
# slider, or open any libadwaita app that picks up accent_blue.
hd "§15ad Sprint K-A — copper goes live (rev r16)"

# (a) Hyprland active window border now leads with copper #b8865a
HY="${AIROOT}/etc/skel/.config/hypr/hyprland.conf"
if grep -Eq '^\s*col\.active_border\s*=\s*rgba\(b8865aff\)' "$HY"; then
  ok "Sprint K-A: Hyprland active-border leads with copper #b8865a"
else
  fail "Sprint K-A: Hyprland active-border does NOT lead with copper"
fi

# (b) Hyprlock indicator outer ring uses copper rgba(184, 134, 90, ...)
HL="${AIROOT}/etc/skel/.config/hypr/hyprlock.conf"
if grep -Eq '^\s*outer_color\s*=\s*rgba\(184,\s*134,\s*90,' "$HL"; then
  ok "Sprint K-A: Hyprlock indicator outer_color = copper"
else
  fail "Sprint K-A: Hyprlock indicator outer_color is NOT copper"
fi

# (c) dunst urgency_critical frame uses copper #b8865a
DR="${AIROOT}/etc/skel/.config/dunst/dunstrc"
if awk '/^\[urgency_critical\]/{f=1; next} /^\[/{f=0} f && /frame_color.*#b8865a/{found=1} END{exit !found}' "$DR"; then
  ok "Sprint K-A: dunst urgency_critical frame_color = copper"
else
  fail "Sprint K-A: dunst urgency_critical frame_color is NOT copper"
fi

# (d) GTK accent_blue mapped to copper in NYXUS-Dark gtk-4.0
G4="${AIROOT}/usr/share/themes/NYXUS-Dark/gtk-4.0/gtk.css"
if grep -Eq '@define-color\s+accent_blue\s+#b8865a' "$G4" && grep -Eq '@define-color\s+nyxus_copper\s+#b8865a' "$G4"; then
  ok "Sprint K-A: GTK NYXUS-Dark exposes accent_blue + nyxus_copper as copper"
else
  fail "Sprint K-A: GTK NYXUS-Dark does NOT expose copper via accent_blue/nyxus_copper"
fi

# (e) eww .dash-scale + .qs-scale highlights warm cream → copper
for f in "$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/eww/eww.scss" \
         "${AIROOT}/etc/skel/.config/eww/eww.scss"; do
  TAG="$(basename $(dirname $f))/eww.scss"
  if grep -B1 -A2 '^\.dash-scale highlight' "$f" 2>/dev/null | grep -q '#b8865a'; then
    ok "Sprint K-A: ${TAG} .dash-scale highlight warms into copper"
  else
    fail "Sprint K-A: ${TAG} .dash-scale highlight missing copper"
  fi
  if grep -B1 -A2 '^\.qs-scale highlight' "$f" 2>/dev/null | grep -q '#b8865a'; then
    ok "Sprint K-A: ${TAG} .qs-scale highlight warms into copper"
  else
    fail "Sprint K-A: ${TAG} .qs-scale highlight missing copper"
  fi
done

# ── §15ae Sprint K-A parity: artifact source ↔ airootfs (rev r16) ────
# Architect-flagged in K-A review: the 5 K-A landings live in BOTH
# `artifacts/api-server/nyxus-scripts/*` (source-of-truth) and the
# corresponding `airootfs/etc/skel/.config/*` paths. If they drift,
# a future build sync could silently regress copper. Mirror the
# existing eww parity guard for the 3 hypr/dunst surfaces.
hd "§15ae Sprint K-A parity — artifact ↔ airootfs (rev r16)"

ART_HY="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/hyprland.conf"
ART_HL="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/hyprlock.conf"
ART_DR="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/nyxus-dunstrc"

# (a) hyprland.conf active border copper parity
if grep -Eq '^\s*col\.active_border\s*=\s*rgba\(b8865aff\)' "$ART_HY"; then
  ok "Sprint K-A parity: artifact hyprland.conf active-border = copper"
else
  fail "Sprint K-A parity: artifact hyprland.conf active-border drifted off copper"
fi

# (b) hyprlock.conf outer copper parity
if grep -Eq '^\s*outer_color\s*=\s*rgba\(184,\s*134,\s*90,' "$ART_HL"; then
  ok "Sprint K-A parity: artifact hyprlock.conf outer_color = copper"
else
  fail "Sprint K-A parity: artifact hyprlock.conf outer_color drifted off copper"
fi

# (c) nyxus-dunstrc critical frame copper parity
if awk '/^\[urgency_critical\]/{f=1; next} /^\[/{f=0} f && /frame_color.*#b8865a/{found=1} END{exit !found}' "$ART_DR"; then
  ok "Sprint K-A parity: artifact nyxus-dunstrc critical frame = copper"
else
  fail "Sprint K-A parity: artifact nyxus-dunstrc critical frame drifted off copper"
fi

# ── §15af Sprint K-B: full NYXUS-Glyph .desktop coverage (rev r16) ────
# Sprint J shipped 13 NYXUS-Glyph SVGs covering the headline apps. K-B
# closes the long tail: 24 new puck SVGs + 30 .desktop Icon= re-points
# so every shipped NYXUS .desktop entry uses an on-brand black-puck +
# copper-ring + cream-glyph icon — no Adwaita fallthrough remains for
# anything in the NYXUS surface.
hd "§15af Sprint K-B — full NYXUS-Glyph .desktop coverage (rev r16)"

# (a) Every shipped NYXUS-flavored .desktop must use a NYXUS-Glyph icon
#     name. Allowed forms: `nyxus-*` (the 99% case), bare `nyxus` (the
#     welcome wizard's brand-mark exception), or `io.nyxus.*` (Intel
#     app's reverse-DNS ID). No raw Adwaita generic names like
#     `preferences-system`, `dialog-error`, etc.
GLYPH_APPS="${AIROOT}/usr/share/icons/NYXUS-Glyph/scalable/apps"
LEFTOVER=$(find "${AIROOT}" -name '*.desktop' -type f -exec grep -lE '^Icon=(applications-|battery$|calamares$|dialog-|drive-|edit-|folder-|network-|preferences-|security-|system-|tools-|user-)' {} \; 2>/dev/null)
if [[ -z "$LEFTOVER" ]]; then
  ok "Sprint K-B: zero shipped .desktop files use generic Adwaita icon names"
else
  fail "Sprint K-B: still using generic icons in: $(echo "$LEFTOVER" | xargs -n1 basename | tr '\n' ' ')"
fi

# (b) Every Icon=nyxus* value referenced by any .desktop must have a
#     matching SVG in the NYXUS-Glyph theme — no broken icon refs.
#     (Includes both `nyxus-*` and the bare `nyxus` brand-mark form.)
MISSING=""
while IFS= read -r icon; do
  [[ -z "$icon" ]] && continue
  [[ -f "${GLYPH_APPS}/${icon}.svg" ]] || MISSING="${MISSING}${icon} "
done < <(find "${AIROOT}" -name '*.desktop' -type f -exec grep -hE '^Icon=nyxus(-|$)' {} \; | sed 's/^Icon=//' | sort -u)
if [[ -z "$MISSING" ]]; then
  ok "Sprint K-B: every Icon=nyxus* has a matching SVG in NYXUS-Glyph"
else
  fail "Sprint K-B: missing NYXUS-Glyph SVGs for: ${MISSING}"
fi

# (c) Every new K-B SVG must follow the recipe: copper ring at r=23.5
#     and cream #f4ead5 stroke (no drift back to white/yellow/red).
KB_NEW=(nyxus-account nyxus-backup nyxus-battery nyxus-clipboard
        nyxus-control nyxus-crashd nyxus-display nyxus-doctor
        nyxus-drop nyxus-error nyxus-hotcorners nyxus-icons-gen
        nyxus-info nyxus-installer nyxus-launcher nyxus-locale
        nyxus-network nyxus-palette nyxus-power nyxus-run
        nyxus-screensaver nyxus-security nyxus-updater nyxus-usb
        nyxus-wallpaper)
RECIPE_OK=0; RECIPE_BAD=""
for n in "${KB_NEW[@]}"; do
  f="${GLYPH_APPS}/${n}.svg"
  if [[ -f "$f" ]] \
     && grep -q 'stroke="#b8865a"' "$f" \
     && grep -q 'r="23.5"' "$f" \
     && grep -q '#f4ead5' "$f"; then
    RECIPE_OK=$((RECIPE_OK+1))
  else
    RECIPE_BAD="${RECIPE_BAD}${n} "
  fi
done
if [[ -z "$RECIPE_BAD" ]]; then
  ok "Sprint K-B: all ${RECIPE_OK} new puck SVGs follow the copper-ring + cream-glyph recipe"
else
  fail "Sprint K-B: recipe drift in: ${RECIPE_BAD}"
fi

# (d) NYXUS-Glyph apps directory must now hold ≥37 SVGs (13 from J + 24 from K-B)
SVG_COUNT=$(ls "${GLYPH_APPS}/"*.svg 2>/dev/null | wc -l)
if (( SVG_COUNT >= 37 )); then
  ok "Sprint K-B: NYXUS-Glyph apps directory holds ${SVG_COUNT} SVGs (≥37 expected)"
else
  fail "Sprint K-B: NYXUS-Glyph apps directory only has ${SVG_COUNT} SVGs (need ≥37)"
fi

# (e) None of the new SVGs may use banned palette colors (red/cyan/purple/yellow-gold)
BANNED=""
for n in "${KB_NEW[@]}"; do
  f="${GLYPH_APPS}/${n}.svg"
  [[ -f "$f" ]] || continue
  if grep -qiE '#(f87171|ef4444|dc2626|22d3ee|06b6d4|7b7390|a78bfa|fbbf24|fcd34d|eab308)' "$f"; then
    BANNED="${BANNED}${n} "
  fi
done
if [[ -z "$BANNED" ]]; then
  ok "Sprint K-B: no banned palette colors (red/cyan/purple/yellow-gold) in any new SVG"
else
  fail "Sprint K-B: banned palette colors found in: ${BANNED}"
fi

# ── §15ag Sprint K-B parity: artifact desktop-entries ↔ airootfs ─────
# Architect-flagged in K-B review: K-A's parity-drift pattern repeats
# for the desktop entries. `artifacts/api-server/nyxus-scripts/
# desktop-entries/*.desktop` is the artifact-side source-of-truth and
# must match the Icon= line of its airootfs counterpart, otherwise a
# future build sync could silently revert all 30 K-B Icon= updates.
hd "§15ag Sprint K-B parity — artifact desktop-entries ↔ airootfs"

ART_DE="$(dirname "${PROFILE}")/../artifacts/api-server/nyxus-scripts/desktop-entries"
AIR_DE="${AIROOT}/usr/share/applications"

if [[ -d "$ART_DE" ]]; then
  PARITY_BAD=""
  PARITY_OK=0
  for f in "$ART_DE"/*.desktop; do
    [[ -f "$f" ]] || continue
    bn=$(basename "$f")
    src="$AIR_DE/$bn"
    [[ -f "$src" ]] || continue
    a=$(grep -m1 '^Icon=' "$f" || true)
    b=$(grep -m1 '^Icon=' "$src" || true)
    if [[ "$a" == "$b" ]]; then
      PARITY_OK=$((PARITY_OK+1))
    else
      PARITY_BAD="${PARITY_BAD}${bn} "
    fi
  done
  if [[ -z "$PARITY_BAD" ]]; then
    ok "Sprint K-B parity: all ${PARITY_OK} artifact desktop-entries match airootfs Icon= lines"
  else
    fail "Sprint K-B parity: Icon= drift in artifact desktop-entries: ${PARITY_BAD}"
  fi
else
  warn "Sprint K-B parity: artifact desktop-entries dir not found (skipping)"
fi

# ── final ─────────────────────────────────────────────────────────────
echo
if (( FAIL == 0 )); then
  printf '\033[1;32m✓ verify-profile passed.\033[0m\n'
  exit 0
else
  printf '\033[1;31m✗ verify-profile FAILED.\033[0m\n'
  exit 1
fi

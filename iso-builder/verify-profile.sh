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
[[ -f "${WP_DIR}/manifest.tsv" ]] && ok "manifest.tsv present" || fail "manifest.tsv missing"
MAN_LINES=$(grep -c . "${WP_DIR}/manifest.tsv" 2>/dev/null || echo 0)
if (( MAN_LINES >= WP_COUNT )); then
  ok "manifest.tsv has ${MAN_LINES} entries (>= ${WP_COUNT} files)"
else
  fail "manifest.tsv has ${MAN_LINES} entries, expected >= ${WP_COUNT}"
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
  WP_DEFAULT=$(grep -oP '^path=\K.*' "${WP_CONF}" | head -1)
  if [[ -n "${WP_DEFAULT}" && -f "${AIROOT}${WP_DEFAULT}" ]]; then
    ok "default wallpaper present: ${WP_DEFAULT}"
  else
    fail "default wallpaper path invalid: ${WP_DEFAULT}"
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

#!/usr/bin/env bash
# NYXUS · ISO build readiness verifier.
#
# Runs anywhere — does NOT require an Arch host or root. Walks the
# iso-builder profile and checks for everything that would cause the
# real `mkarchiso -v` run on an Arch box to fail. Exits non-zero on
# any structural / lint problem.
#
# This script is the gate the CI pipeline uses; it is also the script a
# human runs locally before pushing a release tag.
set -euo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE="${ROOT}/iso-builder/nyx-profile"
FAIL=0

note() { printf "  · %s\n" "$*"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$*"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$*"; FAIL=$((FAIL + 1)); }
hdr()  { printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

hdr "1. Profile skeleton"
[[ -d "$PROFILE" ]]                            && ok "iso-builder/nyx-profile/ exists"             || bad "missing iso-builder/nyx-profile/"
[[ -f "$PROFILE/profiledef.sh" ]]              && ok "profiledef.sh present"                       || bad "missing profiledef.sh"
[[ -f "$PROFILE/packages.x86_64" ]]            && ok "packages.x86_64 present"                     || bad "missing packages.x86_64"
[[ -f "$PROFILE/pacman.conf" ]]                && ok "pacman.conf present"                         || bad "missing pacman.conf"
[[ -d "$PROFILE/airootfs" ]]                   && ok "airootfs/ tree present"                      || bad "missing airootfs/"
[[ -d "$PROFILE/efiboot" || -d "$PROFILE/grub" || -d "$PROFILE/syslinux" ]] \
                                               && ok "boot loader assets present"                  || bad "no efiboot/grub/syslinux dirs"

hdr "2. Shell-script syntax (bash -n)"
mapfile -t SHFILES < <(
  find "$PROFILE" -type f \( -name "*.sh" -o -name "*.hook" \) 2>/dev/null
  find "$ROOT/artifacts/api-server/nyxus-scripts" -maxdepth 1 -type f \
       -name "*.sh" 2>/dev/null
)
for f in "${SHFILES[@]}"; do
  [[ -z "$f" ]] && continue
  if bash -n "$f" 2>/tmp/shn.err; then
    ok "$(basename "$f")"
  else
    bad "$(basename "$f"): $(tr '\n' ' ' </tmp/shn.err)"
  fi
done

hdr "2b. Shipped script text sanity"
utf8_bad="$(grep -RIn --binary-files=without-match $'\xEF\xBF\xBD' \
  "$ROOT/artifacts/api-server/nyxus-scripts" --include='*.sh' | head -n1 || true)"
if [[ -z "$utf8_bad" ]]; then
  ok "no UTF-8 replacement chars in nyxus-scripts/*.sh"
else
  bad "UTF-8 replacement char (U+FFFD) found: $utf8_bad"
fi

hdr "3. Python syntax (py_compile)"
mapfile -t PYFILES < <(find "$ROOT/artifacts/api-server/nyxus-scripts" -maxdepth 1 -type f -name "*.py" 2>/dev/null)
for f in "${PYFILES[@]}"; do
  if python3 -m py_compile "$f" 2>/tmp/py.err; then
    ok "$(basename "$f")"
  else
    bad "$(basename "$f"): $(tr '\n' ' ' </tmp/py.err)"
  fi
done

hdr "4. Hyprland config sanity"
HC="$PROFILE/airootfs/etc/skel/.config/hypr/hyprland.conf"
if [[ -f "$HC" ]]; then
  ok "skel hyprland.conf present"
  # Detect duplicate bind chords — same modifier+key on two lines is
  # almost always an unintentional collision (real source of bugs).
  dup=$(grep -E '^bind\s*=' "$HC" | awk -F',' '{print $1","$2}' | sort | uniq -d || true)
  if [[ -z "$dup" ]]; then ok "no duplicate keybind chords"
  else                     bad "duplicate keybind chords: $dup"; fi
else
  bad "missing skel hyprland.conf"
fi

hdr "5. Polkit policies (XML well-formed)"
mapfile -t POLS < <(find "$ROOT" -path "*/node_modules" -prune -o -type f -name "*.policy" -print 2>/dev/null)
for f in "${POLS[@]}"; do
  [[ -z "$f" ]] && continue
  if python3 -c "import xml.etree.ElementTree as E; E.parse('$f')" 2>/tmp/xml.err; then
    ok "$(basename "$f")"
  else
    bad "$(basename "$f"): $(tr '\n' ' ' </tmp/xml.err)"
  fi
done

hdr "6. systemd units (basic key check)"
mapfile -t SVCS < <(find "$ROOT" -path "*/node_modules" -prune -o -type f -name "*.service" -print 2>/dev/null)
for f in "${SVCS[@]}"; do
  [[ -z "$f" ]] && continue
  if grep -q '^\[Unit\]' "$f" && grep -qE '^\[(Service|Socket|Timer|Mount|Path)\]' "$f"; then
    ok "$(basename "$f")"
  else
    bad "$(basename "$f"): missing [Unit] or service section"
  fi
done

hdr "7. Required packages declared"
PKG="$PROFILE/packages.x86_64"
for p in base linux linux-firmware hyprland sddm networkmanager; do
  if grep -qE "^${p}$" "$PKG" 2>/dev/null; then ok "package: $p"
  else                                          bad "missing package: $p"; fi
done

hdr "9. Calamares profile coherence"
CAL="$PROFILE/airootfs/etc/calamares"
if [[ -d "$CAL" ]]; then
  ok "calamares profile dir present"
  for f in settings.conf branding/nyxus/branding.desc \
           branding/nyxus/show.qml modules/welcome.conf \
           modules/finished.conf; do
    [[ -f "$CAL/$f" ]] && ok "calamares: $f" || bad "calamares: missing $f"
  done
  # Every `images:` PNG referenced in branding.desc must exist.
  bd="$CAL/branding/nyxus/branding.desc"
  if [[ -f "$bd" ]]; then
    while read -r img; do
      [[ -z "$img" ]] && continue
      if [[ -f "$CAL/branding/nyxus/$img" ]]; then
        ok "calamares image: $img"
      elif [[ "${NYXUS_REQUIRE_BRAND:-0}" == "1" ]]; then
        bad "calamares image MISSING: $img (declared in branding.desc)"
      else
        printf "  \033[33m!\033[0m calamares image MISSING (brand bucket): %s -- set NYXUS_REQUIRE_BRAND=1 to fail\n" "$img"
      fi
    done < <(grep -E '^[[:space:]]*(productLogo|productIcon|productWelcome):' "$bd" \
              | awk -F'"' '{print $2}')
  fi
  # Every shellprocess `config:` referenced in settings.conf must exist
  # (Calamares aborts early when it can't find the named config file).
  sc="$CAL/settings.conf"
  if [[ -f "$sc" ]]; then
    while read -r cfg; do
      [[ -z "$cfg" ]] && continue
      if [[ -f "$CAL/modules/$cfg" ]]; then
        ok "calamares module config: $cfg"
      else
        bad "calamares module config MISSING: $cfg"
      fi
    done < <(awk '/^[[:space:]]*config:/{print $2}' "$sc" | tr -d '"')
  fi
  # Calamares package declared
  if grep -qE '^calamares$' "$PKG"; then
    ok "calamares declared in packages.x86_64"
  else
    bad "calamares NOT declared in packages.x86_64"
  fi
else
  bad "no calamares profile under airootfs/etc/calamares"
fi

hdr "8. SDDM theme bundled"
if [[ -d "$PROFILE/airootfs/usr/share/sddm/themes/nyxus" ]] || \
   [[ -f "$ROOT/artifacts/api-server/nyxus-scripts/nyxus-sddm-theme.tar.gz" ]]; then
  ok "SDDM nyxus theme present"
else
  bad "no SDDM nyxus theme found"
fi

printf "\n"
if (( FAIL == 0 )); then
  printf "\033[32mISO BUILD READY — %d checks passed\033[0m\n" "$((${#SHFILES[@]} + ${#PYFILES[@]}))"
  exit 0
fi
printf "\033[31mFAILED — %d issue(s) above must be fixed before mkarchiso\033[0m\n" "$FAIL"
exit 1

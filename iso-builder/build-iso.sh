#!/usr/bin/env bash
# ============================================
# NYXUS — nyx-2026.05.11-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# build-iso.sh — bakes the NYX ISO from this archiso profile.
# Must run as root on an Arch Linux host with archiso installed.
#
# Usage:
#   sudo ./build-iso.sh
#
# Output:
#   ./out/nyx-2026.05.11-x86_64.iso
set -euo pipefail

# Colours
B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

# ── ISO version (auto-dated) ─────────────────────────────────────────────
# Default = today's date in YYYY.MM.DD; override with NYX_ISO_DATE env var
# for deterministic re-bakes (e.g. NYX_ISO_DATE=2026.05.11 sudo ./build-iso.sh).
ISO_DATE="${NYX_ISO_DATE:-$(date +%Y.%m.%d)}"
ISO_NAME="nyx-${ISO_DATE}-x86_64.iso"

TARBALL_URL="https://nyxus-core.replit.app/api/download/nyxus/nyxus-intel.tgz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="${SCRIPT_DIR}/nyx-profile"
WORK_DIR="${NYX_WORK_DIR:-/var/tmp/nyx-work}"
OUT_DIR="${SCRIPT_DIR}/out"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── preflight ────────────────────────────────────────────────────────────
step "preflight"
if [[ $EUID -ne 0 ]]; then
  fail "must be run as root"; exit 1
fi
if ! command -v mkarchiso >/dev/null 2>&1; then
  fail "mkarchiso not found — install archiso: pacman -S archiso"; exit 1
fi
if [[ ! -f /etc/arch-release ]]; then
  fail "this script must run on Arch Linux (mkarchiso requires it)"; exit 1
fi
ok "running on Arch as root with mkarchiso available"
ok "iso version: ${ISO_DATE} → ${ISO_NAME}"

# ── stamp version into profiledef.sh + os-release ────────────────────────
# Keep the date in a single place (this script). At every bake we rewrite
# the iso_version in profiledef.sh (consumed by mkarchiso for ISO metadata)
# and BUILD_ID in airootfs/etc/os-release (visible inside the live system)
# so they always match ISO_NAME. No more "is this last week's bake?" drift.
step "stamp iso version into profile metadata"
PROFILEDEF="${PROFILE_DIR}/profiledef.sh"
OSRELEASE="${PROFILE_DIR}/airootfs/etc/os-release"
sed -i -E "s/^iso_version=\".*\"/iso_version=\"${ISO_DATE}\"/" "${PROFILEDEF}"
sed -i -E "s/^BUILD_ID=nyx-[0-9]+\.[0-9]+\.[0-9]+-x86_64/BUILD_ID=nyx-${ISO_DATE}-x86_64/" "${OSRELEASE}"
ok "stamped profiledef.sh   → iso_version=\"$(grep -oP '(?<=^iso_version=")[^"]+' "${PROFILEDEF}")\""
ok "stamped os-release      → $(grep -oP '^BUILD_ID=\S+' "${OSRELEASE}")"

# ── pull NYXUS Phantom tarball ───────────────────────────────────────────
step "fetch latest NYXUS Phantom (nyxus-intel.tgz)"
TGZ_LOCAL="${REPO_ROOT}/artifacts/api-server/nyxus-scripts/nyxus-intel.tgz"
TGZ_TMP="/tmp/nyxus-intel.tgz"

if [[ -f "${TGZ_LOCAL}" ]]; then
  cp "${TGZ_LOCAL}" "${TGZ_TMP}"
  ok "using local tarball at ${TGZ_LOCAL} (TRUSTED — same repo as this script)"
else
  warn "local tarball not found — downloading from production"
  warn "this is the supply chain trust boundary — verify the SHA below"
  curl -fL "${TARBALL_URL}" -o "${TGZ_TMP}"
  ok "downloaded from ${TARBALL_URL}"
fi

# Always print the SHA-256 of the staged tarball so the user can sign off
# before it gets baked into the ISO. If NYXUS_INTEL_SHA256 is set in the
# environment we enforce it (fail closed); otherwise we just display it.
TGZ_SHA="$(sha256sum "${TGZ_TMP}" | cut -d' ' -f1)"
printf "  ${B}sha256:${R} ${PINK}%s${R}\n" "${TGZ_SHA}"
if [[ -n "${NYXUS_INTEL_SHA256:-}" ]]; then
  if [[ "${NYXUS_INTEL_SHA256}" != "${TGZ_SHA}" ]]; then
    fail "tarball SHA-256 mismatch!"
    fail "expected: ${NYXUS_INTEL_SHA256}"
    fail "got:      ${TGZ_SHA}"
    exit 1
  fi
  ok "SHA-256 matches NYXUS_INTEL_SHA256 — verified"
fi

# ── stage NYXUS chrome (Phase 2: configs + GTK apps + wallpapers + scripts)
# Single source of truth: artifacts/api-server/nyxus-scripts/
# This is what makes the live ISO actually feel like NYXUS instead of vanilla
# Hyprland. Copies the full chrome layer into airootfs/ so mkarchiso bakes it
# into the squashfs. Idempotent — safe to re-run.
step "stage NYXUS chrome (configs, GTK apps, wallpapers, scripts)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
SKEL="${PROFILE_DIR}/airootfs/etc/skel"
OPT_NYXUS="${PROFILE_DIR}/airootfs/opt/nyxus"
WALLS_USER="${SKEL}/.config/hypr/walls"
WALLS_SYS="${PROFILE_DIR}/airootfs/usr/share/backgrounds/nyxus"
LBIN="${PROFILE_DIR}/airootfs/usr/local/bin"
APPS="${PROFILE_DIR}/airootfs/usr/share/applications"

# Wipe & recreate so we never inherit stale files from a prior bake.
rm -rf "${SKEL}/.config" "${OPT_NYXUS}" "${WALLS_SYS}"
mkdir -p \
  "${SKEL}/.config/hypr/conf.d" \
  "${SKEL}/.config/hypr/walls" \
  "${SKEL}/.config/eww/scripts" \
  "${SKEL}/.config/dunst" \
  "${SKEL}/.config/rofi" \
  "${SKEL}/.config/wlogout" \
  "${SKEL}/.config/alacritty" \
  "${OPT_NYXUS}" \
  "${WALLS_USER}" \
  "${WALLS_SYS}" \
  "${LBIN}" \
  "${APPS}"

# ── Configs → /etc/skel/.config/ ────────────────────────────────────────
# rev r6-eww (2026-05-11): waybar replaced by EWW. waybar-config.json,
# waybar-style.css, waybar-stats.sh, waybar-ticker.sh deleted from source.
install -m 0644 "${NS}/hyprland.conf"        "${SKEL}/.config/hypr/hyprland.conf"
install -m 0644 "${NS}/hyprlock.conf"        "${SKEL}/.config/hypr/hyprlock.conf"
install -m 0644 "${NS}/hypridle.conf"        "${SKEL}/.config/hypr/hypridle.conf"
install -m 0644 "${NS}/nyxus-dunstrc"        "${SKEL}/.config/dunst/dunstrc"
install -m 0644 "${NS}/rofi-config.rasi"     "${SKEL}/.config/rofi/config.rasi"
install -m 0644 "${NS}/rofi-nyxus.rasi"      "${SKEL}/.config/rofi/nyxus.rasi"
install -m 0644 "${NS}/rofi-startmenu.rasi"  "${SKEL}/.config/rofi/startmenu.rasi"
install -m 0644 "${NS}/wlogout-style.css"    "${SKEL}/.config/wlogout/style.css"
install -m 0644 "${NS}/wlogout-layout"       "${SKEL}/.config/wlogout/layout"
install -m 0644 "${NS}/alacritty.toml"       "${SKEL}/.config/alacritty/alacritty.toml"

# ── Hyprland conf.d/ overlays (blur/fog/general/opacity/rules/layerblur) ────
install -m 0644 "${NS}"/nyxus-hyprland-*.conf "${SKEL}/.config/hypr/conf.d/"

# ── EWW (replaces waybar as of rev r6-eww) ──────────────────────────────────
# Top-level eww.yuck / eww.scss / nyxus.conf + scripts/ subdir.
install -m 0644 "${NS}/eww/eww.yuck"   "${SKEL}/.config/eww/eww.yuck"
install -m 0644 "${NS}/eww/eww.scss"   "${SKEL}/.config/eww/eww.scss"
install -m 0644 "${NS}/eww/nyxus.conf" "${SKEL}/.config/eww/nyxus.conf"
if [[ -f "${NS}/eww/README.md" ]]; then
  install -m 0644 "${NS}/eww/README.md" "${SKEL}/.config/eww/README.md"
fi
if [[ -d "${NS}/eww/scripts" ]]; then
  install -m 0755 "${NS}"/eww/scripts/* "${SKEL}/.config/eww/scripts/" 2>/dev/null || true
fi

ok "configs: hypr (+conf.d) / eww / dunst / rofi / wlogout / alacritty"

# ── GTK apps + chrome library + helpers → /opt/nyxus/ ───────────────────
# Plus skel symlink ~/.nyxus → /opt/nyxus so hyprland.conf keybinds (which
# launch python3 ~/.nyxus/nyxus_*.py to stay compatible with the
# download-portal install flow that uses ~/.nyxus/) work on the live ISO.
install -m 0644 "${NS}"/nyxus_*.py "${OPT_NYXUS}/"

# ── Welcome Wizard companion files (rev r9-eww 2026-05-11) ─────────────
# Stage the three hand-written files into airootfs/root/ where
# customize_airootfs.sh expects them. The launcher script overrides the
# auto-generated /usr/local/bin/nyxus-welcome wrapper because it adds
# marker-file gating and a single-instance flock.
ROOT_STAGE="${PROFILE_DIR}/airootfs/root"
mkdir -p "${ROOT_STAGE}"
for f in nyxus-welcome nyxus-welcome-helper nyxus-welcome.policy; do
  if [ -f "${NS}/${f}" ]; then
    install -m 0644 "${NS}/${f}" "${ROOT_STAGE}/${f}"
  fi
done
ok "Welcome Wizard: staged 3 companion files into airootfs/root/"
ln -sfn /opt/nyxus "${SKEL}/.nyxus"
ok "GTK apps: $(ls "${OPT_NYXUS}"/*.py | wc -l) python files in /opt/nyxus/ (~/.nyxus → /opt/nyxus symlink in skel)"

# ── Wallpapers → both user skel (matches hyprland.conf path) and system ─
# Includes the new void-vortex (default EWW-era wallpaper, replaces drifter).
install -m 0644 "${NS}"/nyxus-bg-*.png            "${WALLS_USER}/" 2>/dev/null || true
install -m 0644 "${NS}"/nyxus-sierengowski-*.png  "${WALLS_USER}/" 2>/dev/null || true
install -m 0644 "${NS}"/nyxus-void-vortex.png     "${WALLS_USER}/" 2>/dev/null || true
install -m 0644 "${NS}"/nyxus-bg-*.png            "${WALLS_SYS}/"  2>/dev/null || true
install -m 0644 "${NS}"/nyxus-sierengowski-*.png  "${WALLS_SYS}/"  2>/dev/null || true
install -m 0644 "${NS}"/nyxus-void-vortex.png     "${WALLS_SYS}/"  2>/dev/null || true
ok "wallpapers: $(ls "${WALLS_SYS}" | wc -l) files in /usr/share/backgrounds/nyxus/ + skel"

# ── Helper scripts → /usr/local/bin/ ────────────────────────────────────
# rev r6-eww: waybar-stats / waybar-ticker removed. nyxus-eww-launch added.
install -m 0755 "${NS}/wallpaper-rotate.sh"  "${LBIN}/wallpaper-rotate"
install -m 0755 "${NS}/nyxus-eww-launch"     "${LBIN}/nyxus-eww-launch"
ok "helpers: wallpaper-rotate / nyxus-eww-launch"

# ── First-boot bootstrap shims → /usr/local/bin/ ────────────────────────
# nyxus-bootstrap is the first-run installer wrapper that Hyprland's
# exec-once fires on first login. nyxus-wait-bootstrap gates dependent
# autostarts (eww, swaybg, nyxus-home) on bootstrap completion.
# Both must exist on the live ISO at 0755 — see profiledef.sh
# file_permissions which enforces the perms post-bake.
install -m 0755 "${NS}/nyxus-bootstrap"      "${LBIN}/nyxus-bootstrap"
install -m 0755 "${NS}/nyxus-wait-bootstrap" "${LBIN}/nyxus-wait-bootstrap"
ok "bootstrap shims: nyxus-bootstrap / nyxus-wait-bootstrap"

# ── Offline cache → /opt/nyxus-cache/ ───────────────────────────────────
# nyxus-bootstrap falls back to this path when the network is unreachable
# on first boot. Mirroring the entire dist/nyxus-scripts/ payload in here
# means the live ISO can fully install NYXUS chrome with zero internet —
# the difference between "the user's coffee shop has no Wi-Fi" being a
# blocker vs a non-event. ~52 MB added to the squashfs; the user's already
# paying ~1.8 GB for the base ISO so this is rounding error.
NYXUS_DIST="${REPO_ROOT}/artifacts/api-server/dist/nyxus-scripts"
OFFLINE_CACHE="${PROFILE_DIR}/airootfs/opt/nyxus-cache"
# Always wipe first so a missing dist/ never silently ships a stale cache
# from a prior bake. The whole point of staging is fresh-each-time.
rm -rf "${OFFLINE_CACHE}"
if [[ -d "${NYXUS_DIST}" ]]; then
  mkdir -p "${OFFLINE_CACHE}"
  cp -a "${NYXUS_DIST}/." "${OFFLINE_CACHE}/"
  ok "offline cache: $(ls "${OFFLINE_CACHE}" | wc -l) files in /opt/nyxus-cache/ ($(du -sh "${OFFLINE_CACHE}" | cut -f1))"
else
  warn "dist/nyxus-scripts/ not found — ISO will be ONLINE-ONLY (offline fallback disabled)"
  warn "to enable offline fallback, run 'pnpm --filter @workspace/api-server run build' first"
fi

# ── SDDM theme → /usr/share/sddm/themes/nyxus/ + config ────────────────
# Stages the NYXUS QML login theme into the airootfs. The live ISO itself
# autologs into Hyprland (no SDDM at boot) so this is dormant on the live
# session — but when the disk installer (Job 2) provisions a real install,
# sddm.service gets enabled and this theme is what the user sees at boot.
SDDM_TMP_STAGE="$(mktemp -d)"
tar -xzf "${NS}/nyxus-sddm-theme.tar.gz" -C "${SDDM_TMP_STAGE}"
SDDM_THEME_DIR="${PROFILE_DIR}/airootfs/usr/share/sddm/themes/nyxus"
SDDM_CONF_DIR="${PROFILE_DIR}/airootfs/etc/sddm.conf.d"
mkdir -p "${SDDM_THEME_DIR}" "${SDDM_CONF_DIR}"
# Tarball is packed flat (files at root, no wrapper dir) so copy from STAGE root.
cp -a "${SDDM_TMP_STAGE}/." "${SDDM_THEME_DIR}/"
rm -f "${SDDM_THEME_DIR}/install.sh"  # not needed at runtime
cat > "${SDDM_CONF_DIR}/nyxus.conf" <<'SDDM'
[Theme]
Current=nyxus
SDDM
# DisplayServer is intentionally NOT set — SDDM defaults to X11 for the
# greeter, which is the only setting that works reliably across NVIDIA,
# Intel, and AMD hardware. The user's actual session (Hyprland) is still
# pure Wayland regardless of what the greeter uses to render itself.
# To opt into a Wayland greeter, the user can drop their own conf into
# /etc/sddm.conf.d/wayland.conf later.
rm -rf "${SDDM_TMP_STAGE}"
ok "SDDM theme staged: /usr/share/sddm/themes/nyxus/ + /etc/sddm.conf.d/nyxus.conf"

# ── App launchers + .desktop entries ────────────────────────────────────
# mod-name : Display Name : tooltip
#  Each entry maps to a real `nyxus_<mod>.py` in nyxus-scripts/. Any app
#  added here must have a matching script — phantom entries produce
#  launchers that exec a non-existent file and confuse the menu.
#  weather/quicksettings/powermenu live in EWW, not as standalone .py
#  apps, so they are intentionally NOT here.
APPS_LIST=(
  "notepad:Notepad:NYXUS markdown notepad"
  "stickies:Stickies:Sticky notes pinned to your desktop"
  "notes:Notes:Quick scratchpad notes"
  "sysmon_gtk:System Monitor:Real-time system metrics"
  "settings:Settings:System control center"
  "control:Control:Quick toggles & launchers"
  "terminal:Terminal:NYXUS-themed terminal"
  "launcher:Launcher:Application launcher"
  "screenshot:Screenshot:Region & full-screen capture"
  "store:App Store:Browse, install, and update software"
  "powermenu:Power:Lock / suspend / logout / restart / shutdown"
  "doctor:Doctor:NYXUS health audit"
)
for entry in "${APPS_LIST[@]}"; do
  IFS=':' read -r mod name comment <<< "${entry}"
  # Friendly bin name: nyxus_sysmon_gtk → nyxus-sysmon (special-case),
  # everything else → nyxus-<mod with underscores → dashes>.
  if [[ "${mod}" == "sysmon_gtk" ]]; then
    bin_name="nyxus-sysmon"
  else
    bin_name="nyxus-${mod//_/-}"
  fi
  cat > "${LBIN}/${bin_name}" <<LAUNCHER
#!/usr/bin/env bash
# NYXUS ${name} launcher — Copyright © 2026 Joseph Sierengowski
exec python3 /opt/nyxus/nyxus_${mod}.py "\$@"
LAUNCHER
  chmod 0755 "${LBIN}/${bin_name}"
  cat > "${APPS}/io.nyxus.${mod}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=NYXUS ${name}
Comment=${comment}
Exec=/usr/local/bin/${bin_name}
Icon=preferences-system
Categories=System;Utility;
Terminal=false
StartupNotify=true
DESKTOP
done
ok "launchers + desktop entries: ${#APPS_LIST[@]} apps"

# ── populate airootfs/opt/nyxus-intel ────────────────────────────────────
step "stage Phantom into airootfs/opt/nyxus-intel/"
INSTALL_DIR="${PROFILE_DIR}/airootfs/opt/nyxus-intel"
rm -rf "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

# Extract → ${INSTALL_DIR}
TMP_EXTRACT="$(mktemp -d)"
tar -xzf "${TGZ_TMP}" -C "${TMP_EXTRACT}"
install -m 0644 "${TMP_EXTRACT}/intel/nyxus-intel/"*.py "${INSTALL_DIR}/"
ok "deployed $(ls "${INSTALL_DIR}"/*.py | wc -l) python files"

# Per-app docs alongside the binaries
for doc in LICENSE.md README.md CHANGELOG.md CREDITS.md; do
  if [[ -f "${TMP_EXTRACT}/intel/${doc}" ]]; then
    install -m 0644 "${TMP_EXTRACT}/intel/${doc}" "${INSTALL_DIR}/${doc}"
  fi
done

# Tamper manifest (matches _tamper._digest_dir)
python3 - <<'PY' "${INSTALL_DIR}"
import hashlib, sys
from pathlib import Path
d = Path(sys.argv[1])
h = hashlib.sha256()
for p in sorted(d.glob("*.py")):
    h.update(p.name.encode()); h.update(b"\0")
    h.update(p.read_bytes());   h.update(b"\0")
(d / ".manifest.sha256").write_text(h.hexdigest() + "\n", encoding="utf-8")
PY
ok "sealed tamper manifest"

# Caveat font into airootfs/usr/share/fonts/TTF/
if [[ -f "${TMP_EXTRACT}/intel/fonts/Caveat.ttf" ]]; then
  install -Dm 0644 "${TMP_EXTRACT}/intel/fonts/Caveat.ttf" \
    "${PROFILE_DIR}/airootfs/usr/share/fonts/TTF/Caveat.ttf"
  ok "staged Caveat font"
fi

# Launcher → /usr/local/bin/nyxus-intel on the live system
mkdir -p "${PROFILE_DIR}/airootfs/usr/local/bin"
cat > "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-intel" <<'LAUNCHER'
#!/usr/bin/env bash
# NYXUS Phantom launcher — Copyright © 2026 Joseph Sierengowski
exec python3 -c '
import sys
sys.path.insert(0, "/opt/nyxus-intel")
from main import main
sys.exit(main())
' "$@"
LAUNCHER
chmod 0755 "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-intel"

# Desktop entry
mkdir -p "${PROFILE_DIR}/airootfs/usr/share/applications"
cat > "${PROFILE_DIR}/airootfs/usr/share/applications/io.nyxus.intel.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=NYXUS Phantom
GenericName=Open Source Intelligence Workstation
Comment=Professional grade OSINT and investigation app
Exec=/usr/local/bin/nyxus-intel
Icon=preferences-system-search
Categories=Network;Security;Office;
Terminal=false
StartupNotify=true
DESKTOP
ok "launcher + desktop entry staged"

rm -rf "${TMP_EXTRACT}"

# ── mirror OS-level docs into /etc/nyxus/ ────────────────────────────────
step "mirror OS-level docs into airootfs/etc/nyxus/"
NYXUS_DOCS="${PROFILE_DIR}/airootfs/etc/nyxus"
mkdir -p "${NYXUS_DOCS}"
for doc in LICENSE.md README.md CHANGELOG.md CREDITS.md; do
  if [[ -f "${REPO_ROOT}/${doc}" ]]; then
    install -m 0644 "${REPO_ROOT}/${doc}" "${NYXUS_DOCS}/${doc}"
  fi
done
ok "OS-level docs in /etc/nyxus/"

# ── bake the ISO ─────────────────────────────────────────────────────────
step "running mkarchiso (this takes 5-15 minutes)"
rm -rf "${WORK_DIR}"
mkdir -p "${OUT_DIR}"
mkarchiso -v -w "${WORK_DIR}" -o "${OUT_DIR}" "${PROFILE_DIR}"

# Rename to canonical filename
cd "${OUT_DIR}"
PRODUCED="$(ls -t *.iso | head -1)"
if [[ "${PRODUCED}" != "${ISO_NAME}" ]]; then
  mv "${PRODUCED}" "${ISO_NAME}"
fi
ok "ISO baked → ${OUT_DIR}/${ISO_NAME}"

# ── done ─────────────────────────────────────────────────────────────────
cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYX ISO ready.${R}

  ${B}file:${R}   ${PINK}${OUT_DIR}/${ISO_NAME}${R}
  ${B}size:${R}   $(du -h "${OUT_DIR}/${ISO_NAME}" | cut -f1)
  ${B}sha:${R}    $(sha256sum "${OUT_DIR}/${ISO_NAME}" | cut -d' ' -f1)

  ${PURPLE}burn / dd / Ventoy and boot.${R}

EOF

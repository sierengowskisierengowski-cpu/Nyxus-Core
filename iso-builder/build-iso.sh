#!/usr/bin/env bash
# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
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
#   ./out/nyx-2026.05.02-x86_64.iso
set -euo pipefail

# Colours
B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

ISO_NAME="nyx-2026.05.02-x86_64.iso"
TARBALL_URL="https://nyxus-core.replit.app/api/download/nyxus/nyxus-intel.tgz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_DIR="${SCRIPT_DIR}/nyx-profile"
WORK_DIR="/tmp/nyx-work"
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

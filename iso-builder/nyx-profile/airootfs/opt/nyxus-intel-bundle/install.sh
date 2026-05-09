#!/usr/bin/env bash
# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
# ============================================================================
# NYXUS INTEL — installer (runs INSIDE the extracted tarball)
#
# This is invoked by the bootstrap script `nyxus_intel_install.sh` after the
# tarball has been fetched and extracted. It installs:
#   • Arch system packages (pacman)
#   • Python deps (pip --break-system-packages)
#   • Sherlock + Holehe (pip)
#   • Inter font → /usr/share/fonts/TTF/
#   • App tree → /opt/nyxus-intel/
#   • Launcher → /usr/local/bin/nyxus-intel
#   • Desktop entry → /usr/share/applications/io.nyxus.intel.desktop
#
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -euo pipefail

# Colours
B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'; DIM=$'\e[2m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

if [[ $EUID -ne 0 ]]; then
  fail "must be run as root"; exit 1
fi

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo $USER)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="/opt/nyxus-intel"
BIN_DIR="/usr/local/bin"
APP_DIR="/usr/share/applications"
FONT_DIR="/usr/share/fonts/TTF"

# ── Arch system packages ─────────────────────────────────────────────────
step "Arch system packages"
if command -v pacman >/dev/null 2>&1; then
  PKGS=()
  while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    PKGS+=("$line")
  done < "${SCRIPT_DIR}/packages.txt"
  if ((${#PKGS[@]})); then
    pacman -S --needed --noconfirm "${PKGS[@]}" || warn "some packages may have failed; continuing"
    ok "installed: ${PKGS[*]}"
  fi
else
  warn "pacman not found — assuming a non-Arch host; skipping system packages"
fi

# ── Inter font ──────────────────────────────────────────────────────────
step "Inter hand-drawn font"
mkdir -p "${FONT_DIR}"
if [[ -f "${SCRIPT_DIR}/fonts/Inter.ttf" ]]; then
  install -m 0644 "${SCRIPT_DIR}/fonts/Inter.ttf" "${FONT_DIR}/Inter.ttf"
  fc-cache -f >/dev/null 2>&1 || true
  ok "font installed → ${FONT_DIR}/Inter.ttf"
else
  warn "Inter.ttf not bundled — relying on system Inter (installed by main NYXUS installer)"
fi

# ── Python deps (system-managed, so --break-system-packages) ────────────
step "Python OSINT tooling (pip)"
PIP_CMD="pip"
command -v pip3 >/dev/null 2>&1 && PIP_CMD="pip3"
$PIP_CMD install --break-system-packages --upgrade -r "${SCRIPT_DIR}/requirements.txt" \
  || warn "pip install reported errors; some intel modules may degrade"
ok "Holehe, Sherlock, Shodan, piexif, python-whois installed"

# ── Application tree ────────────────────────────────────────────────────
step "deploying application tree → ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
# Copy every .py file from nyxus-intel/ into the install dir flat
install -m 0644 "${SCRIPT_DIR}/nyxus-intel/"*.py "${INSTALL_DIR}/"
ok "deployed $(ls "${INSTALL_DIR}"/*.py | wc -l) python files"

# Optional bundled tor exit-node list (refreshed by app on first run)
[[ -f "${SCRIPT_DIR}/data/tor_exit_nodes.txt" ]] && {
  mkdir -p "${INSTALL_DIR}/data"
  install -m 0644 "${SCRIPT_DIR}/data/tor_exit_nodes.txt" "${INSTALL_DIR}/data/tor_exit_nodes.txt"
}

# ── NYXUS brand documentation (LICENSE, README, CHANGELOG, CREDITS) ─────
step "NYXUS brand documentation → ${INSTALL_DIR}"
for doc in LICENSE.md README.md CHANGELOG.md CREDITS.md; do
  if [[ -f "${SCRIPT_DIR}/${doc}" ]]; then
    install -m 0644 "${SCRIPT_DIR}/${doc}" "${INSTALL_DIR}/${doc}"
  fi
done
ok "license + readme + changelog + credits in place"

# ── Tamper-detection manifest (SHA-256 of every .py at install time) ────
# Includes _tamper.py itself so the check cannot be bypassed by editing
# the verifier. Algorithm matches _tamper._digest_dir().
step "tamper-detection manifest → ${INSTALL_DIR}/.manifest.sha256"
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
ok "manifest sealed"

# ── Launcher ────────────────────────────────────────────────────────────
step "launcher → ${BIN_DIR}/nyxus-intel"
cat > "${BIN_DIR}/nyxus-intel" <<EOF
#!/usr/bin/env bash
# NYXUS INTEL launcher
exec python3 -c '
import sys
sys.path.insert(0, "${INSTALL_DIR}")
from main import main
sys.exit(main())
' "\$@"
EOF
chown root:root "${BIN_DIR}/nyxus-intel"
chmod 0755 "${BIN_DIR}/nyxus-intel"
ok "${BIN_DIR}/nyxus-intel"

# ── Desktop entry ───────────────────────────────────────────────────────
step "desktop entry → ${APP_DIR}/io.nyxus.intel.desktop"
mkdir -p "${APP_DIR}"
cat > "${APP_DIR}/io.nyxus.intel.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=NYXUS Intel
GenericName=Open Source Intelligence Workstation
Comment=Professional grade OSINT and investigation app
Exec=${BIN_DIR}/nyxus-intel
Icon=io.nyxus.intel
Categories=Network;Security;Office;
Terminal=false
StartupNotify=true
EOF
ok "desktop entry installed"

# ── Per-user config dir ─────────────────────────────────────────────────
USER_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"
CFG_DIR="${USER_HOME}/.config/nyxus-intel"
sudo -u "$REAL_USER" mkdir -p "${CFG_DIR}/cases" "${CFG_DIR}/backups"
ok "user config dir prepared → ${CFG_DIR}"

cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS INTEL is installed.${R}

  ${B}launch:${R}    ${PINK}nyxus-intel${R}
  ${B}config:${R}    ${CFG_DIR}/config.json
  ${B}cases:${R}     ${CFG_DIR}/cases/  (encrypted)

  ${PURPLE}First launch will:${R}
    1. show the legal disclaimer (one time)
    2. prompt you to set a master password
    3. open the locked workstation

  ${B}API keys:${R}  add them in Settings → API Keys
            (every key is optional — features without a
             key show a "set API key" hint instead of
             returning fake data)

  ${PURPLE}I N V E S T I G A T E   R E S P O N S I B L Y${R}

EOF

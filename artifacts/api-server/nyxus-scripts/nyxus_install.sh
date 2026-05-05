#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║          NYXUS OS — Full System Installer                            ║
# ║  Downloads and deploys all NYXUS configs, scripts, and wallpapers    ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
API="${BASE_URL}/api/download/nyxus"

SCRIPTS_DIR="$HOME/.nyxus"
HYPR_DIR="$HOME/.config/hypr"
WAYBAR_DIR="$HOME/.config/waybar"
ROFI_DIR="$HOME/.config/rofi"
DUNST_DIR="$HOME/.config/dunst"

# ── COLORS ────────────────────────────────────────────────────────────────────
R="\033[0m"
B="\033[1m"
PURPLE="\033[38;5;135m"
PINK="\033[38;5;213m"
GOLD="\033[38;5;220m"
DIM="\033[2m"
GREEN="\033[92m"
RED="\033[91m"
CYAN="\033[96m"

ok()   { printf "  ${GREEN}${B}✓${R}  ${DIM}%s${R}\n" "$1"; }
fail() { printf "  ${RED}${B}✗${R}  ${DIM}%s — FAILED${R}\n" "$1"; }
hdr()  { printf "\n${PURPLE}${B}── %s ${DIM}%s${R}\n" "$1" "────────────────────────────────────────────"; }

dl() {
  local name="$1" dest="$2"
  if curl -fsSL -o "$dest" "${API}/${name}" 2>/dev/null; then
    ok "$name → $dest"
  else
    fail "$name"
    failed_items+=("$name")
    return 1
  fi
}

# ── HEADER ────────────────────────────────────────────────────────────────────
clear
echo ""
printf "${PURPLE}${B}  ███   ██  ██  ██  ██  ██  ██  █████ ${R}\n"
printf "${PINK}${B}  ████  ██   ████   ██  ██  ██  ██    ${R}\n"
printf "${GOLD}${B}  ██ █  ██    ██    ██  ██  ██   ████ ${R}\n"
printf "${PINK}${B}  ██  █ ██    ██     ████   ██      ██ ${R}\n"
printf "${PURPLE}${B}  ██   ████   ██      ██    ██  █████ ${R}\n"
echo ""
printf "  ${DIM}S I L E N T  ·  D A R K  ·  P U R E L Y   F U N C T I O N A L${R}\n"
printf "  ${DIM}© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED${R}\n"
echo ""

failed=0
failed_items=()


# ── PYTHON TERMINAL SCRIPTS ───────────────────────────────────────────────────
hdr "Python Terminal Scripts"
mkdir -p "$SCRIPTS_DIR"
for f in nyxus_preboot.py nyxus_motd.py nyxus_splash.py nyxus_error.py \
         nyxus_sysmon.py nyxus_sysmon_gtk.py \
         nyxus_stickies.py nyxus_notes.py nyxus_weather.py nyxus_terminal.py \
         nyxus_gen_icons.py nyxus_control.py nyxus_settings.py \
         nyxus_doctor.py nyxus_launcher.py nyxus_powermenu.py \
         nyxus_screenshot.py nyxus_chrome.py nyxus_quicksettings.py; do
  dl "$f" "$SCRIPTS_DIR/$f" && chmod +x "$SCRIPTS_DIR/$f" || failed=$((failed+1))
done

# ── GTK4 Python dependencies ──────────────────────────────────────────────────
hdr "Python GTK4 Dependencies"
if command -v pacman &>/dev/null; then
  pacman -S --noconfirm --needed python-gobject python-psutil python-cairo gtk4 vte4 chafa \
    python-cryptography python-reportlab python-markdown gtksourceview5 2>/dev/null \
    && ok "python-gobject gtk4 python-psutil python-cairo vte4 chafa cryptography reportlab markdown gtksourceview5" \
    || printf "  ${DIM}(pacman install failed — try: pip install PyGObject psutil pycairo)${R}\n"
else
  pip install PyGObject psutil pycairo 2>/dev/null \
    && ok "PyGObject psutil pycairo (pip)" \
    || printf "  ${DIM}pip install failed — install python-gobject manually${R}\n"
  printf "  ${DIM}Note: also install vte4 / gir1.2-vte-2.91 for the NYXUS Terminal${R}\n"
  printf "  ${DIM}      install chafa for inline image display (chafa -f sixel image.jpg)${R}\n"
fi

# ── ACTION CENTER backends ────────────────────────────────────────────────────
# NetworkManager, bluez, brightness, screen-snip, notifications, displays
hdr "Action Center backends (network/bluetooth/audio/screen-snip/etc)"
if command -v pacman &>/dev/null; then
  # Core (must succeed)
  sudo pacman -S --noconfirm --needed \
    networkmanager bluez bluez-utils brightnessctl \
    grim slurp wl-clipboard dunst \
    wireplumber pipewire-pulse \
    2>/dev/null && ok "core: networkmanager bluez brightnessctl grim slurp wl-clipboard dunst wireplumber pipewire-pulse" \
                || printf "  ${DIM}(some core packages failed — re-run: sudo pacman -S networkmanager bluez bluez-utils)${R}\n"
  # Optional (best-effort — Action Center degrades gracefully if any are missing)
  sudo pacman -S --noconfirm --needed wdisplays blueman geoclue power-profiles-daemon hyprshade 2>/dev/null \
    && ok "optional: wdisplays blueman geoclue power-profiles-daemon hyprshade" \
    || printf "  ${DIM}(optional: install with: sudo pacman -S wdisplays blueman geoclue power-profiles-daemon; AUR: hyprshade)${R}\n"
  # Make sure NetworkManager + bluetooth daemons are enabled & running
  sudo systemctl enable --now NetworkManager.service 2>/dev/null && ok "NetworkManager.service enabled" || true
  sudo systemctl enable --now bluetooth.service       2>/dev/null && ok "bluetooth.service enabled"     || true
  # Dunst is started on demand by Hyprland exec-once — no systemd user service needed.
  # (NYXUS standardized on dunst in Phase 2; mako removed to avoid daemon conflict.)
fi

# ── Caveat Font (REQUIRED for NYXUS hand-drawn aesthetic) ────────────────────
hdr "Caveat Font (NYXUS hand-drawn design)"
FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"
CAVEAT_URL="https://github.com/googlefonts/caveat/raw/main/fonts/ttf"
CAVEAT_FILES=("Caveat-Regular.ttf" "Caveat-Bold.ttf" "Caveat-Medium.ttf" "Caveat-SemiBold.ttf")
caveat_ok=0
for f in "${CAVEAT_FILES[@]}"; do
  if [ -f "$FONT_DIR/$f" ]; then
    caveat_ok=$((caveat_ok+1))
  else
    if curl -fsSL "$CAVEAT_URL/$f" -o "$FONT_DIR/$f" 2>/dev/null; then
      caveat_ok=$((caveat_ok+1))
    elif wget -qO "$FONT_DIR/$f" "$CAVEAT_URL/$f" 2>/dev/null; then
      caveat_ok=$((caveat_ok+1))
    fi
  fi
done
if [ $caveat_ok -ge 2 ]; then
  fc-cache -f "$FONT_DIR" 2>/dev/null
  ok "Caveat font installed ($caveat_ok files) → fc-cache updated"
else
  # Try pacman as fallback
  if command -v pacman &>/dev/null; then
    pacman -S --noconfirm --needed ttf-google-fonts-git 2>/dev/null || \
    pacman -S --noconfirm --needed ttf-croscore 2>/dev/null || true
  fi
  printf "  ${DIM}Caveat font: $caveat_ok files found — if Caveat is missing, fonts fall back to Comic Sans${R}\n"
fi

# ── App Icons — paint-splatter neon icons via Cairo ───────────────────────────
hdr "App Icons (NYXUS paint-splatter)"
# Hard-require pycairo before generating icons. If missing, install it.
if ! python3 -c "import cairo" 2>/dev/null; then
  printf "  ${DIM}pycairo missing — installing python-cairo via pacman...${R}\n"
  sudo pacman -S --noconfirm --needed python-cairo 2>/dev/null \
    || pip install --user pycairo 2>/dev/null \
    || pip install --break-system-packages pycairo 2>/dev/null \
    || true
fi
if ! python3 -c "import cairo" 2>/dev/null; then
  printf "  \033[91mFAILED:\033[0m pycairo could not be installed. App icons WILL NOT render.\n"
  printf "  Run manually:  sudo pacman -S python-cairo  (or:  pip install --user pycairo)\n"
  failed=$((failed+1))
else
  # Run icon generator with FULL output visible so failures are loud
  if python3 "$SCRIPTS_DIR/nyxus_gen_icons.py"; then
    icon_count=$(ls ~/.local/share/icons/hicolor/256x256/apps/io.nyxus.*.png 2>/dev/null | wc -l)
    if [ "$icon_count" -ge 11 ]; then
      ok "NYXUS icons: $icon_count painted → ~/.local/share/icons/hicolor/256x256/apps/"
    else
      printf "  \033[93mWARN:\033[0m only $icon_count of 11 icons created\n"
      failed=$((failed+1))
    fi
  else
    printf "  \033[91mFAILED:\033[0m icon generator crashed (see output above)\n"
    failed=$((failed+1))
  fi
fi

# ── HYPRLAND CONFIGS ──────────────────────────────────────────────────────────
hdr "Hyprland"
mkdir -p "$HYPR_DIR"
dl "hyprland.conf" "$HYPR_DIR/hyprland.conf" || failed=$((failed+1))
dl "nyxus-hyprlock.conf" "$HYPR_DIR/hyprlock.conf"  || failed=$((failed+1))
dl "hypridle.conf"  "$HYPR_DIR/hypridle.conf"  || failed=$((failed+1))

# ── WALLPAPER ─────────────────────────────────────────────────────────────────
hdr "Wallpaper (SIERENGOWSKI)"
WALLS_DIR="$HYPR_DIR/walls"
mkdir -p "$WALLS_DIR"
dl "nyxus-sierengowski-clean.png" "$WALLS_DIR/nyxus-sierengowski-clean.png" || failed=$((failed+1))
dl "nyxus-taskbar-bg.png"         "$WALLS_DIR/nyxus-taskbar-bg.png"         || failed=$((failed+1))
dl "nyxus-rightbar-bg.png"        "$WALLS_DIR/nyxus-rightbar-bg.png"        || failed=$((failed+1))

# ── APP BACKGROUNDS (neon splat panels — used by all GTK apps) ────────────────
hdr "App Backgrounds (neon splat panels)"
BG_DIR="$HOME/.nyxus/backgrounds"
mkdir -p "$BG_DIR"
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15; do
  dl "nyxus-bg-${i}.png" "$BG_DIR/nyxus-bg-${i}.png" || failed=$((failed+1))
done

# ── WAYBAR ────────────────────────────────────────────────────────────────────
hdr "Waybar"
mkdir -p "$WAYBAR_DIR"
dl "waybar-config.json"       "$WAYBAR_DIR/config"            || failed=$((failed+1))
dl "waybar-style.css"         "$WAYBAR_DIR/style.css"         || failed=$((failed+1))
# Inject real paths into CSS
WALL_PATH="$HOME/.config/hypr/walls/nyxus-sierengowski-clean.png"
TASKBAR_BG_PATH="$HOME/.config/hypr/walls/nyxus-taskbar-bg.png"
RIGHTBAR_BG_PATH="$HOME/.config/hypr/walls/nyxus-rightbar-bg.png"
sed -i "s|NYXUS_WALL_PATH|${WALL_PATH}|g"                  "$WAYBAR_DIR/style.css"
sed -i "s|NYXUS_TASKBAR_BG|file://${TASKBAR_BG_PATH}|g"    "$WAYBAR_DIR/style.css"
sed -i "s|NYXUS_RIGHTBAR_BG|file://${RIGHTBAR_BG_PATH}|g"  "$WAYBAR_DIR/style.css"
# Belt-and-suspenders: convert any leftover hardcoded /home/nyx/ to real $HOME
sed -i "s|file:///home/nyx/|file://$HOME/|g"               "$WAYBAR_DIR/style.css"
dl "waybar-ticker.sh"         "$WAYBAR_DIR/ticker.sh"         || failed=$((failed+1))
dl "waybar-stats.sh"          "$WAYBAR_DIR/stats.sh"          || failed=$((failed+1))
dl "nyxus_quicksettings.py"   "$WAYBAR_DIR/quicksettings.py"  || failed=$((failed+1))
chmod +x "$WAYBAR_DIR/ticker.sh" "$WAYBAR_DIR/stats.sh" "$WAYBAR_DIR/quicksettings.py" 2>/dev/null || true

# ── ROFI ─────────────────────────────────────────────────────────────────────
hdr "Rofi"
mkdir -p "$ROFI_DIR"
dl "rofi-config.rasi"    "$ROFI_DIR/config.rasi"     || failed=$((failed+1))
dl "rofi-nyxus.rasi"     "$ROFI_DIR/nyxus.rasi"      || failed=$((failed+1))
dl "rofi-startmenu.rasi" "$ROFI_DIR/startmenu.rasi"  || failed=$((failed+1))

# ── WLOGOUT ──────────────────────────────────────────────────────────────────
hdr "Wlogout Power Menu"
mkdir -p "$HOME/.config/wlogout"
dl "wlogout-style.css" "$HOME/.config/wlogout/style.css" || failed=$((failed+1))
dl "wlogout-layout"    "$HOME/.config/wlogout/layout"    || failed=$((failed+1))

# ── DUNST (NYXUS-themed notification daemon) ─────────────────────────────────
hdr "Dunst Notifications (NYXUS theme)"
mkdir -p "$DUNST_DIR"
dl "nyxus-dunstrc" "$DUNST_DIR/dunstrc" || failed=$((failed+1))
# Dunst has no signal-based config reload — restart it if it's running.
# (USR1/USR2 are pause/unpause, not reload — common foot-gun.)
if pgrep -x dunst &>/dev/null; then
  pkill -x dunst 2>/dev/null || true
  # dunst will be re-started by Hyprland exec-once on next session;
  # for the current session, kick it off detached so notifications keep working.
  if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]] && command -v dunst &>/dev/null; then
    setsid -f dunst &>/dev/null || (dunst &>/dev/null &)
  fi
fi

# Best-effort: disable any legacy mako.service from prior NYXUS installs
# so it doesn't race with dunst on next login.
systemctl --user disable --now mako.service 2>/dev/null || true

# ── ALACRITTY ────────────────────────────────────────────────────────────────
hdr "Alacritty"
mkdir -p "$HOME/.config/alacritty"
dl "alacritty.toml" "$HOME/.config/alacritty/alacritty.toml" || failed=$((failed+1))

# ── GTK4 TARBALL APPS — Home, Intel, Panel, Start, Sage, Studio, Shield… ────
hdr "GTK4 Tarball Apps"
TARBALL_APPS=(home weather notepad passwords intel panel start sage studio security)
for app in "${TARBALL_APPS[@]}"; do
  installer="nyxus_${app}_install.sh"
  if curl -fsSL "${API}/${installer}" | bash >/tmp/nyxus-${app}-install.log 2>&1; then
    ok "${app} (nyxus-${app})"
  else
    fail "${app} — see /tmp/nyxus-${app}-install.log"
    failed=$((failed+1))
    failed_items+=("nyxus-${app}")
  fi
done

# ── CLEANUP — remove old/duplicate binaries and desktop files ────────────────
hdr "Cleanup (legacy apps + duplicate symlinks)"

# Old nyx-* binaries from previous build
OLD_BINS=(
  nyx-command-hub nyx-fan nyx-firstboot nyx-monitor-workspace
  nyx-msi-control nyx-msi-status nyx-sec-workspace nyx-security
  nyx-security-center nyx-setup-wizard nyx-taskbar nyx-terminal
  nyx-thermal nyx-trap nyx-wallpaper-rotate nyx-wallsync
  nyx-ws-wallpaper nyx-yubikey-setup nyxus-audit nyxus-calendar
  nyxus-clock nyxus-notifications
)
for bin in "${OLD_BINS[@]}"; do
  for p in /usr/local/bin/$bin /usr/bin/$bin; do
    if [[ -e "$p" || -L "$p" ]]; then
      # /usr/local/bin and /usr/bin are root-owned — needs sudo.
      if sudo rm -f "$p" 2>/dev/null; then
        ok "removed binary: $p"
      else
        printf "  ${DIM}(skip: $p — needs sudo; re-run with sudo to clean)${R}\n"
      fi
    fi
  done
done

# Duplicate symlinks (plain short names — keep only nyxus-* prefixed names)
for sym in gods godsapp sage; do
  for p in /usr/local/bin/$sym /usr/bin/$sym; do
    if [[ -L "$p" ]]; then
      if sudo rm -f "$p" 2>/dev/null; then
        ok "removed symlink: $p"
      else
        printf "  ${DIM}(skip: $p — needs sudo; re-run with sudo to clean)${R}\n"
      fi
    fi
  done
done

# Legacy desktop files that should not exist in NYXUS
# NOTE: io.nyxus.store.desktop intentionally NOT listed — it is a real,
# active launcher created by the nyxus-start tarball's install.sh and
# was previously being silently deleted by this cleanup loop, which is
# why the App Store icon stopped appearing in Rofi / the Start menu.
OLD_DESKTOPS=(
  nyx-notepad.desktop
  nyx-security-center.desktop
  nyx-terminal.desktop
)
for desk in "${OLD_DESKTOPS[@]}"; do
  # User-writable dir — no sudo needed
  if [[ -f "$HOME/.local/share/applications/$desk" ]]; then
    rm -f "$HOME/.local/share/applications/$desk" \
      && ok "removed desktop: $HOME/.local/share/applications/$desk"
  fi
  # System dir — needs sudo; non-fatal if not granted
  if [[ -f "/usr/share/applications/$desk" ]]; then
    if sudo -n rm -f "/usr/share/applications/$desk" 2>/dev/null; then
      ok "removed desktop: /usr/share/applications/$desk"
    else
      printf "  ${DIM}(skip: /usr/share/applications/$desk — needs sudo; re-run with sudo to clean)${R}\n"
    fi
  fi
done

ok "cleanup complete"

# ── DESKTOP ENTRIES — show in Rofi / any app launcher ────────────────────────
hdr "App Launcher Entries (Rofi / .desktop)"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

NYXUS_URL="${BASE_URL}"

cat > "$DESKTOP_DIR/nyxus-sysmon.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS SysMon
GenericName=System Monitor
Comment=NYXUS OS live system stats — CPU, RAM, Network, Disk, Processes
Exec=python3 /home/nyx/.nyxus/nyxus_sysmon_gtk.py
Icon=io.nyxus.sysmon
Terminal=false
Categories=System;Monitor;
Keywords=nyxus;sysmon;cpu;ram;network;monitor;stats;
StartupWMClass=io.nyxus.sysmon
DEOF
ok "nyxus-sysmon.desktop"

cat > "$DESKTOP_DIR/nyxus-stickies.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Stickies
GenericName=Sticky Notes
Comment=NYXUS OS neon sticky notes — native GTK4
Exec=python3 /home/nyx/.nyxus/nyxus_stickies.py
Icon=io.nyxus.stickies
Terminal=false
Categories=Utility;
Keywords=nyxus;stickies;notes;sticky;widget;
StartupWMClass=io.nyxus.stickies
DEOF
ok "nyxus-stickies.desktop"

cat > "$DESKTOP_DIR/nyxus-settings.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Settings
GenericName=System Settings
Comment=NYXUS OS system control center — display, sound, network, bluetooth, power, appearance
Exec=python3 /home/nyx/.nyxus/nyxus_settings.py
Icon=io.nyxus.settings
Terminal=false
Categories=Settings;System;DesktopSettings;
Keywords=nyxus;settings;preferences;control;system;display;sound;network;bluetooth;power;wifi;
StartupWMClass=io.nyxus.settings
DEOF
ok "nyxus-settings.desktop"

cat > "$DESKTOP_DIR/nyxus-weather.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Weather
GenericName=Weather Widget
Comment=NYXUS OS animated weather widget — native GTK4
Exec=python3 /home/nyx/.nyxus/nyxus_weather.py
Icon=io.nyxus.weather
Terminal=false
Categories=Utility;Weather;
Keywords=nyxus;weather;widget;forecast;
StartupWMClass=io.nyxus.weather
DEOF
ok "nyxus-weather.desktop"

cat > "$DESKTOP_DIR/nyxus-notes.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Notes
GenericName=Notes
Comment=NYXUS OS minimal plain-text notes — Tesla-tier, auto-saved
Exec=/usr/local/bin/nyxus-notes
Icon=org.nyxus.notes
Terminal=false
Categories=Utility;TextEditor;
Keywords=nyxus;notes;notepad;text;editor;minimal;
StartupWMClass=org.nyxus.notes
DEOF
ok "nyxus-notes.desktop"

# Install /usr/local/bin/nyxus-notes launcher (calls /opt/nyxus-notes/main.py)
sudo mkdir -p /opt/nyxus-notes
sudo cp "$SCRIPTS_DIR/nyxus_notes.py" /opt/nyxus-notes/main.py
sudo chmod 755 /opt/nyxus-notes/main.py
echo '#!/bin/sh' | sudo tee /usr/local/bin/nyxus-notes >/dev/null
echo 'exec python3 /opt/nyxus-notes/main.py "$@"' | sudo tee -a /usr/local/bin/nyxus-notes >/dev/null
sudo chmod 755 /usr/local/bin/nyxus-notes
ok "/usr/local/bin/nyxus-notes (launcher)"

cat > "$DESKTOP_DIR/nyxus-terminal.desktop" << 'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Terminal
GenericName=Terminal
Comment=NYXUS OS brick-wall graffiti terminal — native GTK4 + VTE
Exec=python3 /home/nyx/.nyxus/nyxus_terminal.py
Icon=io.nyxus.terminal
Terminal=false
Categories=System;TerminalEmulator;
Keywords=nyxus;terminal;bash;graffiti;brick;
StartupWMClass=io.nyxus.terminal
DEOF
ok "nyxus-terminal.desktop"

cat > "$DESKTOP_DIR/nyxus-control.desktop" << 'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Control
GenericName=Hardware Control Center
Comment=NYXUS OS hardware control — fans, thermal, profiles, RGB, power
Exec=python3 /home/nyx/.nyxus/nyxus_control.py
Icon=io.nyxus.control
Terminal=false
Categories=System;Settings;HardwareSettings;
Keywords=nyxus;control;fans;thermal;rgb;power;hardware;profiles;
StartupWMClass=io.nyxus.control
DEOF
ok "nyxus-control.desktop"

# Refresh app launcher cache
cat > "$DESKTOP_DIR/nyxus-launcher.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Launcher
GenericName=Application Launcher
Comment=NYXUS Spotlight-style fuzzy app launcher (SUPER+Space)
Exec=python3 /home/nyx/.nyxus/nyxus_launcher.py
Icon=io.nyxus.launcher
Terminal=false
Categories=Utility;
Keywords=nyxus;launcher;run;spotlight;search;
StartupWMClass=io.nyxus.launcher
NoDisplay=false
DEOF
ok "nyxus-launcher.desktop"

cat > "$DESKTOP_DIR/nyxus-powermenu.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Power
GenericName=Power Menu
Comment=NYXUS lock / logout / suspend / reboot / shutdown menu
Exec=python3 /home/nyx/.nyxus/nyxus_powermenu.py
Icon=io.nyxus.power
Terminal=false
Categories=System;
Keywords=nyxus;power;logout;shutdown;reboot;suspend;lock;
StartupWMClass=io.nyxus.powermenu
DEOF
ok "nyxus-powermenu.desktop"

cat > "$DESKTOP_DIR/nyxus-screenshot.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Screenshot
GenericName=Screenshot
Comment=NYXUS screenshot — region / window / full + annotate + OCR
Exec=python3 /home/nyx/.nyxus/nyxus_screenshot.py
Icon=io.nyxus.screenshot
Terminal=false
Categories=Graphics;Utility;
Keywords=nyxus;screenshot;capture;snip;grab;ocr;annotate;
StartupWMClass=io.nyxus.screenshot
DEOF
ok "nyxus-screenshot.desktop"

cat > "$DESKTOP_DIR/nyxus-doctor.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Doctor
GenericName=System Health
Comment=NYXUS health audit — cache, scripts, hyprctl, theme integrity
Exec=alacritty -e python3 /home/nyx/.nyxus/nyxus_doctor.py
Icon=io.nyxus.doctor
Terminal=false
Categories=System;
Keywords=nyxus;doctor;audit;health;diagnostic;
StartupWMClass=io.nyxus.doctor
DEOF
ok "nyxus-doctor.desktop"

update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# ── SDDM (NYXUS-themed login screen — the boot/lock-out screen, NOT hyprlock)
# hyprlock = Super+L lock inside an active session.
# SDDM     = the login screen you see at boot, before Hyprland starts.
# This block installs the NYXUS QML theme + flips GDM→SDDM if GDM is active.
hdr "SDDM Login Theme (NYXUS)"
if ! command -v sddm &>/dev/null; then
  printf "  ${PURPLE}→${R} ${DIM}installing sddm package …${R}\n"
  if command -v pacman &>/dev/null; then
    # sudo -n: don't prompt — when piped from curl, prompts are swallowed
    # and sudo returns failure instantly. Cleaner to skip with guidance.
    if sudo -n pacman -S --needed --noconfirm sddm qt5-quickcontrols2 qt5-graphicaleffects qt5-declarative \
        >/tmp/nyxus-sddm-pacman.log 2>&1; then
      ok "sddm + qt5 deps installed"
    elif ! sudo -n true 2>/dev/null; then
      printf "  ${DIM}(skip: sddm install — needs sudo; run 'sudo -v' first then re-run)${R}\n"
    else
      fail "sddm package install (see /tmp/nyxus-sddm-pacman.log)"
      failed_items+=("sddm package"); failed=$((failed+1))
    fi
  else
    printf "  ${DIM}pacman not available — skipping SDDM (install sddm manually first)${R}\n"
  fi
fi

if command -v sddm &>/dev/null; then
  SDDM_TMP="$(mktemp -d)"
  if dl "nyxus-sddm-theme.tar.gz" "${SDDM_TMP}/theme.tar.gz"; then
    if tar -xzf "${SDDM_TMP}/theme.tar.gz" -C "${SDDM_TMP}" 2>/dev/null \
       && [[ -f "${SDDM_TMP}/sddm-theme/install.sh" ]]; then
      # Theme installer (writes to /usr/share/sddm/themes/) needs sudo
      if sudo -n bash "${SDDM_TMP}/sddm-theme/install.sh" >/tmp/nyxus-sddm-install.log 2>&1; then
        ok "NYXUS SDDM theme → /usr/share/sddm/themes/nyxus/"
        _sddm_theme_ok=1
      elif ! sudo -n true 2>/dev/null; then
        printf "  ${DIM}(skip: SDDM theme — needs sudo; run 'sudo -v' first then re-run)${R}\n"
        _sddm_theme_ok=0
      else
        fail "SDDM theme installer (see /tmp/nyxus-sddm-install.log)"
        failed_items+=("SDDM theme installer"); failed=$((failed+1))
        _sddm_theme_ok=0
      fi

      # Atomic DM swap: ONLY disable GDM if SDDM was successfully enabled.
      # Doing it the other way around can leave the user with NO active
      # display manager and a TTY-only boot — never acceptable.
      if [[ ${_sddm_theme_ok:-0} -eq 1 ]]; then
        if sudo -n systemctl enable sddm.service &>/dev/null; then
          ok "sddm.service enabled"
          if systemctl is-enabled gdm.service &>/dev/null; then
            printf "  ${PURPLE}→${R} ${DIM}sddm OK — now disabling gdm.service …${R}\n"
            if sudo -n systemctl disable gdm.service &>/dev/null; then
              ok "gdm.service disabled (sddm is now your login manager)"
            else
              printf "  ${ORANGE}⚠${R}  could not disable gdm — run: sudo systemctl disable gdm\n"
            fi
          fi
          printf "  ${DIM}Reboot or 'sudo systemctl start sddm' to see the NYXUS login screen${R}\n"
        elif ! sudo -n true 2>/dev/null; then
          printf "  ${DIM}(skip: sddm.service enable — needs sudo; run:${R}\n"
          printf "  ${DIM}     sudo -v && curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash${R}\n"
          printf "  ${DIM}   or one-shot:  sudo systemctl enable sddm.service${R}\n"
        else
          printf "  ${RED}✗${R}  could not enable sddm.service — leaving gdm in place to keep you logged in\n"
          printf "  ${DIM}    Manual fix:  sudo systemctl enable sddm.service && sudo systemctl disable gdm.service${R}\n"
          failed_items+=("sddm.service enable"); failed=$((failed+1))
        fi
      fi
    else
      fail "SDDM theme tarball extract failed"
      failed_items+=("SDDM theme tarball"); failed=$((failed+1))
    fi
  fi
  rm -rf "${SDDM_TMP}"
fi

# ── APPLY LIVE ───────────────────────────────────────────────────────────────
hdr "Applying Changes"

if command -v hyprctl &>/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  hyprctl reload &>/dev/null && ok "Hyprland config reloaded" || true
  hyprctl dismissnotify -1 &>/dev/null || true
else
  printf "  ${DIM}Run ${PURPLE}hyprctl reload${DIM} to apply the new config${R}\n"
fi

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  pkill -x waybar 2>/dev/null || true
  sleep 1.0
  nohup waybar \
    --config "$WAYBAR_DIR/config" \
    --style  "$WAYBAR_DIR/style.css" \
    > /tmp/nyxus-waybar.log 2>&1 &
  disown
  sleep 1.2
  if pgrep -x waybar > /dev/null; then
    ok "Waybar restarted — 4-bar NYXUS layout active"
  else
    printf "  ${RED}${B}✗${R}  ${DIM}Waybar failed to start — check /tmp/nyxus-waybar.log${R}\n"
    printf "  ${DIM}Run:  cat /tmp/nyxus-waybar.log${R}\n"
    failed=$((failed+1))
    failed_items+=("waybar-start")
  fi
fi

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  pkill swaybg 2>/dev/null || true
  swaybg -i "$WALLS_DIR/nyxus-sierengowski-clean.png" -m fill &
  disown
  ok "Wallpaper set — nyxus-sierengowski-clean"
fi

if command -v dunst &>/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  # Restart (not signal-reload — dunst lacks a real reload signal) so the
  # freshly-written ~/.config/dunst/dunstrc is picked up in the live session.
  if pgrep -x dunst &>/dev/null; then
    pkill -x dunst 2>/dev/null || true
    setsid -f dunst &>/dev/null || (dunst &>/dev/null &)
    ok "Dunst restarted with new config"
  fi
fi

# ── OS Name Fix (patch any old name → NYXUS in /etc/os-release) ──────────────
hdr "OS Name"
if grep -qE "NyX\.oS|NyX\.x\.OS|NyXxOS" /etc/os-release 2>/dev/null; then
  if sudo sed -i -E 's/NyX\.oS|NyX\.x\.OS|NyXxOS/NYXUS/g' /etc/os-release 2>/dev/null; then
    ok "/etc/os-release patched → NYXUS"
  else
    printf "  ${DIM}Could not patch /etc/os-release (needs sudo) — run manually:${R}\n"
    printf "  ${DIM}  sudo sed -i -E 's/NyX\\.oS|NyX\\.x\\.OS|NyXxOS/NYXUS/g' /etc/os-release${R}\n"
  fi
else
  if grep -q "NYXUS" /etc/os-release 2>/dev/null; then
    ok "/etc/os-release already correct (NYXUS)"
  else
    printf "  ${DIM}/etc/os-release — no legacy name found, skipping${R}\n"
  fi
fi

# ── SUMMARY ───────────────────────────────────────────────────────────────────
echo ""
printf "${DIM}──────────────────────────────────────────────────────────────────────${R}\n"
echo ""

if [[ $failed -eq 0 ]]; then
  printf "  ${GREEN}${B}NYXUS fully installed.${R}\n\n"
  printf "  ${GOLD}Wallpaper:${R} SIERENGOWSKI (permanent — set at boot)\n"
  printf "    ${DIM}Super+Alt+W  → reload wallpaper if it ever clears${R}\n\n"
  printf "  ${PURPLE}${B}Lock your screen:${R}  ${DIM}Super+L${R}\n"
  printf "  ${PURPLE}${B}Open launcher:${R}    ${DIM}Super+D${R}\n"
  printf "  ${PURPLE}${B}Screenshot:${R}       ${DIM}Super+Print  (region)${R}\n"
  printf "  ${PURPLE}${B}Logout menu:${R}      ${DIM}Super+Shift+E${R}\n\n"
  printf "  ${DIM}S I L E N T · D A R K · P U R E L Y   F U N C T I O N A L${R}\n"
else
  printf "  ${RED}${B}${failed} item(s) failed:${R}\n"
  for item in "${failed_items[@]}"; do
    printf "    ${RED}✗${R}  ${DIM}${item}${R}\n"
  done
  echo ""
  printf "  ${DIM}If waybar failed, run:  cat /tmp/nyxus-waybar.log${R}\n"
  printf "  ${DIM}Otherwise re-run:  curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash${R}\n"
  exit 1
fi

echo ""

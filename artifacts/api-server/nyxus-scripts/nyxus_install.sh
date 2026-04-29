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
MAKO_DIR="$HOME/.config/mako"

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
         nyxus_stickies.py nyxus_notepad.py nyxus_weather.py nyxus_terminal.py \
         nyxus_gen_icons.py nyxus_control.py; do
  dl "$f" "$SCRIPTS_DIR/$f" && chmod +x "$SCRIPTS_DIR/$f" || failed=$((failed+1))
done

# ── GTK4 Python dependencies ──────────────────────────────────────────────────
hdr "Python GTK4 Dependencies"
if command -v pacman &>/dev/null; then
  pacman -S --noconfirm --needed python-gobject python-psutil python-cairo gtk4 vte4 chafa 2>/dev/null \
    && ok "python-gobject gtk4 python-psutil python-cairo vte4 chafa" \
    || printf "  ${DIM}(pacman install failed — try: pip install PyGObject psutil pycairo)${R}\n"
else
  pip install PyGObject psutil pycairo 2>/dev/null \
    && ok "PyGObject psutil pycairo (pip)" \
    || printf "  ${DIM}pip install failed — install python-gobject manually${R}\n"
  printf "  ${DIM}Note: also install vte4 / gir1.2-vte-2.91 for the NYXUS Terminal${R}\n"
  printf "  ${DIM}      install chafa for inline image display (chafa -f sixel image.jpg)${R}\n"
fi

# ── App Icons — paint-splatter neon icons via Cairo ───────────────────────────
hdr "App Icons (NYXUS paint-splatter)"
if python3 "$SCRIPTS_DIR/nyxus_gen_icons.py" 2>/dev/null; then
  ok "NYXUS icons generated → ~/.local/share/icons/hicolor/256x256/apps/"
else
  printf "  ${DIM}Icon generation skipped (pycairo not available yet)${R}\n"
fi

# ── HYPRLAND CONFIGS ──────────────────────────────────────────────────────────
hdr "Hyprland"
mkdir -p "$HYPR_DIR"
dl "hyprland.conf" "$HYPR_DIR/hyprland.conf" || failed=$((failed+1))
dl "hyprlock.conf"  "$HYPR_DIR/hyprlock.conf"  || failed=$((failed+1))
dl "hypridle.conf"  "$HYPR_DIR/hypridle.conf"  || failed=$((failed+1))

# ── WALLPAPER ─────────────────────────────────────────────────────────────────
hdr "Wallpaper (SIERENGOWSKI)"
WALLS_DIR="$HYPR_DIR/walls"
mkdir -p "$WALLS_DIR"
dl "nyxus-sierengowski-clean.png" "$WALLS_DIR/nyxus-sierengowski-clean.png" || failed=$((failed+1))
dl "nyxus-taskbar-bg.png"         "$WALLS_DIR/nyxus-taskbar-bg.png"         || failed=$((failed+1))

# ── WAYBAR ────────────────────────────────────────────────────────────────────
hdr "Waybar"
mkdir -p "$WAYBAR_DIR"
dl "waybar-config.json"       "$WAYBAR_DIR/config"            || failed=$((failed+1))
dl "waybar-style.css"         "$WAYBAR_DIR/style.css"         || failed=$((failed+1))
# Inject real paths into CSS
WALL_PATH="$HOME/.config/hypr/walls/nyxus-sierengowski-clean.png"
TASKBAR_BG_PATH="$HOME/.config/hypr/walls/nyxus-taskbar-bg.png"
sed -i "s|NYXUS_WALL_PATH|${WALL_PATH}|g"                "$WAYBAR_DIR/style.css"
sed -i "s|NYXUS_TASKBAR_BG|file://${TASKBAR_BG_PATH}|g"  "$WAYBAR_DIR/style.css"
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

# ── MAKO ─────────────────────────────────────────────────────────────────────
hdr "Mako Notifications"
mkdir -p "$MAKO_DIR"
dl "mako-config" "$MAKO_DIR/config" || failed=$((failed+1))

# ── ALACRITTY ────────────────────────────────────────────────────────────────
hdr "Alacritty"
mkdir -p "$HOME/.config/alacritty"
dl "alacritty.toml" "$HOME/.config/alacritty/alacritty.toml" || failed=$((failed+1))

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

cat > "$DESKTOP_DIR/nyxus-notepad.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS Notepad
GenericName=Notepad
Comment=NYXUS OS markdown notepad with auto-save — native GTK4
Exec=python3 /home/nyx/.nyxus/nyxus_notepad.py
Icon=io.nyxus.notepad
Terminal=false
Categories=Utility;TextEditor;
Keywords=nyxus;notepad;notes;markdown;editor;
StartupWMClass=io.nyxus.notepad
DEOF
ok "nyxus-notepad.desktop"

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
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

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

if command -v makoctl &>/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  makoctl reload 2>/dev/null && ok "Mako reloaded" || true
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

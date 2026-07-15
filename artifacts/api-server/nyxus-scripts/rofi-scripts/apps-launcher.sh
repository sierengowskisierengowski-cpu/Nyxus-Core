#!/usr/bin/env bash
# NYXUS · Apps & tools launcher (optional — bind in hyprland if desired)
set -euo pipefail
THEME="${HOME}/.config/rofi/launcher.rasi"
REPO="${NYXUS_REPO:-$HOME/Nyxus-Core}"

menu() {
  cat <<'EOF'
🌌 NYXUS Desktop
  Start Menu
  Dashboard
  Quick Settings
  Mission Control
  Home App
  Settings
  Security Center
  Doctor
🖥 Apps
  Terminal
  File Manager
  Browser
  Launcher (drun)
🔧 Tools
  Wallpaper Studio
  Screenshot (region)
  Key Cheat Sheet
  Power Menu
  Lock Screen (screensaver)
EOF
}

pick=$(menu | rofi -dmenu -i -p "NYXUS Apps" -theme "$THEME" -lines 18)
[[ -n "$pick" ]] || exit 0

case "$pick" in
  *Start\ Menu*)      nyxus-start & ;;
  *Dashboard*)        eww open --toggle dashboard & ;;
  *Quick\ Settings*)  eww open --toggle quicksettings & ;;
  *Mission\ Control*) nyxus-mission-control-toggle & ;;
  *Home\ App*)        nyxus-home & ;;
  *Settings*)         nyxus-settings & ;;
  *Security\ Center*)
    if command -v nyxus-security >/dev/null; then
      nyxus-security &
    else
      notify-send "NYXUS" "nyxus-security not installed"
    fi
    ;;
  *Doctor*)           alacritty -e python3 ~/.nyxus/nyxus_doctor.py ;;
  *Terminal*)         alacritty ;;
  *File\ Manager*)    nyxus-files 2>/dev/null || thunar ~ ;;
  *Browser*)          (command -v chromium >/dev/null && chromium) || firefox ;;
  *Launcher*)         rofi -show drun -theme "$THEME" ;;
  *Wallpaper\ Studio*) /usr/local/bin/nyxus wallpaper_studio & ;;
  *Screenshot*)       python3 ~/.nyxus/nyxus_screenshot.py region ;;
  *Cheat\ Sheet*)     eww open --toggle hotkey-cheatsheet & ;;
  *Power\ Menu*)      bash ~/.config/rofi/power.sh ;;
  *Lock\ Screen*)     eww open screensaver & ;;
esac

#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
#  NYXUS · TTY RESCUE   (rev 2026-05-15)
#
#  One-liner from a TTY (Ctrl+Alt+F2, log in as `nyx`):
#    curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/rescue.sh | bash
#
#  Restores Hyprland config + apps + wallpaper + EWW bar from scratch.
#  Safe to re-run. Old config saved to ~/.config/hypr.broken.<timestamp>
# ═══════════════════════════════════════════════════════════════════════
set -u
N="https://7d45d4aa-bc2d-4fae-a4a4-a672ca904937-00-2ixlfhdaz3p4i.kirk.replit.dev/api/download/nyxus"

# ── 0. Network check.
ping -c1 -W2 1.1.1.1 >/dev/null 2>&1 || { echo "no network — run: nmtui"; exit 1; }

# ── 1. Quarantine the broken config and start clean.
[ -d ~/.config/hypr ] && mv ~/.config/hypr ~/.config/hypr.broken.$(date +%s)
mkdir -p ~/.config/hypr/conf.d ~/.config/hypr/walls ~/.nyxus \
         ~/.config/eww/scripts ~/.config/nyxus

# ── 2. Hyprland configs (fresh from server).
for f in hyprland.conf hyprlock.conf hypridle.conf; do
  curl -fsSL "$N/$f" -o ~/.config/hypr/$f && echo "  ok  $f"
done
for f in nyxus-hyprland-rules.conf nyxus-hyprland-blur.conf nyxus-hyprland-general.conf \
         nyxus-hyprland-opacity.conf nyxus-hyprland-fog.conf nyxus-hyprland-layerblur.conf \
         nyxus-hyprland-mission.conf nyxus-windowrules.conf nyxus-browser-blur.conf; do
  curl -fsSL "$N/$f" -o ~/.config/hypr/conf.d/$f 2>/dev/null && echo "  ok  conf.d/$f"
done

# ── 2b. Failsafe: guarantee a terminal auto-launches and Super+Return works,
#       even if the NYXUS exec-once chain errors out due to missing helpers.
cat >> ~/.config/hypr/hyprland.conf << 'FAILSAFE'

# === NYXUS rescue failsafe (appended by rescue.sh) ===
# Guarantees a terminal exists no matter which NYXUS helpers are missing.
exec-once = kitty
bind = SUPER, Return, exec, kitty
bind = SUPER, Q,      exec, kitty
bind = SUPER, C,      killactive
bind = SUPER SHIFT, E, exit
FAILSAFE
echo "  ok  appended failsafe (auto-kitty + Super+Return)"

# ── 3. NYXUS apps -> ~/.nyxus/  (where every keybind looks).
for f in nyxus_palette.py nyxus_chrome.py nyxus_settings.py nyxus_notepad.py \
         nyxus_notes.py nyxus_stickies.py nyxus_terminal.py nyxus_control.py \
         nyxus_launcher.py nyxus_screenshot.py nyxus_store.py nyxus_powermenu.py \
         nyxus_wallpaper_studio.py nyxus_sysmon_gtk.py \
         nyxus_account.py nyxus_backup.py nyxus_hotcorners.py \
         nyxus_usb_watch.py nyxus-crash-report.py; do
  curl -fsSL "$N/$f" -o ~/.nyxus/$f 2>/dev/null && echo "  ok  ~/.nyxus/$f"
done
chmod +x ~/.nyxus/*.py

# ── 4. Wallpaper helpers + Eclipse at canonical paths.
curl -fsSL "$N/nyxus-wallpaper-autostart" -o /tmp/wpa
curl -fsSL "$N/nyxus-set-wallpaper.sh"    -o /tmp/wpset
curl -fsSL "$N/nyxus-bg-eclipse.png"      -o /tmp/eclipse.png
chmod +x /tmp/wpa /tmp/wpset
sudo install -Dm755 /tmp/wpa   /usr/local/bin/nyxus-wallpaper-autostart
sudo install -Dm755 /tmp/wpset /usr/local/bin/nyxus-set-wallpaper
sudo install -Dm644 /tmp/eclipse.png /usr/share/backgrounds/nyxus/nyxus-eclipse-horizon.png
sudo install -Dm644 /tmp/eclipse.png /usr/share/backgrounds/nyxus/nyxus-eclipse-reference.png
install  -Dm644 /tmp/eclipse.png ~/.config/hypr/walls/nyxus-bg-eclipse.png
echo "WALLPAPER_PATH=\"/usr/share/backgrounds/nyxus/nyxus-eclipse-horizon.png\"" \
     > ~/.config/nyxus/wallpaper.conf

# ── 4b. Rofi launcher configs (Super+D start menu, Super+Tab window switcher).
mkdir -p ~/.config/rofi
for f in rofi-config.rasi rofi-nyxus.rasi rofi-startmenu.rasi; do
  curl -fsSL "$N/$f" -o ~/.config/rofi/${f#rofi-} 2>/dev/null && echo "  ok  rofi/${f#rofi-}"
done
# Also expose under the names the keybinds use.
[ -f ~/.config/rofi/startmenu.rasi ] || cp ~/.config/rofi/config.rasi ~/.config/rofi/startmenu.rasi 2>/dev/null

# ── 4c. SDDM theme (NYXUS Eclipse login screen).
curl -fsSL "$N/nyxus-sddm-theme.tar.gz" -o /tmp/nyxus-sddm.tar.gz 2>/dev/null
if [ -s /tmp/nyxus-sddm.tar.gz ]; then
  sudo mkdir -p /usr/share/sddm/themes/nyxus
  sudo tar xzf /tmp/nyxus-sddm.tar.gz -C /usr/share/sddm/themes/nyxus
  sudo mkdir -p /etc/sddm.conf.d
  echo -e "[Theme]\nCurrent=nyxus" | sudo tee /etc/sddm.conf.d/10-nyxus-theme.conf >/dev/null
  echo "  ok  sddm theme installed (nyxus)"
fi

# ── 5. EWW shell (top bar + dashboard + OSDs).
curl -fsSL "$N/eww/eww.yuck"   -o ~/.config/eww/eww.yuck
curl -fsSL "$N/eww/eww.scss"   -o ~/.config/eww/eww.scss
curl -fsSL "$N/eww/nyxus.conf" -o ~/.config/eww/nyxus.conf
for s in audio battery bluetooth brightness calendar cpu-bars mic network \
         notifications osd-show player power-profile sys-pulse ticker updates \
         weather workspaces quicksettings qs-toggle wifi-list wifi-action \
         bt-list bt-action audio-sinks audio-action calendar-month \
         notif-history notif-action; do
  curl -fsSL "$N/eww/scripts/$s.sh" -o ~/.config/eww/scripts/$s.sh 2>/dev/null \
    && chmod +x ~/.config/eww/scripts/$s.sh
done

# ── 6. Required packages (no-op if already installed).
sudo pacman -S --noconfirm --needed hyprland hyprlock hypridle eww-wayland \
     swww swaybg grim slurp wl-clipboard hyprshot alacritty kitty rofi-wayland \
     dunst wlogout playerctl nm-connection-editor sddm qt6-svg qt6-declarative \
     qt6-virtualkeyboard 2>/dev/null

# ── 6b. SDDM display manager — enable so graphical login comes up on boot.
sudo systemctl enable sddm 2>/dev/null && echo "  ok  sddm enabled"

# ── 7. Done.
echo ""
echo "=== rescue complete ==="
echo ""
echo "NEXT STEP — pick ONE based on where you are right now:"
echo ""
echo "  If you are in a TTY (text login):   hyprland"
echo "  If you are already in Hyprland:     hyprctl reload"
echo ""
echo "DO NOT run 'systemctl restart sddm' — it kills your live session."
echo "Kitty will auto-open and Super+Return will always spawn a terminal."

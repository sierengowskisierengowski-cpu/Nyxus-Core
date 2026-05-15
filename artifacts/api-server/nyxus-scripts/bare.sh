#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
#  NYXUS bare.sh — One-shot "give me a working Hyprland + terminal".
#  Run from TTY (no sudo wrapper, NOT from inside Hyprland):
#    curl -fsSL https://7d45d4aa-bc2d-4fae-a4a4-a672ca904937-00-2ixlfhdaz3p4i.kirk.replit.dev/api/download/nyxus/bare.sh | bash
#  Then: sudo reboot
#  Result: SDDM → Hyprland → kitty terminal auto-opens + cream wallpaper.
#  No NYXUS configs, no eww, no python apps. Just a working base to
#  iterate on from inside a real terminal.
# ─────────────────────────────────────────────────────────────────────
set -e

API="https://7d45d4aa-bc2d-4fae-a4a4-a672ca904937-00-2ixlfhdaz3p4i.kirk.replit.dev/api/download/nyxus"

echo "── 1/6  Wiping any broken Hyprland configs..."
rm -rf ~/.config/hypr ~/.config/eww ~/.nyxus ~/.config/nyxus 2>/dev/null || true

echo "── 2/6  Installing required packages (hyprland, kitty, sddm, swaybg)..."
sudo pacman -S --noconfirm --needed hyprland kitty sddm swaybg \
     qt6-svg qt6-declarative qt6-virtualkeyboard 2>&1 | tail -5

echo "── 3/6  Downloading cream NYXUS wallpaper..."
mkdir -p ~/Pictures ~/.config/hypr
curl -fsSL "$API/nyxus-bg-03.png" -o ~/Pictures/wall.png \
  && echo "  ok  ~/Pictures/wall.png"

echo "── 4/6  Writing minimal hyprland.conf (auto-launch kitty + binds)..."
cat > ~/.config/hypr/hyprland.conf << 'HYPRCONF'
# NYXUS bare config — auto-launch terminal + wallpaper, working keybinds.
monitor=,preferred,auto,1

input {
    kb_layout = us
    follow_mouse = 1
}

general {
    border_size = 2
    gaps_in     = 6
    gaps_out    = 12
    layout      = dwindle
}

decoration {
    rounding = 10
}

# Auto-start: terminal + wallpaper appear the moment you log in.
exec-once = kitty
exec-once = swaybg -i /home/nyx/Pictures/wall.png -m fill

# Keybinds (Super = Windows key)
bind = SUPER, Return, exec, kitty
bind = SUPER, Q,      exec, kitty
bind = SUPER, C,      killactive
bind = SUPER, V,      togglefloating
bind = SUPER, F,      fullscreen
bind = SUPER SHIFT, M, exit

# Window movement / resize with mouse
bindm = SUPER, mouse:272, movewindow
bindm = SUPER, mouse:273, resizewindow

# Workspaces 1-9
bind = SUPER, 1, workspace, 1
bind = SUPER, 2, workspace, 2
bind = SUPER, 3, workspace, 3
bind = SUPER, 4, workspace, 4
bind = SUPER, 5, workspace, 5
bind = SUPER SHIFT, 1, movetoworkspace, 1
bind = SUPER SHIFT, 2, movetoworkspace, 2
bind = SUPER SHIFT, 3, movetoworkspace, 3
HYPRCONF
echo "  ok  ~/.config/hypr/hyprland.conf"

echo "── 5/6  Enabling SDDM (graphical login at boot)..."
sudo systemctl enable sddm 2>&1 | tail -2

echo "── 6/6  Done."
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  NEXT STEP:  sudo reboot"
echo ""
echo "  After reboot:"
echo "    1. SDDM blue screen → top-left Session: Hyprland"
echo "    2. Log in as nyx"
echo "    3. Cream wallpaper appears + kitty terminal opens automatically"
echo "    4. From kitty you have full shell access — iterate freely."
echo "════════════════════════════════════════════════════════════════════"

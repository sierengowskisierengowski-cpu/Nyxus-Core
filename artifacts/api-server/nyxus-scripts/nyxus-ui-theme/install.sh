#!/usr/bin/env bash
# ============================================================
#  NYXUS — UI Configs Master Installer
#  Installs: Mako · Alacritty · GTK3/4 Theme
#
#  Silent. Dark. Purely Functional.
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sep() { echo "  ──────────────────────────────────────────"; }

echo ""
echo "  ██╗   ██╗██╗   ██╗██╗  ██╗   ██╗  ██╗ ██████╗ ███████╗"
echo "  ███╗  ██║╚██╗ ██╔╝╚██╗██╔╝   ╚██╗██╔╝██╔═══██╗██╔════╝"
echo "  ████╗ ██║ ╚████╔╝  ╚███╔╝     ╚███╔╝ ██║   ██║███████╗"
echo "  ██╔██╗██║  ╚██╔╝   ██╔██╗     ██╔██╗ ██║   ██║╚════██║"
echo "  ██║╚████║   ██║   ██╔╝ ██╗   ██╔╝ ██╗╚██████╔╝███████║"
echo "  ╚═╝ ╚═══╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""
echo "  NYXUS UI Configuration Installer"
echo "  Silent. Dark. Purely Functional."
sep
echo ""

# ── 1. Notifications (NYXUS standardized on dunst in Phase 2) ─
# Mako removed; dunst is now installed by the main nyxus_install.sh.
echo "  [1/3] Notifications: handled by main nyxus_install.sh (dunst)"
echo ""

# ── 2. Alacritty terminal ─────────────────────────────────────
echo "  [2/3] Installing Alacritty terminal config..."
ALACRITTY_DIR="$HOME/.config/alacritty"
mkdir -p "$ALACRITTY_DIR"
cp "$SCRIPT_DIR/alacritty/alacritty.toml" "$ALACRITTY_DIR/alacritty.toml"
echo "  [OK]  $ALACRITTY_DIR/alacritty.toml"
echo ""

# ── 3. GTK3/4 Theme ──────────────────────────────────────────
echo "  [3/3] Installing NYXUS GTK theme..."
THEME_DEST="$HOME/.themes/NYXUS"
mkdir -p "$THEME_DEST"
cp -r "$SCRIPT_DIR/NYXUS/." "$THEME_DEST/"
echo "  [OK]  $THEME_DEST/index.theme"
echo "  [OK]  $THEME_DEST/gtk-3.0/gtk.css"
echo "  [OK]  $THEME_DEST/gtk-4.0/gtk.css"

# Activate via gsettings if available (optional — not required on bare Hyprland)
if command -v gsettings &>/dev/null; then
    gsettings set org.gnome.desktop.interface gtk-theme "NYXUS" 2>/dev/null \
        && echo "  [OK]  GTK theme activated via gsettings" || true
fi

# Hyprland: set via hyprland.conf env / environment block
# Add these to hyprland.conf:
#   env = GTK_THEME,NYXUS
#   env = QT_QPA_PLATFORMTHEME,gtk3

sep
echo ""
echo "  ✓  All configs installed."
echo ""
echo "  Hyprland: add to hyprland.conf to activate GTK theme:"
echo "    env = GTK_THEME,NYXUS"
echo "    env = QT_QPA_PLATFORMTHEME,gtk3"
echo ""
echo "  Font note: ensure JetBrains Mono Nerd Font is installed:"
echo "    sudo pacman -S ttf-jetbrains-mono-nerd   # Arch"
echo "    # or download from nerdfonts.com"
echo ""
echo "  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED"
echo ""

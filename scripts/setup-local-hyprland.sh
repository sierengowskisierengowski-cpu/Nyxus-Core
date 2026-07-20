#!/usr/bin/env bash
# NYXUS — Local Hyprland setup for existing Arch installs
# Deploys configs/themes from this repo and installs runtime packages.
# Usage: bash scripts/setup-local-hyprland.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_SRC="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
DIST_SRC="${REPO_ROOT}/artifacts/api-server/dist/nyxus-scripts"
OFFLINE_DIR="${NYXUS_OFFLINE_DIR:-$DIST_SRC}"

if [[ ! -d "$OFFLINE_DIR" ]]; then
  echo "Missing offline cache at $OFFLINE_DIR"
  echo "Run: cd $REPO_ROOT/artifacts/api-server && node ./build.mjs"
  exit 1
fi

echo "==> NYXUS local setup"
echo "    Repo: $REPO_ROOT"
echo "    Offline cache: $OFFLINE_DIR ($(find "$OFFLINE_DIR" -maxdepth 1 -type f | wc -l) files)"

# ── 1. System packages (requires sudo) ───────────────────────────────────────
CORE_PKGS=(
  hyprland hyprlock hypridle hyprcursor
  rofi rofi-emoji dunst alacritty
  grim slurp wl-clipboard cliphist brightnessctl
  pipewire pipewire-pulse wireplumber
  networkmanager bluez bluez-utils polkit polkit-gnome
  gtk4 gtk-layer-shell adw-gtk3
  python-gobject python-cairo python-psutil python-cryptography
  python-reportlab python-markdown gtksourceview5 vte4 chafa
  socat jq acpi swaybg swww
  ttf-jetbrains-mono-nerd inter-font
  xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
  qt5-wayland qt6-wayland xorg-xwayland
  playerctl pamixer pavucontrol
  greetd
)

BUILD_PKGS=(base-devel rust gtk3 pango cairo gdk-pixbuf2 glib2 dbus librsvg libdbusmenu-gtk3)

echo "==> Installing core packages (sudo required)..."
if sudo -v; then
  sudo pacman -Syu --needed --noconfirm "${CORE_PKGS[@]}" || {
    echo "Some packages failed — retrying individually..."
    for pkg in "${CORE_PKGS[@]}"; do
      sudo pacman -S --needed --noconfirm "$pkg" || echo "  skip: $pkg"
    done
  }

  if ! command -v eww &>/dev/null; then
    echo "==> Installing eww (required for NYXUS bars/widgets)..."
    if command -v yay &>/dev/null && yay -Si eww 2>/dev/null | grep -q '^Repository'; then
      yay -S --needed --noconfirm eww || yay -S --needed --noconfirm eww-wayland || true
    fi
  fi

  if ! command -v eww &>/dev/null; then
    echo "==> Building eww v0.6.0 from source (3–5 min)..."
    sudo pacman -S --needed --noconfirm "${BUILD_PKGS[@]}"
    rustup default stable 2>/dev/null || sudo rustup default stable 2>/dev/null || true
    cargo install --git https://github.com/elkowar/eww --tag v0.6.0 --root "$HOME/.local" eww \
      || { echo "eww build failed — install manually: yay -S eww-wayland"; exit 1; }
    export PATH="$HOME/.local/bin:$PATH"
  fi

  sudo systemctl enable --now NetworkManager.service 2>/dev/null || true
  sudo systemctl enable --now bluetooth.service 2>/dev/null || true
else
  echo "WARNING: sudo unavailable — skipping package install. Install manually:"
  echo "  sudo pacman -S ${CORE_PKGS[*]}"
fi

# ── 2. Deploy NYXUS chrome from local cache ──────────────────────────────────
echo "==> Deploying NYXUS configs, EWW, themes..."
export NYXUS_OFFLINE_DIR="$OFFLINE_DIR"
export PATH="$HOME/.local/bin:$PATH"
export TERM="${TERM:-xterm-256color}"
# nyxus_install.sh calls `clear` which aborts under set -e in non-TTY shells
sed 's/^clear$/clear 2>\/dev\/null || true/' "$OFFLINE_DIR/nyxus_install.sh" | bash

# ── 3. GTK theme (NYXUS custom theme) ───────────────────────────────────────
if [[ -x "$SCRIPTS_SRC/nyxus-ui-theme/install.sh" ]]; then
  echo "==> Installing NYXUS GTK theme..."
  bash "$SCRIPTS_SRC/nyxus-ui-theme/install.sh"
fi

# ── 4. Hyprland session entry ────────────────────────────────────────────────
SESSION_DIR="$HOME/.local/share/wayland-sessions"
mkdir -p "$SESSION_DIR"
cat > "$SESSION_DIR/nyxus-hyprland.desktop" <<'EOF'
[Desktop Entry]
Name=NYXUS (Hyprland)
Comment=NYXUS Silent Dark Desktop
Exec=Hyprland
Type=Application
DesktopNames=Hyprland
EOF

echo ""
echo "============================================"
echo " NYXUS setup complete"
echo "============================================"
echo ""
echo "Log out of COSMIC and select 'NYXUS (Hyprland)' at the login screen."
echo "Or from a TTY: Hyprland"
echo ""
echo "Verify after login:"
echo "  hyprctl version"
echo "  eww --version"
echo "  ls ~/.config/hypr/hyprland.conf ~/.config/eww/eww.yuck"
echo ""
echo "Build NYX ISO (optional):"
echo "  cd $REPO_ROOT/iso-builder && sudo ./build-iso.sh"
echo ""

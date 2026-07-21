#!/usr/bin/env bash
set -e

REPO="sierengowskisierengowski-cpu/Desktop-Assistant-AI"
INSTALL_DIR="$HOME/.local/bin"
APP_NAME="axiom"

echo ""
echo "  Installing AXIOM..."
echo ""

# Fetch latest release tag
LATEST=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | grep '"tag_name"' | head -1 | cut -d'"' -f4)

if [ -z "$LATEST" ]; then
  echo "  ERROR: Could not fetch latest release. Check your internet connection."
  exit 1
fi

echo "  Latest version: $LATEST"

DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST/AXIOM-linux-x86_64.AppImage"
DEST="$INSTALL_DIR/$APP_NAME"

mkdir -p "$INSTALL_DIR"

echo "  Downloading from GitHub..."
curl -fsSL --progress-bar "$DOWNLOAD_URL" -o "$DEST"
chmod +x "$DEST"

# Add ~/.local/bin to PATH if not already there
if ! echo "$PATH" | grep -q "$INSTALL_DIR"; then
  SHELL_RC="$HOME/.bashrc"
  [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
  echo "" >> "$SHELL_RC"
  echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
  export PATH="$INSTALL_DIR:$PATH"
  echo "  Added $INSTALL_DIR to PATH in $SHELL_RC"
fi

# Create a .desktop entry for app launchers
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/axiom.desktop" <<EOF
[Desktop Entry]
Name=AXIOM
Comment=AI Desktop Assistant
Exec=$DEST
Icon=$DEST
Type=Application
Categories=Utility;
StartupNotify=true
EOF

echo ""
echo "  AXIOM $LATEST installed successfully!"
echo ""
echo "  Run it now:  axiom"
echo "  Or find it in your app launcher."
echo ""

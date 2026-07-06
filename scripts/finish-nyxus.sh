#!/usr/bin/env bash
# ============================================================================
# NYXUS — finish-line installer for THIS machine (no USB, no ISO needed)
# Completes everything that needs root: system daemons, themes, cursors,
# remaining apps, polkit helpers, session entry.
#
# Run as your normal user (NOT with sudo in front — it sudos internally):
#   bash /home/cosmic/GowskiNet-Vault/OS/Nyxus-Core/scripts/finish-nyxus.sh
# ============================================================================
set -uo pipefail

REPO="/home/cosmic/GowskiNet-Vault/OS/Nyxus-Core"
CACHE="$REPO/artifacts/api-server/dist/nyxus-scripts"
AIR="$REPO/iso-builder/nyx-profile/airootfs"

G=$'\e[92m'; R=$'\e[91m'; Y=$'\e[93m'; N=$'\e[0m'; B=$'\e[1m'
ok()   { echo "  ${G}✓${N} $*"; }
warn() { echo "  ${Y}!${N} $*"; }
fail() { echo "  ${R}✗${N} $*"; }
hdr()  { echo; echo "${B}── $* ──────────────────────────${N}"; }

FAILED=0

[[ -d "$CACHE" ]] || { fail "offline cache missing: $CACHE"; exit 1; }
[[ -d "$AIR"   ]] || { fail "airootfs missing: $AIR"; exit 1; }

hdr "sudo check"
sudo -v || { fail "sudo required"; exit 1; }
ok "sudo OK"

# ── 1. Remaining official-repo packages ─────────────────────────────────────
hdr "1/8 · System packages"
sudo pacman -S --needed --noconfirm \
  hyprpaper wofi wdisplays kitty swaync scdoc cmake cpio meson ninja \
  gnome-keyring python-keyring blueman geoclue power-profiles-daemon \
  kdeconnect hyprshot python-dnspython python-bcrypt easyeffects \
  && ok "repo packages installed" || { fail "some repo packages failed"; FAILED=$((FAILED+1)); }

# ── 2. wlogout (build from source, same as ISO) ─────────────────────────────
hdr "2/8 · wlogout"
if command -v wlogout >/dev/null 2>&1; then
  ok "wlogout already installed"
else
  _w=$(mktemp -d)
  if git clone --depth 1 https://github.com/ArtsyMacaw/wlogout.git "$_w/wlogout" \
     && cd "$_w/wlogout" && meson setup build --prefix=/usr && ninja -C build \
     && sudo ninja -C build install; then
    ok "wlogout built + installed"
  else
    warn "wlogout build failed — EWW powermenu still covers logout"
  fi
  cd /; rm -rf "$_w"
fi

# ── 3. swww (AUR, optional — swaybg fallback exists) ────────────────────────
hdr "3/8 · swww (optional)"
if command -v swww >/dev/null 2>&1; then
  ok "swww already installed"
elif command -v yay >/dev/null 2>&1; then
  yay -S --needed --noconfirm swww && ok "swww installed via yay" \
    || warn "swww failed — swaybg fallback will handle wallpaper"
else
  warn "yay missing — skipping swww (swaybg fallback active)"
fi

# ── 4. System daemons + binaries + themes from airootfs ────────────────────
hdr "4/8 · NYXUS system files (daemons, binaries, cursors, icons)"
sudo mkdir -p /opt/nyxus
sudo cp -f "$AIR/opt/nyxus/"*.py /opt/nyxus/ && ok "/opt/nyxus daemons (dockd, hotkeyd, qsd, snapd, missiond, …)"
sudo find "$AIR/usr/local/bin" -maxdepth 1 -type f -exec cp -f {} /usr/local/bin/ \; \
  && sudo chmod +x /usr/local/bin/nyxus* 2>/dev/null \
  && ok "/usr/local/bin nyxus tools ($(ls "$AIR/usr/local/bin" | grep -c nyxus) binaries)"
sudo cp -rf "$AIR/usr/share/icons/NYXUS-Aurora" "$AIR/usr/share/icons/NYXUS-Dark" /usr/share/icons/ \
  && ok "NYXUS-Aurora cursor + NYXUS-Dark icon themes"
[[ -d "$AIR/usr/share/nyxus" ]] && sudo cp -rf "$AIR/usr/share/nyxus" /usr/share/ && ok "/usr/share/nyxus assets"
[[ -d "$AIR/usr/share/backgrounds" ]] && sudo cp -rf "$AIR/usr/share/backgrounds/." /usr/share/backgrounds/ 2>/dev/null && ok "backgrounds"
[[ -d "$AIR/usr/share/sounds" ]] && sudo cp -rf "$AIR/usr/share/sounds/." /usr/share/sounds/ 2>/dev/null && ok "sounds"
if [[ -d "$AIR/usr/share/applications" ]]; then
  sudo cp -f "$AIR/usr/share/applications/"*.desktop /usr/share/applications/ 2>/dev/null && ok "system .desktop entries"
fi
sudo gtk-update-icon-cache -f /usr/share/icons/NYXUS-Dark 2>/dev/null || true
sudo update-desktop-database /usr/share/applications 2>/dev/null || true

# ── 5. Polkit helpers + policies ─────────────────────────────────────────────
hdr "5/8 · Polkit helpers + policies"
for h in nyxus-welcome-helper nyxus-parental-helper nyxus-account-helper \
         nyxus-backup-helper nyxus-doctor-helper nyxus-usbwatch-helper; do
  if [[ -f "$CACHE/$h" ]]; then
    sudo install -Dm0755 "$CACHE/$h" "/usr/local/libexec/$h" && ok "$h"
  fi
done
for p in nyxus-welcome.policy com.nyxus.parental.policy; do
  [[ -f "$CACHE/$p" ]] && sudo install -Dm0644 "$CACHE/$p" "/usr/share/polkit-1/actions/$p" && ok "$p"
done
for p in com.nyxus.account.policy com.nyxus.backup.policy com.nyxus.doctor.policy \
         com.nyxus.firewall.policy com.nyxus.updater.policy com.nyxus.usbwatch.policy; do
  [[ -f "$CACHE/polkit-policies/$p" ]] && sudo install -Dm0644 "$CACHE/polkit-policies/$p" "/usr/share/polkit-1/actions/$p" && ok "$p"
done
[[ -f "$HOME/.local/bin/nyxus-crash-report" ]] && sudo install -Dm0755 "$HOME/.local/bin/nyxus-crash-report" /usr/local/bin/nyxus-crash-report && ok "nyxus-crash-report → /usr/local/bin"

# ── 6. Remaining GTK4 apps from local tarballs ──────────────────────────────
hdr "6/8 · GTK4 apps (weather, notepad, passwords, intel, sage, studio, security)"
for app in weather notepad passwords intel sage studio security; do
  tgz="$CACHE/nyxus-$app.tgz"
  [[ "$app" == "security" && ! -f "$tgz" ]] && tgz="$CACHE/nyxus-shield.tgz"
  if [[ ! -f "$tgz" ]]; then warn "$app: tarball missing"; continue; fi
  W=$(mktemp -d)
  if tar -xzf "$tgz" -C "$W" 2>/dev/null; then
    inner=$(find "$W" -maxdepth 2 -name install.sh | head -1)
    if [[ -n "$inner" ]]; then
      if sudo SUDO_USER="$USER" HOME="$HOME" bash "$inner" >"/tmp/nyxus-$app-finish.log" 2>&1; then
        ok "$app"
      else
        fail "$app — see /tmp/nyxus-$app-finish.log"; FAILED=$((FAILED+1))
      fi
    else
      warn "$app: no install.sh in tarball"
    fi
  else
    fail "$app: extract failed"; FAILED=$((FAILED+1))
  fi
  rm -rf "$W"
done

# ── 7. Session entry + services ──────────────────────────────────────────────
hdr "7/8 · Hyprland session entry"
sudo tee /usr/share/wayland-sessions/nyxus-hyprland.desktop >/dev/null <<'EOF'
[Desktop Entry]
Name=NYXUS (Hyprland)
Comment=NYXUS Silent Dark Desktop
Exec=Hyprland
Type=Application
DesktopNames=Hyprland
EOF
ok "/usr/share/wayland-sessions/nyxus-hyprland.desktop"
systemctl --user daemon-reload && ok "user services reloaded"

# ── 8. Mark bootstrapped (everything is already deployed offline) ───────────
hdr "8/8 · Bootstrap marker + icons"
mkdir -p "$HOME/.nyxus"
echo "2026.05.12-r10-mission" > "$HOME/.nyxus/.bootstrapped"
ok "bootstrap marker written — first Hyprland login won't re-download"
python3 "$HOME/.nyxus/nyxus_gen_icons.py" >/dev/null 2>&1 && ok "app icons generated" || warn "icon gen skipped"
fc-cache -f >/dev/null 2>&1 || true

echo
echo "======================================================"
if [[ $FAILED -eq 0 ]]; then
  echo " ${G}${B}NYXUS COMPLETE — everything is in place.${N}"
else
  echo " ${Y}${B}Done with $FAILED failure(s) — check logs above.${N}"
fi
echo "======================================================"
echo
echo " Log out → pick 'NYXUS (Hyprland)' at the login screen."
echo " First login: Mission Control plugin (hyprexpo) auto-installs (~1 min)."
echo " If bars don't appear: cat /tmp/nyxus-bootstrap.log"
echo

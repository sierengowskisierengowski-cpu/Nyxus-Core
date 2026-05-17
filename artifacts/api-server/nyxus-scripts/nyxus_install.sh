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
EWW_DIR="$HOME/.config/eww"
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
warn() { printf "  ${YELLOW:-\033[33m}${B}!${R}  ${DIM}%s${R}\n" "$1"; }
hdr()  { printf "\n${PURPLE}${B}── %s ${DIM}%s${R}\n" "$1" "────────────────────────────────────────────"; }

## Offline mode: if NYXUS_OFFLINE_DIR is set, copy from local cache
## instead of fetching over the network. Used by the offline ISO bake
## (cache pre-staged into /opt/nyxus-cache by customize_airootfs.sh).
dl() {
  local name="$1" dest="$2"
  if [ -n "${NYXUS_OFFLINE_DIR:-}" ] && [ -f "${NYXUS_OFFLINE_DIR}/${name}" ]; then
    if cp -f "${NYXUS_OFFLINE_DIR}/${name}" "$dest" 2>/dev/null; then
      ok "$name → $dest  ${DIM}(offline)${R}"
      return 0
    else
      fail "$name (offline copy failed)"
      failed_items+=("$name")
      return 1
    fi
  fi
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
## NOTE (rev r6-eww, 2026-05-11): the following four Python apps were
## REMOVED because EWW now provides the same functionality natively:
##   nyxus_quicksettings.py → eww open --toggle dashboard
##   nyxus_clock.py        → built into EWW dashboard clock card
##   nyxus_calendar.py     → built into EWW dashboard calendar card
##   nyxus_cheatsheet.py   → eww open --toggle cheatsheet
## See artifacts/api-server/nyxus-scripts/eww/ for the replacements.
for f in nyxus_palette.py nyxus-palette.css \
           nyxus_preboot.py nyxus_motd.py nyxus_splash.py nyxus_error.py \
           nyxus_account.py nyxus_backup.py nyxus_parental.py \
           nyxus_sysmon_gtk.py nyxus_notepad.py nyxus_store.py \
           nyxus_powermenu.py nyxus_welcome.py \
           nyxus_stickies.py nyxus_notes.py nyxus_terminal.py \
           nyxus_gen_icons.py nyxus_control.py nyxus_settings.py \
           nyxus_wallpaper_studio.py \
           nyxus_settings_accessibility.py nyxus_settings_notifications.py \
           nyxus_settings_sandbox.py nyxus_settings_snapshots.py \
           nyxus_doctor.py nyxus_launcher.py \
           nyxus_screenshot.py nyxus_chrome.py \
           nyxus_screensaver.py nyxus_demon_wake.py \
           nyxus_usb_watch.py nyxus-crash-report.py; do
  dl "$f" "$SCRIPTS_DIR/$f" && chmod +x "$SCRIPTS_DIR/$f" || failed=$((failed+1))
done

# Crash report CLI wrapper (nyxus_settings.py / nyxus_crashd.py launch this by name)
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/nyxus-crash-report" <<'EOF'
#!/usr/bin/env bash
exec python3 "$HOME/.nyxus/nyxus-crash-report.py" "$@"
EOF
chmod 0755 "$HOME/.local/bin/nyxus-crash-report"
sudo -n install -Dm0755 "$HOME/.local/bin/nyxus-crash-report" /usr/local/bin/nyxus-crash-report 2>/dev/null || true

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

# ── Inter Font (REQUIRED for NYXUS hand-drawn aesthetic) ────────────────────
hdr "Inter Font (NYXUS hand-drawn design)"
FONT_DIR="$HOME/.local/share/fonts"
mkdir -p "$FONT_DIR"
INTER_URL="https://github.com/googlefonts/inter/raw/main/fonts/ttf"
INTER_FILES=("Inter-Regular.ttf" "InterDisplay-Bold.ttf" "Inter-Medium.ttf" "Inter-SemiBold.ttf")
inter_ok=0
for f in "${INTER_FILES[@]}"; do
  if [ -f "$FONT_DIR/$f" ]; then
    inter_ok=$((inter_ok+1))
  else
    if curl -fsSL "$INTER_URL/$f" -o "$FONT_DIR/$f" 2>/dev/null; then
      inter_ok=$((inter_ok+1))
    elif wget -qO "$FONT_DIR/$f" "$INTER_URL/$f" 2>/dev/null; then
      inter_ok=$((inter_ok+1))
    fi
  fi
done
if [ $inter_ok -ge 2 ]; then
  fc-cache -f "$FONT_DIR" 2>/dev/null
  ok "Inter font installed ($inter_ok files) → fc-cache updated"
else
  # Try pacman as fallback
  if command -v pacman &>/dev/null; then
    pacman -S --noconfirm --needed ttf-google-fonts-git 2>/dev/null || \
    pacman -S --noconfirm --needed ttf-croscore 2>/dev/null || true
  fi
  printf "  ${DIM}Inter font: $inter_ok files found — DARK MIRROR fallback chain handles missing fonts${R}\n"
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

# ── GTK DARK THEME (adw-gtk3-dark) ────────────────────────────────────────────
# Without this, GTK4 apps fall back to default light Adwaita and error
# dialogs render as white text on white background (unreadable). The
# Hyprland env line `env = GTK_THEME,adw-gtk3-dark` only sets the env var;
# the theme package + settings.ini files have to actually exist for it to
# resolve. We belt-and-suspender three things:
#   1) Install adw-gtk3 from official repo (or AUR fallback)
#   2) Write XDG settings.ini for GTK3 + GTK4 (covers apps that ignore env)
#   3) Set gsettings color-scheme=prefer-dark (covers libadwaita apps)
hdr "GTK Dark Theme (adw-gtk3-dark)"
if ! pacman -Qi adw-gtk3 >/dev/null 2>&1; then
  if sudo pacman -S --noconfirm --needed adw-gtk3 2>/dev/null; then
    ok "adw-gtk3 installed via pacman"
  elif command -v yay >/dev/null 2>&1 && yay -S --noconfirm adw-gtk3 2>/dev/null; then
    ok "adw-gtk3 installed via yay (AUR fallback)"
  else
    printf "  \033[93mWARN:\033[0m adw-gtk3 install failed — error dialogs may stay white-on-white\n"
    failed=$((failed+1))
  fi
else
  ok "adw-gtk3 already installed"
fi

# Write XDG settings.ini for GTK3 + GTK4 (these files are READ even when
# GTK_THEME env var is unset — belt-and-suspenders against env loss)
mkdir -p "$HOME/.config/gtk-3.0" "$HOME/.config/gtk-4.0"
cat > "$HOME/.config/gtk-3.0/settings.ini" <<'GTK3'
[Settings]
gtk-theme-name=adw-gtk3-dark
gtk-icon-theme-name=NYXUS-Dark
gtk-application-prefer-dark-theme=1
gtk-font-name=Inter 11
gtk-cursor-theme-name=NYXUS-Aurora
gtk-cursor-theme-size=24
gtk-decoration-layout=icon:minimize,maximize,close
gtk-enable-animations=true
GTK3
cat > "$HOME/.config/gtk-4.0/settings.ini" <<'GTK4'
[Settings]
gtk-theme-name=adw-gtk3-dark
gtk-icon-theme-name=NYXUS-Dark
gtk-application-prefer-dark-theme=1
gtk-font-name=Inter 11
gtk-cursor-theme-name=NYXUS-Aurora
gtk-cursor-theme-size=24
gtk-decoration-layout=icon:minimize,maximize,close
GTK4
ok "GTK 3 + 4 settings.ini written (NYXUS-Dark icon theme, prefer-dark)"

# gsettings handles libadwaita apps that ignore both env and settings.ini
if command -v gsettings >/dev/null 2>&1; then
  gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
  gsettings set org.gnome.desktop.interface gtk-theme 'adw-gtk3-dark' 2>/dev/null || true
  ok "gsettings color-scheme=prefer-dark, gtk-theme=adw-gtk3-dark"
fi

# ── HYPRLAND CONFIGS ──────────────────────────────────────────────────────────
hdr "Hyprland"
mkdir -p "$HYPR_DIR"
mkdir -p "$HYPR_DIR/conf.d"
dl "hyprland.conf" "$HYPR_DIR/hyprland.conf" || failed=$((failed+1))
dl "hyprlock.conf" "$HYPR_DIR/hyprlock.conf"  || failed=$((failed+1))
dl "hypridle.conf"  "$HYPR_DIR/hypridle.conf"  || failed=$((failed+1))

# ── Modular DARK MIRROR confs (sourced by hyprland.conf) ─────────────────────
# Without these, hyprland.conf's `source = ~/.config/hypr/conf.d/...` lines
# silently no-op and apps render fully opaque / unblurred. These six files
# carry the locked NYXUS window opacity, blur tuning, layer-shell blur,
# float/center/size rules, fog daemon hooks, and general behavior.
for conf in nyxus-hyprland-general.conf \
            nyxus-hyprland-rules.conf \
            nyxus-hyprland-opacity.conf \
            nyxus-hyprland-blur.conf \
            nyxus-hyprland-layerblur.conf \
            nyxus-hyprland-fog.conf \
            nyxus-hyprland-mission.conf; do
  dl "$conf" "$HYPR_DIR/conf.d/$conf" || failed=$((failed+1))
done

# ── WALLPAPER ─────────────────────────────────────────────────────────────────
hdr "Wallpaper (SIERENGOWSKI)"
WALLS_DIR="$HYPR_DIR/walls"
mkdir -p "$WALLS_DIR"
dl "nyxus-void-vortex.png"    "$WALLS_DIR/nyxus-void-vortex.png"    || failed=$((failed+1))
dl "nyxus-ink-swirl.png" "$WALLS_DIR/nyxus-ink-swirl.png" || failed=$((failed+1))
dl "nyxus-void-wallpaper.mp4" "$WALLS_DIR/nyxus-void-wallpaper.mp4" || failed=$((failed+1))
dl "nyxus-starfield-wall.png" "$WALLS_DIR/nyxus-starfield-wall.png" || failed=$((failed+1))
dl "nyxus-drifter-wall.png"   "$WALLS_DIR/nyxus-drifter-wall.png"   || failed=$((failed+1))
dl "nyxus-taskbar-bg.png"         "$WALLS_DIR/nyxus-taskbar-bg.png"         || failed=$((failed+1))
dl "nyxus-rightbar-bg.png"        "$WALLS_DIR/nyxus-rightbar-bg.png"        || failed=$((failed+1))
dl "nyxus-starlight.png"          "$WALLS_DIR/nyxus-starlight.png"          || failed=$((failed+1))
dl "nyxus-monogram-mist.png"      "$WALLS_DIR/nyxus-monogram-mist.png"      || failed=$((failed+1))
dl "nyxus-topbar-mist.png"        "$WALLS_DIR/nyxus-topbar-mist.png"        || failed=$((failed+1))
dl "nyxus-hyprlock-eye.png"       "$WALLS_DIR/nyxus-hyprlock-eye.png"       || failed=$((failed+1))
dl "nyxus-login-stars.png"        "$WALLS_DIR/nyxus-login-stars.png"        || failed=$((failed+1))
dl "nyxus-bar-stone.png"          "$WALLS_DIR/nyxus-bar-stone.png"          || failed=$((failed+1))

# ── APP BACKGROUNDS (neon splat panels — used by all GTK apps) ────────────────
hdr "App Backgrounds (neon splat panels)"
BG_DIR="$HOME/.nyxus/backgrounds"
mkdir -p "$BG_DIR"
for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16; do
  dl "nyxus-bg-${i}.png" "$BG_DIR/nyxus-bg-${i}.png" || failed=$((failed+1))
done

# ── EWW (replaces waybar as of rev r6-eww, 2026-05-11) ──────────────────────
hdr "EWW (ElKowar's Wacky Widgets)"
# 4 bars (top/bottom/left/right) + dashboard + powermenu + cheatsheet + 3 OSDs.
# All real backends — no mock data, no placeholders. See eww/README.md.
EWW_DIR="$HOME/.config/eww"
EWW_SCRIPTS_DIR="$EWW_DIR/scripts"
mkdir -p "$EWW_DIR" "$EWW_SCRIPTS_DIR"
hdr "EWW Shell (bars · dashboard · powermenu · cheatsheet · OSDs)"
dl "eww/eww.yuck"     "$EWW_DIR/eww.yuck"     || failed=$((failed+1))
dl "eww/eww.scss"     "$EWW_DIR/eww.scss"     || failed=$((failed+1))
dl "eww/nyxus.conf"   "$EWW_DIR/nyxus.conf"   || failed=$((failed+1))
dl "eww/README.md"    "$EWW_DIR/README.md"    || failed=$((failed+1))
for s in audio audio-action audio-sinks battery bluetooth brightness \
         bt-action bt-list calendar calendar-month cpu-bars mic network \
         notif-action notif-history notifications osd-show player \
         power-profile qs-toggle quicksettings sys-pulse ticker \
         updates weather wifi-action wifi-list workspaces; do
  dl "eww/scripts/${s}.sh" "$EWW_SCRIPTS_DIR/${s}.sh" || failed=$((failed+1))
done
chmod +x "$EWW_SCRIPTS_DIR"/*.sh 2>/dev/null || true

# nyxus-eww-launch (deadline-bounded launcher) → /usr/local/bin/
if dl "nyxus-eww-launch" "/tmp/nyxus-eww-launch.new"; then
  if sudo -n install -m 0755 /tmp/nyxus-eww-launch.new /usr/local/bin/nyxus-eww-launch 2>/dev/null; then
    ok "nyxus-eww-launch → /usr/local/bin/"
  else
    install -m 0755 /tmp/nyxus-eww-launch.new "$HOME/.local/bin/nyxus-eww-launch" 2>/dev/null \
      && ok "nyxus-eww-launch → ~/.local/bin/ (sudo unavailable)" \
      || failed=$((failed+1))
  fi
  rm -f /tmp/nyxus-eww-launch.new
fi
if dl "nyxus-mission-control-toggle" "/tmp/nyxus-mission-control-toggle.new"; then
  if sudo -n install -m 0755 /tmp/nyxus-mission-control-toggle.new /usr/local/bin/nyxus-mission-control-toggle 2>/dev/null; then
    ok "nyxus-mission-control-toggle → /usr/local/bin/"
  else
    install -m 0755 /tmp/nyxus-mission-control-toggle.new "$HOME/.local/bin/nyxus-mission-control-toggle" 2>/dev/null \
      && ok "nyxus-mission-control-toggle → ~/.local/bin/ (sudo unavailable)" \
      || failed=$((failed+1))
  fi
  rm -f /tmp/nyxus-mission-control-toggle.new
fi

# ── A4 FIX (2026-05-12): bootstrap shims + welcome wizard parity ─────────────
# hyprland.conf references nyxus-bootstrap, nyxus-wait-bootstrap, nyxus-welcome,
# and nyxus_welcome.py. The ISO build installs them; the per-user installer
# was missing them — leaving fresh installs unable to complete first-boot
# bootstrap (the wait-shim would block 120s and the welcome wizard would
# 'command not found'). Install path mirrors build-iso.sh:208-210.
hdr "Bootstrap shims + Welcome wizard"
mkdir -p "$HOME/.local/bin"
for helper in nyxus-bootstrap nyxus-wait-bootstrap nyxus-welcome; do
  if dl "$helper" "/tmp/${helper}.new"; then
    if sudo -n install -m 0755 "/tmp/${helper}.new" "/usr/local/bin/${helper}" 2>/dev/null; then
      ok "$helper → /usr/local/bin/"
    else
      install -m 0755 "/tmp/${helper}.new" "$HOME/.local/bin/${helper}" 2>/dev/null \
        && ok "$helper → ~/.local/bin/ (sudo unavailable)" \
        || failed=$((failed+1))
    fi
    rm -f "/tmp/${helper}.new"
  fi
done
# Welcome wizard python module → ~/.nyxus/ (run by /usr/local/bin/nyxus-welcome)
mkdir -p "$HOME/.nyxus"
dl "nyxus_welcome.py" "$HOME/.nyxus/nyxus_welcome.py" || failed=$((failed+1))
# Polkit helper + policy — root-only; only stage when sudo is non-interactive
if sudo -n true 2>/dev/null; then
  if dl "nyxus-welcome-helper" "/tmp/nyxus-welcome-helper.new"; then
    sudo -n install -m 0755 /tmp/nyxus-welcome-helper.new /usr/local/bin/nyxus-welcome-helper 2>/dev/null \
      && ok "nyxus-welcome-helper → /usr/local/bin/"
    rm -f /tmp/nyxus-welcome-helper.new
  fi
  if dl "nyxus-welcome.policy" "/tmp/nyxus-welcome.policy.new"; then
    sudo -n install -m 0644 /tmp/nyxus-welcome.policy.new /usr/share/polkit-1/actions/dev.nyxus.welcome.policy 2>/dev/null \
      && ok "nyxus-welcome.policy → /usr/share/polkit-1/actions/"
    rm -f /tmp/nyxus-welcome.policy.new
  fi
else
  warn "skipping nyxus-welcome-helper + .policy (no passwordless sudo) — run installer with sudo to enable polkit elevation"
fi

# Optional systemd user service (idempotent — Hyprland exec-once also works)
mkdir -p "$HOME/.config/systemd/user"
_any_user_units_updated=0
dl "nyxus-eww.service" "$HOME/.config/systemd/user/nyxus-eww.service" && _any_user_units_updated=1 || true
dl "nyxus-crashd.service" "$HOME/.config/systemd/user/nyxus-crashd.service" && _any_user_units_updated=1 || true
# USB plug-in / removal toast notifier — toggle lives in
# Settings → Notifications → External devices.
dl "nyxus-usb-watch.service" \
   "$HOME/.config/systemd/user/nyxus-usb-watch.service" && _any_user_units_updated=1 || true
if [ "$_any_user_units_updated" -eq 1 ]; then
  systemctl --user daemon-reload 2>/dev/null || true
fi

# ── Welcome Wizard launcher / helper / policy ────────────────────────────────
hdr "Welcome Wizard"
mkdir -p "$HOME/.local/bin"
if dl "nyxus-welcome" "/tmp/nyxus-welcome.new"; then
  install -m 0755 /tmp/nyxus-welcome.new "$HOME/.local/bin/nyxus-welcome" \
    && ok "nyxus-welcome → ~/.local/bin/"
  sudo -n install -m 0755 /tmp/nyxus-welcome.new /usr/local/bin/nyxus-welcome 2>/dev/null \
    && ok "nyxus-welcome → /usr/local/bin/" \
    || printf "  ${DIM}(sudo unavailable — keeping nyxus-welcome in ~/.local/bin)${R}\n"
  rm -f /tmp/nyxus-welcome.new
fi
if dl "nyxus-welcome-helper" "/tmp/nyxus-welcome-helper.new"; then
  if sudo -n install -Dm0755 /tmp/nyxus-welcome-helper.new /usr/local/libexec/nyxus-welcome-helper 2>/dev/null; then
    ok "nyxus-welcome-helper → /usr/local/libexec/"
  else
    printf "  ${DIM}(skip: nyxus-welcome-helper — needs sudo for /usr/local/libexec)${R}\n"
  fi
  rm -f /tmp/nyxus-welcome-helper.new
fi
if dl "nyxus-welcome.policy" "/tmp/nyxus-welcome.policy.new"; then
  if sudo -n install -Dm0644 /tmp/nyxus-welcome.policy.new /usr/share/polkit-1/actions/dev.nyxus.welcome.policy 2>/dev/null; then
    ok "nyxus-welcome.policy → /usr/share/polkit-1/actions/"
  else
    printf "  ${DIM}(skip: nyxus-welcome.policy — needs sudo for polkit actions)${R}\n"
  fi
  rm -f /tmp/nyxus-welcome.policy.new
fi

# ── Parental Controls helper / policy ───────────────────────────────────────
# Settings → Parental Controls invokes this via:
#   pkexec /usr/local/libexec/nyxus-parental-helper ...
if dl "nyxus-parental-helper" "/tmp/nyxus-parental-helper.new"; then
  if sudo -n install -Dm0755 /tmp/nyxus-parental-helper.new /usr/local/libexec/nyxus-parental-helper 2>/dev/null; then
    ok "nyxus-parental-helper → /usr/local/libexec/"
  else
    printf "  ${DIM}(skip: nyxus-parental-helper — needs sudo for /usr/local/libexec)${R}\n"
  fi
  rm -f /tmp/nyxus-parental-helper.new
fi
if dl "com.nyxus.parental.policy" "/tmp/com.nyxus.parental.policy.new"; then
  if sudo -n install -Dm0644 /tmp/com.nyxus.parental.policy.new /usr/share/polkit-1/actions/com.nyxus.parental.policy 2>/dev/null; then
    ok "com.nyxus.parental.policy → /usr/share/polkit-1/actions/"
  else
    printf "  ${DIM}(skip: com.nyxus.parental.policy — needs sudo for polkit actions)${R}\n"
  fi
  rm -f /tmp/com.nyxus.parental.policy.new
fi

# ── Completion wave helpers/policies (account/backup/doctor/usbwatch etc.) ──
for h in nyxus-account-helper nyxus-backup-helper nyxus-doctor-helper nyxus-usbwatch-helper; do
  if dl "${h}" "/tmp/${h}.new"; then
    if sudo -n install -Dm0755 "/tmp/${h}.new" "/usr/local/libexec/${h}" 2>/dev/null; then
      ok "${h} → /usr/local/libexec/"
    else
      printf "  ${DIM}(skip: ${h} — needs sudo for /usr/local/libexec)${R}\n"
    fi
    rm -f "/tmp/${h}.new"
  fi
done
for p in com.nyxus.account.policy com.nyxus.backup.policy com.nyxus.doctor.policy \
         com.nyxus.firewall.policy com.nyxus.updater.policy com.nyxus.usbwatch.policy; do
  if dl "polkit-policies/${p}" "/tmp/${p}.new"; then
    if sudo -n install -Dm0644 "/tmp/${p}.new" "/usr/share/polkit-1/actions/${p}" 2>/dev/null; then
      ok "${p} → /usr/share/polkit-1/actions/"
    else
      printf "  ${DIM}(skip: ${p} — needs sudo for polkit actions)${R}\n"
    fi
    rm -f "/tmp/${p}.new"
  fi
done

# Build EWW from source (v0.6.0 pinned) ONLY if not already installed.
# Pinning + fail-fast lives in customize_airootfs.sh on the ISO; on existing
# systems we install via cargo if the binary is missing.
if ! command -v eww &>/dev/null; then
  printf "  ${PURPLE}→${R} ${DIM}eww binary missing — installing prerequisites…${R}\n"
  if command -v pacman &>/dev/null; then
    sudo -n pacman -S --noconfirm --needed rustup gtk3 gtk-layer-shell pango cairo gdk-pixbuf2 \
      glib2 dbus librsvg libdbusmenu-gtk3 2>/dev/null || true
    sudo -n rustup default stable 2>/dev/null || rustup default stable 2>/dev/null || true
    if command -v cargo &>/dev/null; then
      printf "  ${DIM}building eww v0.6.0 (this takes ~3-5 min)…${R}\n"
      cargo install --git https://github.com/elkowar/eww --tag v0.6.0 --root "$HOME/.local" eww 2>/tmp/nyxus-eww-build.log \
        && ok "eww v0.6.0 built → ~/.local/bin/eww" \
        || { fail "eww build (see /tmp/nyxus-eww-build.log)"; failed=$((failed+1)); }
    else
      fail "cargo missing — cannot build eww (re-run installer after rustup setup)"
      failed=$((failed+1))
    fi
  else
    printf "  ${DIM}pacman unavailable — install eww manually: cargo install --git https://github.com/elkowar/eww --tag v0.6.0 eww${R}\n"
  fi
else
  ok "eww binary already installed: $(eww --version 2>/dev/null | head -1)"
fi

# ── WAYBAR REMOVED (rev r6-eww 2026-05-11) ──────────────────────────────────
# The entire waybar download + sed-substitution block was deleted with the
# EWW migration. EWW (see EWW SHELL block above) is now the sole bar/widget
# toolkit. If a user really wants to fall back to waybar, they must:
#   1. install waybar from pacman: sudo pacman -S waybar
#   2. write their own ~/.config/waybar/config + style.css (the upstream
#      NYXUS waybar theme is no longer maintained or shipped via the API)
#   3. comment out the EWW exec-once lines in ~/.config/hypr/hyprland.conf
#      and add: exec-once = waybar
# History of removed pieces (deleted from nyxus-scripts/ source-of-truth):
#   waybar-config.json, waybar-style.css, waybar-stats.sh, waybar-ticker.sh,
#   nyxus-sys-pulse.sh, nyxus-waybar-stars.png

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

# ── PALETTE.CSS COPY-ALONGSIDE (rev r13) ─────────────────────────────────────
# Every CSS file that @imports nyxus-palette.css needs the file resolvable
# in its own directory (GTK CSS @import is path-relative). Copy it next to
# every consumer.
hdr "Palette CSS (mirroring to all consumer dirs)"
PALETTE_SRC="$SCRIPTS_DIR/nyxus-palette.css"
if [[ -f "$PALETTE_SRC" ]]; then
  for dest in "$EWW_DIR" "$HOME/.config/wlogout" "$HOME/.config/dunst" \
              "$HOME/.config/rofi" "$HOME/.config/hypr" "$HOME/.nyxus"; do
    [[ -d "$dest" ]] && cp -f "$PALETTE_SRC" "$dest/nyxus-palette.css" 2>/dev/null && echo "  · mirrored to $dest/"
  done
  # And into every per-app tarball install dir under ~/.nyxus/
  for d in "$HOME/.nyxus"/*/; do
    [[ -d "$d" ]] && cp -f "$PALETTE_SRC" "$d/nyxus-palette.css" 2>/dev/null
  done
else
  echo "  WARN: nyxus-palette.css missing at $PALETTE_SRC — palette imports will fail"
  failed=$((failed+1))
fi

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

# NOTE: nyxus-weather.desktop is created by the nyxus-weather tarball's
# own install.sh (rich GTK4 variant). The standalone .py duplicate has
# been removed (rev 2026-05-07 r13).

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

cat > "$DESKTOP_DIR/nyxus-store.desktop" <<'DEOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=NYXUS App Store
GenericName=App Store
Comment=Browse, install, and update software in NYXUS
Exec=python3 /home/nyx/.nyxus/nyxus_store.py
Icon=io.nyxus.store
Terminal=false
Categories=System;Utility;
Keywords=nyxus;store;apps;packages;updates;software;
StartupWMClass=io.nyxus.store
DEOF
ok "nyxus-store.desktop"

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

# NOTE (rev r6-eww, 2026-05-11): standalone Calendar + Clock .desktop entries
# REMOVED — both surfaces are now permanently visible inside the EWW dashboard
# (Super+`). Keeping them as separate launchers would create duplicate UI.
# The EWW dashboard's calendar card uses scripts/calendar.sh (real `cal` output)
# and the clock card uses defpoll on the system locale time string.

# ── FIX HARDCODED /home/nyx/ PATHS ────────────────────────────────────────────
# All the .desktop heredocs above use the literal `/home/nyx/.nyxus/...`
# because GTK desktop entries don't expand $HOME at runtime. On the live
# ISO the user IS `nyx` so this works, but the moment someone installs
# NYXUS and creates a real account, every Exec= path breaks. Rewrite to
# the actual $HOME so apps launch under any username.
if [[ "$HOME" != "/home/nyx" ]]; then
  sed -i "s|/home/nyx/|$HOME/|g" "$DESKTOP_DIR"/nyxus-*.desktop 2>/dev/null \
    && ok "desktop entries rewritten: /home/nyx/ → $HOME/"
fi

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
    # Tarball extracts flat (./install.sh, ./Main.qml, etc.) — extract into
    # a sddm-theme/ subdir so the rest of the install path is consistent.
    mkdir -p "${SDDM_TMP}/sddm-theme"
    if tar -xzf "${SDDM_TMP}/theme.tar.gz" -C "${SDDM_TMP}/sddm-theme" 2>/dev/null \
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

      # ── SDDM theme fail-safe (rev r1-sddm-heal · 2026-05-17) ────────────
      # Root cause of the 2026-05-17 "blank login / TTY-only" incident:
      # the SDDM theme installer can write /etc/sddm.conf.d/nyxus.conf
      # (pinning Current=nyxus) BEFORE it finishes copying theme files.
      # If anything fails mid-install — partial tarball, disk full, sudo
      # timeout, killed process — the conf is left pointing at an empty
      # or incomplete /usr/share/sddm/themes/nyxus/ dir. On next boot
      # SDDM tries to load the empty theme, fails with
      # HELPER_DISPLAYSERVER_ERROR, and dies — user gets a black screen
      # with a blinking cursor and is locked out except via TTY rescue.
      #
      # Fail-safe: after the installer runs (success OR failure), verify
      # the theme dir is complete (theme.conf + metadata.desktop + Main.qml).
      # If anything is missing AND the conf was written, remove the conf
      # so SDDM falls back to its built-in theme on next start. The user
      # gets the default SDDM login screen instead of a brick — recovery
      # without TTY rescue.
      _SDDM_CONF_PATH="/etc/sddm.conf.d/nyxus.conf"
      _SDDM_THEME_PATH="/usr/share/sddm/themes/nyxus"
      _sddm_theme_complete=1
      if [[ -f "$_SDDM_CONF_PATH" ]] \
         && grep -q '^Current=nyxus' "$_SDDM_CONF_PATH" 2>/dev/null; then
        [[ ! -f "$_SDDM_THEME_PATH/theme.conf" ]]      && _sddm_theme_complete=0
        [[ ! -f "$_SDDM_THEME_PATH/metadata.desktop" ]] && _sddm_theme_complete=0
        [[ ! -f "$_SDDM_THEME_PATH/Main.qml" \
           && ! -f "$_SDDM_THEME_PATH/main.qml" ]]     && _sddm_theme_complete=0

        if [[ $_sddm_theme_complete -eq 0 ]]; then
          warn "SDDM theme is incomplete but $_SDDM_CONF_PATH pins Current=nyxus"
          warn "removing the conf so SDDM falls back to default theme (no login brick)"
          if sudo -n rm -f "$_SDDM_CONF_PATH" 2>/dev/null; then
            ok "$_SDDM_CONF_PATH removed — SDDM will use built-in theme"
            _sddm_theme_ok=0
          else
            fail "could not remove $_SDDM_CONF_PATH (no sudo) — MANUAL FIX REQUIRED:"
            fail "  sudo rm -f $_SDDM_CONF_PATH  (otherwise next boot may brick login)"
          fi
        fi
      fi

      # Atomic DM swap: ONLY disable GDM if SDDM was successfully enabled.
      # Doing it the other way around can leave the user with NO active
      # display manager and a TTY-only boot — never acceptable.
      if [[ ${_sddm_theme_ok:-0} -eq 1 ]]; then
        # daemon-reload so systemd sees the just-installed sddm.service unit
        # (without this, `systemctl enable sddm.service` will fail with
        # "Unit sddm.service does not exist" on a fresh sddm install).
        sudo -n systemctl daemon-reload &>/dev/null || true

        # Verify the unit file actually exists before trying to enable —
        # gives us a clearer error than systemctl's generic "does not exist".
        if [[ ! -f /usr/lib/systemd/system/sddm.service \
            && ! -f /etc/systemd/system/sddm.service ]]; then
          printf "  ${RED}✗${R}  sddm.service unit not found on disk — sddm package install probably failed silently\n"
          printf "  ${DIM}    Manual fix:  sudo pacman -S sddm && sudo systemctl enable sddm.service${R}\n"
          failed_items+=("sddm.service enable (unit missing)"); failed=$((failed+1))
        elif {
            # If gdm (or any other DM) is already linked as display-manager,
            # `systemctl enable sddm.service` will fail with
            # "Failed to enable unit: File ... already exists". Force-overwrite
            # the display-manager.service symlink so SDDM wins cleanly.
            sudo -n rm -f /etc/systemd/system/display-manager.service 2>/dev/null
            sudo -n systemctl enable --force sddm.service \
                >/tmp/nyxus-sddm-enable.log 2>&1
          }; then
          ok "sddm.service enabled (display-manager.service → sddm)"
          if systemctl is-enabled gdm.service &>/dev/null; then
            printf "  ${PURPLE}→${R} ${DIM}sddm OK — now disabling gdm.service …${R}\n"
            if sudo -n systemctl disable gdm.service &>/dev/null; then
              ok "gdm.service disabled (sddm is now your login manager)"
            else
              printf "  ${GOLD}⚠${R}  could not disable gdm — run: sudo systemctl disable gdm\n"
            fi
          fi
          printf "  ${DIM}Reboot or 'sudo systemctl start sddm' to see the NYXUS login screen${R}\n"
        elif ! sudo -n true 2>/dev/null; then
          printf "  ${DIM}(skip: sddm.service enable — needs sudo; run:${R}\n"
          printf "  ${DIM}     sudo -v && curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash${R}\n"
          printf "  ${DIM}   or one-shot:  sudo systemctl enable sddm.service${R}\n"
        else
          # Real failure — show the captured systemctl error so the user can
          # see WHY (conflicting DM, masked unit, missing dep, etc.).
          printf "  ${RED}✗${R}  could not enable sddm.service — leaving gdm in place to keep you logged in\n"
          if [[ -s /tmp/nyxus-sddm-enable.log ]]; then
            printf "  ${DIM}    systemctl said:${R}\n"
            sed 's/^/      /' /tmp/nyxus-sddm-enable.log | head -5
          fi
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
  # ── EWW restart (rev r6-eww — replaces the waybar restart block) ──────────
  pkill -x eww 2>/dev/null || true
  sleep 0.6
  if command -v eww &>/dev/null; then
    nohup eww daemon > /tmp/nyxus-eww-daemon.log 2>&1 &
    disown
    sleep 0.8
    if command -v nyxus-eww-launch &>/dev/null; then
      nohup nyxus-eww-launch > /tmp/nyxus-eww-launch.log 2>&1 &
      disown
      sleep 1.0
    else
      # Fallback: open windows directly from nyxus.conf list
      for w in bar-bottom bar-top bar-left bar-right; do
        eww open "$w" 2>/dev/null || true
      done
    fi
    if pgrep -x eww > /dev/null; then
      ok "EWW shell active — 4 bars + dashboard + powermenu + cheatsheet + OSDs"
    else
      fail "EWW daemon failed to start — check /tmp/nyxus-eww-daemon.log"
      failed=$((failed+1))
      failed_items+=("eww-start")
    fi
  else
    printf "  ${RED}${B}✗${R}  ${DIM}eww binary not found on PATH — install above failed${R}\n"
    failed=$((failed+1))
    failed_items+=("eww-binary")
  fi
fi

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  # rev r25 — VOID ANIMATED WALLPAPER. mpvpaper plays the swirling-galaxy
  # MP4 on loop on every output as a wlr-layer-shell BACKGROUND surface.
  # Flags: --no-audio (silence), loop-file=inf (seamless), hwdec=auto-safe
  # (GPU decode where available, fallback to CPU), no-osc/no-osd (bare).
  # We kill any prior wallpaper daemon (swaybg/hyprpaper/mpvpaper) first
  # so re-runs don't stack instances.
  pkill -x swaybg    2>/dev/null || true
  pkill -x hyprpaper 2>/dev/null || true
  pkill -x mpvpaper  2>/dev/null || true
  VORTEX_PNG="$WALLS_DIR/nyxus-void-vortex.png"
  DRIFTER_PNG="$WALLS_DIR/nyxus-drifter-wall.png"
  STAR_PNG="$WALLS_DIR/nyxus-starfield-wall.png"
  # rev r6-eww (2026-05-11) — VOID-VORTEX is the locked-in default wallpaper
  # for the EWW era. Matches hyprland.conf swaybg autostart line. Falls back
  # to drifter, then starfield, then ink-swirl if any are missing.
  if command -v swaybg >/dev/null 2>&1 && [[ -s "$VORTEX_PNG" ]]; then
    nohup swaybg -i "$VORTEX_PNG" -m fill -c "#000000" \
      >/tmp/nyxus-swaybg.log 2>&1 &
    disown
    ok "Wallpaper set — nyxus-void-vortex.png (swaybg · EWW-era default)"
  elif command -v swaybg >/dev/null 2>&1 && [[ -s "$DRIFTER_PNG" ]]; then
    nohup swaybg -i "$DRIFTER_PNG" -m fill -c "#000000" \
      >/tmp/nyxus-swaybg.log 2>&1 &
    disown
    warn "void-vortex missing — fell back to drifter portrait"
  elif command -v swaybg >/dev/null 2>&1 && [[ -s "$STAR_PNG" ]]; then
    nohup swaybg -i "$STAR_PNG" -m fill -c "#000000" \
      >/tmp/nyxus-swaybg.log 2>&1 &
    disown
    warn "void-vortex+drifter missing — fell back to static starfield"
  elif command -v swaybg >/dev/null 2>&1; then
    swaybg -i "$WALLS_DIR/nyxus-ink-swirl.png" -m fill & disown
    warn "all preferred walls missing — fell back to static swaybg ink-swirl"
  fi
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
  printf "  ${DIM}If EWW failed, run:  cat /tmp/nyxus-eww.log${R}\n"
  printf "  ${DIM}Otherwise re-run:  curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash${R}\n"
  exit 1
fi

echo ""

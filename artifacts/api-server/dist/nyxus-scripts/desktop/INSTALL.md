# NYXUS Desktop install (MSI host)

Symlinks needed so the wrapper command names in `hyprland.conf` resolve.

```bash
# Arch package dep (one-time)
sudo pacman -S --needed gtk4-layer-shell python-gobject

# Symlinks (or copy) — after `git pull` on MSI
sudo install -m 0755 ~/nyxus/artifacts/api-server/nyxus-scripts/desktop/nyxus_desktop.py \
  /usr/local/bin/nyxus-desktop
sudo install -m 0755 ~/nyxus/artifacts/api-server/nyxus-scripts/desktop/nyxus-context-menu.sh \
  /usr/local/bin/nyxus-context-menu.sh

# Verify
command -v nyxus-desktop          # → /usr/local/bin/nyxus-desktop
command -v nyxus-context-menu.sh  # → /usr/local/bin/nyxus-context-menu.sh
python3 -c 'import gi; gi.require_version("Gtk4LayerShell","1.0"); \
  from gi.repository import Gtk4LayerShell; print("layer-shell OK")'

# Restart Hyprland session (or hyprctl reload + relaunch desktop)
hyprctl reload
pkill swaybg 2>/dev/null
nyxus-desktop &
```

## Behavior

- Right-click on wallpaper → context menu (rofi).
- Left-click on wallpaper → dismiss any open menu/launcher.
- `Super+Ctrl+M` → context menu by keyboard.
- `Super+Alt+W` → reset to default wallpaper (hot-swap via IPC, no flicker).

## Fallbacks (graceful)

- No `gtk4-layer-shell` → process execs `swaybg` instead. Right-click stops working
  but wallpaper still paints. Install the package and re-launch to recover.
- No `rofi` and no `wofi` → menu shows a `notify-send` toast asking you to install one.
- Desktop process dead → wallpaper hot-swap silently no-ops; the on-disk wallpaper
  setter still runs so the next session boots with the chosen wallpaper.

## Logs

- `~/.cache/nyxus/desktop.log` — desktop process (rotated, 3×512KB).
- `~/.cache/nyxus/context-menu.log` — menu invocations.

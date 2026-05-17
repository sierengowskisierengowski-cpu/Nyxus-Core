-- NYXUS Hyprland — Safe Mode overrides.
--
-- Sourced ONLY when the user manually launches Hyprland from a Safe Mode
-- multi-user target. The wrapper script /usr/bin/nyxus-hypr-launch checks
-- /proc/cmdline for `nyxus.safemode=1` and, when present, points
-- HYPRLAND_CONFIG at this file instead of the full hyprland.lua.
--
-- Goals: get the user a usable session with NO custom daemons, NO GPU
-- acceleration features, and ONLY the keybinds needed to recover.

monitor = , preferred, auto, 1

-- No fog, no blur, no animations — keep things alive on broken GPUs.
animations {
    enabled = no
}
decoration {
    blur { enabled = no }
    drop_shadow = no
    rounding = 0
}
misc {
    vfr = false
    no_direct_scanout = true
}

-- Bare minimum apps — terminal + file manager + a clean way out.
$mod = SUPER
exec-once = mako --config /etc/skel/.config/mako/config 2>/dev/null || true
exec-once = waybar -c /etc/skel/.config/waybar/safemode.json 2>/dev/null || alacritty --title 'NYXUS Safe Mode'

bind = $mod, RETURN, exec, alacritty
bind = $mod, E,      exec, nyxus-files || alacritty -e ranger
bind = $mod, Q,      killactive
bind = $mod CTRL, R, exec, systemctl reboot
bind = $mod CTRL, S, exec, systemctl poweroff
bind = $mod, M,      exit

-- Big visible badge so the user knows they are in safe mode.
exec-once = sh -c 'notify-send -u critical "NYXUS Safe Mode" "Recovery session — most NYXUS daemons disabled. Reboot via Super+Ctrl+R."'

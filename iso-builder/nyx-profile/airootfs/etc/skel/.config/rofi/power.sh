#!/usr/bin/env bash
# ============================================================
#  NYXUS · Obsidian Prism — rofi power menu
#  Location: ~/.config/rofi/power.sh
#  Triggered by Super+Shift+P or the top-bar power button
# ============================================================

MENU_THEME="$HOME/.config/rofi/power.rasi"

# Options with icons (Nerd Font glyphs)
SHUTDOWN="  Shutdown"
REBOOT="  Reboot"
SUSPEND="  Suspend"
LOGOUT="  Logout"
LOCK="  Lock"
CANCEL="  Cancel"

# Prompt rofi
CHOICE=$(printf "%s\n%s\n%s\n%s\n%s\n%s" \
    "$SHUTDOWN" \
    "$REBOOT" \
    "$SUSPEND" \
    "$LOCK" \
    "$LOGOUT" \
    "$CANCEL" \
    | rofi \
        -dmenu \
        -i \
        -no-fixed-num-lines \
        -p "Power" \
        -theme "$MENU_THEME" \
        -selected-row 2)

case "$CHOICE" in
    "$SHUTDOWN")
        loginctl poweroff 2>/dev/null || systemctl poweroff
        ;;
    "$REBOOT")
        loginctl reboot 2>/dev/null || systemctl reboot
        ;;
    "$SUSPEND")
        loginctl suspend 2>/dev/null || systemctl suspend
        ;;
    "$LOCK")
        loginctl lock-session 2>/dev/null || hyprlock &
        ;;
    "$LOGOUT")
        if [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
            hyprctl dispatch exit
        else
            loginctl terminate-user "$USER" --kill=yes 2>/dev/null || pkill -KILL -u "$USER"
        fi
        ;;
    "$CANCEL"|"")
        exit 0
        ;;
esac

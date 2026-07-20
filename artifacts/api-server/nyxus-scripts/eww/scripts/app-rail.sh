#!/usr/bin/env bash
# NYXUS · EWW · right app-rail focus + occupancy from Hyprland
# Maps active window class → rail slot so float-island-active can glow.
set -u
export LC_ALL=C.UTF-8

# Slot ids must match app_rail in eww.yuck
SLOTS=(terminal browser files sysmon notepad stickies mixer bluetooth)

idle='{"active":"","terminal":{"active":false,"occupied":false},"browser":{"active":false,"occupied":false},"files":{"active":false,"occupied":false},"sysmon":{"active":false,"occupied":false},"notepad":{"active":false,"occupied":false},"stickies":{"active":false,"occupied":false},"mixer":{"active":false,"occupied":false},"bluetooth":{"active":false,"occupied":false}}'

class_to_slot() {
  local raw="${1:-}"
  local cls="${raw,,}"
  [[ -z "$cls" ]] && return 0

  case "$cls" in
    alacritty|kitty|wezterm|foot|ghostty|konsole|xterm|terminator|\
    org.wezfurlong.wezterm|io.alacritty|com.mitchellh.ghostty)
      echo terminal; return ;;
    firefox|zen|librewolf|chromium|google-chrome|brave-browser|brave|\
    vivaldi|waterfox|org.mozilla.firefox|org.mozilla.zen)
      echo browser; return ;;
    thunar|cosmic-files|org.gnome.nautilus|nautilus|dolphin|pcmanfm|\
    io.elementary.files|org.kde.dolphin|cosmic-files-applet)
      echo files; return ;;
    btop|btop++|nyxus-sysmon|nyxus_sysmon_gtk|io.nyxus.sysmon)
      echo sysmon; return ;;
    cosmic-text-editor|nyxus-notepad|nyxus_notepad|org.gnome.gedit|xed|\
    io.nyxus.notepad)
      echo notepad; return ;;
    cherrytree|nyxus-stickies|nyxus_stickies|io.nyxus.stickies)
      echo stickies; return ;;
    pavucontrol|pwvucontrol|pulsemixer|nyxus-mixer|io.nyxus.mixer)
      echo mixer; return ;;
    blueman-manager|blueberry|nyxus-bluetooth|io.nyxus.bluetooth)
      echo bluetooth; return ;;
  esac

  case "$cls" in
    *sysmon*)   echo sysmon; return ;;
    *notepad*)  echo notepad; return ;;
    *stickies*) echo stickies; return ;;
  esac

  return 0
}

eww_slot_open() {
  local want="$1"
  command -v eww >/dev/null 2>&1 || return 1
  eww active-windows 2>/dev/null | grep -qx "$want"
}

active_slot=""
declare -A occ=()
for s in "${SLOTS[@]}"; do occ["$s"]=false; done

if command -v hyprctl >/dev/null 2>&1; then
  active_class="$(hyprctl activewindow -j 2>/dev/null \
    | jq -r '(.class // .initialClass // "")' 2>/dev/null || echo "")"
  active_slot="$(class_to_slot "$active_class")"

  if command -v jq >/dev/null 2>&1; then
    while IFS= read -r cls; do
      slot="$(class_to_slot "$cls")"
      [[ -n "$slot" ]] && occ["$slot"]=true
    done < <(hyprctl clients -j 2>/dev/null \
      | jq -r '.[] | select(.mapped == true) | (.class // .initialClass // "")' 2>/dev/null)
  fi
fi

# EWW flyouts: open panel counts as occupied; focused eww client refines active.
if eww_slot_open mixer; then
  occ[mixer]=true
  [[ -z "$active_slot" ]] && active_slot=mixer
fi
if eww_slot_open bluetooth; then
  occ[bluetooth]=true
  [[ -z "$active_slot" ]] && active_slot=bluetooth
fi

# If hypr focused an eww client while a flyout is open, prefer the flyout slot.
if [[ "${active_class,,}" == "eww" || "${active_class,,}" == "eww-bar" ]]; then
  eww_slot_open mixer && active_slot=mixer
  eww_slot_open bluetooth && active_slot=bluetooth
fi

[[ -n "$active_slot" ]] && occ["$active_slot"]=true

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' "$idle"
  exit 0
fi

args=(--arg active "${active_slot:-}")
for s in "${SLOTS[@]}"; do
  is_active=false
  [[ "$active_slot" == "$s" ]] && is_active=true
  args+=(--argjson "${s}_active" "$is_active")
  args+=(--argjson "${s}_occ" "${occ[$s]}")
done

jq -nc "${args[@]}" '
  {
    active: $active,
    terminal:   {active: $terminal_active,   occupied: ($terminal_occ   or $terminal_active)},
    browser:    {active: $browser_active,    occupied: ($browser_occ    or $browser_active)},
    files:      {active: $files_active,      occupied: ($files_occ      or $files_active)},
    sysmon:     {active: $sysmon_active,     occupied: ($sysmon_occ     or $sysmon_active)},
    notepad:    {active: $notepad_active,    occupied: ($notepad_occ    or $notepad_active)},
    stickies:   {active: $stickies_active,   occupied: ($stickies_occ   or $stickies_active)},
    mixer:      {active: $mixer_active,      occupied: ($mixer_occ      or $mixer_active)},
    bluetooth:  {active: $bluetooth_active,  occupied: ($bluetooth_occ  or $bluetooth_active)}
  }'

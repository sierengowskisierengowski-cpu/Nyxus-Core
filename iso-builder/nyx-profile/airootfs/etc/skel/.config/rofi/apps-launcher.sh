#!/usr/bin/env bash
# APEX RIG — Apps & tools launcher (Super+A)
set -euo pipefail
THEME="${HOME}/.config/rofi/launcher.rasi"

menu() {
  cat <<'EOF'
🤖 AI & Code
  Cursor (Bifrost)
  Claude
  Terminal
🌐 Web & Chat
  Firefox
  Chromium
  Discord
📁 Files & Projects
  File Manager (home)
  Security Toolkit
  Projects folder
🔧 Security & Lab
  NOC Mini
  Security Toolkit Shell
  Lab Terminal
  Honeypot Stack
  Flipper Hub
  qFlipper
  Bad USB Payloads
📡 Live Control (gowski)
  Control Center (overview)
  Service Status (live)
  Honeypots (plain English)
  Local AI Stack
  SharkFin Monitor (dashboard)
  SharkFin Mini Ops (panel)
  SharkFin Vitals (live)
  SharkFin Screensaver (rotate)
  Hardware Status (sharkctl)
📒 Records & Vault
  Open Command Vault (editor)
  Vault Command List
  Command Ledger (master list)
  Ledger Audit Log
  Honeypot Events (all 10)
  System Inventory
⚙ System
  App Launcher (drun)
  Power Menu
  Lock Screen
  Flip to COSMIC
  Key Cheat Sheet
EOF
}

pick=$(menu | rofi -dmenu -i -p "APEX Apps" -theme "$THEME" -lines 18)
[[ -n "$pick" ]] || exit 0

case "$pick" in
  *Cursor*)           cursor ~/Projects/bifrost ;;
  *Claude*)           /usr/bin/chromium --profile-directory=Default --app-id=fmpnliohjhemenmnlpbfagaolkdacoja ;;
  *Terminal*)         alacritty ;;
  *Firefox*)          firefox ;;
  *Chromium*)         chromium ;;
  *Discord*)          discord ;;
  *File\ Manager*)    thunar ~ ;;
  *Security\ Toolkit) thunar ~/security-toolkit ;;
  *Projects*)         thunar ~/Projects ;;
  *NOC\ Mini*)        bash ~/Scripts/utilities/gowskinet-noc-mini.sh ;;
  *Security\ Toolkit\ Shell*) alacritty -e bash -lc 'cd ~/security-toolkit; exec bash -l' ;;
  *Lab\ Terminal*)    alacritty --class GowskinetLab -e bash -lc 'cd ~/security-toolkit/lab; exec bash -l' ;;
  *Honeypot*)         alacritty -e bash -lc 'source ~/.bashrc; honeypot-up; exec bash -l' ;;
  *Flipper\ Hub*)     alacritty --class FlipperHub -e bash -lc '~/Scripts/utilities/flipper-hub.sh; exec bash -l' ;;
  *qFlipper*)         ~/Projects/GNI/qFlipper-x86_64-1.3.3.AppImage ;;
  *Bad\ USB*)         thunar ~/security-toolkit/flipper/badusb ;;
  *Control\ Center*)  alacritty --class GowskiCenter -e bash -lc 'gowski; echo; gowski status; exec bash -l' ;;
  *Service\ Status*)  alacritty --class GowskiCenter -e bash -lc 'gowski watch status 3' ;;
  *plain\ English*)   alacritty -e bash -lc 'gowski plain honeypots; echo; gowski plain maze; echo; gowski plain cowrie; exec bash -l' ;;
  *Local\ AI\ Stack*) alacritty -e bash -lc 'gowski ai; exec bash -l' ;;
  *SharkFin\ Monitor*) sharkdash-app ;;
  *SharkFin\ Mini\ Ops*) sharknoc ;;
  *SharkFin\ Vitals*) sharksaver vitals ;;
  *SharkFin\ Screensaver*) sharksaver ;;
  *Hardware\ Status*) alacritty --class SharkCtl -e bash -lc 'sharkctl status; echo; exec bash -l' ;;
  *Command\ Ledger*)  alacritty --class LedgerScratch -e bash -lc 'ledger view' ;;
  *Ledger\ Audit*)    alacritty -e bash -lc 'ledger watch' ;;
  *Honeypot\ Events*) "$(command -v cursor || command -v cosmic-edit || echo xdg-open)" ~/CommandVault/honeypots ;;
  *System\ Inventory*) bash ~/.local/bin/system-inventory.sh --open ;;
  *Open\ Command\ Vault*) "$(command -v cursor || command -v cosmic-edit || echo xdg-open)" ~/CommandVault ;;
  *Vault\ Command\ List*) alacritty -e bash -lc 'source ~/.local/bin/cmd-ledger.sh; cmdvault commands; exec bash -l' ;;
  *App\ Launcher*)    rofi -show drun -theme "$THEME" ;;
  *Power*)            bash ~/.config/rofi/power.sh ;;
  *Lock*)             bash ~/Scripts/utilities/apex-lock.sh ;;
  *COSMIC*)           bash ~/Scripts/utilities/gowskinet-flip.sh ;;
  *Cheat*)            bash ~/.config/rofi/cheatsheet.sh ;;
esac

# ============================================================
#  NYXUS — ~/.bashrc
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

# Source the system bashrc if present (sane defaults, completion, etc.)
[ -f /etc/bash.bashrc ] && . /etc/bash.bashrc

# Only run the interactive bits when this is an interactive shell.
case $- in *i*) ;; *) return ;; esac

# ~/.local/bin on PATH (NYXUS launchers live there).
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac

# History niceties.
export HISTSIZE=10000 HISTFILESIZE=20000 HISTCONTROL=ignoreboth
shopt -s histappend checkwinsize

# `glow` — opt-in NYXUS neon colorizer (not run automatically):
#   ls | glow        say "hello" | glow -c        glow "loud text"
glow() { nyxus-glow "$@"; }

# Auto rainbow greeting is OFF by default (live-boot QA 2026-07-25).
# Opt in:  NYXUS_GREETING=1
if [ "${NYXUS_GREETING:-0}" = "1" ] && command -v nyxus-glow >/dev/null 2>&1; then
  printf '\n'
  nyxus-glow -c "        N Y X U S"
  NYXUS_GLOW_DENSITY=0.5 nyxus-glow -w "  alien neon · you are in it"
  printf '\n'
fi

# NYXUS · shell environment · rev 2026-05-13 r1
export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
export NYXUS_VERSION="2026.05.13"
export NYXUS_HOME="/opt/nyxus"
export EDITOR="${EDITOR:-nvim}"
export VISUAL="${VISUAL:-nvim}"
# Make sure ~/.cache/nyxus/ exists for app logs.
[ -d "${HOME}/.cache/nyxus" ] || mkdir -p "${HOME}/.cache/nyxus" 2>/dev/null

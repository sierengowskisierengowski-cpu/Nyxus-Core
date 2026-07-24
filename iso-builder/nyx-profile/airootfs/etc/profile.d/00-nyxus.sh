# NYXUS · shell environment · rev 2026-07-24 r2
export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
export NYXUS_VERSION="2026.07.24"
export NYXUS_HOME="/opt/nyxus"
export EDITOR="${EDITOR:-nvim}"
export VISUAL="${VISUAL:-nvim}"
# Expose build stamp (baked by build-iso.sh into /etc/nyxus-build) for scripts.
export NYXUS_BUILD_STAMP
NYXUS_BUILD_STAMP="$(sed -n '3p' /etc/nyxus-build 2>/dev/null | sed 's/.*: //' | tr -d '[:space:]' || echo 'dev')"
# Make sure ~/.cache/nyxus/ exists for app logs.
[ -d "${HOME}/.cache/nyxus" ] || mkdir -p "${HOME}/.cache/nyxus" 2>/dev/null

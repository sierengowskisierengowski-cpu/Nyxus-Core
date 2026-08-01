#!/usr/bin/env bash
# ============================================================================
#  nyxus-reclaim.sh — reclaim disk on the build box, safely
#
#  ⚠ READ THIS FIRST: cache cleanup does NOT fix a freeze. A full disk can
#  wedge a desktop, so it is worth ruling out, but if the machine locked up
#  with room to spare then the answer is in scripts/nyxus-freeze-report.sh,
#  not here. Run that one first.
#
#  DRY RUN BY DEFAULT. Nothing is deleted until you pass --apply.
#
#      bash scripts/nyxus-reclaim.sh              # show what would go
#      bash scripts/nyxus-reclaim.sh --apply      # actually delete
#      bash scripts/nyxus-reclaim.sh --apply --isos   # include old ISOs
#
#  Deliberately NOT touched: ~/.ssh, ~/.gnupg, ~/Projects, /opt/*, the pacman
#  database, any *.db, anything under the repo except iso-builder/out, and the
#  two most recent ISOs even with --isos.
#
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -u

APPLY=0; DO_ISOS=0
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --isos)  DO_ISOS=1 ;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) printf 'unknown option: %s (try --help)\n' "$a" >&2; exit 1 ;;
  esac
done

B=$'\e[1m'; R=$'\e[0m'
VIOLET=$'\e[38;2;125;61;255m'; GREEN=$'\e[38;2;57;255;20m'
ORANGE=$'\e[38;2;255;138;30m'; DIM=$'\e[2m'
hd() { printf '\n%s── %s ──%s\n' "${VIOLET}" "$*" "${R}"; }
note() { printf '  %s%s%s\n' "${DIM}" "$*" "${R}"; }

TOTAL_KB=0
sizeof() { du -sk "$1" 2>/dev/null | awk '{print $1}'; }
human()  { awk -v k="$1" 'BEGIN{ s="KMGT"; i=1; while(k>=1024 && i<4){k/=1024;i++} printf "%.1f%s", k, substr(s,i,1) }'; }

# report <label> <path-or-->  <size-kb>  <command...>
consider() {
  local label="$1" kb="$2"; shift 2
  [[ -z "${kb}" || "${kb}" -eq 0 ]] && { note "${label}: nothing to reclaim"; return; }
  TOTAL_KB=$(( TOTAL_KB + kb ))
  printf '  %s%s%s  %s\n' "${B}" "$(human "${kb}")" "${R}" "${label}"
  if (( APPLY )); then
    "$@" >/dev/null 2>&1 && printf '      %s✓ reclaimed%s\n' "${GREEN}" "${R}" \
                         || printf '      %s! failed (permissions?)%s\n' "${ORANGE}" "${R}"
  fi
}

printf '%s\n' "${B}NYXUS reclaim — $( ((APPLY)) && echo 'APPLYING' || echo 'DRY RUN (nothing will be deleted)' )${R}"
df -h / /home 2>/dev/null | sed 's/^/  /'

hd "pacman package cache"
# Keeps the 2 most recent versions of every package — the rollback safety net.
if command -v paccache >/dev/null 2>&1; then
  _kb="$(paccache -dk2 2>/dev/null | grep -oP 'finished: \K[0-9]+' >/dev/null 2>&1; sizeof /var/cache/pacman/pkg)"
  consider "/var/cache/pacman/pkg (keeping 2 newest per package)" "${_kb}" sudo paccache -rk2
  note "uninstalled packages are also purged with: sudo paccache -ruk0"
else
  note "paccache not found (pacman-contrib) — skipping"
fi

hd "systemd journal"
if command -v journalctl >/dev/null 2>&1; then
  _kb="$(journalctl --disk-usage 2>/dev/null | grep -oP '[0-9.]+(?=[A-Z])' | head -1)"
  _kb="$(sizeof /var/log/journal)"
  consider "/var/log/journal (trimming to 500M)" "${_kb}" sudo journalctl --vacuum-size=500M
  note "keep at least a few hundred MB — this is the only place freeze evidence lives"
fi

hd "user caches"
for d in "${HOME}/.cache/pip" "${HOME}/.cache/thumbnails" "${HOME}/.cache/nyxus-eww" \
         "${HOME}/.cache/yay" "${HOME}/.cache/mesa_shader_cache" "${HOME}/.cache/nv"; do
  [[ -d "${d}" ]] || continue
  consider "${d/#${HOME}/\~}" "$(sizeof "${d}")" rm -rf "${d}"
done
note "pip's cache is pure waste on this box; the bootstrap now sets PIP_NO_CACHE_DIR=1"

hd "build leftovers"
for d in /var/tmp/nyxus-work /var/tmp/nyxus-profile-bake; do
  [[ -d "${d}" ]] || continue
  consider "${d} (abandoned bake working tree)" "$(sizeof "${d}")" sudo rm -rf "${d}"
done
note "these are left behind when a bake is killed — a frozen machine always leaves one"

hd "docker"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker system df 2>/dev/null | sed 's/^/  /'
  if (( APPLY )); then
    printf '  running: docker system prune -f (dangling images + stopped containers)\n'
    docker system prune -f 2>/dev/null | tail -1 | sed 's/^/      /'
  else
    note "would run: docker system prune -f   (add --volumes ONLY if you accept losing honeypot capture data)"
  fi
else
  note "docker not running — skipping"
fi

hd "old ISOs"
_out="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)/iso-builder/out"
if [[ -d "${_out}" ]]; then
  ls -1t "${_out}"/*.iso 2>/dev/null | sed 's/^/      /'
  _kb="$(sizeof "${_out}")"
  printf '  %s%s%s  total in %s\n' "${B}" "$(human "${_kb}")" "${R}" "${_out}"
  if (( DO_ISOS )); then
    # Never the two newest: one is what you just baked, one is the fallback.
    mapfile -t _old < <(ls -1t "${_out}"/*.iso 2>/dev/null | tail -n +3)
    if (( ${#_old[@]} == 0 )); then
      note "only two or fewer ISOs present — keeping both"
    else
      for f in "${_old[@]}"; do
        printf '      %s %s\n' "$( ((APPLY)) && echo 'deleting' || echo 'would delete')" "${f}"
        (( APPLY )) && rm -f "${f}"
      done
    fi
  else
    note "pass --isos to remove all but the two most recent (HANDOFF records ~30G sitting here)"
  fi
fi

printf '\n%s%s reclaimable outside docker/ISOs%s\n' "${B}" "$(human "${TOTAL_KB}")" "${R}"
if (( APPLY )); then
  printf '%sDone.%s\n' "${GREEN}" "${R}"
else
  printf '%sDry run — nothing was deleted. Re-run with --apply.%s\n' "${ORANGE}" "${R}"
fi
printf '\n%sReminder: if the disk was not full, this did not fix your freeze.%s\n' "${DIM}" "${R}"
printf '%sRun: bash scripts/nyxus-freeze-report.sh%s\n' "${DIM}" "${R}"

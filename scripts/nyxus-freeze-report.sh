#!/usr/bin/env bash
# ============================================================================
#  nyxus-freeze-report.sh — what happened before the machine locked up
#
#  Run this AFTER a hard reboot. It reads the PREVIOUS boot's journal (-b -1),
#  which is the only place the evidence survives, and prints the handful of
#  things that actually explain a desktop freeze on this hardware.
#
#  Read-only. It changes nothing, kills nothing and deletes nothing. Some
#  sections need journal access; run with sudo for the complete picture.
#
#      bash scripts/nyxus-freeze-report.sh              # this boot + last boot
#      bash scripts/nyxus-freeze-report.sh -2           # two boots back
#
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -u

BOOT="${1:--1}"
B=$'\e[1m'; R=$'\e[0m'
VIOLET=$'\e[38;2;125;61;255m'; MAGENTA=$'\e[38;2;255;45;173m'
GREEN=$'\e[38;2;57;255;20m'; ORANGE=$'\e[38;2;255;138;30m'; DIM=$'\e[2m'

hd()   { printf '\n%s── %s ──%s\n' "${VIOLET}" "$*" "${R}"; }
ok()   { printf '  %s✓%s %s\n' "${GREEN}" "${R}" "$*"; }
warn() { printf '  %s!%s %s\n' "${ORANGE}" "${R}" "$*"; }
bad()  { printf '  %s✗%s %s\n' "${MAGENTA}" "${R}" "$*"; }
note() { printf '  %s%s%s\n' "${DIM}" "$*" "${R}"; }

jr() { journalctl -b "${BOOT}" "$@" 2>/dev/null; }

printf '%s\n' "${B}NYXUS freeze report — previous boot (${BOOT})${R}"
date '+  generated %F %T %Z'
if ! journalctl -b "${BOOT}" -n1 >/dev/null 2>&1; then
  bad "cannot read boot ${BOOT} from the journal."
  note "Either there is no such boot, or you need: sudo bash $0 ${BOOT}"
  note "If the journal is volatile (Storage=volatile) the evidence is already gone —"
  note "set Storage=persistent in /etc/systemd/journald.conf so the NEXT freeze is diagnosable."
  exit 1
fi

# ── 1. Did it die of memory? ────────────────────────────────────────────────
# This is the first question, because it is the most common cause of a total
# desktop lockup and the only one with a one-line fix.
hd "1. Out of memory"
_oom="$(jr -k --grep 'Out of memory|oom-kill|oom_reaper' | tail -20)"
if [[ -n "${_oom}" ]]; then
  bad "the kernel OOM killer fired on the previous boot:"
  printf '%s\n' "${_oom}" | sed 's/^/      /'
  note "By the time the KERNEL kills something the machine has usually already"
  note "been unresponsive for a while. earlyoom exists to act long before this."
else
  ok "no kernel OOM kills recorded"
  note "That does NOT rule memory out — a machine can thrash itself unusable"
  note "without the kernel ever completing an OOM kill. Check section 2."
fi

# ── 2. Was anything protecting it? ──────────────────────────────────────────
hd "2. OOM protection"
if systemctl is-active --quiet earlyoom 2>/dev/null; then
  ok "earlyoom is running now"
else
  bad "earlyoom is NOT running"
  _ey="$(systemctl status earlyoom 2>/dev/null | sed -n '1,6p')"
  [[ -n "${_ey}" ]] && printf '%s\n' "${_ey}" | sed 's/^/      /'
  note "Known cause: /etc/default/earlyoom passing '-N --avoid <regex>'. -N takes"
  note "an argument (the post-kill script), so earlyoom reads --avoid as that path"
  note "and refuses the command line. Fixed in the repo 2026-08-01; if this box"
  note "predates that, compare against:"
  note "  iso-builder/nyx-profile/airootfs/etc/default/earlyoom"
fi
if systemctl is-active --quiet systemd-oomd 2>/dev/null; then
  warn "systemd-oomd is ALSO running — two OOM daemons racing on different signals"
fi
_sw="$(free -h 2>/dev/null | awk '/^Swap:/{print $2}')"
if [[ "${_sw}" == "0B" || -z "${_sw}" ]]; then
  warn "no swap configured — memory pressure turns into a hard stall with no warning"
else
  ok "swap: ${_sw}"
fi
free -h 2>/dev/null | sed 's/^/      /'

# ── 3. GPU ──────────────────────────────────────────────────────────────────
# Hybrid Intel+NVIDIA is this project's target hardware and NVRM Xid errors are
# a classic total-lockup cause that leaves nothing else in the log.
hd "3. GPU faults"
_gpu="$(jr -k --grep 'NVRM|Xid|nouveau|i915.*(error|hang|reset)|GPU HANG|drm.*(error|timeout)' | tail -15)"
if [[ -n "${_gpu}" ]]; then
  bad "GPU errors on the previous boot:"
  printf '%s\n' "${_gpu}" | sed 's/^/      /'
  note "An Xid or a GPU hang on hybrid graphics can lock the whole session with"
  note "no other symptom. Note the Xid number — it identifies the fault class."
else
  ok "no GPU faults recorded"
fi

# ── 4. Thermal ──────────────────────────────────────────────────────────────
hd "4. Thermal"
_th="$(jr -k --grep 'thermal|Core temperature|critical temperature|throttl' | tail -10)"
if [[ -n "${_th}" ]]; then
  warn "thermal events on the previous boot:"
  printf '%s\n' "${_th}" | sed 's/^/      /'
else
  ok "no thermal events recorded"
fi

# ── 5. What was actually running ────────────────────────────────────────────
# A bake, a model and ten containers at once is the realistic worst case on
# this machine, and all three are avoidable at the same time.
hd "5. Heavy load at the time"
_heavy=0
if jr --grep 'mkarchiso|mksquashfs' | tail -3 | grep -q .; then
  bad "a BAKE was running on the previous boot"
  note "mksquashfs uses zstd -19 over a ~7 GB tree and takes every core it can."
  note "build-iso.sh now refuses to start one without checking free memory first."
  _heavy=1
fi
if systemctl is-active --quiet ollama 2>/dev/null; then
  warn "ollama is running now — a loaded model is GBs of resident memory"; _heavy=1
fi
if command -v docker >/dev/null 2>&1; then
  _n="$(docker ps -q 2>/dev/null | wc -l)"
  (( _n > 0 )) && { warn "${_n} docker container(s) running now (honeypot stack is ten)"; _heavy=1; }
fi
for u in bifrost-guardian jett-daemon; do
  systemctl is-active --quiet "${u}" 2>/dev/null && { warn "${u} is running now"; _heavy=1; }
done
(( _heavy == 0 )) && ok "no known heavy workload running right now"

# ── 6. The session itself ───────────────────────────────────────────────────
hd "6. Compositor and session"
_hy="$(jr --grep 'Hyprland.*(crash|segfault|abort)|hyprlock|hyprpm' | tail -10)"
if [[ -n "${_hy}" ]]; then
  warn "compositor / lock events on the previous boot:"
  printf '%s\n' "${_hy}" | sed 's/^/      /'
  note "hyprlock has stranded this session three times before — the standing rule"
  note "in HANDOFF.md is that only the owner runs it, never an agent."
else
  ok "no compositor crash or lock events recorded"
fi
_seg="$(jr --grep 'segfault|general protection|traps:' | tail -10)"
[[ -n "${_seg}" ]] && { warn "segfaults on the previous boot:"; printf '%s\n' "${_seg}" | sed 's/^/      /'; }

# ── 7. Disk ─────────────────────────────────────────────────────────────────
hd "7. Disk pressure"
df -h / /home 2>/dev/null | sed 's/^/      /'
_full="$(df --output=pcent / 2>/dev/null | tail -1 | tr -dc '0-9')"
if [[ -n "${_full}" ]] && (( _full >= 90 )); then
  bad "root filesystem is ${_full}% full — this alone can wedge a desktop"
else
  ok "root filesystem has headroom"
fi
_io="$(jr -k --grep 'I/O error|EXT4-fs error|BTRFS error|ata[0-9]+.*failed|nvme.*(timeout|reset)' | tail -10)"
[[ -n "${_io}" ]] && { bad "storage errors on the previous boot:"; printf '%s\n' "${_io}" | sed 's/^/      /'; }

# ── 8. The last thing it said ───────────────────────────────────────────────
# A hard lockup usually ends mid-sentence. The final lines are often the only
# direct evidence of what the machine was doing when it stopped.
hd "8. Final 25 lines before the machine stopped"
jr -n 25 --no-pager | sed 's/^/      /'

printf '\n%s%s%s\n' "${B}" "Nothing above was modified. See scripts/nyxus-reclaim.sh for cleanup." "${R}"

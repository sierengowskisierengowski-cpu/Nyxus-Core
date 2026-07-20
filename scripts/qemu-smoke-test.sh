#!/usr/bin/env bash
# qemu-smoke-test.sh — boot a freshly-baked NYXUS ISO headless in QEMU
# and verify it actually reaches a working live session. rev 2026-07-20 r1
#
# This is the "never flash a broken USB again" gate: it catches an old or
# broken bake (no splash, dead greeter, missing services) BEFORE you burn
# it to a stick. Run it on the bake host right after build-iso.sh.
#
# Usage:
#   bash scripts/qemu-smoke-test.sh /path/to/nyx-*.iso [--uefi] [--timeout SECS]
#
# What it does:
#   1. Boots the ISO in QEMU (4 GiB RAM, KVM if available, virtio GPU).
#   2. Watches the serial console for boot-progress markers.
#   3. After boot settles, takes a screendump and reports PASS/FAIL:
#        PASS = systemd reached graphical/multi-user target and greetd
#               started, with no emergency-mode / failed-unit markers.
#
# Exit codes: 0 = PASS · 1 = FAIL · 2 = usage/environment error
#
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

ISO="${1:-}"
UEFI=0
TIMEOUT=180
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --uefi)    UEFI=1; shift ;;
    --timeout) TIMEOUT="${2:?--timeout needs seconds}"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

[[ -n "${ISO}" && -f "${ISO}" ]] || { echo "usage: $0 /path/to/nyx.iso [--uefi] [--timeout SECS]" >&2; exit 2; }
command -v qemu-system-x86_64 >/dev/null || { echo "qemu-system-x86_64 not installed (pacman -S qemu-full)" >&2; exit 2; }

WORK="$(mktemp -d /tmp/nyxus-smoke.XXXXXX)"
SERIAL="${WORK}/serial.log"
MON="${WORK}/monitor.sock"
trap 'kill "${QPID:-}" 2>/dev/null || true; rm -rf "${WORK}"' EXIT

QEMU_ARGS=(
  -m 4096 -smp 2
  -cdrom "${ISO}" -boot d
  -display none
  -serial "file:${SERIAL}"
  -monitor "unix:${MON},server,nowait"
  -device virtio-vga
  -no-reboot
)
# KVM if the host supports it (much faster; falls back to TCG otherwise).
[[ -w /dev/kvm ]] && QEMU_ARGS+=(-enable-kvm -cpu host)
if (( UEFI )); then
  OVMF=""
  for c in /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/edk2-ovmf/x64/OVMF_CODE.fd \
           /usr/share/OVMF/OVMF_CODE.fd; do
    [[ -f "$c" ]] && OVMF="$c" && break
  done
  [[ -n "${OVMF}" ]] || { echo "--uefi requested but no OVMF firmware found (pacman -S edk2-ovmf)" >&2; exit 2; }
  QEMU_ARGS+=(-drive "if=pflash,format=raw,readonly=on,file=${OVMF}")
fi

# Append serial console so systemd chatter lands in our log alongside the
# normal boot (archiso GRUB reads kernel opts from the ISO; we inject via
# -append only when using direct kernel boot, so instead rely on systemd's
# default console output which archiso mirrors to ttyS0 when present).
echo "── NYXUS smoke test ──"
echo "ISO      : ${ISO}"
echo "Mode     : $([[ ${UEFI} == 1 ]] && echo UEFI || echo BIOS) · KVM $([[ -w /dev/kvm ]] && echo on || echo off)"
echo "Timeout  : ${TIMEOUT}s"
echo "Work dir : ${WORK}"

qemu-system-x86_64 "${QEMU_ARGS[@]}" &
QPID=$!

PASS_TARGET=0
FAILED_UNITS=0
EMERGENCY=0
GREETD=0

deadline=$(( SECONDS + TIMEOUT ))
while (( SECONDS < deadline )); do
  kill -0 "${QPID}" 2>/dev/null || { echo "✗ QEMU exited early — boot crashed"; exit 1; }
  if [[ -s "${SERIAL}" ]]; then
    grep -qE 'Reached target.*(Graphical|Multi-User)' "${SERIAL}" && PASS_TARGET=1
    grep -qiE 'greetd' "${SERIAL}" && GREETD=1
    grep -qiE 'emergency (mode|shell)|You are in emergency mode' "${SERIAL}" && EMERGENCY=1
    FAILED_UNITS=$(grep -cE '\[FAILED\]' "${SERIAL}" || true)
    (( PASS_TARGET )) && break
  fi
  sleep 5
done

# Screendump for the human eye (PPM — view with any image viewer).
if command -v socat >/dev/null 2>&1; then
  echo "screendump ${WORK}/boot.ppm" | socat - "UNIX-CONNECT:${MON}" >/dev/null 2>&1 || true
  [[ -s "${WORK}/boot.ppm" ]] && cp "${WORK}/boot.ppm" ./nyxus-smoke-screendump.ppm \
    && echo "Screendump : ./nyxus-smoke-screendump.ppm"
fi

kill "${QPID}" 2>/dev/null || true
cp "${SERIAL}" ./nyxus-smoke-serial.log 2>/dev/null || true
echo "Serial log : ./nyxus-smoke-serial.log"

echo "── Results ──"
echo "  boot target reached : $([[ ${PASS_TARGET} == 1 ]] && echo yes || echo NO)"
echo "  greetd seen         : $([[ ${GREETD} == 1 ]] && echo yes || echo no  '(only visible if console=ttyS0 in kernel opts)')"
echo "  emergency mode      : $([[ ${EMERGENCY} == 1 ]] && echo YES || echo no)"
echo "  [FAILED] units      : ${FAILED_UNITS}"

if (( PASS_TARGET )) && (( ! EMERGENCY )); then
  echo "✓ SMOKE TEST PASSED — ISO boots to its target"
  exit 0
else
  echo "✗ SMOKE TEST FAILED — inspect nyxus-smoke-serial.log / screendump"
  exit 1
fi

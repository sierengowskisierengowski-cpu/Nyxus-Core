#!/usr/bin/env bash
# NYXUS · kernel module audit (read-only, safe on live system)
# Captures lsmod baseline + hardware hints for lean mkinitcpio / future
# linux-nyx config. Does NOT blacklist or unload modules.
set -u

OUT="${XDG_CACHE_HOME:-$HOME/.cache}/nyxus-kernel"
TS="$(date +%Y%m%d-%H%M%S)"
REPORT="${OUT}/module-audit-${TS}.txt"
mkdir -p "$OUT"

{
  echo "NYXUS kernel module audit · $(date -Iseconds)"
  echo "kernel: $(uname -r)"
  echo "machine: $(cat /sys/class/dmi/id/product_name 2>/dev/null || echo unknown)"
  echo ""
  echo "── loaded modules ($(lsmod | tail -n +2 | wc -l)) ──"
  lsmod
  echo ""
  echo "── GPU / display ──"
  lsmod | grep -iE 'nvidia|i915|drm' || true
  echo ""
  echo "── network / wifi ──"
  lsmod | grep -iE 'iwl|wifi|bluetooth|btusb|r8169' || true
  echo ""
  echo "── audio ──"
  lsmod | grep -iE 'snd|sof' || true
  echo ""
  echo "── storage ──"
  lsmod | grep -iE 'nvme|usb_storage' || true
  echo ""
  echo "── MSI / platform ──"
  lsmod | grep -iE 'msi|wmi|thunderbolt' || true
  echo ""
  echo "── mkinitcpio (live) ──"
  grep -E '^MODULES|^HOOKS' /etc/mkinitcpio.conf 2>/dev/null || echo "(no /etc/mkinitcpio.conf)"
  echo ""
  echo "── NYXUS ISO recipe (reference) ──"
  grep -E '^MODULES|^HOOKS' "${NYXUS_REPO:-$HOME/Nyxus-Core}/iso-builder/nyx-profile/airootfs/etc/mkinitcpio.conf" 2>/dev/null || true
} > "$REPORT"

echo "wrote $REPORT"
echo "loaded modules: $(lsmod | tail -n +2 | wc -l)"
echo "module files available: $(find "/lib/modules/$(uname -r)" -name '*.ko*' 2>/dev/null | wc -l)"

#!/usr/bin/env bash
# ============================================================
#  NYXUS — fix NVIDIA suspend/resume on the LIVE machine (Phase 4.3)
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  The GS77's nvidia-suspend/resume/hibernate services are DISABLED on the
#  live install (the ISO already enables them; the installed system didn't).
#  On an Optimus laptop that's a common cause of black-screen / broken resume.
#  This enables the services and sets NVreg_PreserveVideoMemoryAllocations so
#  the dGPU's VRAM survives sleep.
#
#  Prepared, NOT auto-run — deploy after the greetd login is verified stable
#  (we don't stack changes on an unverified login). Run once:
#      sudo scripts/nyxus-fix-nvidia-suspend.sh
# ============================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "run: sudo $0"; exit 1; fi

echo "▌ NVIDIA suspend/resume fix"

install -Dm644 /dev/stdin /etc/modprobe.d/nvidia-power.conf <<'EOF'
# NYXUS — preserve dGPU VRAM across suspend/hibernate (rev 2026-07-14)
options nvidia NVreg_PreserveVideoMemoryAllocations=1 NVreg_TemporaryFilePath=/var/tmp
EOF
echo "  ✓ /etc/modprobe.d/nvidia-power.conf"

systemctl enable nvidia-suspend.service nvidia-resume.service nvidia-hibernate.service
echo "  ✓ enabled nvidia-suspend / resume / hibernate services"

echo "  · rebuilding initramfs so the modprobe option is picked up..."
mkinitcpio -P

cat <<EOF

── done. Test after next boot:  systemctl suspend  (then wake) ───────
Expect a clean resume with the desktop + CUDA (jeTT) intact — no black
screen. If resume still fails, capture: journalctl -b -1 -e | grep -i nvidia
──────────────────────────────────────────────────────────────────────
EOF

# NYXUS · Kernel + ISO Build Path

Phased guide for the MSI GS77 (MS-17P1) lean kernel and custom ISO stack.
Complements [NYXUS_BUILD.md](NYXUS_BUILD.md).

## Hardware reference

Canonical profile: `artifacts/nyxus-config/hw_profiles/gs77-ms17p1-cosmic.json`

| Component | Value |
|-----------|-------|
| Board | MSI MS-17P1 (GS77) |
| CPU | Intel i7-12700H (Alder Lake-P, 20 threads) |
| iGPU | Intel Iris Xe (`i915`) |
| dGPU | NVIDIA RTX 3060 Mobile (`nvidia-open`) |
| WiFi | Intel CNVi (`iwlwifi`) |
| Ethernet | Realtek Killer E3000 (`r8169`) |

Hyprland NVIDIA env vars live in `hyprland.conf` and the ISO airootfs skel.

## What ships today

| Layer | Status | Location |
|-------|--------|----------|
| ISO builder | ✅ | `iso-builder/build-iso.sh` |
| Archiso profile | ✅ | `iso-builder/nyx-profile/` (~301 packages) |
| mkinitcpio i915-first | ✅ repo | `nyx-profile/airootfs/etc/mkinitcpio.conf` |
| nvidia_drm modeset | ✅ repo | `nyx-profile/airootfs/etc/modprobe.d/nvidia.conf` |
| nyxus-postinstall | ✅ | copies boot configs on disk install |
| nyxus-kernel-switch | ✅ | stock `linux` / `linux-lts` / `linux-zen` / `linux-hardened` |
| Custom `linux-nyx` PKGBUILD | ❌ | not started |
| Module trim script | ✅ read-only | `scripts/nyxus-kernel-module-audit.sh` |

**Bifrost / jeTT** are optional deepcore probes — not bundled in the daily-driver ISO.

## Phase 0 — Boot config alignment (live GS77, user approval)

Apply NYXUS hybrid-graphics boot recipe on the installed system:

```bash
sudo cp iso-builder/nyx-profile/airootfs/etc/mkinitcpio.conf /etc/mkinitcpio.conf
sudo cp iso-builder/nyx-profile/airootfs/etc/modprobe.d/nvidia.conf /etc/modprobe.d/nvidia.conf
sudo mkinitcpio -P
# reboot and verify: lsmod | grep -E 'i915|nvidia'
```

## Phase 1 — Lean ISO tier

Set `NYX_ISO_TIER=lean` when baking to use `packages.x86_64.lean` (drops extra
kernels, gaming, virt, duplicate browsers — saves ~1–2 GB squashfs).

```bash
NYX_ISO_TIER=lean ./iso-builder/build-iso.sh
```

## Phase 2 — Module audit (before custom kernel)

Capture loaded modules after exercising all hardware (WiFi, BT, suspend, HDMI, dGPU):

```bash
nyxus-kernel-module-audit.sh   # read-only report under ~/.cache/nyxus-kernel/
```

Use output to tune `MODULES=` in mkinitcpio — not a full kernel rebuild.

## Phase 3 — Firmware subset

Replace monolithic `linux-firmware` with vendor subsets on lean ISO:
`linux-firmware-intel`, `linux-firmware-nvidia`, `linux-firmware-realtek`.

## Phase 4 — Custom `linux-nyx` (multi-session, user approval)

1. Fork Arch `linux` PKGBUILD with `CONFIG_LOCALVERSION=-nyx`
2. `make localmodconfig` on GS77 after module audit
3. Enable: `i915`, `nvidia` (or DKMS), `iwlwifi`, `snd_sof`, `nvme`, `r8169`, `msi_wmi`
4. CI build; optional `sbctl` UKI for Secure Boot

## Kernel-to-session matrix

| Layer | Repo | Live nyx-cosmic |
|-------|------|-----------------|
| Custom kernel | ❌ | stock `linux` |
| mkinitcpio MODULES order | ✅ ISO | user must apply Phase 0 |
| Hyprland NVIDIA env | ✅ | ✅ |
| EWW + Hypr session | ✅ | ✅ |
| hw_profile in git | ✅ | generated at runtime |

## Related commands

```bash
nyxus-build-iso.sh          # remote wrapper → build-iso.sh
nyxus-kernel-module-audit   # safe module baseline report
nyxus-verify-build          # session health (includes untangle)
nyxus-save-state            # backport live → artifacts
```

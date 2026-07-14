# NYXUS — Kernel (kage-ryu, selectable security kernel)

> **Status (2026-07-14): PREPARED, NOT DEPLOYED.** Recipe fixed and committed;
> holding the actual build/install/boot until the Nyxus greetd login is
> verified stable, so we don't stack an unbooted custom kernel on top of an
> unverified login change.

## What this is
`kage-ryu` is the operator's own security-lab kernel (separate repo:
`github.com/sierengowskisierengowski-cpu/kage-ryu`) — Linux + XanMod, tuned for
the MSI GS77 (i7-12700H / Alder Lake) and the jeTT eBPF EDR + Docker honeypot +
CUDA workload. Nyxus ships it as a **selectable** kernel: **stock `linux` stays
the default boot entry**, kage-ryu is chosen from the bootloader when you want
the security loadout. This guarantees a bad custom-kernel build can never
strand you.

## Recipe fixes applied (in the kage-ryu repo, commit `fix(kage-ryu)`)
- **microarch bug fixed:** `_microarchitecture=98` was a no-op (not in the
  option table → generic x64, all tuning discarded). Now **41 = Alder Lake**.
- **Security-lab "beast" config** added (all justified by the real workload in
  `../docs/MACHINE_PROFILE.md`): kprobes/uprobes/BPF_EVENTS + BTF_MODULES,
  userns/cgroup-bpf/overlayfs/CRIU/bridge/veth/vxlan (Docker), KVM(Intel)
  modules (malware VMs), BBR+FQ, MGLRU, THP(madvise), io_uring.
- Kept from before: HZ=1000, full PREEMPT, eBPF/WireGuard/NTFS3, and the strip
  list (ham radio/ISDN/ATM/PCMCIA/FireWire/NFC/InfiniBand).
- **CPU mitigations stay available** (operator runs untrusted code) — never
  hardcoded off.

## Base version note
Recipe base is XanMod **7.0.12** (proven — a built package exists). Live system
runs stock 7.1.3. Bumping kage-ryu to 7.1.x requires the matching XanMod patch +
a fresh `sha256sums` for the new tarball/patch — a networked build step, not a
blind edit. 7.0.12 fully supports the GS77 (DRM_XE, MSI_EC, iwlwifi all present),
so it's a fine baseline; bump when convenient. See install helper `--bump` note.

## Build + install (run LATER, after login is verified)
```bash
# Lean build (recommended): capture your real module set first, once,
# after exercising all hardware (wifi/bt/suspend/hdmi/dGPU):
#   pacman -S modprobed-db && sudo modprobed-db store   # populate ~/.config/modprobed.db
# Then:
sudo kernel/install-kage-ryu.sh          # builds + installs, adds selectable entry
# stock `linux` remains the default boot entry; pick "kage-ryu" at the bootloader.
```

## Files here
- `install-kage-ryu.sh` — builds kage-ryu from its repo (localmodconfig if a
  modprobed.db exists), installs the packages, regenerates the bootloader menu
  **without changing the default**, and prints how to select it.
- `nyxus-bbr.conf` — sysctl drop-in (BBR congestion control + FQ qdisc) that
  pairs with the kernel's `CONFIG_TCP_CONG_BBR`/`NET_SCH_FQ`. Deploy to
  `/etc/sysctl.d/`. Safe on stock kernel too.

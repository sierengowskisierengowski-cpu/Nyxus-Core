# NYXUS — Kernel ("Kage Ryu Nyxus", the primary/default security kernel)

> **Status (2026-07-23): PRIMARY KERNEL, BAKE-READY — not yet boot-verified.**
> The prebuilt `linux-kage-ryu-7.0.12` + headers packages exist at
> `~/Projects/arch-custom-kernel/linux-kage-ryu/`. As of 2026-07-23 Kage-Ryu is
> the **default** kernel: `build-iso.sh` bakes it by default and makes it the
> primary boot entry on both the live USB and the installed system, with stock
> `linux` kept as a rescue entry. Still needs one bake → boot to verify on
> real hardware.

## What this is
**Kage Ryu Nyxus** is the operator's own security-lab kernel — the
user-facing/display name for NYXUS's custom kernel build. The underlying
build recipe/package id stays `kage-ryu` / `linux-kage-ryu` (separate repo:
`github.com/sierengowskisierengowski-cpu/kage-ryu`) so pacman, the bootloader,
and `/usr/lib/modules/*-kage-ryu` module paths keep working unchanged — only
the human-facing name is "Kage Ryu Nyxus". It's Linux + XanMod, tuned for
the MSI GS77 (i7-12700H / Alder Lake) and the jeTT eBPF EDR + Docker honeypot +
CUDA workload. NYXUS ships it as the **primary/default** kernel: **Kage Ryu
Nyxus is the default boot entry** (live USB + installed system) so you run and
validate the real kernel, while **stock `linux` stays as a rescue entry** you
can pick from the bootloader — so a bad custom-kernel build can never strand you.

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

## Alternative kernels considered (trade-offs, for future-you)
Kage Ryu (custom XanMod) is a *signature*, Alder-Lake-tuned, security-configured
kernel — cool and bespoke, but it's a multi-GB compile, pinned to an old base
(7.0.12), and needs a manual rebuild on every bump. If maintenance/version-lag
ever outweighs the bespoke factor, these are the honest alternatives — all in the
official Arch repos (no compile, always current, auto-update with the system):
- **`linux-zen`** — the pragmatic sweet spot. ~90% of XanMod's desktop/low-latency
  benefit, full config (BPF/KVM/userns/overlayfs — everything the security tools
  need), zero maintenance. For "perf desktop + security tooling," this would have
  been the lower-effort choice with nearly the same result.
- **`linux-hardened`** — max *host* exploit-hardening, best if the priority is
  protecting the box that detonates malware. Caveat: the hardening can *interfere*
  with the offensive/analysis tooling (eBPF, containers, debuggers) and costs some
  performance. Since NYXUS already isolates malware in KVM VMs and keeps mitigations
  on, this is a defensible-but-not-required upgrade.
- **stock `linux`** — newest kernel = latest security patches, zero effort, has
  every needed option enabled. NYXUS keeps it installed as the **rescue** entry
  regardless, so you always have a known-good fallback.

None of these are wrong — the "right" one is a priority call: bespoke/tuned
(Kage Ryu) vs low-effort performance (`linux-zen`) vs max host hardening
(`linux-hardened`) vs simplest/newest (stock). As of 2026-07-23 NYXUS commits to
Kage-Ryu as the default and ships **only** it + stock (rescue); `linux-zen` /
`linux-hardened` were dropped from the ISO. To try one, `pacman -S linux-zen`
on a running system and pick it at the bootloader — nothing here prevents that.

## Two ways to get Kage Ryu Nyxus onto a machine

**A) Post-install, on a running NYXUS system (simplest — works today):**
```bash
# Lean build (recommended): capture your real module set first, once,
# after exercising all hardware (wifi/bt/suspend/hdmi/dGPU):
#   pacman -S modprobed-db && sudo modprobed-db store   # populate ~/.config/modprobed.db
# Then:
sudo kernel/install-kage-ryu.sh          # builds + installs, adds selectable entry
# stock `linux` remains the default boot entry; pick "Kage Ryu Nyxus" at the bootloader.
```

**B) Baked into the ISO (the default), so a fresh install already runs it:**
The kernel is a multi-GB, long compile and is NOT in any Arch repo, so
`build-iso.sh` never compiles it — you build the **package** once, then the
bake stages it. As of 2026-07-23 this is **ON by default**: a normal bake makes
Kage-Ryu the primary boot kernel and **hard-fails if the prebuilt package is
missing** (so it can never silently ship kernel-less). Opt out with
`NYX_WITH_KAGE_RYU=0` for a stock-only debug ISO.
```bash
# 1. Produce the package (either the full install helper above, which also
#    leaves the .pkg.tar.zst in the kage-ryu repo dir, or just:)
cd ~/Projects/arch-custom-kernel/linux-kage-ryu && makepkg -sc   # → linux-kage-ryu-*.pkg.tar.zst

# 2. Bake (Kage-Ryu is staged into the ISO's [nyxus-local] repo automatically):
sudo ./iso-builder/build-iso.sh
#   Override the package location with NYX_KAGE_PKGDIR=/dir/with/the/.pkg.tar.zst
#   Stock-only debug ISO:  NYX_WITH_KAGE_RYU=0 sudo ./iso-builder/build-iso.sh
```
The bake also makes Kage-Ryu the primary entry in all three live boot menus, and
the installed system's GRUB default is set to Kage-Ryu by Calamares
(`nyxus-set-grub-default-kage`); **stock `linux` remains as a rescue entry**.

## Optional build modes (bigger/meaner, higher cost)
The kage-ryu PKGBUILD already supports these env toggles — pick per build:
- **Leanest module set:** `pacman -S modprobed-db`, run `modprobed-db store`
  a handful of times across normal use (after wifi/bt/suspend/hdmi/dGPU), then
  build with `_localmodcfg=y`. Compiles only modules you actually load — big
  cut to build time and on-disk size. `install-kage-ryu.sh` auto-uses this if
  `~/.config/modprobed.db` exists.
- **Clang + ThinLTO:** `env _compiler=clang makepkg -sc` — a measurably faster
  kernel (whole-program opt). Costs longer build + pulls clang/llvm/lld.
- **Pure `-march=native`:** `env _microarchitecture=99` instead of the default
  41 (Alder Lake) — locks the binary to *this exact* CPU. 41 is portable across
  Alder Lake; 99 squeezes marginally more but only runs on this chip.

## Secure Boot (sbctl — already shipped in the ISO)
Kage Ryu Nyxus is an unsigned custom kernel, so it won't boot with Secure Boot ON
until signed. After install, before rebooting into it:
```bash
sudo sbctl sign -s /usr/lib/modules/*-kage-ryu/vmlinuz    # sign the image
sudo sbctl sign -s /boot/EFI/.../grubx64.efi              # if not already
sudo sbctl verify                                          # confirm all signed
```
Or leave Secure Boot off (stock `linux` still boots either way, so you're never
locked out). Documented here so it's not a surprise at the boot screen.

## Files here
- `install-kage-ryu.sh` — builds Kage Ryu Nyxus from its repo (localmodconfig if a
  modprobed.db exists), installs the packages, regenerates the bootloader menu
  **without changing the default**, and prints how to select it.
- `nyxus-bbr.conf` — sysctl drop-in (BBR congestion control + FQ qdisc) that
  pairs with the kernel's `CONFIG_TCP_CONG_BBR`/`NET_SCH_FQ`. Deploy to
  `/etc/sysctl.d/`. Safe on stock kernel too.

## Deliberately NOT done (honest calls)
- **No host nftables/ufw lockdown ruleset shipped.** This box runs a Docker
  honeypot fleet that *intentionally* exposes ports to attract attackers, and
  Docker manages its own iptables/nftables rules. A restrictive host firewall
  would fight the working setup and can silently break honeypot exposure or
  container networking. Firewall policy stays operator-driven, per-need.
- **CPU speculative-exec mitigations stay ON/available** — never hardcoded
  `mitigations=off`. This machine detonates malware and runs honeypots; the
  small perf gain isn't worth weakening a security lab. Adjustable per-boot.

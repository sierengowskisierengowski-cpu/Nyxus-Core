# NYXUS — Machine & Workflow Profile

> Captured 2026-07-14 from a read-only survey of the live machine, local
> projects, and GitHub. Purpose: drive a **lean-and-mean, security-focused**
> kernel + ISO tuned to what this operator *actually* does — not a generic
> workstation. Corrects the Phase 1 audit, which mis-flagged `kage-ryu` and
> `jeTT` as "separate experiments, not Nyxus" — they are **central to the
> build's identity**.

## Who this is for
A **security-lab builder**, not a generic desktop user. The daily driver runs
a live security stack while also being a Hyprland dev workstation. The ISO/
kernel should reflect that.

## Hardware (MSI GS77 · MS-17P1)
- CPU: Intel i7-12700H (Alder Lake-P, 20 threads)
- GPU: Intel Iris Xe (`xe` driver, live) + NVIDIA RTX 3060 Mobile (Optimus, `nvidia-open`)
- NVMe 1 TB · WiFi Intel CNVi (`iwlwifi`) · Realtek 2.5G eth · Goodix fingerprint · IR camera

## The stack (flagship, all real & mostly running now)
| Layer | Project | State |
|---|---|---|
| Custom OS/ISO | **Nyxus-Core** | active daily (this build) |
| AI EDR (userspace) | **jeTT** — Rust daemon + Granite GGUF (~1.5 GB q4) on CUDA | **running now** (`jett-daemon`, ~2.2 GB VRAM, systemd-enabled) |
| Security kernel | **kage-ryu** — Linux 7.0.12 + XanMod + eBPF sensor | **built, NOT booted / unfinished** |
| SOC dashboard | **Bifrost** (Python Guardian + Tauri) | `bifrost-guardian` running |
| Honeypot ops | **Meli** (GTK) + **honeypot** Docker farm (10 containers) | running (Cowrie/Dionaea/Conpot/Heralding/endlessh + Prometheus/Grafana/Loki) |
| Lineage | **Cerberus** (retired XDR) → meli(Rust) → **jeTT** | archived → current |

Loop: kage-ryu eBPF sensor → jeTT (AI verdict + PID quarantine) → Bifrost (dashboard/alerts).

## Daily loadout (what must "just work")
- **CUDA inference always-on** (jeTT). CUDA 13.3, cuDNN, NCCL, PyTorch-cuda, `nvidia-open` 610.
- **eBPF/BTF tooling**: bpftool, BCC, libbpf, rust-bindgen, clang bpf targets.
- **Docker-heavy**: 10 always-on honeypot/monitoring containers (bridge/overlay/netfilter/cgroups/namespaces).
- **Dev toolchains**: Rust 1.97, Python 3.14 (+3.11), Go 1.26, Node 26/pnpm, Clang/LLVM 22, GCC 16.
- **Security tools installed**: nmap, masscan, ffuf, gobuster, nikto, sqlmap, hydra, aircrack-ng, bettercap, metasploit, hashcat, john, tshark, audit, ufw, fail2ban, clamav, wireguard-tools.
- **MQTT** (mosquitto), sshd, prometheus-node-exporter — all enabled.
- Hyprland/NYXUS Wayland desktop + custom daemons.

## Lean-and-mean kernel targets (for kage-ryu / NYX ISO)
**MUST KEEP:** full eBPF + BTF + BPF_LSM, kprobes/uprobes/tracepoints/perf, `DEBUG_INFO_BTF`(+BTF_MODULES), Docker trinity (cgroups/namespaces/bridge/veth/overlayfs), netfilter+nftables+conntrack, AUDIT, WireGuard, NTFS3, `DRM_I915`/`xe` + NVIDIA (modules), HZ=1000 + preempt, IO_uring, MODULE support, KVM (as modules).

**SAFE TO STRIP for this user:** ham radio, ISDN, ATM, PCMCIA, FireWire, NFC, InfiniBand (already done in kage-ryu); AMD GPU stack + nouveau; exotic/legacy DRM panels; most non-x86 QEMU firmware (ISO bloat); IPVS scheduler suite; excess netfilter xt modules; CAN/WWAN/most staging; unused built-in LSMs (SELinux/SMACK/TOMOYO — active LSM is bpf/landlock/yama). Bluetooth: **keep** (BT service is active).

## kage-ryu finish-work (known gaps found in its config.last/PKGBUILD)
1. `_microarchitecture=98` is not in the gcc-opt case table → falls back generic. Alder Lake wants **41 (`MALDERLAKE`)** or **99 (native)**.
2. README/PKGBUILD claim full `CONFIG_PREEMPT`, but `config.last` has `PREEMPT_LAZY`. Pick one (full preempt favors EDR latency).
3. Tracers: PKGBUILD default off, config.last has FTRACE on — decide (security research wants them).
4. Base is 7.0.12; live is 7.1.3 — bump toward current before shipping.
5. Not yet booted — must validate the eBPF sensor loop on the custom kernel on real hardware before relying on it.
6. Consider `modprobed-db` localmodconfig for a genuinely lean module set (big ISO/build-time win).

## Integration plan (see brief §8 + Phase 4)
- Ship **kage-ryu as a SELECTABLE kernel** (bootloader entry) — stock `linux` stays the safe default.
- Ship the **"GowskiNet security loadout"** (jeTT + kage-ryu sensor + Bifrost) as an **opt-in** module with a Hub toggle — not baked into the base, keeps the daily driver stable and the ISO lean.
- Deployed jeTT footprint is modest (Rust daemon + ~1.5 GB q4 GGUF); the 82 GB on disk is dev/training bulk that never ships.

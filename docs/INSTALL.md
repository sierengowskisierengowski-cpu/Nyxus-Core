# Installing NYXUS

NYXUS has **two** install paths. Pick the one that matches your situation.

| Path | Use when | Entry point |
|------|----------|-------------|
| **Bootstrap (rice)** | You already run Arch and want the NYXUS desktop on it | `install.sh` |
| **NYX ISO (bare metal)** | Fresh install on a new/wiped machine | `iso-builder/build-iso.sh` → flash → install |

---

## 1. Bootstrap install (onto an existing Arch system)

Dotfiles/rice-style: clone the repo, run one script, get a working NYXUS
Hyprland desktop. `install.sh` is the canonical entry point: it cleans stale
NYXUS-managed user files with backup, redeploys the user surfaces, then runs
the system phase (packages / greeter / session cleanup / verify).

```bash
git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core
cd Nyxus-Core
./install.sh --check     # preview the full plan, change nothing
./install.sh             # full clean deploy
```

### What the base run does
1. **Preflight** — confirms Arch, that you're a normal user (not root), and the package list exists.
2. **Purge with backup** — moves stale NYXUS-managed files out of `~/.config/hypr`, `~/.config/eww`, `~/.nyxus`, `~/.local/bin/nyxus-*`, and `~/.local/share/applications/nyxus-*.desktop` into `~/.nyxus-backup-<timestamp>/`.
3. **Preserve user-owned state** — leaves `~/.config/nyxus`, `nyxus-monitors.conf`, and extra wallpapers in `~/.config/hypr/walls/rotation` untouched.
4. **User deploy** — places the canonical hypr/eww configs, launchers, app suite, desktop entries, and wallpaper rotation set.
5. **System phase** — delegates to `scripts/nyxus-install.sh --yes --skip-user-config` for packages, greeter/session repair, default-session pinning, and build verification.
6. **Verification summary** — reports backup location, session cleanup/default-session status, and managed-file checksum parity.

### Flags
| Flag | Effect |
|------|--------|
| `--dry-run` | Print the full plan and change nothing (recommended first run). |
| `--user-only` | Skip the system phase and deploy only the cleaned user surfaces (does not install or touch system security components such as jeTT/Bifrost/Meli services). |
| `--no-reload` | Do not reload a running Hyprland session after deploy. |
| `--keep-legacy-sessions` | Preserve old `qtile.desktop` / stock Hyprland session entries instead of removing them. |

### Safety notes
- **Idempotent** — safe to re-run; once the system is clean, no new backup dir is created.
- The default run now includes greeter/session repair so the login path matches
  the current NYXUS build after one command.
- Enable the `multilib` repo (in `/etc/pacman.conf`) before installing if you
  want the 32-bit Steam/Proton bits; otherwise those `lib32-*` packages are
  cleanly skipped.
- `scripts/nyxus-install.sh` remains available as the advanced system-phase
  entry point (`--skip-user-config`, `--no-greeter`, kernel/NVIDIA/loadout flags).

---

## 2. NYX ISO (bare-metal install)

For a fresh machine. Built with `mkarchiso` on an Arch host:

```bash
sudo ./iso-builder/build-iso.sh                 # full tier → iso-builder/out/
NYX_ISO_TIER=lean sudo ./iso-builder/build-iso.sh   # lean tier (smaller)
```

Flash the ISO (Ventoy / `dd`), boot it, and run the installer. On disk,
`nyxus-postinstall` runs in the new root's chroot to install the hardware
package set, drop the NYXUS boot config (early-KMS `i915`/`nvidia`,
`NVreg_PreserveVideoMemoryAllocations`), enable services, and deploy the NYXUS
chrome from the offline cache. The ISO greeter is **greetd + regreet**
(Wayland) with a `tuigreet` text fallback — see `docs/NYXUS_BUILD_BRIEF.md` §1.1.

---

## Related docs
- `docs/NYXUS_BUILD_BRIEF.md` — the living build plan.
- `docs/MACHINE_PROFILE.md` — hardware/workflow this build targets.
- `docs/KERNEL_ISO.md` — kernel + ISO build detail.
- `kernel/README.md` — the selectable `kage-ryu` kernel.
- `docs/KEYBINDS.md` — keybind reference.

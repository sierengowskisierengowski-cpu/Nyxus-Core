# Installing NYXUS

NYXUS has **two** install paths. Pick the one that matches your situation.

| Path | Use when | Entry point |
|------|----------|-------------|
| **Bootstrap (rice)** | You already run Arch and want the NYXUS desktop on it | `scripts/nyxus-install.sh` |
| **NYX ISO (bare metal)** | Fresh install on a new/wiped machine | `iso-builder/build-iso.sh` → flash → install |

---

## 1. Bootstrap install (onto an existing Arch system)

Dotfiles/rice-style: clone the repo, run one script, get a working NYXUS
Hyprland desktop. It **orchestrates** the existing, tested pieces (config
restore, greeter, kernel, verify) rather than reimplementing them.

```bash
git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core
cd Nyxus-Core
./scripts/nyxus-install.sh --dry-run     # preview the full plan, change nothing
./scripts/nyxus-install.sh               # base desktop (packages + configs + apps)
```

### What the base run does
1. **Preflight** — confirms Arch, that you're a normal user (not root), and the package list exists.
2. **Packages** — installs the profile package set with `pacman -S --needed`. Entries not in your enabled repos (AUR pkgs, `lib32-*` with multilib off) are **skipped, not fatal**, and reported.
3. **Configs** — runs `nyxus-restore-desktop.sh`, which **backs up** your current `~/.config/{hypr,eww,rofi,dunst,wlogout,alacritty,nyxus}` first, then places the canonical hypr/eww/rofi/dunst configs, stations, wallpapers, and helper launchers.
4. **App suite** — copies the ~40 NYXUS GTK apps into `~/.nyxus/` and generates `~/.local/bin/nyxus-*` launchers.
5. **Verify** — runs `nyxus-verify-build.sh`.

Then log out and pick **NYXUS (Hyprland)** at your login screen.

### Flags
| Flag | Effect |
|------|--------|
| `--dry-run` | Print the full plan and change nothing (recommended first run). |
| `--yes`, `-y` | Skip the confirmation prompt (for automation). |
| `--lean` / `--full` | Use `packages.x86_64.lean` / `.x86_64` (default: full). |
| `--greeter` | **Opt-in.** Switch the login to greetd + regreet (`nyxus-setup-greetd.sh`). |
| `--nvidia-suspend` | **Opt-in.** Fix Optimus suspend/resume (`nyxus-fix-nvidia-suspend.sh`). |
| `--kernel` | **Opt-in.** Build + install the `kage-ryu` kernel as a *selectable* entry (stock stays default). Long build. |
| `--loadout` | **Opt-in.** Install the GowskiNet security loadout (jeTT / kage-ryu sensor / Bifrost) — see brief §8.1. |
| `--all` | Base + every opt-in above. |

### Safety notes
- **Idempotent** — safe to re-run; the config phase backs up each time.
- The **greeter/kernel/loadout are never run by default** — they change the
  login path or install a custom kernel, so they're explicit opt-ins. Make
  sure you can reach a TTY (`Ctrl+Alt+F2`) before using `--greeter`.
- Enable the `multilib` repo (in `/etc/pacman.conf`) before installing if you
  want the 32-bit Steam/Proton bits; otherwise those `lib32-*` packages are
  cleanly skipped.

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

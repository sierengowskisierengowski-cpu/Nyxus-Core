# NYXUS ISO — full hands-on VM audit · 2026-07-31 / 2026-08-01

**ISO under test:** `iso-builder/out/nyxus-2026.07.31-x86_64.iso`
**`/etc/nyxus-build` stamp (read inside the VM):**

```
iso            : nyxus-2026.07.31-x86_64.iso
built          : 2026-07-31 16:52:09 EDT
source commit  : 0f77d1c2  (branch: main)
kernel baked   : kage-ryu (default) + stock linux (rescue)
iso label      : NYXUS_2026_07
```

Stamp matches the expected `0f77d1c2`. Audit is against the correct image.

**Harness.** QEMU/KVM, q35, 8 GB RAM, 6 vCPU, `virtio-vga-gl` at 1920x1080,
`egl-headless` + VNC on `127.0.0.1:8`. Screenshots taken with `gvnccapture`
(native 1920x1080, no scaling). Input driven over QMP (`send-key`,
`input-send-event` with a USB tablet for absolute pointer). Shell inside the
guest via a TTY2 login plus an HTTP relay to the host on `10.0.2.2:9000`, so
every "measured" number below is a real command run inside the live session,
not a value read out of the repo.

Evidence screenshots live in `/home/cosmic/nyxus-vmaudit/shots/` on the build
box (not committed — they are ~4 MB each).

**Two boots were used.** Boot A (03:25 UTC) was the untouched shipped
configuration and is what the PASS/FAIL calls below describe. Boot B (03:38
UTC) is the same image with the live overlay hand-resized
(`mount -o remount,size=6G /run/archiso/cowspace`) so that the rest of the
click-audit would not be poisoned by a full filesystem — see FS-01.

---

## Legend

| Mark | Meaning |
| --- | --- |
| PASS | Exercised in the VM and behaved correctly |
| FAIL | Exercised in the VM and misbehaved |
| NOT-TESTED | Could not be exercised, with the reason stated |

---

## 1. Boot chain

| # | Item | Result | Evidence / notes |
| --- | --- | --- | --- |
| B-01 | ISO boots on BIOS/SeaBIOS | PASS | Cold boot to greeter in ~20 s wall clock. |
| B-02 | BIOS boot **menu** visible / selectable | **FAIL** | `boot/syslinux/syslinux.cfg` in the ISO has `PROMPT 0` and **no `UI menu.c32` / `UI vesamenu.c32` directive**, so syslinux renders no menu at all. The three `MENU LABEL` entries (Kage Ryu, Kage Ryu safe, stock rescue) are inert. A BIOS user cannot reach the safe/no-KMS or rescue kernel. `vesamenu.c32`, `menu.c32`, `libcom32.c32` and `libutil.c32` *are* all present in the ISO, so this is a config omission, not a missing module. |
| B-03 | UEFI GRUB menu visible | **FAIL** | Booted via OVMF. The GRUB theme background renders but **no menu entries or labels draw**. `boot/grub/grub.cfg` sets `theme=${prefix}/themes/nyxus/theme.txt`; the theme's `boot_menu` / `terminal-box` styling references pixmap slices that are not all shipped, so GRUB silently drops the menu widget. GRUB itself is live (the `e` editor responds). |
| B-04 | Kage-Ryu kernel is the default | PASS | `uname -r` inside the live session → `7.0.12-alderlake-xanmod1-1kage-ryu`. |
| B-05 | Plymouth boot splash | PASS | Animated NYXUS saucer over a nebula, wordmark fades up to "WELCOME TO THE DARKSIDE". Clean, no text fallback, no flicker. |
| B-06 | `cow_spacesize` set on any boot path | **FAIL** | Not present in `syslinux.cfg`, `grub.cfg`, or `efiboot/loader/entries/01-nyx.conf`. See FS-01 — this is the single highest-impact defect found. |
| B-07 | Splash → greeter time | PASS | ~13–20 s. The old ~102 s splash→login complaint is **not** reproducible; the delay that remains is after the greeter, see SD-01. |

## 2. Filesystem / live media

| # | Item | Result | Evidence / notes |
| --- | --- | --- | --- |
| FS-01 | Live overlay survives first boot | **FAIL (critical)** | Measured in the VM on the shipped config: `df -h /` → `airootfs 256M 256M 0 100% /`. The live overlay is exhausted roughly 4 minutes into the first session. Root cause is arithmetic, not a leak: `/etc/skel` in the squashfs is **162 MB**, it is copied into `/home/nyx` at first login, first-boot writes take that to **254 MB**, and the archiso default `cow_spacesize` is **256 MB**. Breakdown measured in-guest: `/home/nyx` 254 MB (`.config/hypr` 114 MB, `.config/eww` 55 MB, `.cache/pip` 66 MB), `/var/lib` 116 MB, `/var/log` 34 MB. Everything downstream — app launches, thumbnail caches, logs, the bootstrap itself — is running against a full disk. |
| FS-02 | Enlarging the overlay resolves it | PASS | `sudo mount -o remount,size=6G /run/archiso/cowspace` inside the guest took `/` from `256M 100%` to `6.0G 1%`, and the session became stable. This is the direct proof that `cow_spacesize` is the correct fix. |
| FS-03 | pip cache left behind by bootstrap | **FAIL (minor)** | `~/.cache/pip` measured at **66 MB** after first boot — a quarter of the entire default overlay, spent on a cache nothing reads again. |
| FS-04 | First-boot bootstrap compiles Hyprland plugins on the live system | **FAIL** | `journalctl` shows `hyprpm` running `make installheaders` and installing `borders-plus-plus.so`, `csgo-vulkan-fix.so`, `hyprbars.so`, `hyprfocus.so` between 03:26 and 03:27 of the first session. Load average hit **8.72**. Compiling out-of-tree compositor plugins during the user's first 90 seconds on live media is what makes the first boot feel broken, and it writes into the same 256 MB overlay. |

## 3. Greeter (regreet)

| # | Item | Result | Evidence / notes |
| --- | --- | --- | --- |
| G-01 | Greeter renders with ALIEN NEON theming | PASS | Frosted card, violet border, `welcome back, operator` header, monospace fields. Looks finished. |
| G-02 | Login card position | PASS | Measured on the 1920x1080 framebuffer: card occupies x 1336–1899, y 398–668. It does **not** run off-screen and does **not** cover the alien. The `margin-left: 1360px` + DRM rescale is correct at this resolution. |
| G-03 | Wallpaper on greeter | PASS | `nyxus-login-wall` alien renders full-bleed, correct palette. |
| G-04 | Clock / date widget | PASS | Top-right `03:20 · Saturday · August 01`. Renders, updates. (Shows UTC in the VM because the live image has no timezone set — cosmetic, not tested against a real install.) |
| G-05 | Reboot / Power Off buttons present | PASS | Bottom-centre, violet outlined, fully on-screen (not clipped). |
| G-06 | Default user | **FAIL** | Greeter preselects **`nyxbuild`**, the ISO *build* account. Confirmed twice, on two separate boots, and it does **not** remember `nyx` after a successful `nyx` login. |
| G-07 | `nyxbuild` offered as a login option at all | **FAIL** | Opening the user dropdown lists exactly two accounts: `nyxbuild` and `nyx`. The build user has leaked into the shipped image with a UID ≥ 1000, a home directory and a login shell, so regreet enumerates it. It should not exist on the shipped ISO. |
| G-08 | Default session | **FAIL** | Preselects plain **`Hyprland`** (and on the second boot `Hyprland (uwsm-managed)`). A first-time user who just types their password gets a bare upstream compositor, not NYXUS. |
| G-09 | Session list contents | **FAIL** | Three entries offered: `Hyprland`, `Hyprland (uwsm-managed)`, `NYXUS (Hyprland)`. The two upstream entries ship from the `hyprland` package and should be suppressed on a product image — only `NYXUS (Hyprland)` is a supported session. |
| G-10 | User dropdown opens and selects | PASS | Popover opens, both users listed, selection applies. |
| G-11 | Session dropdown opens and selects | PASS | Popover opens, selection applies, selected row floats to the top of the list on reopen. |
| G-12 | Password stage | PASS | Appears after Login, has a reveal (eye) toggle and a Cancel button, both themed. `nyx` / `nyx` authenticates. |
| G-13 | Manual-username pencil buttons | NOT-TESTED | Present and themed; not exercised because the dropdown path already worked and the audit needed the session. |
| G-14 | Focus ring colour reads as an error | FAIL (polish) | Focused dropdowns and the Login button fill with `#ff2d55` crimson, which is the same red used for the "wrong password" affordance elsewhere. It is in the locked palette but it makes a normal keyboard-focused field look like a validation failure. |
| G-15 | Dropdown popover theming | FAIL (polish) | The popover list is default Adwaita grey — it does not pick up the frosted / neon treatment of the card it drops out of. |

## 4. Session start

| # | Item | Result | Evidence / notes |
| --- | --- | --- | --- |
| SS-01 | NYXUS session starts | PASS | Hyprland 0.56.1 (`built from branch v0.56.1 at commit 5c9377c`). |
| SS-02 | `hyprctl configerrors` clean | PASS | Empty. 157 binds registered, all config shards parsed. |
| SS-03 | Desktop wallpaper | PASS | `awww-daemon --format xrgb` running, urban-alien wallpaper full-bleed at L0. |
| SS-04 | Hyprland deprecation nag banner | **FAIL** | A yellow warning banner — `You are using the .conf config format, support for which will be removed in Hyprland 0.57` — is drawn over the top-right of the desktop for the first seconds of every session. A shipped product should not show its user an upstream migration nag. |
| SS-05 | Workspaces / stations defined | PASS | Measured: 10 numbered stations (OPS, FORGE, GHOST, PULSE, WAVE, CORE, MESH, SCRIBE, BIFROST, ARSENAL) plus 13 named special workspaces (HOME, START, LAB, RELAY, ANVIL, TRACE, BEACON, MIXER, VAULT, SCAN, BOARD, SENTRY, RANGE). |
| SS-06 | Welcome Transmission riddle | PASS (with a polish FAIL) | The `nyxus.welcome-note` terminal opens, types out the riddle, accepts `dream`, plays the DREAM PROTOCOL unlock and dissolves. Exercised end to end in the VM. |
| SS-07 | Welcome Transmission escape is discoverable | **FAIL (polish)** | The prompt reads `[WARNING] HUMANITY COMPROMISED. ENTER CREATION HASH TO ENGAGE SUB-SHELL.` with no visible way out. `q`/`quit`/`exit`/`skip` all work and it gives up after 5 attempts, but the `skip` hint is only printed *after* the user submits an empty line. This is exactly what trapped a previous agent, and it will trap a first-time user. |
| SS-08 | Welcome Transmission window geometry | FAIL (minor) | Measured 980x920 at 470,80 — its bottom edge lands at y=1000, overlapping the bottom bar (which starts at y=922). Floating windows ignore the reserved zone. |
| SS-09 | NYXUS Welcome wizard window | **FAIL** | `dev.nyxus.welcome` maps at **480x320** — GTK's fallback size for a window with no content — and renders blank. Consistent with the previously-diagnosed `nyxus_chrome.install_chrome()` reparenting bug. |
| SS-10 | Stray Alacritty shell at login | FAIL (minor) | An extra `Alacritty` window titled `nyx@nyxus:~` (800x600 at 560,240) is present on OPS at first login alongside the two welcome surfaces. |

## 5. eww bars — measured

All four bars come up and render. Geometry taken from `hyprctl layers -j`.

| # | Item | Result | Measured |
| --- | --- | --- | --- |
| BR-01 | `nyxus-bar-top` | PASS | L1 (bottom), 1920x36 @ 0,4 — ticker with kernel, uptime, disk, net, host, pkgs |
| BR-02 | `nyxus-bar-bottom` | PASS | L1 (bottom), 1920x150 @ 0,922 — saucer clock, fan/temp sparklines, CPU %, net up/down |
| BR-03 | `nyxus-bar-left` | PASS | L2 (top), 56x756 @ 10,103 — station rail, all 12 labels legible |
| BR-04 | `nyxus-bar-right` | PASS | L2 (top), 56x756 @ 1854,103 — app rail |
| BR-05 | Reserved zone | PASS | `hyprctl monitors` → `reserved [0, 40, 0, 158]`. Top and bottom reserve, left/right rails deliberately do not. |
| BR-06 | eww data layer healthy | PASS | `eww state` returns fully populated `WORKSPACES`, `TIME`, `TICKER`, `SYSGRAPH`, `NETGRAPH`, `CAVA`, `PLAYER`, `THREAT`, `FANGRAPH`. No stale or empty vars. |
| BR-07 | `nyxus-bar-right` mapped **twice** | **FAIL** | `hyprctl layers -j` on the first boot listed two `nyxus-bar-right` surfaces at identical geometry (56x756 @ 1854,103) while `eww active-windows` listed only one. An orphaned layer surface from a duplicate open was left mapped. |
| BR-08 | Bars painted immediately after session start | **FAIL** | At 03:29 the four surfaces were mapped with correct geometry but painted nothing (verified by cropping all four screen edges at native resolution — pure wallpaper). They painted correctly by 03:33. The bars are gated behind the first-boot bootstrap, which at 03:27:30 was still rewriting `/usr/local/bin/nyxus-eww-launch` in place. |
| BR-09 | Zombie eww process | FAIL (minor) | A defunct `[eww] <defunct>` child was left parented to the session. |
| BR-10 | Fan / temperature readings | NOT-TESTED | Reads 0 RPM / 0 °C in the VM because QEMU exposes no `hwmon` sensors. Cannot be validated without real hardware. |
| BR-11 | GPU tile | NOT-TESTED | `SYSGRAPH.gpu.present` is `false` under `virtio-vga-gl`. Cannot be validated without a real GPU. |

## 6. Tool resolution on the ISO

This is the check that can only be done on the ISO, because `~/.local/bin` is
populated on the build box and (was) empty on the image.

| # | Item | Result | Evidence |
| --- | --- | --- | --- |
| T-01 | `~/.local/bin` populated on the ISO | PASS | 92 files, **all** executable. |
| T-02 | The six called-out keybind tools resolve | PASS | `nyxus-living`, `nyxus-shader`, `nyxus-soundd`, `nyxus-whispers`, `nyxus-supernova`, `nyxus-graffiti-wall` all resolve to `/home/nyx/.local/bin/…` and are `+x`. |
| T-03 | Session `PATH` puts `~/.local/bin` first | PASS | Read from `/proc/<hyprland>/environ`: `PATH=/home/nyx/.local/bin:/usr/local/bin:…`. |
| T-04 | `/usr/local/bin` executables | **FAIL** | 12 files ship mode 644 and cannot run: `axiom`, `jett-daemon`, **`nyxus-consoles`**, `nyxus-edr-repair`, **`nyxus-home-deck`**, `nyxus-journal-ship`, `nyxus-overlay-open`, `nyxus-stage-system-walls`, `nyxus-suricata-setup`, `sharkdash_core.py`, `sharkdash_health.py`, **`sharknoc`**. `nyxus-consoles` is the ARSENAL station launcher and `sharknoc` is the MESH station launcher, so those stations cannot start their app. Root cause: `mkarchiso` copies `airootfs` with `--no-preserve=mode` and these paths have no `file_permissions` entry in `profiledef.sh`. |
| T-05 | `~/.config/hypr/scripts` executables | **FAIL** | 5 files ship mode 644: `nyxus-daily-line.sh`, `nyxus-idle-glass.sh`, `nyxus-lens.sh`, `nyxus-prism-pulse.sh`, `nyxus-pulse.sh`. |
| T-06 | `~/.config/eww/scripts` executables | **FAIL** | 13 files ship mode 644, including the feed scripts the decks read: `ghost-feed.py`, `lab-feed.py`, `forge-feed.py`, `start-feed.py`, `start-search.py`, `mascot.py`, `dock-enrich-icons.py`, and six `gen-*.py` asset generators. |

## 7. systemd

| # | Item | Result | Evidence |
| --- | --- | --- | --- |
| SD-01 | `graphical.target` reach time | **FAIL** | `systemd-analyze` → `Startup finished in 1.915s (kernel) + 2min 14.095s (userspace) = 2min 16.011s`. The ~2-minute stall is **not** fixed. |
| SD-02 | `systemd-networkd-wait-online.service` | **FAIL** | Enabled and **failing** after its full timeout. This is what holds `graphical.target` for two minutes. NetworkManager is the actual network stack on this image; `systemd-networkd` is not in use, so this unit can only ever time out. |
| SD-03 | Failed units on a clean first boot | **FAIL** | Four: `audit-rules.service`, `earlyoom.service`, `systemd-networkd-wait-online.service`, `usbguard.service`. |
| SD-04 | User-scope failed units | PASS | None. |

---

## 8. Disposition of §§1–7 — 2026-08-01 source audit

Every FAIL above has been taken to a fix, a correction, or a documented
non-fix. Nothing is left as "noted". This pass was **source-level, not
VM-level**: the defects were already measured in the guest on 2026-07-31, so
the work here was finding and fixing the cause in the repo. Each line below
says which. **None of it is in a baked ISO yet — a rebake is required to
re-test any of it in the guest.**

| # | Was | Now | Where |
| --- | --- | --- | --- |
| B-02 | BIOS menu never drew | **FIXED** — `syslinux.cfg` had `MENU LABEL` entries and no `UI` directive; syslinux ignores every MENU line without one. Now `UI vesamenu.c32` (mkarchiso always installs it) with ALIEN NEON colours, plus a copy-to-RAM entry. Gate 13pd. | `nyx-profile/syslinux/syslinux.cfg`, `build-iso.sh` |
| B-03 | UEFI menu widget never drew | **FIXED** — GRUB boxes are nine-slice; the theme shipped `select_c/_e/_w` only and pointed `terminal-box` at that same incomplete prefix. Both theme trees now get all nine slices for every prefix they name, the installed-system theme stops naming Unifont sizes GRUB never loads, and `grub.cfg` only sets `theme=` when the file exists. Gate 13pe. | `grub/themes/nyxus/`, `scripts/generate-grub-theme.py` |
| B-06 / FS-01 | No boot path set `cow_spacesize`; overlay 100% full ~4 min in | **FIXED** — every entry now passes `cow_spacesize=50%`. Overridable at bake with `NYX_COW_SPACESIZE`. Gate 13pd. | both menus, `build-iso.sh` |
| FS-03 | 66 MB `~/.cache/pip` | **FIXED** — bootstrap exports `PIP_NO_CACHE_DIR=1` for its whole process tree. | `nyxus-bootstrap` |
| FS-04 | hyprpm compiled 4 plugins on live media | **FIXED, and this is the likely dominant overlay filler.** The existing guard tested for `/usr/include/hyprland`, which the `hyprland` package ships — so it never fired. Replaced with the live-media test the honeypot fragment uses. | `nyxus-bootstrap` |
| G-06 / G-07 | Greeter preselected `nyxbuild` | **FIXED in PR #84 + hardened** — `customize_airootfs.sh` now asserts at the end of the bake that `nyx` is the only account in the login.defs UID range regreet enumerates, and fails if not. | `customize_airootfs.sh` |
| G-08 / G-09 | Three sessions offered, upstream preselected | **FIXED** — the two upstream entries ship inside the `hyprland` package, so `NoExtract` in *both* pacman configs (build-time keeps them off the image, installed-system keeps them off after `pacman -Syu`), plus a sweep and a hard check that the NYXUS session entry exists. | `pacman.conf` ×2, `customize_airootfs.sh` |
| G-14 | Focus ring used the error red | **FIXED** — focus is magenta `#ff2dad`; `#ff2d55` is danger only. The file header had been mislabelling `#ff2d55` as "magenta", which is how they got conflated. | `greetd/regreet.css` |
| G-15 | Dropdown popovers were Adwaita grey | **FIXED** — GTK4 paints a `GtkDropDown` list in `popover > contents` as a `listview` of rows; only the bare `popover` node was styled. | `greetd/regreet.css` |
| SS-04 | `.conf` deprecation banner | **NOT FIXABLE — see §9.** No opt-out exists. | — |
| SS-07 | Riddle had no visible exit | **FIXED** — the escape is in the banner before the prompt, and every wrong guess repeats it with a remaining-attempts count. | `nyxus_welcome_note.py` |
| SS-08 | Floating windows behind the bottom bar | **FIXED** — `center` centres in the monitor, not the usable area, so anything taller than 764 is partly swallowed at 1080p. Welcome note 920→760; sysmon/control/stickies/terminal/Settings 800→760. Arithmetic recorded beside the rules. | `nyxus-hyprland-rules.conf` |
| SS-09 | Welcome wizard blank at 480x320 | **FIXED, and it was our own chrome.** The wizard calls `fullscreen()`, then `install_chrome()` ran `unfullscreen()` + `set_default_size(480,320)`. The same policy was also discarding the chosen size of ~two dozen other apps. It is a default now, not an override, and a window can opt out with `_nyxus_own_geometry`. | `nyxus_chrome.py`, `nyxus_welcome.py` |
| SS-10 | "Stray" Alacritty at first login | **NOT A DEFECT** — station 1 (OPS) carries `on-created-empty:alacritty`. That is the window. Working as designed. | — |
| BR-07 | Two `nyxus-bar-right` surfaces | **LIKELY FIXED, needs re-test** — `nyxus-eww-launch-safe` has taken a single-flight lock since it was written; plain `nyxus-eww-launch` (the fallback path in `nyxus-persist-login` and `sync-eww.sh`) never did, so two launchers could interleave `close-all` and `open`. Same lock file now. | `nyxus-eww-launch` |
| BR-08 | Bars mapped but unpainted for ~4 min | **LIKELY FIXED via FS-04** — they wait on `nyxus-wait-bootstrap`, and bootstrap was busy compiling plugins. Re-measure after a rebake. | `nyxus-bootstrap` |
| SD-01 / SD-02 | 2min 14s userspace, `systemd-networkd-wait-online` failing | **FIXED** — masked, not disabled: `disable` only removes symlinks and any `Wants=network-online.target` pulls it back. | `customize_airootfs.sh` |
| SD-03 | Four failed units | **FIXED — four unrelated causes.** `earlyoom`: `-N` takes an argument, so `-N --avoid <re>` fed earlyoom "--avoid" as its post-kill script and it refused the command line (the regexes were also literally single-quoted, which systemd does not strip). `audit-rules`: the FIM ruleset watched the honeypot's *build-machine* path, and one bad `-w` fails `augenrules --load`, which took the whole FIM feed down — that is why Bifrost's FIM panel was blank. `usbguard`: used `AuditBackend=LinuxAudit`, inheriting auditd's failure — and it is no longer enabled by default at all, because its shipped policy is empty by design and lockdown is opt-in from Settings. `jett-daemon`: the unit ships unconditionally, the binary only when the build host has one; an `ExecCondition` marks it skipped rather than failed. | `etc/default/earlyoom`, `nyxus-fim.rules`, `usbguard-daemon.conf`, `jett-daemon.service`, `customize_airootfs.sh` |
| T-04 / T-05 / T-06 | 12 executables at mode 644 | **FIXED, and it was 116.** `file_permissions` was a hand-maintained mirror of a directory tree. It is derived now, at bake time, from the staged airootfs. Gate 13pc. | `regen-file-permissions.py`, `build-iso.sh` |

### Corrections to §§1–7

- **FS-01's breakdown is misleading.** It attributes the full overlay to
  `/home/nyx` being 254 MB. `/home/nyx` is populated in the chroot at bake
  time, so it lives in the read-only squashfs lower layer, and `du` on an
  overlayfs reports the merged view. Copying it consumes no overlay space. The
  writes that do — the pip cache and the hyprpm plugin build — are FS-03 and
  FS-04.
- **B-06 partly cited a file that does not ship.** `efiboot/loader/entries/01-nyx.conf`
  is only read by mkarchiso's `uefi.systemd-boot` boot modes, and this profile
  uses `bios.syslinux` + `uefi.grub`. The whole `efiboot/` tree has been
  deleted rather than kept in sync.
- **SS-10 is not a defect** (see the table).

## 9. SS-04 — the one that cannot be fixed, and the deadline behind it

The yellow banner reading *"You are using the .conf config format, support for
which will be removed in Hyprland 0.57"* was added in
[hyprwm/Hyprland#15538](https://github.com/hyprwm/Hyprland/pull/15538) and
shipped in 0.56.1. **There is no setting to suppress it.** The only way to
clear it is to migrate off `.conf`.

That is not a cosmetic issue, it is a countdown. **Hyprland 0.57 removes
`.conf` support entirely.** NYXUS currently has 157 registered binds across a
dozen sourced shards, all in `.conf`, plus every `windowrule`, `layerrule`,
`workspace` and `env` line the desktop depends on. When 0.57 lands in `extra`,
a bake that picks it up produces an image whose entire configuration layer is
ignored.

This is the largest forward risk in the build. It is scoped work, not
open-ended — `hyprland.conf` plus `conf.d/*.conf`, mechanically translatable,
and `hyprmorph` exists as a starting point — but it has to happen before 0.57
reaches the ISO, and it wants a live session to verify against, so it is not
something to start blind.

## 10. Sections still genuinely untested

Hub, NYXUS Power, station switching, Settings pages, app launches, keybinds,
lock and screensaver were never exercised in the guest and are **not** covered
above. The source-level defects found near them are fixed, but the click-audit
itself is still owed. Do that against a **fresh bake**, not the `0f77d1c2`
image — the fixes above are not in it.

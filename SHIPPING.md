# NYXUS — Print-Before-Flash Checklist

> **Rewritten 2026-07-30.** The previous revision of this file was written for
> the May-2026 build and had gone dangerously stale: it named the ISO `nyx-*`,
> expected it to be **1.8–2.2 GB** (it is ~**9.5–10 GB**), told you to build
> `dist/` "or the ISO becomes online-only" (the bake prefers the git tree and
> `dist/` is a known bake hazard), and pointed at `~/nyxus-iso` instead of the
> one canonical repo. Everything below was re-derived from `build-iso.sh`,
> `profiledef.sh` and `HANDOFF.md` on 2026-07-30.

> The canonical narrative procedure lives in
> [`HANDOFF.md` §6](./HANDOFF.md) — this file is the printable tick-list version.
> **Read `HANDOFF.md` first.** It carries the current bake-readiness state,
> which this file deliberately does not duplicate.

Print this page. Tick boxes with a real pen. The bake runs on the owner's
**Arch Linux host** with root + `archiso`. An agent cannot run it (sudo on this
machine is fingerprint-only).

---

## 0 · Pre-flight (host machine)

- [ ] Running on **Arch Linux** (not Manjaro, not EndeavourOS — base Arch)
- [ ] `mkarchiso` installed: `sudo pacman -S --needed archiso squashfs-tools libisoburn dosfstools`
- [ ] **≥ 40 GB free** for the work dir plus **≥ 12 GB** for `iso-builder/out/`.
      The ISO is ~9.5–10 GB and the squashfs work dir needs real headroom.
      Old ISOs in `out/` are gitignored and stack up fast — clear them first.
- [ ] `sudo` available for the whole run (fingerprint prompt mid-build is fine)
- [ ] USB stick ≥ **16 GB**, contents you don't care about (it will be wiped)
- [ ] Prebuilt Kage-Ryu packages present at
      `~/Projects/arch-custom-kernel/linux-kage-ryu/` — **the bake hard-fails
      without them** so it can never silently ship kernel-less

---

## 1 · Sync the canonical repo

**There is exactly one canonical repo: `~/Nyxus-Core`, branch `main`.** Any
lowercase `~/nyxus-core`, `~/.nyxus-backup-*`, `~/nyxus-KNOWN-GOOD-*` or
`~/Backups/nyxus*` is a stale snapshot — never bake from one.

```bash
cd ~/Nyxus-Core
git pull --rebase
git status          # MUST say nothing to commit
```

- [ ] Working tree clean — **a bake reads the profile as it runs**, so an
      in-flight edit ships a partial change set (this really happened on
      2026-07-22 and cost a stick)
- [ ] On `main`
- [ ] Nothing else is editing the repo (no other agent mid-write)

---

## 2 · Gate the profile

```bash
bash iso-builder/verify-profile.sh
```

- [ ] Exits **PASS**. It is not decoration — its gates encode bugs that already
      shipped: bake-wipe gaps, `~/.local/bin` unreachable tools, unsourced
      shards, station drift, greeter path, `workspace name:0`, layer-blur
      ordering, eww handler timeouts. If a gate fails, fix the cause; do not
      bypass it.

> The offline cache at `/opt/nyxus-cache` is staged from
> **`artifacts/api-server/nyxus-scripts/`** (the git source of truth) and the
> bake **hard-fails** if `nyxus_install.sh` would be missing, so an online-only
> ISO can no longer ship silently. `artifacts/api-server/dist/nyxus-scripts` is
> only a *fallback* and is rejected outright if it contains host symlinks —
> you do **not** need to build it, and historically it poisoned bakes.

---

## 3 · Bake the ISO

```bash
cd ~/Nyxus-Core/iso-builder
sudo ./build-iso.sh
# sudo NYX_WITH_KAGE_RYU=0 ./build-iso.sh   # stock-kernel-only debug ISO
# sudo NYX_SQUASH_COMP=xz  ./build-iso.sh   # smaller ISO, ~7.6x slower cold reads
```

Watch for:

- [ ] `✓ configs: hypr / eww / dunst / rofi / wlogout / alacritty`
- [ ] `✓ bootstrap shims: nyxus-bootstrap / nyxus-wait-bootstrap`
- [ ] `✓ offline cache: N files … first boot works with NO internet`
- [ ] Kage-Ryu staged into the profile-local `[nyxus-local]` repo and the three
      live boot menus rewritten (Kage entry #0, stock as labelled rescue)
- [ ] `✓ ISO baked → .../out/nyxus-<YYYY.MM.DD>-x86_64.iso`

Bake wall-clock time on this host is **not currently recorded** — do not trust
the "5–15 minutes" figure the May-2026 revision of this file carried, which was
for a ~2 GB ISO. Since 2026-07-30 the squashfs compressor is `zstd` rather than
`xz`, which compresses considerably faster, so the bake is quicker than it was
immediately before that change. **Time it on the next bake and record it here.**

---

## 4 · Verify the ISO

```bash
cd ~/Nyxus-Core/iso-builder/out
ls -lh nyxus-*.iso
ISO=$(ls -t nyxus-*.iso | head -1)
sha256sum "$ISO"
bsdtar -tf "$ISO" | head            # no root needed
```

- [ ] Size is ~**9.5–10 GB**. Dramatically smaller means something did not bake.
- [ ] SHA-256 written down

---

## 5 · Flash to USB

```bash
lsblk          # identify the USB — get this WRONG and you wipe your system disk
```

On the owner's machine the USB is normally `/dev/sda` (SanDisk 57 GB) and the
internal disk is `/dev/nvme0n1`. **Never put `nvme` as `of=`.** The letter moves
between boots — re-check every time.

```bash
sudo dd if="$ISO" of=/dev/sda bs=4M status=progress oflag=sync
sync
```

- [ ] Target triple-checked
- [ ] Verify after flashing (no sudo needed):
      `lsblk -o NAME,SIZE,FSTYPE,LABEL /dev/sda` → `iso9660` +
      label **`NYXUS_2026_07`** + an `ARCHISO_EFI` vfat partition

**Ventoy** also works — copy the `.iso` onto the Ventoy partition.

---

## 6 · Boot it

- [ ] Boot menu (MSI: **F11**) → pick the **"UEFI: SanDisk"** entry.
      The 🐉 dragon GRUB menu is **UEFI-only**; a Legacy/BIOS boot gets the
      plain syslinux text menu. That is not a bug.
- [ ] Boot entry **#0 is Kage-Ryu**; "stock linux (rescue)" is the fallback.
      If Kage fails with `unknown filesystem type 'iso9660'`, boot the rescue
      entry and re-check the kernel's `CONFIG_ISO9660_FS` / `SQUASHFS` /
      `BLK_DEV_LOOP`.
- [ ] 🛸 UFO "Cosmic Arrival" plymouth splash
- [ ] Greeter appears. **Note which session the dropdown preselects** — the ISO
      ships three `wayland-sessions` entries and `NYXUS (Hyprland)` is not
      guaranteed to be first. This is an open item in `HANDOFF.md`.
- [ ] Login `nyx` / `nyx`
- [ ] `cat /etc/nyxus-build` → the source commit matches the tip you baked

### What to expect on first login

| Time | What you see |
|------|--------------|
| 0s | Wallpaper still paints immediately (the static image, then the live loop swaps in behind it) |
| ~5s | Notification: `downloaded installer · running install…` or `using offline cache…` |
| ~30–60s | All four eww bars appear (top/bottom/left/right); the HOME deck is on `Super+Home` |
| ~60s | `NYXUS · ready · welcome, nyx` |

Bare desktop after **2 minutes** → `cat /tmp/nyxus-bootstrap.log`.
Slow **splash → greeter** → `systemd-analyze critical-chain graphical.target`
on the stick. That command names the offender; do not guess.

---

## 7 · Post-boot smoke test

- [ ] Every station pill 1–10 opens a deck — **except BIFROST (9), which has no
      deck by design**
- [ ] `Super+Home` / `Super+End` / `Super+Delete` reach HOME / START / LAB
- [ ] `Super+Alt+L` living theme (borders pulse — proves `nyxus-living` ran)
- [ ] `Super+O` shaders · `Super+T` tint · `Super+Z` spray
- [ ] `Super+Ctrl+W` whispers · `Super+Alt+Shift+S` supernova ·
      `Super+Alt+Shift+G` graffiti wall
- [ ] Lock the screen → weather line + lock art + track info all render
- [ ] UI blips audible on window open/close (`nyxus-soundd`)
- [ ] Notifications actually appear (dunst → eww bridge)
- [ ] The Hub opens **and dismisses** (`Escape`, `Super+Shift+Escape`).
      `nyxus-panic` and `Super+Ctrl+Shift+Escape` are the escape hatches.
- [ ] `calamares` is present: `command -v calamares`

## 8 · Recovery

```bash
rm ~/.nyxus/.bootstrapped && nyxus-bootstrap   # force re-run
cat /tmp/nyxus-bootstrap.log                   # what failed
```

No Wi-Fi and the offline cache also failed → bare Hyprland, a red toast, and a
`NYXUS-FIRST-BOOT-FAILED.txt` on the desktop.

| Keys | Action |
|------|--------|
| `Super+Return` | Terminal (kitty → alacritty → foot) |
| `Super+Shift+Return` | Alacritty first (use if the above fails) |
| `Super+Q` | Close focused window |
| `Super+Space` | App launcher |
| `Super+Shift+D` | Run a command (rofi) |
| `Super+Shift+E` | Logout menu |
| `Super+Shift+H` | NYXUS Doctor (health audit) |

Then `nmtui` for Wi-Fi and `nyxus-bootstrap` to retry.

Full keybind reference: [`docs/KEYBINDS.md`](docs/KEYBINDS.md).

---

## 9 · Install to disk

Only after the live session is fully themed and you have poked at it enough to
trust it on this hardware. Calamares copies both kernels and
`nyxus-set-grub-default-kage` flips the installed GRUB default to Kage-Ryu.

- [ ] Ready to commit a real disk install
- [ ] Target disk backed up

---

**Last build:** _________________ &nbsp; **SHA-256:** _________________________________

**Hardware tested:** _________________________________________________________

**Notes:** ___________________________________________________________________


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

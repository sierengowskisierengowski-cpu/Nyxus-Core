# NYXUS Clean Reinstall Guide (wipe + fresh install from ISO)

This guide covers wiping this machine (MSI Stealth GS77 12UE, single 1TB
NVMe, UEFI, Secure Boot disabled, hostname `nyx-cosmic`) and doing a clean
install of NYXUS from `iso-builder/out/nyx-2026.07.15-x86_64.iso`, then
restoring everything from a backup.

**Read this whole document before doing anything irreversible.** Steps 1-3
(backup) are safe and non-destructive. Step 5 onward (installer) erases the
disk.

---

## 0. Status as of the investigation that produced this guide

- Machine has **one internal drive** (`nvme0n1`, ~954GiB, `Micron_2400_MTFDKBA1T0QFM`),
  partitioned as `/boot` (1GiB FAT32) + `/` (ext4, ~747GiB used / 143GiB free).
  There is **no second internal drive** to use as a backup target.
- At investigation time, **no external/USB drive was detected** by the
  system (`lsblk`/`lsusb` showed only the built-in webcam, keyboard,
  fingerprint reader, two YubiKeys, and Bluetooth — no mass-storage device).
- `$HOME` is **~625GB** total. A curated "everything irreplaceable" subset
  (configs, projects, keys, docs, pictures — see
  `scripts/nyxus-backup-for-reinstall.sh` for the exact list) is smaller but
  still likely **150-300GB+** depending on how much of `~/.config` (23GB,
  mostly Cursor/Chromium caches) and `~/Projects` (90GB) you keep.
- **You need to physically connect a backup destination with enough free
  space before continuing** — see step 1.

---

## 1. Get a backup destination connected

Pick ONE of these, then re-run the storage check:

- **External USB/HDD/SSD drive** — ideally ≥1TB if you want everything
  including Music/VMs, or ≥300GB for the curated "essentials" backup.
- A **second machine on your network** you can `rsync` to over SSH.
- Cloud storage you already use, if you're comfortable staging a large
  upload (slow for hundreds of GB on most home connections).

Once connected, confirm the system sees it:

```bash
lsblk -o NAME,SIZE,TYPE,TRAN,MOUNTPOINT,FSTYPE,LABEL
```

Look for a device with `TRAN` = `usb` and a sane `SIZE`. Mount it if it
isn't auto-mounted (most desktop environments auto-mount at
`/run/media/cosmic/<label>`).

## 2. Run the backup

From `~/Nyxus-Core`:

```bash
# Preview first — writes nothing, just shows what would happen:
./scripts/nyxus-backup-for-reinstall.sh /run/media/cosmic/<your-drive> --dry-run

# Then for real:
./scripts/nyxus-backup-for-reinstall.sh /run/media/cosmic/<your-drive>
```

This creates `nyxus-backup-<timestamp>/` on the destination with:

| Folder | Contents |
|---|---|
| `home/` | Mirror of dotfiles, `.config`, `.nyxus`, `Nyxus-Core`, `Projects`, `.local/bin`, browser profiles, Pictures/Documents/Desktop/Downloads, etc. |
| `ssh-keys/.ssh/` | Extra verified copy of your SSH keys. |
| `gnupg/.gnupg/` | Extra verified copy of your GPG keyring. |
| `pkglists/` | `pacman -Qqe`/`-Qqm` output for reinstalling your exact package set. |
| `system-info/` | hostnamectl / lsblk / fstab / enabled-services / crontab snapshot. |
| `MANIFEST.txt` | Full description of what's in/out and how to restore. |

By default it **skips** big "bulk" dirs that are already-covered/regenerable
(`Music`, `VirtualBox VMs`, the existing `~/Backups` folder, build-recovery
snapshots, staging dirs). Add `--include-bulk` if you want those too — check
you have the space first.

The script refuses to write to a destination that's on the same disk as
`$HOME` (so you can't accidentally "back up" onto the drive you're about to
wipe), and it spot-checks + size-compares the result before finishing.

**Do not proceed to step 5 until this script finishes cleanly with no
warnings**, and you've glanced at `MANIFEST.txt` on the backup drive.

## 3. Write the ISO to your USB installer stick

**Do this only once the USB stick is physically plugged in and you can see
it in `lsblk` with `TRAN` = `usb`.**

```bash
lsblk -o NAME,SIZE,TYPE,TRAN,MOUNTPOINT,FSTYPE,LABEL,MODEL
```

Identify the exact device path (e.g. `/dev/sdb` — **not** a partition like
`/dev/sdb1`, and **not** `/dev/nvme0n1`, which is this machine's internal
drive). Confirm:
- `TRAN` shows `usb`
- `SIZE` roughly matches your known USB stick capacity
- It is **not** `nvme0n1` or any partition currently mounted at `/` or `/boot`

If there is any doubt at all about which device is the stick, stop and
double check (unplug/replug and diff `lsblk` output) rather than guessing.

Then, everything on that USB stick will be erased:

```bash
sudo dd if=/home/cosmic/Nyxus-Core/iso-builder/out/nyx-2026.07.15-x86_64.iso \
     of=/dev/sdX bs=4M status=progress oflag=sync
sync
```

Verify the write:

```bash
# Compare the first N bytes/checksum of the ISO against what's on the device
cmp -n "$(stat -c%s /home/cosmic/Nyxus-Core/iso-builder/out/nyx-2026.07.15-x86_64.iso)" \
    /home/cosmic/Nyxus-Core/iso-builder/out/nyx-2026.07.15-x86_64.iso /dev/sdX && echo "USB write verified OK"
```

## 4. Double-check before wiping

- [ ] Backup finished with no errors and `MANIFEST.txt` looks right.
- [ ] You've eyeballed a few files on the backup drive directly (not just
      trusted the script) — e.g. open a couple of Pictures, check
      `pkglists/pkglist.txt` has hundreds of lines, check `.ssh/id_rsa` size
      is non-zero.
- [ ] USB installer verified (step 3).
- [ ] You know your GPG/SSH key passphrases from memory (they are not saved
      anywhere in the backup).
- [ ] You're OK proceeding with **wipe + clean install**, not dual-boot —
      this erases the internal 1TB NVMe entirely.

Do not reboot into the installer until every box above is checked.

## 5. Boot from the USB installer

1. Shut down (don't just reboot) so you have a clean boot.
2. Power on and immediately tap the boot-menu key repeatedly. For MSI
   laptops (this is an MSI Stealth GS77) it's typically **F11** for the
   one-time boot menu, or **Del**/**F2** for the UEFI setup screen. If F11
   doesn't work, try **Esc** or check for an MSI logo splash prompt.
3. Select the USB drive (it should show up as a UEFI boot entry, often
   labeled with the drive's vendor name). Secure Boot is already disabled
   on this machine, so the Arch/NYXUS ISO should boot without extra steps.
4. You should land in the NYXUS/Arch live environment with the
   greetd+regreet (or tuigreet) login for the live session.

## 6. Partition and install

Recommended scheme (matches what's currently working on this machine, so
it's low-risk):

| Partition | Size | Type |
|---|---|---|
| EFI System Partition | 1GiB | FAT32, `boot`+`esp` flags |
| Root | remainder (~950GiB) | ext4 |

No separate swap partition needed — NYXUS uses `zram` for swap.

If you'd like an easier time re-installing in the future without a full
home-directory backup/restore cycle, you can instead split root/home:

| Partition | Size | Type |
|---|---|---|
| EFI System Partition | 1GiB | FAT32 |
| Root (`/`) | 100-150GiB | ext4 |
| Home (`/home`) | remainder | ext4 |

This is optional — the simple single-root layout above is what's proven to
work already and is what the restore script assumes (it just restores into
whatever `/home/cosmic` ends up being).

Run through the NYXUS installer (Calamares-based) with **erase disk / clean
install** selected, targeting the internal NVMe (`nvme0n1`), NOT any USB
device. Set hostname `nyx-cosmic` (or whatever you prefer), create your user
as `cosmic` to match backed-up paths (or adjust paths in the restore script
if you use a different username), and let it finish and reboot into the new
system.

Log in for the first time, connect to WiFi/network, and confirm you have
internet access before the next step (package restore needs it).

## 7. Restore everything from backup

Plug the backup drive back in, mount it, then either use the fresh clone of
Nyxus-Core (the ISO should already contain a copy, or `git clone` it) or
copy `scripts/nyxus-restore-from-backup.sh` directly off the backup drive
itself if Nyxus-Core isn't available yet.

```bash
# If Nyxus-Core isn't already on the new system:
git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core ~/Nyxus-Core
cd ~/Nyxus-Core

# Preview the restore first (default is dry-run, changes nothing):
./scripts/nyxus-restore-from-backup.sh /run/media/cosmic/<your-drive>/nyxus-backup-<timestamp>

# Then actually apply it:
./scripts/nyxus-restore-from-backup.sh /run/media/cosmic/<your-drive>/nyxus-backup-<timestamp> --apply
```

This will, in order:
1. Reinstall your recorded repo package set (`pacman -S --needed - < pkglist.txt`).
   Tell you about AUR packages separately (needs an AUR helper like `yay`).
2. Restore `~/.ssh` with correct permissions (`700`/`600`/`644`) — **only**
   if `~/.ssh` is currently empty on the new system, so it never clobbers a
   fresh keypair you may have generated during install.
3. Restore `~/.gnupg` the same way, with `700`/`600` permissions.
4. Merge the rest of the backed-up home content into `$HOME` using
   `rsync --ignore-existing` — it will not overwrite files the fresh
   install already created, so nothing you haven't touched yet gets
   clobbered.
5. Sanity-check that `~/Nyxus-Core` is present and report `git status`.
6. Print a checklist of things it could NOT automate (see below).

Then run the NYXUS bootstrap/build scripts as needed, e.g.:

```bash
cd ~/Nyxus-Core
./scripts/nyxus-install.sh --dry-run   # preview
./scripts/nyxus-install.sh --all       # base + greeter + loadout, your call
./scripts/nyxus-verify-build.sh
nyxus-save-state                       # once you're happy, snapshot it (see docs/REBOOT_SURVIVAL.md)
```

## 8. Things that need your manual attention (cannot be automated)

- **Browser saved passwords**: Firefox (`logins.db`/`key4.db`) and Chromium
  (`Login Data`) profiles are copied byte-for-byte, but their encryption is
  tied to the OS keyring / browser master password. If saved logins don't
  auto-unlock after restore, you may need to re-enter a master password
  once, or use the browser's own **export/import bookmarks & passwords**
  feature as a fallback before wiping, just in case.
- **2FA / authenticator apps** on your phone are untouched by any of this —
  make sure you still have phone access for any 2FA-gated accounts.
- **YubiKeys** (two Yubico 4/5 OTP+U2F+CCID keys were seen on this system) —
  physical hardware, not backed up by software. Keep them safe; some
  services may need you to re-register them if your OS/browser identity
  changes.
- **GPG/SSH key passphrases** are never stored in the backup — you must
  remember them yourself.
- **Cloud-only accounts/services** (GitHub, etc.) aren't affected by a local
  wipe, but double check `~/Nyxus-Core` had **263 uncommitted files** at
  backup time — those changes only exist in the backup's
  `home/Nyxus-Core/`, not on GitHub, until you commit/push them from the new
  system.
- Any secrets stored only in a password manager's cloud vault are fine
  (cloud-synced); anything in a **local-only** vault file should be
  double-checked against the include-list in
  `scripts/nyxus-backup-for-reinstall.sh`.

## Related docs

- `docs/INSTALL.md` — general NYXUS install paths (bootstrap vs. ISO).
- `docs/MACHINE_PROFILE.md` — hardware/workload profile for this machine.
- `docs/REBOOT_SURVIVAL.md` — recovering a broken login/session after this
  reinstall is done and you're back to daily-driving NYXUS.
- `scripts/nyxus-backup-for-reinstall.sh` — the backup script (step 2).
- `scripts/nyxus-restore-from-backup.sh` — the restore script (step 7).

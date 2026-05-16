# NYXUS — Print-Before-Flash Checklist

> Print this page. Tick boxes with a real pen. The ISO build can't be
> reproduced from inside Replit — these steps run on your **Arch Linux
> host** with root + archiso installed.

---

## 0 · Pre-flight (host machine)

- [ ] Running on **Arch Linux** (not Manjaro, not EndeavourOS — base Arch)
- [ ] `mkarchiso` installed: `sudo pacman -S archiso`
- [ ] At least **8 GB** free disk in `/tmp` (work dir) + `~/nyxus-iso/out` (output)
- [ ] You can `sudo` without password prompt mid-build (or be ready to type it)
- [ ] USB stick ≥ **4 GB** ready, contents you don't care about (it'll be wiped)

---

## 1 · Sync the repo

```bash
cd ~/nyxus-iso         # or wherever you cloned it
git pull               # latest commit
```

- [ ] Working tree clean (`git status` says nothing to commit)
- [ ] On the branch you intend to ship from

---

## 2 · Build dist/ — populates the offline cache

> **CRITICAL.** Skip this and the ISO becomes online-only. The user's
> first boot at the coffee shop with no Wi-Fi will fail.

```bash
pnpm install
pnpm --filter @workspace/api-server run build
```

- [ ] `artifacts/api-server/dist/nyxus-scripts/` exists and contains 152+ files (~52 MB)
- [ ] No build errors

Verify:
```bash
ls artifacts/api-server/dist/nyxus-scripts/ | wc -l    # expect ≥ 100 (currently ~152)
du -sh artifacts/api-server/dist/nyxus-scripts/        # expect roughly ~50M
ls artifacts/api-server/dist/nyxus-scripts/nyxus-bootstrap     # must exist
ls artifacts/api-server/dist/nyxus-scripts/nyxus-wait-bootstrap # must exist
ls artifacts/api-server/dist/nyxus-scripts/nyxus_install.sh    # must exist
```

---

## 3 · Bake the ISO

```bash
cd iso-builder
sudo ./build-iso.sh
```

Watch for these lines in the output:

- [ ] `✓ configs: hypr / eww / dunst / rofi / wlogout / alacritty`
- [ ] `✓ bootstrap shims: nyxus-bootstrap / nyxus-wait-bootstrap`
- [ ] `✓ offline cache: 152 files in /opt/nyxus-cache/ (52M)` — if you see `! dist/nyxus-scripts/ not found`, **STOP**, go back to step 2
- [ ] `✓ SDDM theme staged`
- [ ] `✓ deployed N python files` (Phantom)
- [ ] `✓ ISO baked → .../out/nyx-*.iso` (filename version may have shifted)

Total time: **5–15 minutes** depending on host CPU.

---

## 4 · Verify the ISO

```bash
cd iso-builder/out
ls -lh nyx-*.iso          # expect one file, ~1.8–2.2 GB
ISO=$(ls -t nyx-*.iso | head -1)   # capture latest
sha256sum "$ISO"          # write this down
```

- [ ] Size is in the 1.8–2.2 GB range (smaller = something didn't bake; larger = fine)
- [ ] You wrote the SHA-256 down somewhere you'll find it later

---

## 5 · Flash to USB

**Find your USB device first:**
```bash
lsblk          # identify the right /dev/sdX — get this WRONG and you wipe your laptop disk
```

- [ ] You identified the USB as `/dev/sdX` (replace X below) — **triple-check it's not your system disk**

**Flash (dd method — works on any Linux host):**
```bash
sudo dd if="$ISO" of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

**Or Ventoy (drag-and-drop, recommended if you flash multiple ISOs):**
- [ ] Ventoy already installed on the USB → just copy the .iso to the Ventoy partition

---

## 6 · Boot it

- [ ] BIOS/UEFI: USB is first in boot order, Secure Boot **OFF**
- [ ] Boots to the NYX live image, autologins as `nyx` / password `nyx`
- [ ] You land in **Hyprland** (not a TTY)

### What to expect on first login (~60 seconds)

| Time | What you see |
|------|--------------|
| 0s   | Bare Hyprland desktop (black). A small notification top-right: `NYXUS · first-boot setup starting — installing chrome, ~60 seconds…` |
| ~5s  | Notification updates: `downloaded installer · running install…` (or `using offline cache…` if no Wi-Fi) |
| ~30–60s | EWW bars appear (top/bottom/left/right), wallpaper paints, NYXUS Home opens on workspace 0 |
| ~60s | Final notification: `NYXUS · ready · welcome, nyx` |

If you only see the bare desktop after **2 minutes** → check `/tmp/nyxus-bootstrap.log` for what failed.

---

## 7 · Recovery

**Force re-run the bootstrap:**
```bash
rm ~/.nyxus/.bootstrapped && nyxus-bootstrap
```

**See what happened during install:**
```bash
cat /tmp/nyxus-bootstrap.log
```

**No Wi-Fi on first boot, offline cache also failed:**

You'll have a bare Hyprland desktop with a red error notification top-right
and a `NYXUS-FIRST-BOOT-FAILED.txt` file on the desktop.

```bash
# Open a terminal (no EWW bar exists yet):
#   SUPER + RETURN          → NYXUS terminal
#   SUPER + SHIFT + RETURN  → raw Alacritty (use this if NYXUS terminal fails)
nmtui                  # Wi-Fi setup
nyxus-bootstrap        # re-run
```

**Useful keybinds while the desktop is bare:**

| Keys | Action |
|------|--------|
| `SUPER + RETURN` | NYXUS terminal |
| `SUPER + SHIFT + RETURN` | Raw Alacritty (fallback) |
| `SUPER + Q` | Close focused window |
| `SUPER + R` | App launcher (rofi) |
| `SUPER + SHIFT + E` | Logout menu |
| `SUPER + SHIFT + H` | NYXUS health audit |

---

## 8 · Install to disk

Once the live session is fully NYXUS-themed and you've poked around enough
to be sure it works on your hardware, run the disk installer (Phantom's
job 2 — separate workflow).

- [ ] You're ready to commit a real disk install
- [ ] You backed up anything on the target disk

---

**Last build:** _________________ &nbsp; **SHA-256:** _________________________________

**Hardware tested:** _________________________________________________________

**Notes:** ___________________________________________________________________


---

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

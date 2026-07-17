# NYXUS Reboot Survival Guide

Your daily-driver Hyprland setup is designed to survive reboot/login without manual fixes.

## One-time: restore Cosmic login screen (requires password)

Your machine uses **Cosmic greeter** (not SDDM) for the session picker — COSMIC, Hyprland, and NYXUS (Hyprland). If a reboot lands on a broken SDDM screen or you have to TTY in and run `Hyprland` manually:

```bash
sudo nyxus-restore-login
```

Then reboot or log out. You should see the **Cosmic login screen** with a session dropdown.

Pick **NYXUS (Hyprland)** for your themed build, or **COSMIC** for your main desktop.

### Alternative: NYXUS SDDM theme (optional fallback)

If you prefer the NYXUS void login theme instead of Cosmic greeter:

```bash
sudo nyxus-install-sddm
sudo systemctl disable cosmic-greeter
sudo systemctl enable sddm
sudo systemctl restart sddm
```

At login you will see a **session dropdown** with:
- **COSMIC** — System76 Cosmic desktop
- **Hyprland** — stock Hyprland session
- **NYXUS (Hyprland)** — NYXUS-themed Hyprland (recommended)

## After every polish session — save your state

```bash
nyxus-save-state
```

This creates a GOLD snapshot at `~/nyxus-build-recovery/GOLD-LATEST` and locks bootstrap from overwriting your configs.

## If something breaks after reboot

```bash
nyxus-restore-session      # restore last GOLD snapshot + relaunch bars
nyxus-overlay-unstick      # stuck menu / missing bars
nyxus-eww-launch-safe      # quick bar reload
```

Emergency keys:
- **Escape** or **Super+Shift+Escape** — close stuck overlays, restore bars
- **Super+L** — screensaver (not lockout)

## What runs on every Hyprland login

1. `nyxus-bootstrap` — **skipped** when daily-driver is locked (no hyprexpo crash, no remote overwrite)
2. `nyxus-persist-login` — compile CSS, wallpaper, `nyxus-eww-launch-safe`, auto-restore if bars missing

## Fallback snapshots

| Path | Purpose |
|------|---------|
| `~/nyxus-build-recovery/GOLD-LATEST` | Latest saved daily-driver |
| `~/.nyxus/.state-saved` | Timestamp of last save |
| `~/.nyxus/.daily-driver-locked` | Prevents bootstrap from resetting configs |

## Verify health

```bash
nyxus-verify-build
```

## Blank screen at login?

From TTY (Ctrl+Alt+F3):

```bash
sudo nyxus-restore-login
# or if you use SDDM instead:
sudo systemctl restart sddm
# emergency manual start:
Hyprland
```

Then run `sudo nyxus-restore-login` if the greeter is wrong or sessions fail.

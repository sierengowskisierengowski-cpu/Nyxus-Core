# NYXUS Daily Driver — Live Preview Harness

> How to look at the new urban-neon **Daily Driver** desktop on this machine,
> whenever you want, side by side with the alien desktop you use every day —
> **without baking an ISO** and without touching your own account.
>
> Companion to [`DAILY_DRIVER_BRINGUP_PLAN.md`](./DAILY_DRIVER_BRINGUP_PLAN.md)
> (the technical plan) and
> [`DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md`](./DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md)
> §4 (the locked look). Script:
> [`scripts/nyxus-daily-preview.sh`](../scripts/nyxus-daily-preview.sh).

---

## The short version

```bash
cd ~/Nyxus-Core
sudo bash scripts/nyxus-daily-preview.sh
```

Then **log out**, and at the greeter pick the user **`nyxdaily`** (password
`nyxdaily` on first creation) with the session **NYXUS (Hyprland)**. That is the
Daily theme. Log out again and pick your own account to go back. Nothing about
your account changed.

Want to see what it will do before it does anything? This needs no root and
changes nothing:

```bash
bash scripts/nyxus-daily-preview.sh --dry-run
```

---

## Why a second user account

The Daily theme is not a setting — it is **a set of files at fixed paths inside
one user's home**: `~/.config/nyxus/accent.json`, `~/.config/nyxus/wallpaper.conf`,
`~/.config/hypr/`, `~/.config/eww/`, `~/.config/gtk-3.0` and `gtk-4.0`. On top of
that, `nyxus-apply-accent` rewrites about two dozen of those files in one pass
every time a palette is applied.

So a second *session entry* would not work: two sessions sharing one `$HOME`
would keep overwriting each other's theme, and whichever you logged into last
would win. A second **user** gets a completely separate `~/.config` for free.
That is real isolation, not a convention we have to remember to respect — and it
means your own desktop cannot be damaged by anything we do to the Daily theme.

---

## What the script actually does

Everything it writes lands inside `/home/nyxdaily`, with exactly one exception:
creating the account itself touches `/etc/passwd`, `/etc/shadow` and
`/etc/group`. No system theme file, nothing under `/etc/greetd`, nothing under
`/usr/share` is modified.

In order:

1. **Guards.** It refuses to run if the target account is you, `root`, `nyx`,
   uid 1000, any uid below 1000, or if the home it would write to is your home,
   `/home/nyx`, or a directory another account already claims.
2. **Creates `nyxdaily`** if missing, with the group set the NYXUS desktop needs
   — `wheel,audio,video,input,storage,network,uucp` — taken verbatim from the
   ISO's `customize_airootfs.sh`, which is what creates the real `nyx` user.
   Groups that do not exist on this machine are skipped with a warning rather
   than aborting the run. On a re-run it only tops up memberships that are
   missing.
3. **Lays the shared skel** (`iso-builder/nyx-profile/airootfs/etc/skel/`) into
   the preview home — the same base every NYXUS account starts from.
4. **Overlays the Daily edition** from `artifacts/nyxus-config/editions/daily/`:
   `accent.json`, `wallpaper.conf`, `wallpaper.json`, `wall-rotation.list`, and
   `hyprlock-accent.conf`. Files that do not exist yet are skipped quietly and
   picked up automatically on the next run once they land.
5. **Puts the four approved wallpapers** in `~/.config/hypr/walls/` and repoints
   any `/usr/share/backgrounds/nyxus/…` path in the preview's wallpaper config
   that does not resolve on this machine. Without that step the desktop would
   silently fall back to `nyxus-nebula-01.png` and look like the theme failed —
   this machine's `/usr/share/backgrounds/nyxus` predates the urban walls.
6. **Applies the accent for real** by running the repo's own
   `nyxus-apply-accent` as the preview user, which re-skins eww, GTK, hyprlock,
   the Hyprland borders, rofi, dunst, the terminals and the rest from the
   canonical baseline. This is the same engine the ISO uses, not a
   reimplementation.
7. **Marks the preview home as already bootstrapped** so `nyxus-bootstrap` does
   not run — see [First-boot bootstrap](#first-boot-bootstrap) below.
8. **Chowns the home** to `nyxdaily`, mode 0700.

---

## Refreshing after we change the theme

Re-run the exact same command:

```bash
cd ~/Nyxus-Core
sudo bash scripts/nyxus-daily-preview.sh
```

That is the whole point of the harness. A refresh **re-lays the preview home
from the current repo contents**, so whatever we changed in
`artifacts/nyxus-config/editions/daily/` or in the shared skel shows up. Running
it twice in a row produces byte-identical results.

Two things worth knowing:

- **Log out of the preview account first.** A running Hyprland holds the old
  config in memory, so refreshing underneath a live session shows you a mix of
  old and new. The script warns you if it sees a live `nyxdaily` session.
- **A refresh overwrites the preview home's config.** Anything you customised
  by hand inside the preview account is replaced. Treat that account as
  disposable — it is a viewing window, not a second workspace.

---

## The known limitation: the login screen stays alien

**The greeter will not change, no matter which user you pick. This is expected,
not a bug — please don't report it as one.**

The greeter is greetd + regreet, themed by **`/etc/greetd/regreet.css`**. That
file is **system-wide** and is rendered **before** you choose a user — at that
moment nothing in the system knows which account you are about to log into, so
there is nothing to key a per-user theme off. The Daily greeter CSS therefore
cannot be previewed this way; the only honest preview of the Daily login screen
is a `NYX_EDITION=daily` bake, where `regreet.css` is staged at build time.

Because installing it would repaint *your* login screen too — the exact blast
radius this harness exists to avoid — the script stages the Daily
`regreet.css` as a **reference copy only**, at
`/home/nyxdaily/.config/nyxus/daily-preview/regreet.css`. It is never applied.

So: **login screen = alien, desktop after login = Daily.** That is the deal.

Same reasoning, smaller scale, for the lock screen: `hyprlock` is per-user, so
the preview account *does* get the Daily lock accent — but hyprlock's appearance
cannot be judged in a VM at all (it renders nothing under `virtio-vga-gl`), so
what you see on this machine is the first real look at it.

---

## First-boot bootstrap

By default the preview home is pre-marked as bootstrapped, so `nyxus-bootstrap`
no-ops at login and the heavier web-app / chrome-library layer is **not**
installed in the preview account.

That is deliberate. `nyxus_install.sh` calls plain `sudo pacman -S` in several
places, and sudo on this machine is fingerprint-only — inside a login sequence
that becomes an invisible auth prompt that stalls the session. The preview
exists to look at the **theme**, and the theme ships entirely in the skel.

If you do want the full first-boot install in the preview account:

```bash
sudo bash scripts/nyxus-daily-preview.sh --with-bootstrap
```

Expect it to want a sudo prompt you cannot see. Be ready to switch to a TTY.

---

## Removing it entirely

```bash
cd ~/Nyxus-Core
sudo bash scripts/nyxus-daily-preview.sh --remove
```

It asks you to type the account name to confirm, then terminates any live
session for that user, deletes the account and deletes `/home/nyxdaily`. Add
`--yes` to skip the prompt. Your own account is never in scope.

To see exactly what removal would do without doing it:

```bash
bash scripts/nyxus-daily-preview.sh --remove --dry-run
```

---

## Options

| Option | What it does |
|---|---|
| `--user NAME` | preview account name (default `nyxdaily`) |
| `--password PW` | password, set **on creation only** (default: the username) |
| `--no-wheel` | leave the preview account out of `wheel`, i.e. no sudo at all |
| `--with-bootstrap` | let `nyxus-bootstrap` run at first login |
| `--dry-run` | print every action, change nothing, **no root required** |
| `--remove` | delete the preview account and its home |
| `--yes` | skip the confirmation prompt on `--remove` |

---

## If something looks wrong

- **Wrong wallpaper.** Check `~/.config/nyxus/wallpaper.conf` in the preview
  account — the path should point at `~/.config/hypr/walls/…` on this machine,
  not `/usr/share/backgrounds/nyxus/…`. Re-run the script; step 5 fixes this.
- **Colours still violet/magenta.** The accent pass needs `jq` and `python3`.
  The script warns loudly if either is missing and continues without them, so
  read the output — a warning there means the palette was never applied.
- **No sound / no mouse / no GPU in the preview session.** A group is missing.
  Re-run the script; it tops up memberships. If it warned that a group does not
  exist on this machine, that is the one to chase.
- **The login screen is still alien.** That is not a fault. See above.

---

## Scope notes (things this harness does *not* prove)

- It provisions from the **committed skel**. The bake additionally wipes and
  restages `skel/.config/hypr` and `skel/.config/eww` from
  `artifacts/api-server/nyxus-scripts/` (bring-up plan §1.3), so if those two
  trees have drifted from their bake sources, the preview shows the committed
  copies, not exactly what an ISO would ship.
- It previews the **theme**, not the Daily *shell*. The Windows-shaped taskbar,
  Start menu and notification flyout from the product brief do not exist yet;
  when they land as `editions/daily/eww/*` the script picks them up
  automatically.
- It says nothing about the ISO. Only a `NYX_EDITION=daily` bake and a UEFI boot
  prove greetd, first-boot and the skel bootstrap.

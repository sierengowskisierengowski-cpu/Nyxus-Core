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
Daily theme, on a full NYXUS desktop with its own copy of the tool layer. Log
out again and pick your own account to go back. Nothing about your account
changed.

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
`/usr/share` or `/opt` is modified, and it never reads another user's home.

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
6. **Installs the NYXUS tool layer** into the preview home — see the next
   section, which is the whole reason the first preview came up bare.
7. **Applies the accent for real** by running the preview account's own copy of
   `nyxus-apply-accent`, which re-skins eww, GTK, hyprlock, the Hyprland
   borders, rofi, dunst, the terminals and the rest from the canonical
   baseline. This is the same engine the ISO uses, not a reimplementation.
8. **Paints the app icons** (`nyxus_gen_icons.py`) into
   `~/.local/share/icons/`, best-effort — it needs `python-cairo`, and a
   missing icon is cosmetic.
9. **Marks the preview home as already bootstrapped** so `nyxus-bootstrap` does
   not run — see [First-boot bootstrap](#first-boot-bootstrap) below.
10. **Chowns the home** to `nyxdaily`, mode 0700.

---

## The tool layer (why the first preview came up bare)

The first time the preview account was used it logged in to a **bare desktop**:
right wallpaper, right accent colours, no NYXUS shell. The theme was fine. The
cause was permissions.

On this machine the NYXUS tools are installed into **your** home:

```
/home/cosmic/.local/bin    164 nyxus-* commands
/home/cosmic               drwx------  (0700)
/usr/local/bin              56 nyxus-* commands
```

109 of those 164 existed only under `/home/cosmic/.local/bin`, and your home is
0700, so `nyxdaily` could not traverse into it, let alone execute anything
there. `nyxus-session-start` happens to be one of the ones that *is* in
`/usr/local/bin`, which is why the session started at all instead of failing
outright — but nearly everything it launches afterwards to build the desktop
was behind that wall, so the shell never assembled. It is also why the accent
pass had to be run by hand the first time.

The fix is not to loosen your home's permissions. The preview account now gets
**its own copy** of the tool layer from the repo, which is what a real Daily ISO
does for its user anyway. Concretely:

| What | Where it lands | Where the definition comes from |
|---|---|---|
| 95 launchers | `~/.local/bin/` (0755) | the `LAUNCHERS` array in `nyxus_install.sh` |
| 10 GTK app wrappers | `~/.local/bin/` (0755) | `APPS_LIST` in `build-iso.sh` |
| 2 package launchers | `~/.local/bin/` (0755) | `nyxus-panel` / `nyxus-start` ship their own |
| 3 backstop tools | `~/.local/bin/` (0755) | names `hyprland.conf` calls that were still unreachable |
| 54 Python modules | `~/.nyxus/` | every `nyxus_*.py` in `nyxus-scripts`, same set the bake puts in `/opt/nyxus` |
| 3 app packages | `~/.nyxus/nyxus-{panel,start,home}/` | `nyxus-scripts/` and `artifacts/nyxus-home/src` |
| 52 desktop entries | `~/.local/share/applications/` | `nyxus-scripts/desktop-entries/` |
| 16 app backgrounds | `~/.nyxus/backgrounds/` | `nyxus-scripts/nyxus-bg-*.png` |

That takes the preview from roughly 55 reachable commands to **148** — 110 in
its own `~/.local/bin` plus the 56 root-owned ones in `/usr/local/bin` that
were always shared.

Two things about how that list is built are worth knowing, because they are
what keeps it from rotting:

- **Every set is parsed out of an existing definition at run time.** The script
  adds no list of its own. `install.sh` and `nyxus_install.sh` once drifted
  apart in both directions and which tools you got depended on which installer
  ran — `verify-profile` gate 13pg exists because of it. This script reads the
  same arrays those gates check, and warns if the two disagree.
- **The executable bit is decided by looking at the file**, not assumed: a
  shebang or an ELF header gets 0755, everything else 0644. This project has
  shipped 116 executables at mode 644 before.

---

## Refreshing after we change the theme

Re-run the exact same command:

```bash
cd ~/Nyxus-Core
sudo bash scripts/nyxus-daily-preview.sh
```

That is the whole point of the harness. A refresh **re-lays the preview home
from the current repo contents** — theme *and* tool layer — so whatever we
changed in `artifacts/nyxus-config/editions/daily/`, in the shared skel, or in
`artifacts/api-server/nyxus-scripts/` shows up. Running it twice in a row
produces byte-identical results.

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

That is genuinely all of it. Because the harness only ever writes inside the
preview home, `userdel -r` takes the tool layer, the Python modules, the
desktop entries and the icons with it — there is nothing scattered around the
system to clean up afterwards.

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

The first thing to read is the session log. `nyxus-session-start` sends the
compositor's whole output there instead of to the VT:

```
~/.cache/nyxus/hyprland-session.log
```

A missing tool shows up there as a "command not found" or a `source= … found no
match` line, which is a much faster answer than guessing from the screen.

- **The desktop is bare — no bars, no dock, no Hub.** That was the original
  fault and the tool-layer step is the fix. Check that
  `/home/nyxdaily/.local/bin` has about 110 `nyxus-*` entries; if it is empty,
  the tool-layer step did not run, and its warnings will say why.
- **A specific feature does nothing, silently.** Almost always an unreachable
  command. The script prints a `named in hyprland.conf but not resolvable to a
  tool` line listing everything it could not satisfy — check there first.
- **An app opens a window and paints nothing.** Its Python module, or one of
  the siblings it imports, is missing from `~/.nyxus/`. The generated wrappers
  print which file they were looking for when they fail.
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

## Where this approach runs out (read before chasing the next gap)

The tool layer closes the gap that made the desktop bare, but it does not make
a preview account identical to a booted NYXUS install, and it cannot. These
things live outside any user's home, so a harness that refuses to write outside
the preview home structurally cannot reproduce them:

- **`/opt/nyxus`.** The bake installs every `nyxus_*.py` there and gives each
  user a `~/.nyxus` of symlinks pointing back at it. On this machine
  `/opt/nyxus` holds 15 modules, not the ~50 the bake stages. The preview gets
  real copies in `~/.nyxus` instead, which covers the launchers — but anything
  hardcoded to `/opt/nyxus` still sees the short list. Same story for
  `/opt/nyxus-notes` and `/opt/nyxus-intel`.
- **systemd user units are present but not enabled.** The skel ships nine
  `.service` files and no `*.target.wants` symlinks, so nothing enables them on
  a fresh account. Your own account only has `nyxus-ws-wallpaperd` enabled, so
  the preview matches you here — but if a Daily feature ends up depending on
  `nyxus-dockd` / `nyxus-qsd` / `nyxus-snapd` actually running, neither account
  is proving it. Three of those units also `ExecStart` straight out of
  `/opt/nyxus`.
- **Polkit rules and the privileged helpers.** Those belong in `/usr/local/bin`
  root-owned, with policy files under `/usr/share/polkit-1`. The harness
  deliberately does not install user-writable copies — a user-writable shadow
  of a root-invoked helper, earlier on `PATH`, is not something worth adding to
  a machine for the sake of a theme preview.
- **21 tools your own account has that the preview still will not.** They are
  the ones neither installer's allowlist names and `hyprland.conf` never calls:
  `nyxus-consoles`, `nyxus-webapp`, `nyxus-battery`, `nyxus-netusage`,
  `nyxus-wallpaper-studio` and similar. They are reachable for you because your
  `~/.local/bin` accumulated them over time, not because anything deploys them.
  That is worth knowing on its own: **your account is not reproducible from the
  repo**, and the preview account is closer to a real install than it is.
- **The greeter**, for the reason in the section above.

The honest reading: this harness is the right tool for looking at **theme and
palette**, and good enough for exercising most of the shell. The moment a
question depends on services starting in the right order, on `/opt` content, on
polkit, or on the greeter, **a `NYX_EDITION=daily` bake and a UEFI boot is the
cheaper answer** — it is the only thing that proves greetd, first-boot,
squashfs and the skel bootstrap together. Anything the preview shows about
those is a coincidence of how this particular machine happens to be set up.

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

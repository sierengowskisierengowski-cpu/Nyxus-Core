# NYXUS — DESKTOP-ENVIRONMENT COMPLETENESS & TWO-EDITION ARCHITECTURE

**Date:** 2026-07-31 · **Type:** architecture study — research and specification only
**Status:** nothing implemented. No config, eww, `HANDOFF.md` or `verify-profile.sh`
file was touched by this study. This document is the entire deliverable.

> **Two questions from the owner:**
> 1. *"How do you make Hyprland a real, true desktop system?"* — Hyprland is a
>    compositor, not a desktop environment. What would it take for NYXUS to be a
>    genuinely complete system that works like a real OS?
> 2. Should there be a second **daily-driver edition** — *"a single layer system,
>    no workstations, only the main station… a really normal desktop… nothing
>    fancy as in security tooling"* — with the same theme, style and palette?

---

## 0. HOW TO READ THIS, AND WHAT WAS ACTUALLY VERIFIED

Every claim below is tagged. The project has lost days to agents asserting
things they inferred, so the distinction is load-bearing.

| Tag | Meaning |
|---|---|
| **[REPO]** | Read directly out of the canonical tree at `main` today. High confidence. |
| **[PKG]** | Resolved against the live Arch package databases on the builder box (`pacman -Si`, `pacman -Qi`). High confidence for *what a bake would install*. |
| **[DOC]** | Taken from `HANDOFF.md` or a dated brief that recorded a live measurement. Confidence inherits from that record. |
| **[INFER]** | Reasoned, not measured. Treat as a hypothesis to confirm on the next stick. |

**What this study could NOT do, and did not fake:** no `sudo`, no bake, no boot.
Everything about runtime behaviour on a real stick — whether portals actually
answer, whether the greeter picks the right session, whether a MIME association
resolves — is **[INFER]** at best. Two other agents are active (an ISO VM audit
owning the working tree and VM session, and the eye-candy design spec). This
study stayed out of both; the eye-candy spec owns visual design and is not
duplicated here.

**Version basis:** Hyprland **0.56.1** on the ISO, **0.55.4** on the builder box
(gate `13x` warns on the skew). eww 0.5.0. ALIEN NEON locked,
`follow_wallpaper` off, `#f4ead5` and `#a06bff` banned. Package facts are from
`iso-builder/nyx-profile/packages.x86_64` (408 effective entries) resolved
transitively — **not** from memory of what a Hyprland setup "usually" has.

---

## 1. DE COMPLETENESS GAP ANALYSIS

### 1.0 The headline

**The working thesis — "NYXUS is already ~85% a desktop environment and simply
has not been declared or completed as one" — is correct, and if anything
understates the compositor-and-shell half.** By component *count* NYXUS ships
more of a desktop environment than XFCE does. What it is missing is not shell —
it is the boring **integration plumbing** that nobody notices until it is
absent: file-type associations, a desktop surface, clipboard history, media
auto-mount. Those are exactly the things that make a custom setup "feel
unfinished" to someone who has never used Linux.

Three findings reframe the question, and all three are the same shape as the
`~/.local/bin` bug that cost weeks: **something is built, correct, and shipped,
but cannot run.**

1. **The desktop layer already exists.** `nyxus_desktop.py` is a 45 KB GTK4
   layer-shell desktop client that paints the wallpaper per-monitor, catches
   mouse events and dispatches right-clicks to `nyxus-context-menu.sh` (12.5 KB,
   also shipped). `build-iso.sh` stages both and generates a `/usr/local/bin/nyxus-desktop`
   launcher. **It cannot start on the ISO**, and **nothing launches it anyway.**
2. **MIME handling is effectively absent**, not partly configured — and it fails
   in three independent ways at once.
3. **Four packaged, Settings-exposed subsystems are never started**: clipboard
   history, removable-media auto-mount, the secret store, and the XDG autostart
   spec.

None of these is a redesign. All of them are wiring.

### 1.1 Component-by-component inventory

Legend: **✅** complete · **⚠** ships but incomplete or unverified · **❌** real gap.

#### Shell and session — the part that is already done

| Component | What NYXUS ships today | State |
|---|---|---|
| **Compositor / WM** | Hyprland 0.56.1, `hyprland.conf` + 17 `conf.d` shards, 156 active binds, 24+ window rules, named stations, scratchpad **[REPO]** | ✅ Complete, and richer than most DEs |
| **Panel / bar** | eww: 4 bars (top/bottom/left rail/right rail) + 10 station decks, CAVA-reactive, mood/threat-reactive **[REPO][DOC]** | ✅ Complete, bespoke |
| **Launcher** | rofi + wofi packaged; eww `start-panel` (START station) is the real Start menu; `nyxus-hub` is the quick-settings/apps surface **[REPO]** | ✅ Complete — arguably three launchers where one would do |
| **Notifications** | dunst + `nyxus-notif-to-eww` bridge; hacker-mode variant; DND in Settings **[REPO]** | ✅ Complete (bridge was dead on every stick until the `~/.local/bin` fix — **[DOC]**) |
| **Terminal** | alacritty (primary) + kitty, both ALIEN NEON themed **[PKG][REPO]** | ✅ Complete |
| **Lock** | hyprlock, urban-alien hero, weather/track/art widgets **[REPO]** | ✅ Complete |
| **Idle** | hypridle 45 s glass → 300 s dim + saver → 600 s lock + DPMS → 900 s suspend; fullscreen inhibits **[REPO]** | ✅ Complete |
| **Session / login** | greetd + regreet (themed) with tuigreet and agreety fall-through; `nyxus-greeter` rescales the login card per detected panel **[REPO][DOC]** | ⚠ See 1.2-A |
| **Logout / power** | wlogout (`Super+Shift+E`), eww `powermenu` (`Super+Escape`), `nyxus_powermenu.py` (app menu) **[REPO]** | ⚠ Three surfaces for one job |
| **Control center** | `nyxus_settings.py`, 48 documented sections (57 claimed after the Jul-24 pass), GTK4 + libadwaita, deep-linkable **[REPO][DOC]** | ⚠ ~95% — see 1.4 |
| **Screenshot / recording** | `nyxus_screenshot.py` (grim+slurp, region/window/fullscreen/annotate) on 4 binds; `wf-recorder` + `nyxus-record` + Settings page **[REPO][PKG]** | ✅ Complete |
| **Polkit agent** | `polkit-gnome` packaged, `exec-once = /usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1`, plus a `dim_around` window rule for it **[REPO][PKG]** | ✅ Complete |
| **Audio** | pipewire + pipewire-pulse/alsa/jack + wireplumber + pavucontrol + easyeffects (autostarted) + Settings Sound page **[REPO][PKG]** | ✅ Complete |
| **Display / monitors** | `hyprctl monitors`, `wdisplays`, `nwg-displays`, Settings Displays writing `nyxus-monitors.conf`, `wlsunset` night light **[REPO][PKG]** | ✅ Complete |
| **Printing** | cups + cups-pdf + system-config-printer; `cups.service` enabled at bake; Settings Printers page **[REPO][PKG]** | ✅ Complete |
| **Network** | NetworkManager (enabled), full `nmcli` Settings page, VPN/DoH/MAC pages; `nm-applet` XDG autostart deliberately suppressed **[REPO]** | ✅ Complete via Settings |
| **Bluetooth** | `bluetooth.service` enabled, blueman packaged, `bluetoothctl` Settings page **[REPO][PKG]** | ⚠ No tray applet started — Settings-only |
| **Cursor / icon / font themes** | `NYXUS-Aurora` cursor + `NYXUS-Dark` icon theme both shipped under `/usr/share/icons`; `hyprctl setcursor` at login; Inter/Orbitron/Permanent Marker/JetBrains Mono **[REPO]** | ✅ Complete |
| **Trash** | gvfs present (nautilus dependency) → `gio trash` and the Files trash work **[PKG]** | ✅ Complete |
| **Accessibility** | Settings page: cursor size, animations, text scale, `orca` + `at-spi2-core` + `espeak-ng` packaged **[REPO][PKG]** | ⚠ `magnus` and `wvkbd` are launched by Settings but **not packaged** — guarded, so they toast rather than dying |

#### The gaps

| Component | Evidence | State |
|---|---|---|
| **Desktop layer** (right-click, icons) | Built and staged; **`gtk4-layer-shell` is not in `packages.x86_64`** and nothing launches it. See 1.2-C | ❌ |
| **MIME / default apps** | No `mimeapps.list` anywhere in the repo; **0 `MimeType=` lines across all 63 shipped `.desktop` files**; the one firstboot fragment runs in the wrong user context, covers 3 types, and targets an uninstalled app. See 1.2-B | ❌ |
| **Clipboard manager** | `cliphist` + `wl-clipboard` packaged, `nyxus_clipboard.py` shipped, Settings has a Clipboard page — and **no `wl-paste --watch cliphist store` exists in any `exec-once`**. See 1.2-D | ❌ |
| **Removable media** | `udisks2` + `udiskie` packaged. `udiskie` appears in exactly two places in the tree, both of them `nyxus-security` calling `udiskie-umount`. **Nothing ever starts it.** See 1.2-E | ❌ |
| **XDG autostart spec** | `~/.config/autostart/` ships with one entry (`nyxus-welcome.desktop`), and **nothing in the session reads that directory**. Settings Accessibility writes autostart entries that will never fire. See 1.2-F | ❌ |
| **Keyring / secrets** | `gnome-keyring` arrives transitively (seahorse → `org.freedesktop.secrets`), but **nothing starts `gnome-keyring-daemon` and no `pam_gnome_keyring` line exists**. See 1.2-G | ⚠ |
| **XDG portals** | All three packages present *and* `XDG_CURRENT_DESKTOP=Hyprland` is exported. **No explicit portal config ships.** See 1.2-H | ⚠ |
| **Qt theming** | `qt5ct`/`qt6ct` config dirs ship in skel; **neither package is installed**. `QT_QPA_PLATFORMTHEME=adwaita-dark` is set but `adwaita-qt5`/`adwaita-qt6` are absent. See 1.2-I | ⚠ |
| **GTK theming** | `/etc/environment.d/90-nyxus-theme.conf` sets `GTK_THEME=Adwaita:dark`, which **overrides** skel's `gtk-theme-name=adw-gtk3-dark`. See 1.2-I | ⚠ |
| **Thumbnailing** | Image thumbnails work (nautilus 4x uses glycin, a hard dep). `tumbler` and `ffmpegthumbnailer` are absent → no video/PDF thumbnails **[PKG]** | ⚠ Low impact |
| **Document / image viewers** | No PDF viewer (no zathura/evince/atril), no image viewer (no loupe/eog/imv/gthumb). `file-roller`, `gnome-text-editor`, `mpv` are present | ⚠ Compounds the MIME gap — see 1.2-B |

### 1.2 The gaps in detail

#### A · Session entry is still ambiguous, and the greeter is unverified

The ISO ships **three** entries in `/usr/share/wayland-sessions`: upstream
`hyprland.desktop`, `hyprland-uwsm.desktop`, and `nyxus-hyprland.desktop`.
`/var/lib/regreet/` and `/var/cache/regreet/` ship empty, so regreet has no
cached last-session and no configured default — it preselects whatever sorts
first, which is almost certainly plain "Hyprland", not NYXUS **[DOC]**. The
tuigreet/agreety fallbacks *do* hardcode `--cmd nyxus-session-start`, so only
the themed path is ambiguous.

The practical delta shrank once the `~/.local/bin` bug was fixed (plain Hyprland
reads the same `hyprland.conf`), but `nyxus-session-start` is what exports
`XDG_CURRENT_DESKTOP=Hyprland` **[REPO]** — and that variable is what portals
key off. **So the session-selection ambiguity and the portal question in 1.2-H
are the same bug.** If the greeter starts upstream `hyprland.desktop`, portals
may pick the wrong backend or none.

This was deliberately not changed by earlier sessions because guessing at login
behaviour risks a no-desktop boot. That judgement still holds. **The fix is one
observation on the next stick** — read the greeter's dropdown — followed by
either dropping the two upstream entries at bake or pre-seeding
`/var/lib/regreet/state.toml`.

#### B · MIME handling — the biggest single "feels unfinished" gap

This fails in **three independent ways**, which is why it has stayed invisible.

**1. No application declares what it can open.** Across all **63** `.desktop`
files shipped in `airootfs/usr/share/applications/`, there are **zero**
`MimeType=` lines **[REPO]**. `nyxus-files`, `nyxus-notepad`, the Intel suite,
the Arsenal launchers — none of them register as a handler for anything. So even
a correct `mimeapps.list` would have nothing NYXUS-branded to point at.

**2. No `mimeapps.list` ships.** A repo-wide search finds the file nowhere
**[REPO]**.

**3. The one script that would set defaults cannot work.**
`/etc/nyxus-firstboot.d/03-mime-defaults.sh` is three `xdg-mime default` calls.
Each of the three ways it fails is independent:

```
xdg-mime default nyxus-files.desktop      inode/directory
xdg-mime default nyxus-notepad.desktop    text/plain
xdg-mime default org.kde.kate.desktop     text/x-c text/x-c++ text/x-python
```

- **Wrong user.** `nyxus-firstboot.service` has no `User=`, so it runs as
  **root**. `xdg-mime default` writes to `$XDG_CONFIG_HOME/mimeapps.list` — i.e.
  `/root/.config/mimeapps.list`. The `nyx` user never sees it **[REPO][INFER]**.
- **Wrong target.** `org.kde.kate.desktop` — **`kate` is not in
  `packages.x86_64`** **[PKG]**.
- **Wrong coverage.** Three MIME classes. **No PDF, no image, no video, no
  audio, no archive, no `x-scheme-handler/http`.** Every command is `|| true`,
  so all of this fails silently.

**What actually happens today when a user double-clicks a file [INFER]:**
`xdg-open` *is* present — but only because **chromium hard-depends on
`xdg-utils`** **[PKG]**. With no user `mimeapps.list`, resolution falls through
to the desktop-file cache, and the winner is whichever installed `.desktop`
claims the type. In practice **Firefox claims `application/pdf`, most image
types and the http/https schemes** **[PKG]**. So a PDF opens in a browser tab, a
PNG opens in a browser tab, and there is no image viewer or PDF reader at all.
That is not broken, but it is unmistakably *unfinished* — and it is precisely
the impression a Windows or macOS user forms in the first five minutes.

> ⚠ **This gap and the daily edition are coupled.** The `packages.x86_64.lean`
> tier drops `chromium` **[REPO]** — which removes `xdg-utils`, i.e. `xdg-open`
> and `xdg-mime` themselves. See §3.2.

#### C · The desktop layer is built, correct, staged, and cannot run

This is the most surprising finding in the study, and it is good news.

`airootfs/opt/nyxus/desktop/nyxus_desktop.py` (45,227 bytes) is a complete GTK4
layer-shell desktop client. Its own docstring: *"Replaces swaybg. Paints the
wallpaper itself per-monitor at the `bottom` layer-shell layer (under bars,
under all windows). Catches mouse events on the wallpaper and dispatches to
nyxus-context-menu.sh."* It has icon-grid code, multi-monitor hot-plug, and an
IPC socket for live wallpaper hot-swap **[REPO]**.

**It obeys the HANDOFF §7 rule.** The rule exists because a full-screen input
surface on the OVERLAY layer traps the desktop and has forced multiple hard
resets. This client does the right thing:

```
LayerShell.set_layer(self, LayerShell.Layer.BOTTOM)
LayerShell.set_exclusive_zone(self, -1)
LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)
```

BOTTOM layer, so every window and every bar renders above it and it cannot
swallow anything. `ON_DEMAND` keyboard mode, not the session-wide
`EXCLUSIVE` grab that trapped the owner in `nyxus-start`. **A desktop surface
must catch clicks — that is its entire job — and because it is the bottom
layer, catching them is correct rather than dangerous.** The §7 warning is about
OVERLAY surfaces; this is the compliant shape.

`build-iso.sh` stages the payload, stages `nyxus-context-menu.sh` into
`/usr/local/bin`, and generates the launcher **[REPO]**:

```
655:  install -Dm0644 "${NS}/desktop/nyxus_desktop.py" "${OPT_NYXUS}/desktop/nyxus_desktop.py"
793:  install -m 0755 "${NS}/desktop/nyxus-context-menu.sh" "${LBIN}/nyxus-context-menu.sh"
1112: cat > "${LBIN}/nyxus-desktop" <<'LAUNCHER'
```

**Two things stop it, and both are one-liners:**

1. **The dependency is not packaged.** The file does
   `gi.require_version("Gtk4LayerShell", "1.0")`, which needs the Arch package
   **`gtk4-layer-shell`**. `packages.x86_64` contains **`gtk-layer-shell`** (the
   GTK**3** library, a different package) and `swaybg`, and **not**
   `gtk4-layer-shell` **[PKG][REPO]**. The import is wrapped in `try/except`
   whose fallback is `os.execvp("swaybg", …)` — so on a stick it would silently
   degrade to a plain wallpaper with no right-click and **no error anyone would
   ever see**.
2. **Nothing launches it.** The wallpaper `exec-once` is
   `command -v nyxus-live-wallpaper && nyxus-live-wallpaper auto || nyxus-wallpaper-autostart`
   **[REPO]**. `nyxus-desktop` appears in no `exec-once` and no unit.

This is the same class as `nyxus-sense` (built, consumed, never launched) and
the four unsourced hypr shards. The pattern is now well documented; this is one
more instance of it.

#### D · Clipboard history is packaged, exposed in Settings, and never populated

`cliphist` and `wl-clipboard` are both in `packages.x86_64` **[PKG]**.
Settings has a Clipboard page (history size, persistence, secrets filter)
**[DOC]**. `nyxus_clipboard.py` ships.

The two lines that make any of it work —

```
exec-once = wl-paste --type text  --watch cliphist store
exec-once = wl-paste --type image --watch cliphist store
```

— exist in exactly one place in the tree: **inside a Python string literal in
`nyxus_clipboard.py`, where they are printed to the user as setup instructions**
**[REPO]**. A direct grep of `hyprland.conf` and every `conf.d` shard for
`cliphist`/`wl-paste` in an `exec-once` returns nothing. So on a fresh boot the
clipboard history is permanently empty and the Settings page manages a store
that nobody writes to.

#### E · Removable media never auto-mounts

`udisks2` and `udiskie` are packaged **[PKG]**. Repo-wide, `udiskie` appears in
four places: the two package lists, and twice in `nyxus-security` calling
`udiskie-umount -a` to *unmount* everything during a panic **[REPO]**.
**Nothing starts the mount daemon.** Insert a USB stick on the ISO and nothing
happens — no notification, no mount, no icon. For a "never used Linux" user this
is one of the loudest possible signals that a system is not a real OS.

#### F · The XDG autostart spec is not implemented

`etc/skel/.config/autostart/` ships with `nyxus-welcome.desktop` in it
**[REPO]**. Nothing in `hyprland.conf` or any shard scans `~/.config/autostart`
or `/etc/xdg/autostart`. (The welcome app is actually launched by its own
`exec-once` with a `welcome.done` guard, so the autostart entry is decorative.)

This matters more than it looks: **Settings Accessibility writes assistive-tool
entries into XDG autostart** **[DOC]**, and `customize_airootfs.sh` goes to the
trouble of *neutralising* `/etc/xdg/autostart/nm-applet.desktop` **[REPO]** — a
defence against a mechanism that is not running. Any third-party app the user
installs that expects autostart to work will not start.

#### G · The secret store is present but never started

`seahorse` is packaged and depends on the virtual `org.freedesktop.secrets`,
which `gnome-keyring` provides **[PKG]** — so the daemon binary will be on the
ISO. But there is **no `gnome-keyring-daemon` in any `exec-once` or unit, and no
`pam_gnome_keyring` line in the greetd PAM chain** **[REPO]**. Applications that
use libsecret (browsers saving passwords, any app storing a token) will find no
secret service. NetworkManager is unaffected — it has its own store.

#### H · Portals: packaged and probably fine, but nothing asserts it

`xdg-desktop-portal`, `xdg-desktop-portal-hyprland` and `xdg-desktop-portal-gtk`
are **all three in `packages.x86_64`** (lines 97, 98, 330) **[REPO]**, which is
the correct set. `nyxus-session-start` exports `XDG_CURRENT_DESKTOP=Hyprland`
and runs `dbus-update-activation-environment` **[REPO]**. There is even a
`dim_around` window rule for `xdg-desktop-portal-gtk` **[REPO]**, which implies
someone once saw its file chooser appear.

**No portal configuration ships** — no `hyprland-portals.conf`, no
`portals.conf` anywhere in the repo **[REPO]**. Upstream
`xdg-desktop-portal-hyprland` normally supplies its own backend preference file,
so this is likely fine. **But two things make it worth one verification on the
next stick rather than an assumption:**

- If the greeter starts upstream `hyprland.desktop` instead of
  `nyxus-hyprland.desktop` (§1.2-A), `XDG_CURRENT_DESKTOP` is set by the
  upstream entry, not by `nyxus-session-start`, and backend matching changes.
- With both the hyprland and gtk backends installed and no explicit
  preference pinned by NYXUS, which backend answers `ScreenCast` vs `FileChooser`
  is upstream's default, not a NYXUS decision.

**Verification is 10 seconds on a booted stick:** open a file picker from
Firefox and try a screen share. Both working means portals are fine and this row
closes.

#### I · GTK and Qt theming are internally inconsistent

Two separate problems, both cheap:

- **GTK: the env var beats the config.** Skel sets
  `gtk-theme-name=adw-gtk3-dark` with `NYXUS-Dark` icons and the `NYXUS-Aurora`
  cursor **[REPO]**. `/etc/environment.d/90-nyxus-theme.conf` then sets
  `GTK_THEME=Adwaita:dark` **[REPO]** — and `GTK_THEME` has the highest
  precedence in GTK, so **plain Adwaita wins over `adw-gtk3-dark` wherever that
  env var reaches**. The file's own comment says it exists to fix white auth
  popups, which is a real problem it solves, so this is a *conflict between two
  correct intentions*, not a mistake. (Additional wrinkle: `environment.d` is
  read by the systemd user manager; a Hyprland session launched directly by
  greetd is not a child of it, so whether the var reaches GTK apps at all is
  **[INFER]** and differs between apps started by `exec-once` and apps started
  by a systemd user unit. That would explain intermittent white dialogs.)
- **Qt: configured for tools that are not installed.** Skel ships `qt5ct/` and
  `qt6ct/` config directories **[REPO]** and **neither `qt5ct` nor `qt6ct` is in
  `packages.x86_64`** **[PKG]**. `QT_QPA_PLATFORMTHEME=adwaita-dark` is set but
  `adwaita-qt5`/`adwaita-qt6` are **absent** **[PKG]**. So every Qt application
  — and the ISO ships several, plus `xdg-desktop-portal-hyprland` itself links
  qt6-base — falls back to default Fusion, i.e. **light grey**, against an
  ALIEN NEON desktop.

### 1.3 Ranked gap table

Ranked by *distance from "feels like a real OS"* per unit of effort. "Blocker"
means a first-time Linux user would notice within minutes and conclude the
system is unfinished.

| # | Gap | Severity | Effort | Blocker? | One-line fix shape |
|---|---|---|---|---|---|
| **1** | **MIME defaults + `MimeType=` registration** (§1.2-B) | **Critical** | **M** — 63 desktop files to annotate + one `mimeapps.list` + fix the firstboot fragment | **YES** | Ship a skel `mimeapps.list`; add `MimeType=` to the NYXUS apps; move the firstboot fragment into skel or run it as `nyx` |
| **2** | **No image viewer / no PDF viewer** (§1.2-B) | **Critical** | **XS** — 2 package lines | **YES** | Add `loupe` (or `imv`) and `zathura`+`zathura-pdf-mupdf`; then #1 has something to point at |
| **3** | **Removable media never mounts** (§1.2-E) | **High** | **XS** — one `exec-once` | **YES** | `exec-once = udiskie -at` |
| **4** | **Desktop layer dead** (§1.2-C) | **High** | **S** — one package + one `exec-once` | **YES** — this is the owner's own standing request | Add `gtk4-layer-shell`; `exec-once = nyxus-desktop`; gate the launch |
| **5** | **Clipboard history never populated** (§1.2-D) | **High** | **XS** — two `exec-once` lines | Near-blocker | Move the two lines out of the Python string and into a shard |
| **6** | **Session entry ambiguous + portals unverified** (§1.2-A, §1.2-H) | **High** | **S** — one observation, then one bake-time line | Potential blocker (screen share / file pickers) | Read the greeter dropdown on the next stick; then drop the two upstream session entries at bake |
| **7** | **Qt apps render light-grey** (§1.2-I) | Medium | **XS** — 2 package lines | No, but visually jarring | Add `adwaita-qt5` + `adwaita-qt6` (the env var already points at them), or install `qt6ct` to match the shipped config |
| **8** | **Keyring never started** (§1.2-G) | Medium | **XS** — one `exec-once` + one PAM line | No — surfaces later, as "my passwords don't save" | `exec-once = gnome-keyring-daemon --start --components=secrets` |
| **9** | **XDG autostart not implemented** (§1.2-F) | Medium | **S** — one small runner script | No — surfaces when a third-party app is installed | A `nyxus-autostart` that scans both dirs and honours `Hidden`/`OnlyShowIn` |
| **10** | **GTK theme conflict** (§1.2-I) | Medium | **XS** — decide which wins | No | Either drop `GTK_THEME` and fix popups via `adw-gtk-theme`, or accept Adwaita and delete the skel theme line so they stop disagreeing |
| **11** | **Settings' last ~5 terminal escapes** (§1.4) | Medium | **M** | No | Already the Settings workstream's charter |
| **12** | **No video/PDF thumbnails** | Low | **XS** | No | `ffmpegthumbnailer` (+`tumbler` only if a thunar-family FM is ever added) |
| **13** | **Bluetooth has no tray applet** | Low | **XS** | No | `exec-once = blueman-applet`, or accept Settings-only by design |
| **14** | **Three power surfaces** | Low | **S** | No | A naming/consolidation decision, not a bug |
| **15** | **`magnus`/`wvkbd` launched but unpackaged** | Low | **XS** | No | Add both, or remove the rows |

**Note the shape of that list.** Of the top six blockers, **four are a single
line of config or a single package name.** The DE is not missing; it is
unfinished at the seams.

### 1.4 Where a DE gap and a Settings gap are the same gap

The Settings app is being extended under a **"no terminal required"** criterion
(113 → ~21 terminal escapes on PR #83, target ~5) **[DOC]**. That criterion and
DE completeness overlap almost exactly, because *"no terminal required"* and
*"feels like a real OS"* are the same requirement stated twice.

| DE gap | Settings surface | Verdict |
|---|---|---|
| MIME defaults (#1) | **Settings ▸ Apps & Defaults** already claims "default browser/terminal, autostart, mime" **[DOC]** | **Same gap.** The page exists; the substrate under it does not. Fixing #1 makes an existing page truthful. Do #1 first, or the Settings page is a UI over nothing. |
| Image/PDF viewer (#2) | Apps & Defaults default-application pickers | Same gap — a picker with no candidates is worse than no picker |
| Removable media (#3) | No Settings surface today | **Missing on both sides.** Cheapest fix is the `exec-once`; a Settings toggle is optional polish |
| Clipboard (#5) | **Settings ▸ Clipboard** exists and is listed OK **[DOC]** | **Same gap.** The page manages a store nothing writes. This is a *false-green Settings page* — the exact class of "dead control" Increment 1 was created to eliminate |
| Autostart (#9) | **Settings ▸ Apps & Defaults ▸ autostart** and **Accessibility** both write XDG autostart entries **[DOC]** | **Same gap, and worse than it looks** — two Settings pages write to a directory nothing reads |
| Keyring (#8) | No Settings surface; `seahorse` ships as the GUI | Same gap |
| Qt theming (#7) | Settings ▸ Theme Packs / Appearance | Same gap — Settings cannot theme what has no theme engine |
| Desktop layer (#4) | Would need a new Settings section (icons on/off, grid, right-click menu contents) | **New work on both sides**, but the runtime already exists |

**The actionable point:** three Settings pages (Clipboard, Apps & Defaults,
Accessibility) are currently **green over a dead substrate**. That is the same
failure mode as the 25 no-op Resets and 12 blank rows that Increment 1 removed
— it is just harder to see, because the control renders and appears to work.
Whoever continues the Settings work should treat "the backend actually runs" as
part of the completeness criterion, not just "the row is not blank."

---

## 2. THE SHORTEST PATH TO "FEELS LIKE A REAL OS"

The owner asked for the shortest path from where he is to a system that feels
complete **to someone who has never used Linux**. That person's first hour is:
log in, look at the desktop, right-click it, open a file, plug in a USB stick,
copy and paste, change a setting. Everything below is ordered by that hour.

### 2.1 Wave 1 — the ninety-minute wave

Every item here is one package line or one `exec-once`. Together they close
**five of the top six blockers**. This is the highest-leverage work available
anywhere in the project right now.

| # | Change | File | Closes |
|---|---|---|---|
| 1 | `+ gtk4-layer-shell` | `packages.x86_64` | Gap #4 |
| 2 | `+ loupe` (image viewer), `+ zathura`, `+ zathura-pdf-mupdf` (PDF) | `packages.x86_64` | Gap #2 |
| 3 | `+ adwaita-qt5`, `+ adwaita-qt6` | `packages.x86_64` | Gap #7 |
| 4 | `+ ffmpegthumbnailer` | `packages.x86_64` | Gap #12 |
| 5 | `exec-once = udiskie -at` | a new `conf.d` shard | Gap #3 |
| 6 | `exec-once = wl-paste --type text --watch cliphist store` (+ image) | same shard | Gap #5 |
| 7 | `exec-once = gnome-keyring-daemon --start --components=secrets` | same shard | Gap #8 |
| 8 | `exec-once = nyxus-desktop` (guarded with `command -v`) | same shard | Gap #4 |

> ⚠ **Three traps that apply to Wave 1 specifically, all already paid for once:**
>
> - **A new `conf.d` shard must be added to the bake's whitelist AND `source=`d
>   from `hyprland.conf`.** Committing a shard into `airootfs` is not enough —
>   the bake wipes `skel/.config/hypr` and repopulates from NS via a
>   hand-maintained list. This has shipped broken **three** times
>   (`nyxus-arsenal-apps.conf` twice, `nyxus-consoles.conf` once) **[DOC]**.
>   Gate `13w` derives the requirement from `hyprland.conf` itself and will
>   catch it — *if* the `source=` line is added.
> - **Use bare command names, never `~/.local/bin/…`.** Gate `13z` hard-fails
>   otherwise **[DOC]**.
> - **Adding `gtk4-layer-shell` is necessary but not sufficient for the desktop
>   layer.** `nyxus_desktop.py`'s import guard falls back to `swaybg` silently.
>   If the package is added and the desktop still does not appear, the failure
>   will look identical to it not being wired at all. **Verify with
>   `hyprctl layers -j` for a bottom-layer namespace, not by looking at the
>   screen** — a working `nyxus-desktop` and a `swaybg` fallback are visually
>   identical until you right-click.

**Wave 1 does not need a design decision from the owner.** It is entirely
"connect the thing that is already there."

### 2.2 Wave 2 — the MIME wave (the real work)

Gap #1 is the largest single contributor to "feels unfinished" and the only
Wave-1-or-2 item that is genuinely a day of work rather than an hour.

Three pieces, in this order:

1. **Declare handlers.** Add `MimeType=` to the NYXUS apps that are handlers:
   `nyxus-files` (`inode/directory`), `nyxus-notepad` (`text/plain` and
   friends), and any Intel/viewer app that genuinely opens a file type. **Do not
   add `MimeType=` to launcher-style entries** — a `.desktop` claiming a type it
   cannot open is worse than not claiming it.
2. **Ship a `mimeapps.list` in skel** at `etc/skel/.config/mimeapps.list`,
   covering at minimum: directories, plain text, source files, PDF, the common
   image types, audio, video, archives, and `x-scheme-handler/http`+`https`+`mailto`.
   Shipping it in **skel** rather than generating it at firstboot removes the
   user-context bug entirely and makes it reviewable in git.
3. **Fix or delete `03-mime-defaults.sh`.** As written it runs as root, targets
   an uninstalled `kate`, and is redundant once (2) exists. Deleting it is the
   honest option; if it is kept, it must run as `nyx`.

> ⚠ **`xdg-open` is on the ISO only because chromium hard-depends on
> `xdg-utils`** **[PKG]**. That is a load-bearing accident. **Add `xdg-utils`
> and `xdg-user-dirs` explicitly to `packages.x86_64`.** `xdg-user-dirs` is
> reached only transitively via `nautilus → xdg-user-dirs-gtk` — and firstboot
> fragment `02-xdg-user-dirs.sh` calls `xdg-user-dirs-update` with `|| true`, so
> if that chain ever breaks the user silently gets no `~/Documents`,
> `~/Downloads`, `~/Pictures`. This is doubly important for the daily edition,
> which drops chromium (§3.2).

### 2.3 Wave 3 — the one observation

**On the very next stick boot, before anything else: read the greeter's session
dropdown and write down what is preselected.** That single observation settles
§1.2-A and most of §1.2-H. Then, in the same session:

- open a file picker from Firefox (portal FileChooser),
- start a screen share in a browser (portal ScreenCast),
- plug in a USB stick,
- right-click the wallpaper.

Four actions, under a minute, and they convert four **[INFER]** rows in this
document into **[DOC]** rows.

### 2.4 Wave 4 — declare it

The owner's framing — *"Hyprland is a compositor, not a desktop environment"* —
is right, and the last step is the cheapest and the most symbolic: **stop
shipping NYXUS as a Hyprland configuration and start shipping it as a desktop
environment.**

Concretely that means:

- **One session entry.** Drop upstream `hyprland.desktop` and
  `hyprland-uwsm.desktop` at bake so `nyxus-hyprland.desktop` is the only
  choice. This also removes the portal ambiguity and the "which session did it
  start" class of bug permanently.
- **`XDG_CURRENT_DESKTOP=NYXUS:Hyprland`**, not bare `Hyprland`. The colon form
  is the standard way to say "I am NYXUS, and I behave like Hyprland" —
  portals and `OnlyShowIn=` still match `Hyprland`, and NYXUS-specific rules
  become expressible. ⚠ **Change this only *with* Wave 3's verification, not
  before** — anything that currently keys on the exact string `Hyprland` needs
  re-checking, and portal backend selection is exactly such a consumer.
- **Say it in the docs.** `HANDOFF.md` §2 currently describes NYXUS as *"a
  custom Hyprland-based Arch Linux security-lab distro"*. Calling it a desktop
  environment is what makes the completeness criterion legible to the next
  agent — and this study's whole finding is that the gap between the two is
  smaller than anyone assumed.

### 2.5 What is deliberately NOT on the path

| Not doing | Why |
|---|---|
| Migrating to `hyprland.lua` | hyprlang is removed in Hyprland **0.57**; the owner's 2026-07-28 decision is **do not migrate yet** — pin the version, stabilise, migrate on a branch after 0.57 ships **[DOC]**. Gate `13x` hard-fails a bake if the repos offer ≥0.57. See §4.4 |
| Consolidating the three power surfaces | Cosmetic; the eye-candy spec owns look decisions |
| Redesigning the greeter | Net-new work, not a bug hunt — searched exhaustively, there are four `regreet.css` blobs in all of history and `main` has the best one **[DOC]** |
| Adding a dock, a systray daemon, or a second file manager | NYXUS already has more shell surfaces than it needs; adding more is the opposite of feeling finished |

---

## 3. TWO-EDITION ARCHITECTURE

### 3.1 Feasibility and mechanism — recommendation

**Feasible, and the mechanism already exists in a stronger form than the brief
assumed.** `build-iso.sh` does not only have `NYX_WITH_KAGE_RYU`; it already has
an **edition-like tier flag** at line 136 **[REPO]**:

```bash
NYX_ISO_TIER="${NYX_ISO_TIER:-full}"
if [[ "${NYX_ISO_TIER}" == "lean" && -f "${PROFILE_DIR}/packages.x86_64.lean" ]]; then
  cp "${PROFILE_DIR}/packages.x86_64" "${PROFILE_DIR}/packages.x86_64.bake.bak"
  cp "${PROFILE_DIR}/packages.x86_64.lean" "${PROFILE_DIR}/packages.x86_64"
```

`packages.x86_64.lean` exists (311 entries vs 408) and drops 97 packages: the
BlackArch curated set, metasploit, ghidra, ollama, suricata, tor, the whole
recon/exploit/crack/forensics block **[REPO]**.

**And it is already broken in exactly the way HANDOFF warns about.** This is the
most important evidence in this entire section, so it is worth being precise:

| Fact | Consequence |
|---|---|
| `packages.x86_64.lean` is dated **2026-07-22**; `packages.x86_64` is dated **2026-07-30** **[REPO]** | 8 days of divergence, unreviewed |
| `btop` was **added to the full list on 2026-07-30** specifically to fix dead station launches (three stations and four launch chains fall back to it) **[DOC]**. It is **not in the lean list** **[REPO]** | A `NYX_ISO_TIER=lean` bake **today** reintroduces the exact station-launch bug that was diagnosed and fixed the day before yesterday |
| `gnome-text-editor` is in full, not in lean **[REPO]** | The lean tier has no GUI text editor |
| `calamares` is dropped by lean **[REPO]** | **The lean tier has no installer.** It can be booted but never installed |
| `chromium` is dropped by lean **[REPO]**, and chromium is what pulls `xdg-utils` **[PKG]** | **The lean tier has no `xdg-open` and no `xdg-mime` at all.** Nothing opens anything by association |
| `verify-profile.sh` contains **zero references to `NYX_ISO_TIER`** **[REPO]** | 42 gates validate the full profile. **None of them has ever run against the lean one.** |

That is four independent silent regressions in one unmaintained duplicate
surface, discovered in a single afternoon of reading — the same count HANDOFF
records for 2026-07-30 across the entire project. **`packages.x86_64.lean` is
not a precedent to follow. It is the strongest possible argument for how the
second edition must NOT be built.**

#### The four candidate mechanisms

| Mechanism | Maintenance cost | Drift risk | Verdict |
|---|---|---|---|
| **A. Separate branch or repo** | Highest. Every fix must be landed twice, forever | Certain. Violates the one-canonical-repo rule (§0 rule 1) outright | **Reject.** This is the failure mode the whole project was reorganised to escape |
| **B. Separate archiso profile** (`nyx-profile-daily/`) | Very high. Duplicates skel, airootfs, `profiledef.sh`, `customize_airootfs.sh` — thousands of files | Certain, and *invisible*: the bake already reads from three trees, and a fourth is how `nyxus-hyprland-layerblur.conf` and `nyxus-stations.conf` ended up as copies nothing reads (gate `13ak`) **[DOC]** | **Reject** |
| **C. Duplicate data files** (`packages.x86_64.lean` pattern) | High, and deceptively so — it *looks* cheap | **Proven, measured, four instances above** | **Reject, and fix or retire the existing one** |
| **D. Edition flag + subtractive manifest** | Lowest. One shared profile; the edition is expressed as a *list of exclusions* applied at bake | Low — a subtractive list cannot go stale in the dangerous direction | **RECOMMEND** |

#### Recommendation: `NYX_EDITION=lab|daily`, subtractive, one profile

```bash
NYX_EDITION="${NYX_EDITION:-lab}"    # lab = today's build, unchanged, the default
```

The design rule that makes this safe, and the reason it beats the existing
`lean` tier:

> **The daily edition is defined as a set of REMOVALS from the full build. It
> never has its own copy of anything.**

Concretely:

- **Packages**: ship `iso-builder/editions/daily.exclude` — a list of package
  *names to remove* from `packages.x86_64` at bake, not a second full list. A
  name that no longer exists in the full list is a no-op or a warning; a name
  newly *added* to the full list is automatically inherited by the daily
  edition. **`btop` could not have been lost this way.** The failure mode
  inverts from "silently ships stale content" to "harmlessly lists something
  that is gone" — which is the entire point.
- **Payloads**: guard the existing `build-iso.sh` staging steps with
  `[[ "${NYX_EDITION}" == "lab" ]]`. The honeypot, Arsenal, Bifrost, jeTT and
  Meli staging steps are already discrete, individually-guarded blocks
  **[REPO]** — this is a one-line condition on each, not a restructure.
- **Services**: the `for svc in … systemctl enable` loop in
  `customize_airootfs.sh` **[REPO]** becomes edition-aware for the five security
  units. Everything else stays identical.
- **Stations**: see §3.3 — this is the only part that needs real design.
- **Everything visual**: untouched. Same skel, same eww, same palette, same
  greeter, same lock, same saver. **Zero duplicated surfaces.**
- **Build stamp**: `/etc/nyxus-build` must record the edition. Without it, "is
  this stick daily or lab?" becomes unanswerable, and the project has already
  lost days to unanswerable "which build is this" questions **[DOC]**.

**And retire `NYX_ISO_TIER`.** Two overlapping edition mechanisms is worse than
either alone — someone will eventually bake `NYX_ISO_TIER=lean NYX_EDITION=daily`
and get a result nobody designed. Either fold `lean` into the new flag as a
third edition with its own exclude list, or delete it and `packages.x86_64.lean`
outright. It is currently a loaded footgun: documented, reachable, and known
broken.

### 3.2 The stripping manifest

What the daily edition excludes. Everything here is verified present in the full
build today.

#### 3.2.1 Package exclusions

| Group | Packages | Installed size |
|---|---|---|
| Exploitation | `metasploit`, `exploitdb`, `routersploit`, `sqlmap`, `commix`, `xsser`, `dalfox`, `impacket`, `crackmapexec`, `responder` | **~700 MiB** |
| RE / forensics | `ghidra`, `radare2`, `foremost`, `bulk-extractor`, `stegseek`, `mat2`, `secure-delete`, `perl-image-exiftool` | **~790 MiB** |
| Web / scanning | `zaproxy`, `nuclei`, `nikto`, `wpscan`, `gobuster`, `ffuf`, `feroxbuster`, `dirb`, `wfuzz`, `whatweb`, `naabu`, `rustscan`, `masscan` | **~460 MiB** |
| Recon / OSINT | `amass`, `subfinder`, `assetfinder`, `theharvester`, `recon-ng`, `dnsrecon`, `dnsenum`, `fierce`, `sublist3r`, `enum4linux` | **~110 MiB** |
| Wireless | `aircrack-ng`, `wifite`, `reaver`, `bully`, `bettercap`, `kismet`, `hcxtools`, `hcxdumptool`, `mdk4`, `pixiewps` | **~95 MiB** |
| Cracking | `hashcat`, `john`, `hydra`, `medusa`, `ncrack`, `crunch`, `cewl`, `hashid`, `patator` | **~135 MiB** |
| Sniffing / MITM | `ettercap`, `dsniff`, `mitmproxy`, `proxychains-ng` | **~22 MiB** |
| Anonymity | `tor`, `torsocks` | **~28 MiB** |
| AI / IDS | `ollama`, `suricata` | **~70 MiB** |
| Container runtime (honeypot only) | `docker`, `docker-compose` | **~142 MiB** |
| BlackArch plumbing | `blackarch-keyring`, `blackarch-mirrorlist` | trivial — but see the warning below |

**Measured total: ≈ 2.6 GiB of installed size** (summed from `pacman -Si`
Installed Size across the packages above) **[PKG]**.

> ⚠ **Dropping the BlackArch repo is not just two packages.** `packages.x86_64`
> pulls a curated ~67-tool set *from* `[blackarch]`, and — per HANDOFF — so does
> **`calamares`**, which *"is a binary in [blackarch] and is now pacstrapped
> directly"*; four ISOs failed on this before it was understood **[DOC]**.
> **The daily edition must keep the BlackArch repo wired even though it installs
> almost nothing from it, or it loses its installer.** This is exactly the trap
> `packages.x86_64.lean` fell into by dropping calamares.

#### 3.2.2 Payload and service exclusions

| Excluded | Where it comes from | Size |
|---|---|---|
| **Honeypot Docker images** — cowrie, heralding, conpot, dionaea, endlessh, http-honeypot, grafana, loki, prometheus, promtail | `build-iso.sh` `docker save` → `/opt/honeypot/images/*.tar` | **~1 GB** of tarballs **[REPO][DOC]** |
| **Honeypot stack config** | `/opt/honeypot` (compose, service configs, `.env` template) | small |
| **`nyxus-honeypot-firewall.service`** + `nyxus-honeypot-firewall` | `usr/lib/systemd/system/` + `/usr/local/bin` **[REPO]** | trivial — but it is a `multi-user.target` unit that once put ~60 s in front of the greeter **[DOC]** |
| **Firstboot fragment `06-honeypot-stack.sh`** | `/etc/nyxus-firstboot.d/` | trivial; removes the 900 s `TimeoutStartSec` justification |
| **Arsenal** — `/opt/arsenal/tools/{CIPHER,Forge,RedForge,GSL,AI-Cyber-Defense-Trainer,axiom,c2}`, `arsenal` TUI, `/etc/arsenal/registry.toml`, `etc/skel/Arsenal/` | `NYX_STAGE_ARSENAL_APPS` staging **[REPO]** | **34 MB** in-repo |
| **Bifrost EDR** — guardian binary, Tauri shell, `bifrost.desktop`, station 9 pin | `NYX_BIFROST_BIN`/`NYX_BIFROST_REPO` **[REPO]** | ~21 MB PyInstaller ELF **[DOC]** |
| **jeTT EDR** — daemon, `/etc/jett/`, `jett-daemon.service` | `NYX_JETT_BIN`/`NYX_JETT_REPO` **[REPO]** | the live binary is **680 MB** **[DOC]** |
| **Meli** — `/opt/meli`, ingest units, `nyxus-launch-meli` | `NYX_MELI_REPO`/`NYX_MELI_VENV` **[REPO]** | 2.4 MB |
| **GodsApp** (30 modules) and **NYXUS Intel** (OSINT suite) | `nyxus_godsapp_install.sh`, `nyxus_intel_install.sh` **[DOC]** | ~380 KB in-repo; larger installed |
| **Security daemons enabled at bake** — `jett-daemon.service`, `ollama.service`, `docker.service`, `nyxus-honeypot-firewall.service`, `usbguard.service`, `auditd.service` | the `for svc in …` loop in `customize_airootfs.sh` **[REPO]** | — |
| **Security desktop entries** — `arsenal`, `bifrost`, `meli`, `nyxus-godsapp`, `io.nyxus.intel`, `nyxus-{cipher,forge,redforge,gsl,trainer,axiom,c2}`, `gowskinet-*` **[DOC]** | wave-4 `.desktop` glob | — |

**Keep in daily** (general-purpose, not lab tooling): `ufw`/`firewalld`,
`nyxus-security` (Security Center), `nyxus-panic`, `nyxus-vpn`, `nyxus-doh`,
`nyxus-mac-randomize`, `nyxus-secboot`, `nyxus-passwords`, `wireshark`, `nmap`.
A normal desktop still wants a firewall and a password manager. **Ghost Mode**
(Tor + nft kill-switch) dies only if `tor` dies — flag for the owner, since a
privacy mode is arguably a daily-driver feature rather than lab tooling.

#### 3.2.3 Estimated size saving — and the honest caveat

| Component | Installed / raw | Est. on-ISO after zstd |
|---|---|---|
| Security packages (§3.2.1) | ~2.6 GiB | **~1.1–1.4 GB** |
| Honeypot Docker image tarballs | ~1.0 GB | **~0.8–0.9 GB** (container layers are already compressed; squashfs gains little) |
| jeTT daemon binary | 680 MB | **~0.2–0.25 GB** |
| Arsenal + Bifrost + Meli + GodsApp + Intel | ~60 MB | **~0.03 GB** |
| **Total** | | **≈ 2.1 – 2.6 GB** |

Against the **8.49 GB** `nyxus-2026.07.31` ISO **[REPO]**, that gives a daily
edition of roughly **5.9 – 6.4 GB** — a **~25–30% reduction**.

> **Two honest caveats.** First, these are *estimates* from `pacman -Si`
> installed sizes plus a compression assumption; **only a bake settles it**, and
> this project's own history says measure rather than reason. Second, **~6 GB is
> still not a small ISO.** If the goal is "fits on any stick and downloads in a
> reasonable time," the daily edition needs a second pass at the
> *general-purpose* bulk too — the `steam`/`gamescope`/`mangohud` block,
> `libvirt`+`qemu-desktop`+`virt-manager`, `podman`+`distrobox`+`buildah`+`skopeo`,
> `code`, `neovim`+`helix`+`micro`. The existing `lean` list drops all of those
> **[REPO]**. **That is a separate decision from "no security tooling," and
> conflating the two is how the lean tier ended up with no installer and no
> `xdg-open`.** Keep the axes separate: `NYX_EDITION` decides *lab vs daily*; a
> size tier, if wanted, should be its own orthogonal flag with its own exclude
> list.

---

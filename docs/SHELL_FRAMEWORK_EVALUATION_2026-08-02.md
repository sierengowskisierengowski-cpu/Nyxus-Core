# NYXUS — SHELL FRAMEWORK EVALUATION FOR THE DAILY DRIVER EDITION

**Date:** 2026-08-02 · **Revised:** 2026-08-02 (Part II, §13–§16, after owner review)
**Type:** decision document — research only
**Status:** nothing implemented. No package list, `build-iso.sh`, `verify-profile.sh`,
eww file, script or `HANDOFF.md` line was touched. This document is the entire
deliverable.

> **The owner's question:** *should the new "Daily Driver" desktop shell be built
> in AGS/Astal instead of eww?*
>
> **The answer, in one paragraph:** Do not build the Daily shell in eww — that
> part of the question resolves cleanly, and the reasons are stronger than the
> §11 render bugs. But the alternative should not be AGS/Astal either. AGS is
> AUR-only and drags **sixteen** AUR packages into the bake chroot, **fourteen
> of them unpinned `-git` VCS builds** — into a build that has already shipped
> three ISOs with no installer because an AUR build failed silently in exactly
> that chroot. **Quickshell** does everything AGS does for these three surfaces,
> is in the **official Arch `extra` repo** as a signed, versioned package, and
> costs **one line in `packages.x86_64`**. That is the recommendation. §10 states
> it plainly; §9 is the honest accounting of why the option you did not ask about
> beats the one you did.
>
> **→ PART II (§13–§16), added later the same day**, answers the owner's two
> follow-up criteria — *"i want eye candy and rich features"* and *"i dont want
> … [to change] what i can and can not do."* Short version: **for eye candy the
> ranking is Quickshell ≫ AGS/GTK4 ≫ eww/GTK3**, so eye candy and packaging point
> at the same framework and the recommendation is unchanged; and the switch
> **raises** the capability ceiling rather than lowering it — five of the seven
> entries in this project's own *"what is not possible"* list are eww/GTK3 limits,
> not physics. §14 also corrects a misreading about the blurred corners.

---

## 0. HOW TO READ THIS

Same tagging discipline as
[`DE_COMPLETENESS_AND_EDITIONS_2026-07-31.md`](./DE_COMPLETENESS_AND_EDITIONS_2026-07-31.md),
because the project has lost days to agents asserting things they inferred.

| Tag | Meaning |
|---|---|
| **[REPO]** | Read directly out of the canonical tree at `main` today (`4f672e80`). High confidence. |
| **[PKG]** | Resolved against live package sources on 2026-08-02 — `archlinux.org/packages`, the AUR RPC v5 API, Repology. High confidence for *what a bake would install*. |
| **[DOC]** | From `HANDOFF.md` or a dated brief recording a live measurement. Confidence inherits from that record. |
| **[WEB]** | Fetched from upstream on 2026-08-02 — GitHub releases/commits API, upstream docs, maintainer statements in issues. Date-stamped inline, because both projects move. |
| **[INFER]** | Reasoned, not measured. Treat as a hypothesis. |

**What this study could NOT do:** no bake, no boot, no GUI. Nothing here has been
run on a stick. Every claim about *runtime* behaviour of AGS or Quickshell on
NYXUS is **[INFER]** and is called out as such. What *is* solid is the packaging
arithmetic, the upstream state, and the repo facts — and those turn out to be
what decides it.

**Dates matter here.** Both ecosystems moved in the last twelve months and the
training-data picture of either is wrong. Everything below was re-verified today.

---

## 1. THE TARGET — what is actually being built

From [`DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md`](./DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md)
§2/§4 and the approved mockups at `docs/assets/daily-driver/` **[DOC]**, which
were read for this study, not paraphrased from the brief:

| Mockup | Surface | What the shell must actually produce |
|---|---|---|
| `set-desktop.png` | **Taskbar** | Centred bottom bar, frosted glass with corner-bleed. Launcher orb, a centred strip of pinned + **running** app icons, right tray (Wi-Fi / volume / battery) with clock + date on two lines |
| `set-launcher.png` | **Start / launcher** | Centred glass panel: live search field ("applications, files, settings"), an **18-icon pinned grid** with labels, an **All Apps** affordance, a two-column **Recommended / recent files** list with per-item type + timestamp, and a user row with avatar, presence dot and a power button |
| `set-notifications.png` | **Notification + quick-settings flyout** | Right-side glass flyout: **six quick-toggle pills** with icon + label + sub-label state, brightness and volume **sliders**, a full **month calendar** with today highlighted and month navigation, a **media card** (art, track, artist, album, scrub position, transport), then **stacked notification cards** with relative timestamps and **Clear All** |

Three surfaces. **None of them exists yet** — the bring-up plan's own file table
marks *"Bar/flyout/launcher — not started"* **[DOC**,
[`DAILY_DRIVER_BRINGUP_PLAN.md`](./DAILY_DRIVER_BRINGUP_PLAN.md) §6**]**. That is
the whole reason this question is live and cheap to answer now.

**One detail from the current plan matters enormously and is easy to miss.** The
bring-up plan does not intend to build that flyout in eww at all. §6 assigns it
to **swaync**, because *"the approved flyout — calendar, quiet hours, quick-toggle
pills — is a control-centre feature set dunst has no equivalent for"* **[DOC**,
also audit §11.4**]**. So the status-quo plan is not "Daily in eww." It is
**Daily in eww *plus* swaync**, with two styling systems, and with the single
most distinctive surface in the product delegated to a component whose layout you
**configure and theme but do not compose**. The mockup's flyout is a specific
arrangement of six things in a specific order. That is a composition problem, and
swaync is not a composition tool.

Any honest comparison has to score the status quo as **two shell stacks already**,
not one.

---

## 2. PACKAGING AND BAKE INTEGRATION

The owner flagged this as *"likely the deciding practical factor."* It is. It
just does not decide in the direction expected.

### 2.1 The premise is wrong, in NYXUS's favour: eww is already AUR

`packages.x86_64` line 87, verbatim **[REPO]**:

```
# EWW is AUR-only (eww-wayland); built from source by customize_airootfs.sh.
```

`eww` is **not in any Arch repo and never has been**, and NYXUS does not even use
the AUR package. `customize_airootfs.sh` git-clones `elkowar/eww` at a pinned tag
and **compiles Rust inside the mkarchiso chroot** **[REPO]**:

```bash
NYXUS_EWW_TAG="${NYXUS_EWW_TAG:-v0.6.0}"
… git clone --depth 1 --branch "${NYXUS_EWW_TAG}" https://github.com/elkowar/eww.git
… build_eww && install -Dm755 …/target/release/eww /usr/local/bin/eww
```

with hand-maintained crate pins around it, because — the script's own comment —
*"an upstream-unfixed regression because EWW v0.6.0 was tagged in 2024"* **[REPO]**.
FAIL-FAST on a missing binary, since waybar was removed.

And AUR is not a novelty here either. `customize_airootfs.sh` carries a full
`_aur_build` harness — dedicated build user, scoped NOPASSWD sudoers rule,
temporary mirrorlist, `CheckSpace` off, bulletproof teardown — and calls it for
**eight** packages: `yay-bin`, `timeshift`, `snap-pac`, `snapper-rollback`,
`ananicy-cpp`, `distrobox`, `calamares`, `appimagelauncher` **[REPO]**. On top of
that, `[blackarch]` is a third-party repo wired into the profile `pacman.conf`,
and `build-iso.sh` stages the Kage-Ryu kernel into a **profile-local
`[nyxus-local]` pacman repo** via `repo-add` **[REPO]**.

**So "AUR is a genuine complication" cannot be used to rule AGS out.** The
status quo is strictly worse-packaged than the AUR package for AGS would be: a
hand-rolled from-source Rust build with hardcoded dependency workarounds, versus
a maintained tagged PKGBUILD.

### 2.2 …but the same file records why this still matters enormously

Read the rest of that AUR harness **[REPO]**. It is one of the most expensive
comment blocks in the repo:

> *"which is why the 07.26 and 07.27 ISOs both shipped with NO CALAMARES: the
> installer silently never built."*
>
> *"That is why three ISOs in a row shipped with no installer."*
>
> *"a failed AUR build … can leave a stray process owned by the build user, and
> `userdel` REFUSES to remove a user that still owns a running process … so
> `nyxbuild` survived into the shipped image and the greeter defaulted its
> username to it."*

Three ISOs. A greeter lockout. **AUR-builds-inside-the-bake is a proven, measured,
repeat NYXUS failure mode**, and every `_aur_build` call is deliberately
non-fatal, so each new one is a new way for a stick to boot quietly wrong. That
is not an argument that AUR is impossible. It is an argument that each additional
AUR package in the chroot carries a real, historically-priced risk premium — and
therefore that the *number* is what matters.

### 2.3 What AGS/Astal actually costs

AGS is **AUR-only** **[PKG]**. Resolved from the AUR RPC API on 2026-08-02:

| Package | Version today | Kind | Notes |
|---|---|---|---|
| `aylurs-gtk-shell` | **3.1.2-1**, last updated 2026-04-09 | tagged | Depends: `gjs`, `gtk4-layer-shell`, `gobject-introspection`, `libastal`, `libastal-4`, **`npm`**. MakeDepends: `go`, `meson` |
| `libastal-io-git` | `r786.ca3190d-2` | **`-git`** | |
| `libastal-git` (astal3) | `r851.6976fab-2` | **`-git`** | hard dep of the AGS CLI even on a GTK4 shell |
| `libastal-4-git` (astal4) | `r851.6976fab-2` | **`-git`** | **Repology knows exactly one package for `libastal-4` in any distro, and it is this one** |
| `libastal-apps-git` | `r786.ca3190d-2` | **`-git`** | the launcher's app index |
| `libastal-notifd-git` | `r895.dd388d2-1` | **`-git`** | → pulls `quarrel-git` |
| `libastal-mpris-git` | `r908.11842ae-2` | **`-git`** | the media card → also `quarrel-git` |
| `libastal-network-git` | `r786.ca3190d-2` | **`-git`** | the Wi-Fi pill |
| `libastal-bluetooth-git` | `r786.ca3190d-2` | **`-git`** | the Bluetooth pill |
| `libastal-wireplumber-git` | `r776.c1bd89a-1` | **`-git`** | the volume slider |
| `libastal-battery-git` | `r786.ca3190d-2` | **`-git`** | tray battery |
| `libastal-powerprofiles-git` | `r786.ca3190d-2` | **`-git`** | |
| `libastal-tray-git` | `r786.ca3190d-2` | **`-git`** | → pulls `appmenu-glib-translator-git` |
| `libastal-hyprland-git` | `r786.ca3190d-2` | **`-git`** | taskbar window/workspace state |
| `quarrel-git` | `r895.dd388d2-2` | **`-git`** | **first submitted 2026-04-25, 0 votes** |
| `appmenu-glib-translator-git` | — | **`-git`** | transitive, via tray |

**Sixteen AUR packages. Fourteen are `-git`.** The Astal repository has **no
tags at all** — the GitHub tags API returns an empty array on 2026-08-02
**[WEB]** — so `-git` is not a packaging preference, it is the *only* way Astal
is distributed on Arch.

Two consequences, and the second is the serious one:

1. **Bake time and network.** Each `-git` build clones upstream and compiles
   Vala inside the chroot; makedepends add `vala`, `go`, `npm`, `meson`,
   `gobject-introspection` to the build environment. That is roughly **15×** the
   AUR surface of today's single pinned eww build, in the chroot that already
   ate three ISOs **[INFER** on time, **[REPO]** on the risk record**]**.
2. **A `-git` PKGBUILD computes `pkgver()` from `git describe` at build time.**
   Every bake therefore produces a *different* version of the shell libraries,
   from whatever upstream `main` happened to be that afternoon. This project has
   burned days on unanswerable *"which build is this?"* questions — it is why
   `/etc/nyxus-build` exists and why the edition had to be stamped into it
   **[DOC]**. Fourteen unpinned VCS dependencies is the direct negation of that
   discipline.

There is a clean fix, and it is already in the repo: build the closure **once on
the build box**, `repo-add` the resulting `.pkg.tar.zst` files into
`[nyxus-local]`, and let the bake `pacman -S` them — precisely the Kage-Ryu
kernel mechanism **[REPO]**. That converts fourteen unpinned chroot builds into
pinned prebuilt packages and removes the network from the critical path. It is
the right shape. It is also **a new maintenance surface** that someone has to
re-run whenever a rebuild is needed, and it is real work — realistically the
largest single line item in an AGS adoption.

### 2.4 What has to be on the live ISO versus only on the build box

Better than feared, and worth stating precisely because it is a common
misconception:

| Component | Build box | Live ISO | Source |
|---|---|---|---|
| `npm` / Node | **yes** (AGS CLI runtime-depends on `npm`; `ags run` shells to esbuild) | **no**, *if* you ship a bundle | **[PKG]** dep list; **[WEB]** `ags bundle` "embeds JS code into a Bash script" |
| `ags` CLI itself | yes | **no**, if bundled | **[WEB]** |
| `go`, `meson`, `vala`, `gobject-introspection` | yes (makedeps) | no | **[PKG]** |
| `gjs` | yes | **yes** — the JS runtime | **[PKG]** — and it is in **official `extra`**, `2:1.88.1-1`, updated 2026-06-29 |
| `libastal*.so` (12–14 of them) | yes | **yes** | **[PKG]** |
| `gtk4`, `gtk4-layer-shell` | yes | **yes** — **already in `packages.x86_64` (lines 159, 330)** | **[REPO]** |

So: **no Node on the stick**, and the GTK4 layer-shell plumbing AGS4 needs is
already shipped and already exercised by `nyxus_desktop.py` **[REPO]**. The
irreducible ISO cost is `gjs` (official) plus the dozen-odd Astal `.so`s
(AUR-built). That is genuinely modest. **The problem is not the weight on the
ISO. It is the sixteen builds required to produce it.**

### 2.5 The comparison table

| | **eww (status quo)** | **AGS / Astal** | **Quickshell** (§9) |
|---|---|---|---|
| In official Arch repos | **No** — AUR-only, and NYXUS builds from git source **[REPO]** | **No** — AUR-only **[PKG]** | **Yes — `extra/quickshell` 0.3.0-2, built 2026-06-05, signed** **[PKG]** |
| Packages the bake must build | 1 (from source, pinned tag) | **16, of which 14 unpinned `-git`** **[PKG]** | **0** |
| Reproducible version per bake | Yes (tag pin) | **No** without a `[nyxus-local]` staging step | Yes (repo version, signed) |
| Line in `packages.x86_64` | n/a — a 200-line chroot build block | n/a — a large new AUR block | **one line** |
| Build-box toolchain added | rust (already) | npm, go, vala, meson, g-i | none |
| ISO runtime added | none | `gjs` + ~13 `.so` | `qt6-base/declarative/svg` (`qt6-wayland` already present **[REPO]**) |
| Gate-able by `verify-profile.sh` | Only via bespoke gates (13pl) | Would need a new bespoke gate | **Trivially** — it is a package name in a list |

---

## 3. TECHNICAL FIT AGAINST THE MOCKUPS

### 3.1 Surface by surface

| Mockup element | eww | AGS / Astal | Quickshell |
|---|---|---|---|
| **App grid + live search** | `input :onchange` fires a **shell command per keystroke**; results arrive as a JSON string re-parsed and the list re-rendered whole. No app index — a script must scan `.desktop` files | `AstalApps` — in-process app index with fuzzy scoring; `<For>` diffs the list | `DesktopEntries` singleton + QML `ListView` with a filter model |
| **Notification list + Clear All** | eww is **not a notification daemon**. Today: dunst owns the bus, `notif-history.sh` is polled every 3 s **[REPO]**; the plan hands the flyout to swaync **[DOC]** | `AstalNotifd` — **the shell *is* the daemon**, in-process, no second process | `Quickshell.Services.Notifications` — implements the freedesktop server directly **[WEB]** |
| **Month calendar** | eww has a GTK3 `calendar` widget, but NYXUS renders its own month grid in `calendar-month.sh`, polled at 300 s **[REPO]** — because the widget could not be styled to match | `Gtk.Calendar` directly, or compose it; GTK4 CSS | QML `MonthGrid` / composed `Grid`, fully stylable |
| **Media card (art, scrub, transport)** | `player.sh` polling `playerctl` at 1 s **[REPO]**; scrub position is a shell round-trip | `AstalMpris` — properties + signals | `Quickshell.Services.Mpris` — `MprisPlayer` objects |
| **Taskbar with running-window state** | `WORKSPACES` polled at 1 s **[REPO]**; window state via a script over `hyprctl` | `AstalHyprland` — event-driven IPC objects | `Quickshell.Hyprland` **and** `ToplevelManager` (compositor-agnostic) |
| **Tray (Wi-Fi / volume / battery)** | **eww does have a `systray` widget**, added in 0.6.0, StatusNotifierItem **[WEB]**. Not a differentiator. The *values* still come from `network.sh`/`audio.sh`/`battery.sh` on 5 s/2 s/10 s polls **[REPO]** | `AstalNetwork` / `AstalWp` / `AstalBattery` / `AstalTray` | `Services.Pipewire` / `UPower` / `SystemTray` / `Bluetooth` |
| **Toggle pills with sub-label state** | Each pill's state is a key in a polled JSON blob (`QS`, 3 s) **[REPO]** — and a **missing key in `:initial` is exactly what blanked a window** (§11.6) | Typed property on a GObject | Typed QML property |

The pattern is uniform. **eww ships no system integration except the tray.**
Every value on every mockup is, in eww, a subprocess on a timer. Both
alternatives ship these as first-class typed objects, and each one maps 1:1 onto
an element the owner has already approved.

### 3.2 Is the feeder-script sprawl eww's fault or NYXUS's?

The owner asked this directly, and it deserves a straight answer, because it is
the one place the status quo is being blamed for something that is partly a
choice.

Measured today **[REPO]**:

| | Count |
|---|---|
| `.yuck` files shipped across the profile trees | **19** |
| Lines of yuck in `nyxus-scripts/eww/` | **3,968** (`eww.yuck` alone: 3,434) |
| Lines in `eww.scss.source` | **5,991** |
| `defpoll` | **56** |
| `deflisten` | **5** |
| `defwindow` | 48 |
| Feeder scripts in `eww/scripts/` | **88** |
| Sub-second polls | **4** — `0.1s` (TICKER), `200ms` (snap-picker), `600ms` (mission-state), `1500ms` (qs-state) |

*(For the record: the 50 ms figure in the brief is from **hyprlock**, defect
LK-02 in audit §11.5 — 2,969 dropped label updates in 40 s. eww's fastest poll is
100 ms. The distinction matters; the eww numbers are bad enough without
borrowing.)*

**The honest split:**

- **A NYXUS choice:** the 100 ms ticker, the 200 ms snap-picker, and the ratio
  **56 polls to 5 listens**. `deflisten` is eww's event-driven escape hatch and
  it is used in **8% of cases**. Several of those 56 polls have obvious
  `deflisten` equivalents (`hyprctl -j … ` has a socket; `playerctl` has
  `--follow`; `pactl subscribe` exists). A disciplined eww config would be
  materially leaner.
- **Inherent to eww:** that there are *any* feeder scripts. eww has no D-Bus
  client, no NetworkManager binding, no PipeWire binding, no MPRIS client, no
  UPower client, no app index, and cannot be a notification daemon. So the
  *floor* is "one shell script per data source." The 88 scripts are eww's model
  taken to its conclusion; a careful rebuild might reach 25 scripts, not zero.
  In AGS or Quickshell the equivalent floor is **zero**, because those data
  sources are library objects.

So: partly self-inflicted, structurally unavoidable. **A Daily-shell-in-eww
would be smaller than the alien shell and still be a pile of shell scripts on
timers**, because that is the only thing eww can consume.

---

## 4. FAILURE MODES — the actual cost centre

This is the section that should carry the most weight, because the owner is
right that *silent* failure is what this framework choice is really about. A
defect that is invisible without reading a daemon log inside a booted session
costs a bake, a flash, a boot and an audit session. Everything else is taste.

### 4.1 What eww has actually cost, measured

From [`ISO_FULL_AUDIT_2026-07-31.md`](./ISO_FULL_AUDIT_2026-07-31.md) §11.3 and
§11.6, on the 08.01 bake **[DOC]**:

| Defect | Mechanism | How visible |
|---|---|---|
| `:transition "rotate-left-right"` | Not one of the seven values eww parses. Fails **every time the widget is evaluated** → the whole window comes up blank | Only in the eww daemon log, inside a booted session. Written under a comment claiming it had been *"verified live"* — it never had; the build box runs eww 0.5.0 and the ISO ships 0.6.0 |
| Key missing from a `defpoll :initial` | Evaluates to JSON `null` until the first poll lands; `null` cannot be coerced by `? :` → throw while building the widget tree → **whole window blank** | Same. GLITCH.alien was blank for the first 7 s of every session |
| `:truncate` | Silently ignored | Not visible at all |
| `eww open` self-daemonising | During the login race it cannot reach the server, becomes its own daemon; `eww close` reaches the *wrong* daemon and does nothing — **and the script's own verify step reads `active-windows` from that same wrong daemon, so it reports success** | Only via `hyprctl layers` + `ps`. Chased since 2026-07-27 with band-aids applied to the wrong layer. **Still not fixed** |

Note the shape of the first two: **one bad property anywhere in a window aborts
the construction of the entire window.** There is no partial render. A typo in
a corner chip blanks the bar.

Gate **`13pl`** exists solely to catch classes 1 and 2 statically — it is 80
lines of Python that re-parses all 19 `.yuck` files to check that every key read
off a variable exists in that variable's `:initial` and that every `:transition`
is one of seven strings **[REPO]**. **That gate is a hand-written, partial,
project-specific type checker for a language that has no type checker.** It is
excellent work and it is also a symptom.

### 4.2 Does AGS fail more loudly? Partly — and the rest is on us

**The honest bad news first: AGS does not typecheck by default.** `ags run` and
`ags bundle` use esbuild, which strips TypeScript types **without checking them**
— upstream esbuild's own position, restated by its author **[WEB]**. AGS's docs
tell you to run `tsc --noEmit` separately and provide `ags types` to generate
`.d.ts` for the GObject libraries **[WEB]**. Type-incorrect AGS code runs
happily. Anyone who assumes "TypeScript, therefore checked" will get exactly the
eww experience with more syntax.

**The good news, and it is decisive if acted on:** the check is *available,
headless, and free to wire up here.* NYXUS is already a pnpm workspace with
`pnpm run typecheck` at the root and CI that runs it **[REPO/AGENTS]**. Adding
the Daily shell as a workspace package with a `tsc --noEmit` step means the
entire eww silent-blank class — misspelled property, wrong enum value, field that
does not exist on the object, `null` where a `boolean` is required — becomes a
**CI error on a laptop, in seconds, with no bake**. `:transition
"rotate-left-right"` becomes a compile error against a union type. That is the
single strongest argument for leaving eww, and it is worth more than every
aesthetic argument combined.

**Two more structural differences, both real:**

- **Blast radius.** In eww, one bad property aborts the whole window tree. In
  GTK/GJS, an exception in one widget's construction throws a **stack trace with
  a file and line to the journal**, and an unknown CSS class simply does not
  style — the rest of the surface still renders. Blank-window-with-no-message is
  much harder to produce.
- **The daemon-identity bug does not have an analogue.** §11.3's orphan-daemon
  leak is a consequence of eww's client/server split and `eww open`'s
  self-daemonising fallback. AGS and Quickshell both run the shell as a single
  process that owns its own windows; toggling a window is an in-process call, not
  a CLI round-trip to a socket that may belong to a different process.

### 4.3 Would gate-style verification still be needed?

Yes — but it changes shape, and it gets cheaper:

| Gate class | Under eww today | Under a typed shell |
|---|---|---|
| "Every key read exists / every enum value is real" | `13pl`, bespoke Python, partial by construction | **The compiler.** `13pl` becomes redundant for Daily surfaces |
| "The config actually produces a runnable artifact" | Nothing — yuck is parsed at runtime | `ags bundle` / `qmllint` in CI: a build step that either succeeds or fails |
| "The shipped tree matches the source tree" | Existing gates (13ak etc.) | **Unchanged — still needed** |
| "It renders on a real stick" | Only a bake proves it | **Only a bake proves it. Unchanged.** |

Nothing removes the last row. But moving rows 1 and 2 off the bake is the entire
economic case for this change.

---

## 5. GTK VERSION AND STACK COHERENCE

### 5.1 eww is GTK3, permanently

Established today **[WEB]**, and it is worse than "eww is on an older toolkit":

- **Latest eww release is v0.6.0, 2024-04-21 — 27 months ago.** There has been
  no release since.
- **Three commits in all of 2026**: 2026-03-05, 2026-07-05, 2026-07-17. Master
  is not dead, but it is dormant.
- **`gtk3-rs`, the binding eww is built on, is unmaintained** (upstream issue
  #1077), and the `dbusmenu-rs` crate the tray used had its code removed.
- The maintainer on GTK4, in eww's own issue tracker: *"eww currently uses gtk3,
  a gtk4 update would be extremely difficult, so I don't [know] whether it will
  ever happen."* No GPU acceleration either (open issue #1342).

NYXUS is already living the consequence: `customize_airootfs.sh` pins v0.6.0 and
carries hardcoded crate downgrades *because a 2024 tag no longer builds cleanly*
**[REPO]**. That is bit-rot in progress. **The trajectory is that one day
v0.6.0 stops compiling and NYXUS's options are an unversioned master or a fork.**
There is no maintainer to escalate to and no upgrade path off GTK3.

"eww is stable" is not true in the way it sounds. It is *stalled*, which is a
different and worse thing for a distro that has to build it from source.

### 5.2 Coherence, honestly scored

Today the shell layer is **GTK3 (eww) + GTK4 (the Python app layer, plus
`gtk4-layer-shell` for `nyxus_desktop.py`)** **[REPO]** — two toolkits, two CSS
dialects, two `settings.ini` files. Adding swaync for the Daily flyout as
currently planned makes it **three styling systems for one product**.

- **AGS wins this criterion, and it is the only criterion AGS wins outright.**
  AGS v3 defaults to GTK4 (`ags init` defaults to GTK4; the `--gtk4` flag was
  removed because the version is inferred) **[WEB]**. A GTK4 AGS shell would put
  the Daily shell on the *same* CSS dialect as the Daily apps — a genuinely
  shareable token stylesheet, not just shared hex values.
- **Quickshell loses it**, but by less than it appears: it is a lateral move, not
  a regression. eww is already a different toolkit from the apps. And NYXUS
  already ships `qt6-wayland`, `qt5ct`/`qt6ct`, and three Qt5 packages **[REPO]**;
  calamares drags Qt6 in regardless.

**One counterweight that cuts against GTK4, from this project's own experience.**
`DAILY_DRIVER_BRINGUP_PLAN.md` §6.1 records an *unresolved* Daily blocker
**[DOC]**: the greeter card must be centred per the mockup, but *"GTK4 CSS has no
percentage margins and no `halign`, so 'centred' cannot be expressed in the
stylesheet at all"* — forcing pixel arithmetic in `nyxus-greeter`, a documented
lockout-class file. That class of problem is a non-problem in QML, which has
anchors and layouts as first-class primitives. "GTK4 everywhere" is a coherence
benefit that comes with GTK4's layout limitations attached.

### 5.3 Frosted glass with corner-bleed — a wash, and the owner's instinct is right

Being precise, because this is a signature must-have (brief §4) and it is easy to
attribute it to the wrong layer:

- **Per-surface blur is a compositor capability, not a widget-toolkit one.** In
  Hyprland it is `layerrule = blur on, ignore_alpha <n>, match:namespace <ns>`.
  It applies to any layer surface from any toolkit. Toolkit-neutral. **[WEB]**
- **The known limit is also toolkit-neutral.** Hyprland's maintainer, on eww
  specifically: *"hyprland can't really know how to cut the blur on corners,
  since all layersurfaces report is a rectangle."* **[WEB]** Rounded corners over
  blur are handled by the widget's own alpha plus `ignore_alpha`, in every
  stack. eww, AGS and Quickshell hit this identically.
- **Corner-bleed** — the corners fading into the wallpaper — is a radial alpha
  falloff painted by the toolkit, exactly as the bring-up plan's token spec
  already describes (*"radial alpha falloff … compositor layer blur + GTK/eww
  alpha; NOT true per-widget CSS blur"* **[DOC]** §5). GTK3 CSS, GTK4 CSS and
  QML can all paint a radial-gradient alpha. QML additionally has `MultiEffect`
  and `OpacityMask`, and Quickshell ships a `BackgroundEffect` type that requests
  surface blur directly **[WEB]** — a convenience, not a capability difference.

**Verdict: no framework wins on the signature material.** Do not let the glass
decide this.

---

## 6. THE COST OF TWO SHELL FRAMEWORKS IN ONE REPO

The owner suspected this may be the strongest argument against changing. It is
the strongest argument against, and it is still not decisive. Three reasons.

**First, the premise overstates the current state.** The repo does not have one
UI stack. It has eww/yuck+SCSS (GTK3), a GTK4 Python app layer, Tauri/React for
`nyxus-app-shell` and the web apps, and — per the current Daily plan — swaync as
a fourth styling surface **[REPO/DOC]**. The marginal change is not 1→2. For the
*shell layer* it is 2→2: **Daily would trade `eww + swaync` for one framework.**
Under the current plan Daily ships two shell stacks either way.

**Second, the alien shell is frozen by owner decision.** 2026-08-01: *"the
alien-neon build … stays EXACTLY as-is and remains the default"* **[DOC]**. A
frozen stack is far cheaper to carry than a co-evolving one. Nobody has to learn
eww to *change* it; they have to learn it to *not break* it, and 67
`verify-profile` gates already enforce that **[REPO]**.

**Third — and this is the real cost, so state it plainly:** every future agent
must understand two shells, and `HANDOFF.md`'s entire thesis is that scattering
cost the owner time and money. Mitigation is not optional:

- The edition boundary must be explicit in `HANDOFF.md` and in the bring-up
  plan's §6 file table: *alien = eww, daily = X, and no file is shared between
  them.*
- The shared-file discipline already proven for the dunst/swaync split (audit
  §11.4 — one daemon per edition, edition-gated `exec-once` rewrite on the
  throwaway profile copy) is exactly the right shape and it already works
  **[DOC]**.
- `packages.x86_64` is a **shared** file. Daily-only packages must be appended at
  bake by the edition block, the way `build-iso.sh` already appends the Kage-Ryu
  packages **[REPO]** — never edited into the committed list, or the alien ISO's
  package set changes and the "alien does not change by a byte" guarantee dies.
  *(One line for Quickshell; a `[nyxus-local]` block for AGS.)*

---

## 7. MATURITY AND CHURN RISK

Verified from the GitHub releases API on 2026-08-02 **[WEB]**:

| | Releases | Track record |
|---|---|---|
| **eww** | v0.6.0 (2024-04-21) is still the latest. 6 releases ever | **27 months without a release.** 3 commits in 2026. Core binding (`gtk3-rs`) unmaintained. NYXUS already patches crates to build the pinned tag **[REPO]** |
| **AGS** | v1.0.0 2023-08-23 → v2.0.0 **2024-11-13** → v3.0.0 **2025-10-22** → v3.1.2 2026-04-08 | **Two ground-up rewrites in 26 months.** v2 = *"reimplemented from scratch in Vala and C."* v3 = *"Ags was rewritten from scratch and unfortunately everything changed drastically, you will have to rewrite your projects from the ground up."* v3.1.0, five weeks after v3.0.0, already deprecated `.get()` → `.peek()` and the `createComputed` array form |
| **Astal** | **No tags at all.** Actively developed — commits 2026-06-21, 07-03, 07-19, 07-24 | Healthy pulse; zero release discipline. Distribution is `-git` only |
| **Quickshell** | 0.1.0 2025-06-13 → 0.2.0 2025-07-27 → 0.2.1 2025-10-12 → **0.3.0 2026-05-04** | Pre-1.0 and says so: *"There will be breaking changes before 1.0, however a migration guide will be provided."* But v0.3.0's actual breaking-change list is **one item** (config paths no longer canonicalized), and it explicitly made unrecognized pragmas non-fatal *"for future backward compatibility"* |

**Neither incumbent-scale option is risk-free, and the risks are different
species.** eww's risk is **bit-rot**: a stalled project on a dead binding that
NYXUS must compile from source. It is unfixable from here — no maintainer, no
GTK4 path. AGS's risk is **churn**: a maintainer who rewrites from scratch on a
~12-month rhythm. Churn is survivable by pinning, which this project already does
for both the kernel and eww. Bit-rot is not.

Quickshell sits between them: young, pre-1.0, but shipping incremental releases
with changelogs and migration promises, and — critically — **with a distro
maintainer between NYXUS and upstream**, which is the whole point of an official
repo.

---

## 8. WHY NOT AGS, SPECIFICALLY

Consolidating, because the question was about AGS:

| Criterion | AGS verdict |
|---|---|
| Packaging into the bake | **Loses badly.** 16 AUR packages, 14 unpinned `-git`, into the chroot that has already silently sunk three ISOs. Fixable only by standing up a `[nyxus-local]` pipeline for the whole closure |
| Technical fit to the mockups | **Wins clearly** over eww. Astal's service libraries map 1:1 onto every mockup element |
| Failure loudness | **Wins over eww** — but only if `tsc --noEmit` is wired in, because esbuild does not typecheck |
| GTK coherence | **Wins outright.** The only criterion where AGS beats everything |
| Churn exposure | **Loses.** Two ground-up rewrites in 26 months; the dependency closure gained a brand-new transitive package (`quarrel-git`, 0 votes) three months ago |

AGS is a better shell framework than eww for this product. It is not a better
*distro dependency* than eww, and for NYXUS that is the axis that has actually
drawn blood.

---

## 9. THE OPTION NOT ASKED ABOUT — and why it beats both

Flagging this rather than burying it, because it lands precisely on the factor
the owner named as decisive, and it would be dishonest to run a packaging
analysis and omit the option that scores zero on it.

**Quickshell** — QtQuick/QML toolkit for building shells, bars, launchers and
lockscreens.

- **`extra/quickshell` 0.3.0-2, x86_64, built 2026-06-05, signed by a distro
  maintainer** **[PKG]**. Official repo. `pacman -S quickshell`. **One line in
  `packages.x86_64`. Zero AUR. Zero chroot builds. Zero unpinned VCS deps.**
  1.6 MB packaged / 6.0 MB installed.
- **Service coverage is complete for these three surfaces** **[WEB]**:
  `Quickshell.Services.Notifications` (implements the freedesktop notification
  *server* — no swaync, no dunst race), `.Mpris`, `.Pipewire`, `.UPower`
  (+PowerProfiles), `.SystemTray` (+`DBusMenu`), `.Greetd`, `.Pam`,
  `Quickshell.Bluetooth`, `Quickshell.Hyprland`, plus `Quickshell.Wayland` with
  `WlrLayershell`, `ToplevelManager`, `BackgroundEffect` and `WlSessionLock`.
- **Hot reload is the headline feature** — *"loads changes as soon as they're
  saved."* In a project whose dominant cost is *"you must bake and boot to see
  whether it renders,"* iterating on the three surfaces without a bake is worth
  more than any other single property under discussion.
- **`qmlls` / `qmllint`** give editor diagnostics and a headless lint that could
  become a `verify-profile` gate without writing another bespoke Python parser.
- **QML has anchors and layouts**, which dissolves the §6.1 greeter-centring
  blocker class rather than working around it.
- **It could eventually subsume the lock screen** via `WlSessionLock` + `Pam` —
  relevant given audit §11.5, where hyprlock could not be assessed at all and two
  config defects were found underneath it. **Not a reason to adopt it, but worth
  knowing.**

**The honest costs.** Qt6/QML is a third toolkit against a GTK4 app layer, so
tokens must be expressed twice (a generated `.qml` singleton alongside the
generated `accent.scss` — the `nyxus-apply-accent` pattern already generates
per-surface files **[DOC]**, so this is a known shape, not a new one). Nobody in
this project has written QML. It is pre-1.0. And **none of it has been run here**
— **[INFER]**, which is what §11's trial exists to settle.

---

## 10. RECOMMENDATION

**Build the Daily Driver shell in Quickshell. Do not build it in eww. Do not
build it in AGS.**

To answer the question exactly as asked: **is AGS better than eww for this? Yes,
on fit and on failure loudness — but it is not the right choice, because it fails
hardest on the criterion the owner correctly identified as decisive.**

The reasoning in four lines:

1. **eww is out on its own merits, not just §11.** A 27-month-old release, three
   commits in 2026, an unmaintained GTK3 binding, no GTK4 path, a pinned tag that
   NYXUS already patches crates to compile, and zero system integration — so all
   three greenfield surfaces would be shell scripts on timers, and the flyout
   would have to be delegated to swaync anyway. Starting a **new product** on
   that in August 2026 is starting on a stalled base.
2. **AGS solves the right problems and creates a worse one.** Sixteen AUR
   packages — fourteen unpinned `-git` — in the chroot that already shipped three
   ISOs with no installer and once leaked the build user into the greeter. It is
   fixable via `[nyxus-local]`, and that fix is the single largest work item in
   the whole adoption. Paying it to get a framework whose maintainer has rewritten
   it from scratch twice in 26 months is a bad trade.
3. **Quickshell gets the same wins for one line in `packages.x86_64`.** Official
   repo, signed, versioned, distro-maintained, complete service coverage for all
   three surfaces, hot reload, a headless linter, and no bake-time build of any
   kind.
4. **The GTK4-coherence argument is the one thing AGS wins, and it is not worth
   sixteen AUR packages** — particularly since this project's own §6.1 just
   recorded GTK4 CSS being unable to express "centred."

### 10.1 What would change my mind

Concrete and falsifiable, not hedging:

| If this turns out to be true | Then |
|---|---|
| The taskbar trial (§11) shows Quickshell **cannot** produce the corner-bleed glass to the owner's satisfaction, while a GTK build can | Switch to AGS and pay the `[nyxus-local]` cost. Frosted glass with corner-bleed is a **must-have**, brief §4 |
| Qt6/QML proves unlearnable at the pace this project needs, or QML+GTK token duplication drifts within one milestone | Switch to AGS — GTK4 coherence then genuinely earns its price |
| The owner rules out a Qt surface on principle | **AGS, with the three conditions in §10.3.** Not eww |
| `quickshell` is dropped from `extra` or goes long-unmaintained | Re-evaluate immediately; the entire case rests on it being distro-packaged |
| Quickshell 0.4 lands a rewrite-scale break with no migration guide | Re-evaluate. Its incremental-release record is load-bearing here |
| Someone measures the full Astal `[nyxus-local]` pipeline at genuinely low cost, **and** AGS ships a v3 LTS commitment | Reopen AGS. Both would have to be true |

**What would NOT change my mind:** eww's familiarity, the existing 6k-line SCSS
(it is alien-specific and would be rewritten for the glass material under any
framework), or the existence of `13pl` (a gate that exists to compensate for a
missing type system is not an asset).

### 10.2 Can this be deferred? No.

**It must be decided before the first Daily shell file is written**, for a
specific and checkable reason: the bring-up plan's §6 file table already routes
Daily's shell to `artifacts/nyxus-config/editions/daily/eww/*` and already
assigns the flyout to swaync **[DOC]**. The moment someone writes the first
`.yuck` file or the first swaync config, the decision has been made by accretion
— and this project's documented history is that accreted decisions get
re-diagnosed and re-broken later at the owner's expense.

**The good news is symmetric: it is at its cheapest today.** Zero lines exist.
Phase 1 delivered only *theme* files — accent, wallpaper, rotation, greeter CSS,
lock accent **[DOC]**, all framework-neutral and all still valid. Nothing
committed so far has to be thrown away under any of the three answers.

### 10.3 If the answer comes back "AGS anyway"

Three conditions, all non-negotiable. If any cannot be met, stay on eww and
accept its costs knowingly — a half-done AGS migration is worse than either
endpoint.

1. **Pin the entire closure into `[nyxus-local]`.** Build the ~16 packages once
   on the build box, `repo-add`, wire the repo the way `build-iso.sh` already
   wires it for Kage-Ryu **[REPO]**. **No `-git` build ever runs inside the
   bake chroot.**
2. **`ags bundle` at build time.** Ship the bundle plus `gjs` plus the Astal
   `.so`s. No `npm`, no Node, no `ags` CLI on the live ISO.
3. **`tsc --noEmit` in the existing root `pnpm run typecheck`, wired before the
   second surface is written** — with `ags types` generating the GObject `.d.ts`.
   Without this, esbuild strips types unchecked and AGS's headline advantage
   over eww does not exist.

---

## 11. IF WE SWITCH — THE SMALLEST SAFE FIRST STEP

**Yes, one surface can be built alone as a trial, and it should be. Build the
taskbar.**

It is the right probe because it is the surface with the **hardest eww story**
(live running-window state, which is polled today) while touching the **fewest**
of the unknowns, and because the desktop mockup pins its appearance exactly.

**Scope of the trial**

- One QML file plus a token file, under
  `artifacts/nyxus-config/editions/daily/shell/`. Nothing outside
  `editions/daily/` is touched — the boundary that already protects alien
  **[DOC]** §6.
- Reproduce `set-desktop.png`'s bar only: launcher orb (opens nothing yet),
  centred running-app strip via `ToplevelManager`, tray with Wi-Fi / volume /
  battery, two-line clock + date, frosted glass with corner-bleed and the teal
  glow edge.
- `packages.x86_64` is **not** edited. The edition block appends `quickshell` at
  bake, the way `build-iso.sh` already appends the kernel packages **[REPO]**.
- `NYX_EDITION=alien` must remain **byte-identical**, proven by gate `13pm`,
  which already asserts the alien defaults cannot silently flip **[REPO]**.

**Verification ladder — cheapest first**

1. **[headless]** `bash iso-builder/verify-profile.sh` stays at 0 FAIL;
   `bash scripts/iso-build-verify.sh` stays clean.
2. **[headless]** `qmllint` on the shell file, run as a candidate new gate.
3. **[host]** Run it on the build box's own Hyprland session — **this is the
   step eww can never offer.** Hot reload means the glass, the corner-bleed and
   the layerrule interaction are tuned live, in minutes, without a bake.
4. **[VM/bake]** Only then a `NYX_EDITION=daily` bake, to prove the package
   resolves and the bar comes up in a real session.

**Kill criteria — decide at step 3, before any bake**

- Corner-bleed and the teal glow edge cannot be made to match `set-desktop.png`
  → **stop; re-run the same trial in AGS** before committing to either.
- The bar cannot track running windows reliably under Hyprland → stop.
- More than ~2 days to a bar that matches the mockup → the learning curve is the
  real cost and AGS's TypeScript familiarity starts to earn its packaging price.

**If the trial passes**, the launcher and the flyout follow in the same framework
and the same directory, and the swaync assignment in bring-up plan §6 is retired
— one fewer daemon, one fewer styling system, and the §11.4 notification-daemon
race cannot recur in the Daily edition because the shell *is* the daemon.

**If the trial fails**, exactly one QML file is thrown away, `editions/daily/`
loses one directory, alien never changed by a byte, and the theme work from
Phase 1 is untouched. **That is the whole downside.**

---

## 12. WHAT THIS DOCUMENT DOES NOT CLAIM

- **Nothing here has been run.** No bake, no boot, no GUI. Every runtime claim
  about AGS or Quickshell on NYXUS is **[INFER]**. §11 exists to convert the
  most important of them into a measurement for the price of one file.
- **No claim that eww is broken.** After `bd86b52b` and gate `13pl` the alien
  bars render, audit §11.6 explicitly corrected the "never renders" call, and the
  owner's decision that the alien build stays exactly as-is is **not** challenged
  by anything here. This document is about **new** work only.
- **No estimate of total Daily shell effort.** The comparison is relative, not
  absolute.
- **No opinion on the greeter or the lock screen.** Quickshell's `WlSessionLock`
  and `Greetd` support is noted in §9 as a fact, not proposed. hyprlock cannot
  even be assessed until it is run somewhere it renders (audit §11.5).
- **No package was added, and no build file was touched.** Verify with
  `git show --stat`: this document is the only path in either of its commits.
- **Part II's capability claims are documentation-level, not rendered.** Every
  animation, shader, effect and particle capability in §13 is read out of
  upstream reference docs, upstream release notes or Arch package file lists on
  2026-08-02 — **none of it was drawn on a screen here.** "Quickshell has a
  particle system" means the module ships in `qt6-declarative`; it does not mean
  the owner's specific effect has been proven to look right. §11's trial is what
  converts that.

---

# PART II — ANSWERING THE OWNER'S TWO CRITERIA

**Added 2026-08-02, after the owner read Part I.** He is not rejecting the
recommendation — his words were that the decision *"will depend what it all
offers."* He named two criteria that Part I did not weight as primary:

> **"i want eye candy and rich features"**
>
> **"i dont want to start changing all these things and ways on doing them that
> will start changing on what i can and can not do."**

The second is not a preference, it is a **capability-ceiling worry**: *will
switching take options away from me later?* §16 answers it directly. §13 answers
the first with measurements rather than adjectives, §15 covers "rich features",
and §14 corrects a misreading about the blur corners.

Everything below was re-verified on the web on **2026-08-02**. Part I's
recommendation was **re-derived** with these two criteria weighted first, not
defended — §13.6 states where it landed.

---

## 13. EYE CANDY — WHAT EACH FRAMEWORK CAN ACTUALLY DO

### 13.1 The starting point: this project already knows its own ceiling

NYXUS has a measured eye-candy capability study —
[`EYE_CANDY_DESIGN_SPEC_2026-07-31.md`](./EYE_CANDY_DESIGN_SPEC_2026-07-31.md)
— with source-line citations into Hyprland and eww. Its §5 is titled *"WHAT IS
NOT POSSIBLE — PLAINLY"* **[DOC]**. That list is the honest baseline for what the
owner can do **today**, and most of it is a property of **eww/GTK3**, not of
Hyprland:

| From the eye-candy spec | Why |
|---|---|
| §5.2 *"A real 3D look on controls — NO"* | *"GTK3 cannot rotate, scale, skew or light a widget."* The recommended workaround is **pre-rendered Blender sprite sheets** swapped frame by frame |
| §5.3 *"Arbitrary CSS filters in eww — NO"* | *"GTK3 CSS has no `filter`, no `backdrop-filter`, no `mix-blend-mode`."* This is why the `-mono.png` asset variants exist — a greyscale mode had to be **pre-rendered because it could not be computed** |
| §5.4 *"Per-widget blur — NO"* | blur is a whole-layer-surface compositor effect. Workaround: give the widget **its own window, namespace, exclusive zone and watcher** |
| §5.5 *"A rotate/flip transition in eww — NO"* | `GtkStack` has six transitions, none rotate |
| §5.6 *"Custom uniforms into a screen shader — NO"* | Hyprland feeds a fixed uniform set. *"There is no mechanism to pass an application value — mood, CPU, `CAVA_BASS` — into a shader."* |
| §5.1 *"True 3D compositing — NO"* | compositor-level; **true for all three frameworks** |
| §12.1 *"Animated screen shaders are not affordable"* | needs `debug:damage_tracking = 0` → full-screen redraw every frame forever. **Compositor-level; true for all three** |

**Read that column again.** Five of the seven "no"s are **eww/GTK3 limits**, not
laws of physics. The owner has already been paying a capability tax and did not
know it was optional — the workarounds in that document (pre-render the
greyscale, pre-render the toggle, spend a whole extra layer surface to blur one
card) are engineering *around* GTK3.

**And one entry is worse than a "no" — it is a ceiling he has already hit.**
Eye-candy spec §3.3, on eww **[DOC]**:

> *"An inline `:style` beats every stylesheet rule, at any specificity … **any
> property you intend to animate from CSS must not also be written inline on the
> same widget. Pick one owner per property, per widget.** This single rule
> decides most of the architecture in §7."*

In plain terms: in eww, a property driven by **live data** (`CAVA_BASS` glow) can
**never also be animated** by hover or a keyframe. `.nyx-surface` is deliberately
forbidden from declaring `box-shadow` for exactly this reason. That is a
structural "you cannot do both" — precisely the class of thing the owner says he
does not want to run into.

### 13.2 Animation

| | **eww / GTK3** | **AGS / GTK4** | **Quickshell / QML** |
|---|---|---|---|
| Declarative transitions | ✅ CSS `transition` **[WEB** GTK3 CSS Overview**]** | ✅ CSS `transition` **[WEB** GTK4 css-properties**]** | ✅ `Behavior`, `Transition`, `PropertyAnimation` **[WEB** Qt 6.11 docs**]** |
| Keyframes | ✅ `@keyframes` — proven live here (`boombox-led-pulse`) **[DOC]** | ✅ `@keyframes` | ✅ `SequentialAnimation` / `ParallelAnimation` / `PauseAnimation` / `PropertyAction` / `ScriptAction` |
| Easing | CSS timing functions | CSS timing functions | Full `Easing.type` set **plus** per-animation bezier |
| **Spring / physical motion** | ❌ | ❌ | ✅ **`SpringAnimation`** with `mass`, `damping`, `epsilon`; plus `SmoothedAnimation` |
| **`transform` (scale / rotate / translate)** | ❌ **none — GTK3 CSS has no `transform`** **[DOC** spec §3.2**]** | ✅ **`transform` + `transform-origin`** (CSS Transforms Level 1) — but render-only, layout is unaffected **[WEB]** | ✅ `scale`, `rotation`, `transform` are **first-class Item properties**, and layout follows |
| **State machine** | ❌ hand-rolled from `defvar` + conditional `:style` | ❌ hand-rolled from CSS classes | ✅ **`states` + `transitions`**, declarative, with `from`/`to` and `reversible` |
| **Interruptible mid-flight** | Partly — CSS transitions retarget; anything inline does not animate at all | Partly — same | ✅ By construction. `Behavior` retargets on every change |
| **Animation off the UI thread** | ❌ | ❌ | ✅ **Animators** — `XAnimator`, `YAnimator`, `ScaleAnimator`, `RotationAnimator`, `OpacityAnimator`, **`UniformAnimator`** — run on the scene-graph **render thread** and *"continue to animate even when UI is otherwise blocked"* **[WEB]** |
| **Animating a live data value** | ❌ **blocked by the inline-`:style` rule** (§13.1) | ⚠️ possible, needs care | ✅ `Behavior on <property>` animates **every** change to that property regardless of who wrote it |
| GPU-accelerated rendering | ❌ **no** — open request, eww #1342 **[WEB]** | ✅ GSK (GL / Vulkan) | ✅ Qt Quick scene graph (GL / Vulkan) |

The two rows that matter most are the last three. **"Animate a value that comes
from live system data"** is the entire idea behind the CAVA-reactive glow the
owner already loves, and it is the one eww structurally forbids.

### 13.3 Shaders, effects and particles

| | **eww / GTK3** | **AGS / GTK4** | **Quickshell / QML** |
|---|---|---|---|
| **Per-widget GPU shader** | ❌ nothing | ⚠️ `Gtk.GLArea` exists — raw GL from JavaScript, no framework support | ✅ **`ShaderEffect`** — arbitrary GLSL fragment + vertex shaders on any item, **with custom uniforms**, animatable via `UniformAnimator` |
| Shader authoring cost | n/a | hand-written GL boilerplate | Qt 6 requires **precompiled `.qsb`** via the `qsb` tool (`qt6-shadertools`); no inline GLSL. Quickshell 0.3's release notes: *"the process of using a shader with QtQuick is rather painful, requiring `qsb` reruns and a Quickshell relaunch for every change. Full hot-reloading … planned"* **[WEB** outfoxxed.me, 0.3 release**]** |
| Shaders in real use | — | rare | **Yes** — same release notes: *"Far more Quickshell configurations now use shaders"* **[WEB]** |
| **Blur behind a widget, inside the panel** | ❌ §5.4 — costs a whole extra layer surface | ✅ **`backdrop-filter`**, new in **GTK 4.22.0 (2026-03-06)**; Arch ships `gtk4 1:4.22.4-1` built 2026-04-30 **[PKG]**. ⚠️ blurs only content **inside the same window** — it cannot blur the desktop behind a transparent window **[WEB]** | ✅ `MultiEffect` + `ShaderEffectSource` — render any item to a texture, blur it, leave its sibling sharp |
| Bloom / glow / colourise / saturate / mask | ⚠️ faked with `box-shadow` only | ⚠️ `backdrop-filter` gives blur/sepia/invert/saturate behind an element | ✅ **`MultiEffect`** (`QtQuick.Effects`): blur, shadow, colorization, brightness, contrast, saturation, mask — *"multiple effects … into a single item and shader"*, one render pass. **Ships in Arch `qt6-declarative`** **[PKG]** |
| **Particle system** | ❌ | ❌ | ✅ **`QtQuick.Particles`** — `ParticleSystem`, `Emitter`, `ImageParticle`, affectors (`Turbulence`, gravity, wander). **Ships in Arch `qt6-declarative`** **[PKG]** |
| GPU vector shapes / neon strokes | ❌ pre-render a PNG | ⚠️ `GskPath` from code | ✅ `QtQuick.Shapes` — GPU paths, gradients, dashes. **Ships in Arch `qt6-declarative`** **[PKG]** |
| Distortion / warp / chromatic aberration | ❌ | ❌ realistically | ✅ `ShaderEffect` — this is exactly what it is for |
| Full-screen post-process | Hyprland `screen_shader` — **but §12.1 makes it unaffordable animated. Identical for all three** | same | same |

**The honest caveat on the Quickshell column:** shaders require the `qsb`
build step and do not hot-reload yet. So the *ceiling* is enormously higher, but
the *iteration loop for shaders specifically* is closer to compile-and-restart
than to live-edit. Ordinary QML — layout, colour, animation, effects,
particles — **does** hot-reload.

### 13.4 The six effects this project actually cares about

| Effect | Today | eww ceiling | AGS/GTK4 | Quickshell/QML |
|---|---|---|---|---|
| **Lock-screen audio spectrum** (`nyxus-lock-cava`) | hyprlock `cmd[update:50]` shelling out per frame → **2,969 dropped updates in 40 s** (audit §11.5, LK-02) **[DOC]** | n/a — hyprlock is a separate program, so **no framework choice fixes this** | same | ✅ only if the lock itself moves into the shell (`WlSessionLock` + `Pam`) — then bars are items with `Behavior on height`, **no subprocess per frame**. *Not proposed here; noted as a ceiling* |
| **CAVA-driven glow** (`CAVA_BASS` → inline `box-shadow`) | works — **nine** inline `:style` lines in `eww.yuck` interpolate it, 46 references in all **[REPO]** | ⚠️ **works but caps you** — §3.3 forbids CSS-animating any inline-driven property, which is why `.nyx-surface` may not declare `box-shadow` **[DOC]** | ✅ same trick, plus `transform` | ✅ `Behavior on glowRadius { SpringAnimation {} }` — the value can be data-driven **and** animated **and** hover-modulated at once. **Ceiling removed** |
| **Hover-scramble text** | lives in `nyxus_chrome.py`, a per-label Python timer animator in the **GTK4 apps** — not an eww feature **[REPO]** | would need a subprocess or a `defvar` churn per label | ✅ direct port of the same idea | ✅ a `Timer` + string property; `Behavior` handles the fade |
| **Frosted glass + corner-bleed** | compositor blur + widget alpha falloff **[DOC]** | ✅ radial-gradient alpha | ✅ radial-gradient alpha; 4.22 adds non-concentric radial gradients **[WEB]** | ✅ plus `OpacityMask` / `MultiEffect` masking. **All three work — see §14** |
| **Motion implied by the mockups** — taskbar hover-lift + running-dot, launcher scale-in from the orb, results reflowing as you type, pill press, slider drag, calendar month slide, media scrub, notification card enter/dismiss, Clear All cascade | none built | hand-rolled per widget; list add/remove has no animation primitive | `<For>` diffs the list; animation still hand-rolled per item | ✅ `ListView` has **`add` / `remove` / `displaced` / `populate` transitions** as built-ins — the Clear All cascade and the search-results reflow are *declared*, not coded |
| **Live wallpaper** (`mpvpaper`) | layer 0, below everything **[REPO]** | unaffected | unaffected | unaffected — and Quickshell could additionally render video itself via `qt6-multimedia`. **Not a differentiator** |

### 13.5 The ranking, explicitly

**For eye candy: Quickshell/QML ≫ AGS/GTK4 ≫ eww/GTK3.**

Both gaps are large, and they are different in kind:

1. **Quickshell — highest ceiling by a wide margin.** It is the only one of the
   three with real per-widget GPU shaders, a particle system, spring physics,
   render-thread animators, a declarative state machine, and list transitions.
   Nothing on the owner's wish list is out of reach, and several things he was
   told were impossible (per-widget blur, rotate/flip, computed greyscale,
   shader uniforms driven by system state) become ordinary.
2. **AGS/GTK4 — a genuine, large upgrade over eww, but a middle tier.** It gains
   `transform`, GPU rendering, and — new since **GTK 4.22.0, 2026-03-06** —
   `backdrop-filter`, which finally allows blur behind one widget inside a
   panel. It still has no particles, no spring animation, no first-class shader
   item, and no state machine.
3. **eww/GTK3 — the weakest, and structurally so.** No `transform`, no `filter`,
   no per-widget blur, no GPU acceleration, no rotate/flip, and the
   inline-`:style` rule that makes data-driven and animated mutually exclusive.
   Its toolkit binding is unmaintained, so **this list will never get shorter.**

### 13.6 Does this change the recommendation?

**No — and it makes the decision easier, which is worth saying plainly: eye
candy and packaging point at the same framework.**

That is a genuinely lucky outcome and it is the reason to state it rather than
hedge. Part I picked Quickshell on packaging, failure loudness and hot reload,
and explicitly flagged GTK4 coherence as *"the only criterion where AGS beats
everything."* Re-deriving with eye candy weighted **first** does not reopen it:
Quickshell wins that criterion too, and by more than it won the packaging one.
There is no conflict to trade off and no cost the owner has to swallow to get
both.

**Where the re-derivation did change something:** Part I under-sold how much
eww is *already* costing him. §13.1 shows five of the seven "impossible" entries
in his own eye-candy spec are GTK3 limits, not physics. If the owner wants eye
candy as a primary goal, **staying on eww for Daily is the option that most
constrains him**, and that should have been in Part I's summary rather than
buried in the maturity section.

**The one thing that would flip this to AGS** is unchanged from §10.1: if the
trial shows the corner-bleed glass cannot be matched in QML, or if QML proves
unlearnable at this project's pace. Eye candy does not add a new reason to
prefer AGS — it removes one.

---

## 14. THE CORNER ARTIFACT — IN PLAIN LANGUAGE

The owner read "rectangles" as "triangles" and asked whether the result would
look like a cool feature or like a bug. Short answer: **like a small bug if left
alone, it is already solved in this build, and it is not a reason to pick one
framework over another.**

**What the limitation actually is.** A shell panel is a *layer surface*, and a
layer surface is reported to the compositor as a **rectangle** — Hyprland's
maintainer, on eww specifically: *"hyprland can't really know how to cut the blur
on corners, since all layersurfaces report is a rectangle."* **[WEB]** So when
you round the panel's corners in the stylesheet, the **blurred region** is still
the full rectangle. Past each rounded corner you can get a faint square of
blurred wallpaper where you expected sharp wallpaper.

**How visible is it?** Most visible over bright, busy wallpaper; generally
invisible over a dark base with a glow edge — which is exactly the urban-neon
direction (brief §4). **Nothing is triangular.** It is a soft right-angle of
slightly-smeared background hugging each corner.

**It is already fixed in this build, twice over.** `ignore_alpha` tells the
compositor to skip blurring pixels below an alpha threshold, so fully- or
nearly-transparent corner pixels stop being blurred. NYXUS sets it on every
surface **[REPO**,
`airootfs/etc/skel/.config/hypr/conf.d/nyxus-hyprland-layerblur.conf`**]**:

```
layerrule = blur on,        match:namespace ^(nyxus.*)$
layerrule = ignore_alpha 0.2, match:namespace ^(nyxus.*)$
```

and that file's own header records the history:

> *"`ignorealpha` raises the threshold so fully-transparent pixels don't get
> blurred (otherwise the blur leaks past window edges)"* … *"it is why the
> frosted rectangular 'shadow box' behind the tall transparent bars was fought
> twice and came back."*

So this is a **known, named, already-beaten** artifact here, and the fix is one
number. Upstream confirms the same remedy: Hyprland issue #9397 ("Layer
rounding") was resolved by correcting `ignorealpha` syntax, and the current wiki
documents `ignore_alpha` as *"makes blur ignore pixels with opacity of a or
lower"* **[WEB**, wiki.hypr.land, updated 2026-07-31**]**. `xray` is the other
lever — it makes the layer blur the **wallpaper only**, ignoring windows behind
it, which removes the "smeared window edge" version of the same complaint.

**His corner-bleed effect is unaffected.** Corner-bleed is **widget-painted
alpha falloff** — a radial gradient in the panel's own background that fades the
corners toward transparent. That is painted by the toolkit, not by the
compositor's blur pass, so the rectangle limitation does not touch it. If
anything the two cooperate: the alpha falloff is what pushes those corner pixels
below the `ignore_alpha` threshold, so **turning the corner-bleed up makes the
blur artifact smaller, not bigger.** *(Marked **[INFER]** — the mechanism is
documented, but the specific interaction at the Daily glass values has not been
run.)*

**It is identical in eww, AGS and Quickshell**, because it is a property of the
`wlr-layer-shell` protocol and Hyprland's renderer, not of any widget toolkit.
**Do not use it to choose a framework.**

---

## 15. RICH FEATURES — WHAT YOU GET FREE VERSUS WHAT YOU BUILD

"Rich features" is where the gap is widest and least arguable, because it is
countable. **[PKG/WEB**, verified 2026-08-02**]**

| Capability the mockups need | **eww** | **AGS / Astal** | **Quickshell** |
|---|---|---|---|
| **Notification daemon** (flyout cards, Clear All) | ❌ not a daemon at all. Today dunst owns the bus and `notif-history.sh` polls at 3 s; the plan delegates to **swaync** **[REPO/DOC]** | ✅ `AstalNotifd` | ✅ `Services.Notifications` — implements the freedesktop server |
| **MPRIS media** (art, track, scrub, transport) | ❌ `player.sh` + `playerctl` at 1 s **[REPO]** | ✅ `AstalMpris` | ✅ `Services.Mpris` |
| **PipeWire audio** (volume slider, per-app mix, peak meter) | ❌ `audio.sh`/`audio-sinks.sh` at 2–3 s **[REPO]** | ✅ `AstalWp` (wireplumber) | ✅ `Services.Pipewire`, incl. `PwNodePeakMonitor` |
| **Network** (Wi-Fi pill, SSID list) | ❌ `network.sh` 5 s + `WIFILIST` 8 s + `WIFISAVED` 10 s **[REPO]** | ✅ `AstalNetwork` (libnm) | ✅ network service |
| **Bluetooth** (pill, device list) | ❌ `bluetooth.sh` 5 s + `BTLIST` 5 s **[REPO]** | ✅ `AstalBluetooth` | ✅ `Quickshell.Bluetooth` |
| **Battery / UPower** | ❌ `battery.sh` 10 s **[REPO]** | ✅ `AstalBattery` | ✅ `Services.UPower` |
| **Power profiles** | ❌ `POWERPROF` 10 s **[REPO]** | ✅ `AstalPowerProfiles` | ✅ `UPower.PowerProfiles` |
| **System tray** | ✅ `systray` widget since 0.6.0 **[WEB]** — the one thing eww ships | ✅ `AstalTray` | ✅ `Services.SystemTray` + `DBusMenu` |
| **Hyprland workspace / window state** (taskbar) | ❌ `WORKSPACES` 1 s + `hyprctl` scripts **[REPO]** | ✅ `AstalHyprland` | ✅ `Quickshell.Hyprland` **and** compositor-agnostic `ToplevelManager` |
| **App index + launcher search** | ❌ scan `.desktop` yourself; a subprocess per keystroke | ✅ `AstalApps` (fuzzy scoring) | ✅ `DesktopEntries` |
| **Calendar** | ⚠️ GTK3 `calendar` widget exists, but NYXUS renders its own grid in `calendar-month.sh` at 300 s **[REPO]** | ✅ `Gtk.Calendar` or composed | ✅ `MonthGrid` or composed |
| **Brightness** | ❌ `brightness.sh` 5 s **[REPO]** | ⚠️ via `AstalIO` exec or udev | ⚠️ `Io` / `Process`, or UPower where exposed |
| **Clipboard history** | ❌ external (`cliphist`) | ⚠️ external | ⚠️ external |
| **Idle / inhibit** | ❌ external (`hypridle`) | ✅ `AstalIO` + idle | ✅ `IdleInhibitor`, `IdleMonitor` **[WEB]** |
| **PAM auth / session lock** | ❌ | ✅ `AstalAuth` | ✅ `Services.Pam` + `WlSessionLock` |
| **greetd** | ❌ | ✅ `AstalGreet` | ✅ `Services.Greetd` |
| **Screencopy** (live window previews on taskbar hover) | ❌ | ❌ | ✅ `ScreencopyView` — *"displays a video stream from other windows or a monitor"* **[WEB]** |

**Which of the flyout's elements come free.** Of the six things in
`set-notifications.png` — toggle pills (Wi-Fi, Bluetooth, Airplane, Night Light,
Do Not Disturb, Dark Mode), brightness + volume sliders, month calendar, media
card, notification stack, Clear All — **five of the six are backed by a built-in
service in Quickshell and in AGS, and one (brightness) is a small shell-out in
both.** In eww, **zero** are backed; all six are shell scripts on timers, and the
notification stack is not achievable at all without a second daemon.

**Why this is not a convenience argument.** Audit §11.4 records two notification
daemons shipping and racing, `swaync.service` failing on every boot, and the
Settings notifications page configuring a backend that never ran **[DOC]**. That
defect exists *because* the shell could not be the notification daemon. Audit
§11.3's orphan-daemon leak, and LK-02's 2,969 dropped label updates, are the same
species: **a shell that cannot hold state in-process ends up as a constellation
of processes that race.** Built-in services are not garnish here — they delete a
measured class of defect.

**The taskbar hover-preview row is worth a second look.** `ScreencopyView` means
Windows-11-style live thumbnails when you hover a taskbar button are *available*,
not a research project. That is squarely in "eye candy and rich features", and it
exists in exactly one of the three.

---

## 16. "WHAT DOES THIS TAKE AWAY FROM ME?"

The direct answer to the second criterion.

### 16.1 It expands the ceiling; it does not lower it

Everything eww can do, both alternatives can do. The reverse is not true. §13.1
lists five capabilities the owner's own spec records as impossible that stop
being impossible. There is **no** item on the "eww can, Quickshell cannot" side
of the ledger for these three surfaces — not one was found while writing this.

Concretely, things that become available and are not available today:

- Per-widget blur without spending a whole extra layer surface (§5.4 retired).
- Computing a greyscale/desaturated variant at runtime instead of shipping a
  second `-mono.png` for every asset (§5.3 retired).
- Rotate, scale and flip on real widgets, so a toggle can be *modelled* rather
  than pre-rendered as a Blender sprite sheet (§5.2 retired).
- Custom shader uniforms driven by system state — `CAVA_BASS` into a real
  fragment shader — which Hyprland structurally refuses (§5.6 retired, at the
  widget level).
- Animating a property that is *also* data-driven (§3.3's hard rule retired).
- Live window thumbnails on taskbar hover (§15).
- Particles, spring physics, and list add/remove/displace transitions.

### 16.2 What genuinely becomes harder — and how much

**Two theming systems.** The shell would be QML; the apps (`nyxus_chrome.py`,
Settings, Control, Notepad, Stickies, Store) stay GTK4 Python. This is the real
cost and it deserves a straight measurement rather than reassurance.

**The colour half is already solved, and better than expected.**
`nyxus-apply-accent` is not an eww script — it is a **27-consumer** regeneration
pipeline **[REPO]**, and the registered consumers already include:

```
"${HOME}/.config/qt5ct/colors/nyxus-prism.conf"
"${HOME}/.config/qt6ct/colors/nyxus-prism.conf"
```

**A Qt consumer is already in the pipeline today.** The mechanism is a
baseline-substitution pass whose own header states it handles *"`#rrggbb` /
`rrggbb` (CSS, rasi, toml, hyprland `rgba(rrggbbaa)`, **qt `#aarrggbb`**)"* plus
decimal triplets **[REPO]**. Adding `editions/daily/shell/Theme.qml` is **one
line in the `CONSUMERS` array**, in a script that already feeds SCSS, GTK3 CSS,
GTK4 CSS, hyprlang, rasi, dunstrc, TOML, kitty.conf, a btop theme, two Qt
colour files and three Python files. This is a solved shape, not a new one.

**The half that is not automated is visual language** — radii, shadow curves,
motion timings, hover semantics — kept matching by hand between QML and GTK4
CSS. That is ongoing discipline, and it is real. But note: **it is the same
discipline already required today** between eww/GTK3 and the GTK4 apps, and the
eye-candy spec already resolved it with a rule that transfers unchanged
**[DOC** §3.4**]**:

> *"the eye-candy language is specified for eww + Hyprland; GTK4 apps adopt only
> the palette, radii and motion timings, and get no bespoke effects."*

Substitute "Quickshell" for "eww" and the rule still works. **The shell is where
the identity lives; the apps follow the tokens.** That is what NYXUS already
does.

**Three other honest losses:**

- **Nobody in this project has written QML.** Real, and the trial in §11 exists
  to price it. Mitigated by hot reload — the feedback loop is seconds, not a
  bake.
- **AGS would have reused TypeScript skills** already present in this pnpm
  workspace, and Quickshell does not. That is a genuine point in AGS's favour
  that §13 does not erase.
- **eww knowledge stops compounding for Daily.** It stays required for alien,
  which is frozen — so it becomes maintenance knowledge rather than growing
  knowledge.

### 16.3 Nothing already built is lost

Both halves confirmed against the tree **[REPO]**:

- **The alien shell stays eww and stays untouched.** Owner decision 2026-08-01,
  and it is now *enforced*: gate `13pm` asserts the skel accent stays `prism`,
  the wallpaper stays `nyxus-urban-alien`, and `NYX_EDITION` still defaults to
  `alien` **[REPO]**. Daily work cannot silently flip it. All ~4,000 lines of
  yuck, ~6,000 lines of SCSS and 88 feeder scripts keep running exactly as they
  do today.
- **Phase 1's Daily work is framework-neutral.** The entire committed edition
  directory is six files — `accent.json`, `wallpaper.conf`, `wallpaper.json`,
  `wall-rotation.list`, `regreet.css`, `hyprlock-accent.conf` **[REPO]** — plus
  four wallpapers and the `NYX_EDITION` bake hook. **Not one of them is an eww
  file.** They are colour, wallpaper and greeter/lock theming that any shell
  framework consumes unchanged.
- **The only eww-shaped thing to discard is a plan line**, not code: the §6
  entry routing the bar/flyout/launcher to `editions/daily/eww/*`, and the
  swaync assignment for the flyout. Both are marked *"not started"* **[DOC]**.

### 16.4 Reversibility — what backing out actually costs

| Step | Cost to undo |
|---|---|
| The taskbar trial (§11) | Delete one directory under `editions/daily/`. `git rm`. |
| The `quickshell` package | It is **appended at bake by the edition block**, never committed into `packages.x86_64` — remove one line |
| Alien | **Never changed.** Provable, not asserted: bake with the default `NYX_EDITION=alien` and diff; gate `13pm` fails if any shared default moved |
| Phase 1 theme files | Untouched under every outcome |
| Time | The §11 kill criteria stop the trial at ~2 days if it is going badly, **before any bake** |

This is the cheapest reversible decision available, and it gets more expensive
every week that Daily shell code is written in something.

### 16.5 The paragraph to read to him

> Switching does not take options away from you — it gives you back a pile you
> were already told you could not have. Right now, five of the seven things your
> own eye-candy document lists as "not possible" are limits of eww's ancient
> toolkit, not limits of Linux or Hyprland: you cannot blur one card inside a
> panel, you cannot compute a greyscale version of an image (that is why every
> asset ships a second `-mono` copy), you cannot rotate or scale a widget (that
> is why a real-looking toggle would have to be pre-rendered in Blender frame by
> frame), you cannot push a live value like the bass level into a shader, and you
> cannot animate a property that is already driven by live data — which is
> exactly why the panels are forbidden from having an animated glow. All five of
> those come back with Quickshell, and it adds real GPU shaders, a particle
> system, spring physics, and live thumbnails of your open windows when you hover
> the taskbar. What you give up is smaller than it sounds: the shell would be
> written in QML while your apps stay GTK Python, so those are two styling
> systems to keep looking identical — but your accent script already generates
> theme files for twenty-seven different consumers, two of which are already Qt, so
> the colours are one line of wiring; what is left is the same "keep the radii
> and timings matching" discipline you already run between the bars and the apps
> today. Nothing you have built is lost: the alien build stays on eww and is
> locked by an automated check, and every Daily file made so far is colour and
> wallpaper that any framework reads. And if it goes badly, backing out is
> deleting one folder — the trial is one file, and it gets judged on your own
> screen before anything is ever baked.

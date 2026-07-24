# NYXUS — AGENT HANDOFF & BUILD STATE (read this FIRST)

> **Last updated: 2026-07-24 (ALIEN NEON + Settings audit checklist written)** · Owner: Joseph A. Sierengowski (`nyx` / `nyxus`)
> If you are a new agent picking up NYXUS: **read this entire file before touching
> anything.** It exists because this project got scattered across duplicate clones
> and the same problems got re-diagnosed and re-broken multiple times, costing the
> owner a lot of time and money. Do not veer off into a different approach. Keep the
> flow, and **update this file as you work** so the next agent re-derives nothing.

---

## 0. THE RULES (do not break these)

1. **There is exactly ONE canonical repo: `~/Nyxus-Core`** (capital N-C, branch
   `main`, remote `sierengowskisierengowski-cpu/Nyxus-Core`). Always work here,
   commit + push every change. A lowercase `~/nyxus-core` or any
   `~/.nyxus-backup-*`, `~/nyxus-KNOWN-GOOD-*`, `~/nyxus-build-recovery`,
   `~/Backups/nyxus*` is a **stale snapshot — never work in it.** The lowercase
   duplicate was already deleted (2026-07-22) after verifying it held nothing
   unique. If one reappears, it's a wrong clone.
2. **Sudo on this machine is FINGERPRINT ONLY (no passwordless).** The agent
   **cannot** run `sudo`, `dd`, `chown`, or the bake (it needs root). The USER
   runs those in their own terminal. Never assume you can.
3. **Never edit `build-iso.sh` (or any script) while it is baking/running** —
   bash re-reads scripts by byte offset and it corrupts the live run.
3b. **Only start a bake from a fully COMMITTED, IDLE repo.** A bake reads the
   profile/scripts as it runs; if you kick it off mid-edit it captures a
   partial set of your changes. (2026-07-22: a bake started while edits were
   in flight shipped the offline-cache + saucer fixes but MISSED the
   ungated-bars fix — verify baked ISOs with `unsquashfs`, don't assume.)
4. **Don't fold the two sibling repos into Nyxus-Core** without explicit
   direction (see §1).
5. **When something surprises you, write it in this file the moment you hit it.**

---

## 1. THE THREE REPOS (single source of truth for each)

| Repo | Path | Remote | What it holds |
|---|---|---|---|
| **Nyxus-Core** | `~/Nyxus-Core` | `Nyxus-Core` (branch `main`) | The distro: ISO builder, all desktop configs, scripts, apps, docs. **Canonical.** |
| **kage-ryu** | `~/Projects/arch-custom-kernel/linux-kage-ryu` | `kage-ryu` | The custom kernel PKGBUILD + the `scheduler/` scx_kage sched-ext source. |
| **companion-3d** | `~/Nyxus-Core/companion-3d` | `Nyxus-Companion-3D` | A **separate** Godot 3D-companion project. Nested inside Nyxus-Core but its own git repo — **gitignored by the parent.** Not part of the ISO build. |

Live desktop surfaces (`~/.config`, `~/.local/bin`, `~/.nyxus`) mirror the repo —
keep them in sync, but **the repo is canonical.**

---

## 2. WHAT NYXUS IS

A custom **Hyprland-based Arch Linux security-lab distro** — "DARK MIRROR" /
alien-graffiti-space aesthetic — with a bespoke **"Kage Ryu" kernel**. Purpose:
an OSINT / malware-analysis / honeypot workstation that also looks like nothing
else. Login `nyx` / `nyx`, hostname `nyxus`.

---

## 3. ⚠️ HOW THE DESKTOP IS ACTUALLY DELIVERED (the thing that caused the "circles")

**This is the single most important architectural fact. Misunderstanding it is why
the build felt like it went in circles for months.**

The ISO does **not** boot a fully-formed desktop by itself. It ships:

1. **A base airootfs + `/etc/skel`** — the baked configs. `customize_airootfs.sh`
   creates the live user `nyx` and copies `/etc/skel` → `/home/nyx`. This includes
   `hyprland.conf` + its 15 `conf.d/*.conf` shards, all 9 eww `.yuck` bars, the
   theme, wallpaper, keybinds. **The core desktop lives here and is fully offline.**
2. **A first-boot bootstrap** — `nyxus-bootstrap` (Hyprland `exec-once`, every
   login, idempotent via `~/.nyxus/.bootstrapped`). It installs the heavier
   **web-apps / chrome library / Phantom** by running `nyxus_install.sh`, pulled
   either from **production `nyxus-core.replit.app`** (network) or, offline, from a
   **pre-staged cache at `/opt/nyxus-cache`** baked into the ISO.

**Consequences you must internalize:**
- Editing `~/Nyxus-Core/.../etc/skel` changes the **core desktop** (bars, theme,
  wallpaper, keybinds). This is offline-complete and is what boots.
- The **apps** (the Hub's "Main Page / NYXUS Account / App Store / Chrome Library"
  etc.) come from `nyxus_install.sh` + its payload — i.e. from replit or the
  offline cache. Their up-to-date source is `artifacts/api-server/nyxus-scripts/`
  (tracked). `BOOTSTRAP_VERSION` in `nyxus-bootstrap` is still `2026.05.12-r11`
  — **not bumped for July work.** If you need installed systems to re-pull, bump it.
- **ALIEN NEON palette is LOCKED (2026-07-23).** Canonical preset = `prism` in
  `~/.config/nyxus/accent.json` / skel:
  violet `#7d3dff` · magenta `#ff2dad` · neon green `#39ff14` · orange `#ff8a1e`
  (+ fixed cyan `#2bd2ff` · red `#ff2d55` · yellow `#ffe600` · orchid `#e367ff`).
  **`follow_wallpaper` is OFF.** Do NOT re-enable wallpaper→accent extraction —
  that drift (old wallpaper blues / cream "Sprint E") is exactly how the desktop
  kept losing its alien look. Apply via `nyxus-apply-accent prism`.
- **Cream `#f4ead5` is banned.** Cool white `#eef2fa` on void `#05060a` only.

---

## 4. WHAT THE BUILD INCLUDES

### ISO
- Output: `iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso` (gitignored, ~9.5–10 GB).
- `iso_name=nyxus`, `iso_label=NYXUS_2026_07` (**must be identical in profiledef +
  all 5 archisolabel refs** or live media won't boot). Only remaining "nyx" is the
  internal source dir name `nyx-profile` (never appears in the ISO).
- Built by `iso-builder/build-iso.sh` (archiso/mkarchiso, UEFI GRUB + BIOS syslinux).
  **Bakes from a throwaway copy** of the profile → never corrupts the repo (fixed
  2026-07-22, commit `fe089345`).
- **Offline cache** at `/opt/nyxus-cache` is staged from `artifacts/api-server/
  nyxus-scripts` (the bake **hard-fails** if the cache would ship without
  `nyxus_install.sh` — no more silent online-only ISOs). This makes first boot work
  with **no internet**.

### Boot experience
- **🐉 Dragon GRUB menu** — centered Kage-Ryu black-dragon theme with real fonts
  (`.pf2`), no "?" boxes. **UEFI ONLY.** A Legacy/BIOS boot uses the plain
  `syslinux` text menu (unthemed) — that's the "normal menu" if you don't pick the
  **"UEFI: <device>"** entry. `EFI/BOOT/BOOTx64.EFI` is present in the ISO.
- **🛸 UFO "Cosmic Arrival" plymouth splash** — the saucer descends with a beam.
  As of 2026-07-22 the saucer art is the **real NYXUS/HYPRLAND graffiti craft**
  (extracted from `livewall/nyxus-livewall-ufo.png`, magenta glow-blob floodfilled
  out), matching the desktop wallpaper. Plymouth reuses it on shutdown/reboot too.

### Kernel — "Kage Ryu Nyxus" (`linux-kage-ryu`)
- XanMod **7.0.12**, Alder-Lake-tuned (i7-12700H), lean `localmodconfig` build
  (~27 MB pkg). Security-lab config: kprobes/uprobes/BPF/BTF, userns/cgroup-bpf/
  overlayfs/CRIU/bridge/veth/vxlan (Docker), KVM-Intel, BBR+FQ, MGLRU, io_uring;
  CPU mitigations stay **available** (never hardcoded off).
- **Kage-Ryu is the PRIMARY/default kernel (rev 2026-07-23)** — on the live USB
  (so you validate the real kernel before installing) AND on the installed
  system. Stock `linux` is kept ONLY as a rescue entry so a bad Kage-Ryu boot
  can never strand you. `linux-lts` / `linux-zen` / `linux-hardened` were
  dropped from `packages.x86_64` (focused custom-kernel distro).
  **⚠ 2026-07-23:** the currently shipped `7.0.12` pkgs were built without
  iso9660/squashfs/loop — live default is broken until those pkgs are rebuilt
  (PKGBUILD patched) and the ISO rebaked. Use stock rescue on the stick for now.
- Built via `kernel/install-kage-ryu.sh` (on the running system) or
  `cd <kage-ryu repo> && makepkg -sc`. Baked into the ISO **BY DEFAULT**
  (`NYX_WITH_KAGE_RYU` defaults to `1`; kernel is never compiled inside the
  bake). Set `NYX_WITH_KAGE_RYU=0` to opt OUT and bake a stock-only ISO.
- **The bake HARD-FAILS if the prebuilt packages are missing** (so it can never
  silently ship kernel-less — the 2026-07-22 no-kernel bake can't recur). The
  prebuilt packages (`linux-kage-ryu-7.0.12` + headers, ~28M/38M) already exist
  at `~/Projects/arch-custom-kernel/linux-kage-ryu/` and are found automatically.
- **How it's wired:** `build-iso.sh` stages the packages into a profile-local
  `[nyxus-local]` repo, appends them to `packages.x86_64`, and rewrites the three
  live boot menus (grub / systemd-boot / syslinux) so Kage-Ryu is entry #0 and
  stock is a labelled rescue — **all in the throwaway profile copy**, so the
  repo's static menus stay stock-safe. On install, Calamares copies both kernels
  and `nyxus-set-grub-default-kage` (shellprocess) flips the installed GRUB
  saved-default to Kage-Ryu.
- `scheduler/scx_kage` — sched-ext scheduler; source committed to the kage-ryu
  repo (branch `feat/scx-kage-scheduler`). Binary staged into the ISO.
- Bumping to 7.1.x needs a matching XanMod patch + fresh sha256 (not a blind edit).

### Desktop features
- 4 reactive features: **Mood Engine, Machine Whispers, Supernova, Graffiti Memory
  Wall** (built on the `nyxus-sense` bus → `~/.config/nyxus/sense.json`).
- **Reflex layer** coexistence contract: `tintd`=border colors, `beatd`=border
  angle, `pulsed`=event pulses, `wall-fx`=cava→mpv. Don't duplicate these.
- **Hacker mode** (Super+Ctrl+X) transforms the desktop; pauses/resumes the reflex
  layer; `reconcile-boot` clears stale state on login.
- **eww bars** (4) — relaunch ONLY with `nyxus-eww-launch-safe` (one daemon + 4
  bars). Repeated `eww kill`/reload cycles can leave TWO daemons → double bars.
- **Music flip** bottom bar; **NYXUS Hub** (Super-driven quick-settings/apps).

---

## 5. CURRENT STATE (2026-07-23)

### Done + pushed
- Repo un-scattered: one canonical `~/Nyxus-Core`; duplicate deleted; nothing lost.
- Build-iso no longer corrupts the profile (throwaway copy) — `fe089345`.
- **Live-boot post-mortem fixes** — `7ccbaf0b`:
  - Offline cache never ships empty (falls back to in-repo source + hard-fail guard).
  - eww bars **ungated** from the network bootstrap → desktop comes up offline.
  - Splash saucer = real graffiti UFO (both ISO theme + offline-cache source).
- kage-ryu `scheduler/` source committed + pushed (branch `feat/scx-kage-scheduler`).
- `companion-3d/` gitignored by the parent.
- **2026-07-23 — offline-first, Replit cut (`ef360df7`)** — the 07-22 stick booted
  to "offline install failed (code 1)" even on ethernet. Root causes fixed:
  - **Replit is retired.** `nyxus-core.replit.app` 404s; the bootstrap only ever
    probed *that* server, so it mislabeled a working connection as "no internet".
    Bootstrap is now **offline-cache-first and never phones home** (network path is
    opt-in dev-only). The desktop is delivered ENTIRELY from `/opt/nyxus-cache`.
  - **`nyxus_install.sh` aborted at code 1.** It ran `set -euo pipefail`, so the
    first `clear` (no `$TERM` under exec-once) killed the whole install. Dropped
    `-e`, guarded `clear`.
  - **`eww/eww.scss` didn't exist** (repo ships `eww.css` + `eww.scss.source`) —
    the one missing dl() made the install exit 1 forever. Fixed to pull real files.
  - **hyprexpo build burned ~15 min every login** — now one-shot + offline-skip.
  - **Wrong wallpaper**: `wallpaper.conf` hardcoded `/home/cosmic` → unreadable for
    `nyx`. Fixed to `/home/nyx` + slug-robust `nyxus-wallpaper-autostart`.
  - `BOOTSTRAP_VERSION` → `2026.07.23-r12-offline`.
- **2026-07-23 — Kage-Ryu is now the DEFAULT kernel** (see §4): dropped
  lts/zen/hardened; `NYX_WITH_KAGE_RYU` defaults ON; build-iso rewrites all three
  boot menus (Kage-Ryu primary + stock rescue) in the throwaway copy; Calamares
  `nyxus-set-grub-default-kage` sets the installed default. Prebuilt kernel pkgs
  live at `~/Projects/arch-custom-kernel/linux-kage-ryu/` (built).

- **2026-07-23 (round 2) — the "missing eye candy" root cause + feature restore**
  (`e8d01837`, `a920e545`). Live boots were missing sounds, reactive layer,
  Mission Control, etc. Root cause: **`nyxus_install.sh` (the ISO/first-boot
  installer) deployed only ~5 of the ~82 `~/.local/bin` launcher scripts** that
  `hyprland.conf` calls by literal `~/.local/bin/<name>` path — so the entire
  reactive layer, `nyxus-soundd`/`nyxus-sfx`, wallpaper tooling, hub scripts,
  shader/spray/lens FX etc. silently never started (they were built + in the
  cache, just never copied out). The repo-root `install.sh` had the full
  curated `LAUNCHERS` list; the ISO installer did not. Fixed by mirroring it
  (82/82) + globbing all 71 eww helper scripts.
  - Restored 5 daemons deleted by `cf8b612f` (accidental working-tree sync):
    `nyxus_{missiond,hotkeyd,qsd,snapd,dockd}.py` → back in `nyxus-scripts/`
    (bake globs them into `/opt/nyxus/`). Their `.service` units + hypr starts
    + eww windows all still referenced them → they failed every boot. Restores
    Mission Control (Super+F3), hotkey cheatsheet, snap, quick-settings daemon.
  - Screensaver retimed to **5 min** (was 3); dpms 10 min, suspend 15 min.
  - Saucer bottom-bar clock centering (margin 16→4px; art was swapped 07-22).
  - Notification UFO popup: `dunstrc` script/icon paths `/home/cosmic`→`$HOME`.
  - **Builder-home de-leak:** `/home/cosmic` was baked into wallpaper.json,
    qt5ct/qt6ct, hyprland `env = PATH`, hub wrappers — broke for user `nyx`.
    Source defaults → `/home/nyx`; `nyxus_install.sh` now runs a de-leak pass
    rewriting `/home/cosmic|/home/nyx` → real `$HOME` on first boot (works for
    any install user). Deferred: `etc/jett/allowlist.conf`, `etc/audit/rules.d`
    (builder project paths), bundled arsenal-tool `.env.example`/logs.
  - **NOTE:** none of round-2 is in the ISO baked ~1:40am 07-23 (it started
    before these fixes) — needs one more bake.

- **2026-07-23 (evening) — ALIEN NEON palette lock + install code-1 + alien walls**
  (this commit). Cream purged. `follow_wallpaper` OFF. Live session reskinned.
  See **§5b BRIEF** for the full palette table + what still needs a rebake.

- **2026-07-23 (walls purge):** Non-alien wallpapers deleted from ISO airootfs (demon/hacker-mode/kageryu/void-vortex/sierengowski/prism/eye-mosaic/etc.). `stations.json` restored (was wrongly identical to hacker). Stations + workspaces + rotation lists = alien-only. Palette remains prism-only / follow_wallpaper off. Also purged cinematic darkmirror/cosmos/nebula/blackhole/void SDDM packs; dynamic wallpaper set = `alien` only; SDDM greeter = urban-alien heroes. Restored demon + hacker-mode walls (alien art); kageryu dragon stays out.

- **2026-07-24 — GREEN-LIGHT PASS: `main` was RED; fixed the CI gates the
  alien/palette/kernel work had broken (branch `cursor/green-light-ci-wallpaper-kernel-ad9a`).**
  `typecheck`/`validate` were green, but the `ci` aggregate **and** `build-iso`
  were failing on every push. Root causes + fixes (all pushed):
  1. **`verify-profile.sh` (the `ci` gate) had 3 stale/broken checks** — direct
     fallout of the alien-wall purge + the global palette find/replace:
     - *SDDM wallpaper mirror* check demanded the greeter mirror the FULL 58-pack
       (`SDDM_PNG >= WP_PNG`), contradicting the intended **curated alien-hero**
       greeter (7 heroes). Relaxed to: non-empty mirror that **includes the
       default hero** (`${WP_SLUG}.png`).
     - *default `WALLPAPER_PATH`* check only translated `/home/<user>/…` →
       `/etc/skel/…`; it couldn't resolve the **system-wide**
       `/usr/share/backgrounds/nyxus/<slug>.png` path the ALIEN NEON lock
       intentionally adopted (user-agnostic, immune to the de-leak pass). Now
       resolves both forms.
     - *`FORBIDDEN_PATTERN` (13v ALIEN NEON compliance)* — the palette find/replace
       had rewritten the OLD violet/cyan hexes (`C084FC/7C3AED/a06bff/3ad8ff`) to
       the **canonical** `#7d3dff`/`#2bd2ff` *inside the forbidden list*, so the
       check was banning the very ALIEN NEON palette it must enforce. Restored the
       old-palette hexes; canonical colors are explicitly allowed. **⚠ Do not
       re-run a blind global hex sed over `verify-profile.sh` — it will re-corrupt
       this list.**
     `bash iso-builder/verify-profile.sh` now exits 0.
  2. **`build-iso` workflow was perpetually red** — Kage-Ryu is the default kernel
     and `build-iso.sh` hard-fails when its prebuilt pkgs are absent, which they
     always are on a GitHub runner. Made `build-iso.yml` **workflow_dispatch-only**
     + bake with `NYX_WITH_KAGE_RYU=0` (stock-kernel **validation** ISO); Release
     gated behind `create_release` (default off) + clearly labelled stock-only. The
     authoritative Kage-Ryu ISO is still baked locally by the owner (§6).
  3. **ISO filename `nyx-…` → `nyxus-…`** in `build-iso.yml` (checksum/release names
     were mismatched vs `build-iso.sh`'s real `nyxus-<date>-x86_64.iso`) and in
     `iso-builder/README.md` + `docs/REINSTALL_GUIDE.md`. (The `nyx` user account
     and internal `nyx-profile` dir are intentional — left as-is.)
  Palette lock still holds: cream `#f4ead5` appears only here in HANDOFF (docs), 0
  live occurrences. **Not verified here:** live desktop UI / "dead buttons" and the
  ISO bake itself — both require an Arch live-boot / graphical session, out of
  scope for this headless env (per AGENTS.md). (This also closes the
  build-iso owner's flagged TODO below: `nyx-*.iso` → `nyxus-*.iso` is now done
  in `build-iso.yml`.)

- **2026-07-24 — URBAN-ALIEN on every idle/login surface + reworked hypridle**
  (same branch). Owner: "login screen + lock + screensaver must be urban-alien;
  hypridle layout was wrong." Audited every surface; they now ALL resolve to the
  urban-alien hero:
  - **Screensaver** — `nyxus-screensaver` launcher was running
    `nyxus_matrix_saver.py` (matrix-rain — the old effect the owner didn't want).
    The correct urban-alien saver (`nyxus_screensaver.py`, alien wallpaper hero +
    clock + NYXUS mark) already existed but was disconnected. Repointed the
    launcher to it + pinned `NYXUS_SCREENSAVER_WALL=nyxus-urban-alien`.
  - **hypridle** — new layout: 45s idle-glass · 300s (5m) dim + urban-alien
    screensaver · **600s (10m) LOCK the session** (hyprlock, urban-alien) + panel
    off so you log back in · 900s (15m) suspend. Dropped the redundant 330s
    reinforce listener + the wall-staging in `lock_cmd`.
  - **hyprlock** (lock / re-login) — background pinned to
    `/usr/share/backgrounds/nyxus/nyxus-urban-alien.png` (was a random rotating
    `~/.cache/nyxus/lock-wall.png`).
  - **Greeter** (`nyxus-greeter`, greetd→regreet) — login background pinned to
    urban-alien (was random from `wall-rotation.list`). Fixed the shipped copy +
    the `greetd/` bake source (build-iso installs from `greetd/nyxus-greeter`).
  - **Already urban-alien / verified consistent:** desktop `wallpaper.conf` +
    `wallpaper.json` (tint `#7d3dff`); SDDM installed-greeter bg (build-iso
    overrides `background.png` → urban-alien); and all **flyouts / menus /
    settings** backdrops, which `nyxus-gen-backdrop` bakes from the *current*
    wallpaper (urban-alien) behind their glass — so they inherit it automatically.
  - Dropped the now-dead `exec-once = nyxus-rotate-walls lock` seed. The DESKTOP
    still rotates every 20 min but only through the **alien-only** set, so it
    stays on-theme (owner didn't ask to pin the desktop; say so if you want it
    fixed to urban-alien too).
  - **⚠ Stale bits flagged (not deleted — unused, low-risk):**
    `artifacts/api-server/nyxus-scripts/nyxus-greeter` (root copy, rev 2026-07-09)
    is an OLDER greeter variant with NO login-bg wiring; neither `build-iso.sh`
    nor `nyxus_install.sh` reference it (they use `greetd/nyxus-greeter`).
    `nyxus_matrix_saver.py` is now unwired (kept as an alternate saver).
  - **Not verified here:** on-stick idle→saver→lock→login flow — needs an Arch
    live-boot (out of scope headless). Config validated: verify-profile exit 0,
    `bash -n` + `py_compile` clean.

- **2026-07-24 — "flying saucer / UFO" audit (why the owner didn't see them).**
  There are THREE distinct saucer/UFO things — don't confuse them:
  1. **Flying saucer through the background (semi-transparent)** = the LIVING
     WALLPAPER cruising UFO. `nyxus-live-wallpaper` plays an mpvpaper loop on the
     Wayland *background* layer (behind bars + windows); the loop is rendered
     on-device by `nyxus-livewall-flagship` (ffmpeg — the UFO is matted theme art
     with a violet halo, cruises once per loop). **Present + WIRED + ON by
     default** (`livewall.conf` = `LIVE=on`; hyprland exec-once `nyxus-live-wallpaper
     auto`; renders on first boot if the mp4 is absent). If the owner didn't see it:
     the flashed stick predates this wiring (needs the pending rebake) OR mpvpaper
     (AUR, built in customize_airootfs.sh) didn't build OR the awww ws-daemon won
     the login race (the script has a spawn_guard for that). **Not a repo gap.**
  2. **UFO notification** = present + WIRED. `dunstrc` sets `default_icon =
     nyxus-notif-ufo` and forwards every notification to the themed EWW UFO console
     popup (`notif-popup`/`notifications` windows). Icon ships at
     `eww/assets/nyxus-notif-ufo.png`. **Not a repo gap.**
  3. **Desktop companion** (`nyxus-companion`, alien-on-saucer bottom-bar mascot)
     = **DISABLED** (hyprland.conf exec-once commented out, "until the full-body
     game-character redo lands — bust-on-saucer was wrong") AND its app files
     (`companion/companion.py` + `assets/`) are **NOT staged** into the ISO
     airootfs or the offline cache (only the `nyxus-companion` launcher is). So it
     can't run as-is. Left as the owner previously chose; re-enable+stage only on
     request. (Different thing from #1 — this is a mascot on the bar, not the
     background flyby.)

- **2026-07-24 (consistency audit):** Repo-wide sweep to guarantee ONE current build with no stale/prior-build leftovers:
  - **Second wall staging tree** `artifacts/api-server/nyxus-scripts/` still shipped all the old walls (darkmirror/cosmos/prism/void/sierengowski/ink-swirl…) **and was missing the alien heroes** — purged the stale set, added `urban-alien`/`login-wall`/`desktop-hero`/`graffiti-space`/`hacker-mode-a·b`/`demon` so the offline-cache/API bootstrap path matches the ISO. Removed dead `nyxus-set-frost-wallpaper.sh` + stale `download.ts` allowlist entries; added the hero walls to the allowlist so `_soft_wall` fetches resolve.
  - **Palette script drift:** `nyxus_palette.py` / `nyxus_matrix_saver.py` skel copies had drifted back to an old secondary `#ff2d55` — re-synced to locked `#ff2dad`.
  - **GRUB dragon theme → ALIEN NEON:** both the live-USB theme (`nyx-profile/grub/themes/nyxus`) and the installed-disk theme (`airootfs/usr/share/grub/themes/nyxus`) now use the black-dragon background + ALIEN NEON palette (void `#05060a`, text `#eef2fa`, violet/magenta) and the "NYXUS · ALIEN NEON · KAGE RYU" title. Dropped the old "Cosmic Ink Swirl / SIERENGOWSKI / WELCOME TO THE DARKSIDE" branding and the off-brand gold `wordmark.png`. Live theme keeps the DejaVu fonts that `grub.cfg` actually loads (don't switch it to Unifont — the bootloader doesn't load that face).
  - **NYX → NYXUS:** on-screen hint toasts (`NYX · SUPER+SPACE`, `NYX · GRIM+SLURP`) and the LICENSE/README "naming contract" collapsed — NYXUS is the OS **and** the ISO; there is no separate "NYX" product name. (License serial `NYX-J5W-…` left intact; intentional glitch-flicker letters in `nyxus_preboot.py` left intact.)
  - **Config trees verified in sync** across `skel/.config/nyxus`, `skel/.nyxus`, `opt/nyxus`, `artifacts/api-server/nyxus-scripts`. Note: `nyxus-build-iso.yml` still names the release artifact `nyx-*.iso` (CI lane — flagged for the build-iso owner to rename `nyx-` → `nyxus-`). **[DONE 2026-07-24 in the green-light pass above — renamed to `nyxus-*.iso`.]**

### The `nyxus-2026.07.22` stick booted BROKEN — and why (post-mortem)
Two overlapping causes: (1) that stick was baked from a **partial/stale** profile
(missed the ungate-bars fix), and (2) the deeper bugs above (dead Replit + install
`set -e`/`clear` + eww.scss + wallpaper path). All are now fixed in the repo but
**not yet in a baked ISO** — needs a fresh bake. `nyx@nyxus` + auto-login are
correct/expected (it's a live ISO, not an install).

### ⛔ BLOCKER (QEMU-confirmed 2026-07-23): Kage-Ryu cannot boot the live ISO
Default menu entry **"Boot NYXUS · Kage Ryu kernel"** dies in initramfs:
`mount: unknown filesystem type 'iso9660'`. Root cause: `config.last` has
`# CONFIG_ISO9660_FS is not set`, `# CONFIG_SQUASHFS is not set`,
`# CONFIG_BLK_DEV_LOOP is not set` (XanMod lean/localmodconfig stripped them;
archiso needs all three). Stock **rescue** entry still works.

**If you boot the already-flashed `nyxus-2026.07.23` stick:** at GRUB pick
**"Boot NYXUS · stock linux (rescue)"** — do NOT use the highlighted Kage entry
until a rebuilt kernel is rebaked.

**Fix path (owner):**
1. Rebuild kage pkgs (PKGBUILD now forces iso9660/squashfs/loop/dm — patched
   2026-07-23 in `~/Projects/arch-custom-kernel/linux-kage-ryu/PKGBUILD`):
   `cd ~/Projects/arch-custom-kernel/linux-kage-ryu && makepkg -sc`
2. Confirm: `zgrep -E 'CONFIG_(ISO9660_FS|SQUASHFS|BLK_DEV_LOOP)=' \
   /usr/lib/modules/*kage*/config` → all `=y` (or modules present in initramfs).
3. Then RE-BAKE + re-flash (below).

- **2026-07-24 — Live-boot issue fixes (PR #71 → stranded, then landed on main via #72):**
  ⚠️ **Near-miss:** PR #71 merged into `cursor/green-light-ci-wallpaper-kernel-ad9a`
  **after** that branch was already merged to `main` via PR #70. So #71 was **not**
  on `main` until PR #72 (`603139d7`, 2026-07-24) merged the branch again.
  **`main` HEAD must include `0f866221` before any bake.** Verify:
  `git merge-base --is-ancestor 0f866221 origin/main`.
  The flashed `nyxus-2026.07.24` ISO was baked from `139bdc85` — **before** #70/#71/#72
  — which is why the owner saw no eww/black-box/stamp improvement on that stick.

  Root-cause analysis + fixes for five owner-reported live-boot regressions that were NOT yet
  in the repo (distinct from stale-bake issues). All changes are in `skel` and `artifacts/`
  in lockstep per the HANDOFF sync rule.

  1. **eww slow first paint (~5 min) — FIXED.** Root cause: `compile-eww-css.sh` called
     `npx --yes sass` which tried to download the sass NPM package at every login (node/npm
     are NOT in the ISO packages). This blocked bar launch for minutes. Fix: skip the SCSS
     compile entirely when no local `sass` binary is installed (use the pre-committed
     `eww.css` which is correct and complete). Compilation now only runs if `sass` is
     already on `$PATH` — no NPX, no network call, no download.
  2. **eww black/semi-transparent box around bars — addressed.** The root cause was that
     `compile-eww-css.sh` was sometimes called and produced a corrupt/stripped `eww.css`
     (the sed property-strip pass removed `background-size` etc. from bar widgets). With the
     compile skip, the pre-committed `eww.css` is always used; it already has the correct
     `window { background: none; background-color: transparent; }` rule that kills the GTK
     window-paint "ghost box". Also confirmed: the Hyprland layerrule `ignore_alpha 0.2` and
     eww namespace `nyxus-bar-*` are correct.
  3. **eww "globbing errors" at lines 601/606 — addressed.** Added `shopt -s nullglob` /
     `shopt -u nullglob` guards around all glob-based for loops in `sys-graph.sh` that
     iterate `/sys/class/thermal/thermal_zone*/temp` and `/sys/bus/pci/devices/*/`. Without
     `nullglob`, unmatched globs expand to the literal pattern string and subsequent
     path/existence checks produce spurious error-like output. Fan/GPU data degrades
     gracefully to 0 when /sys paths are absent.
  4. **hyprpm "couldn't load header" at startup — FIXED.** Added a Hyprland header
     directory existence check (`/usr/include/hyprland`) at the top of
     `ensure_hyprland_plugins()`. The live ISO does not ship the `hyprland-devel` header
     package, so hyprpm can't compile plugins and prints "couldn't load header" to the
     Hyprland log on every login. With the new guard the entire plugin sync is silently
     skipped when headers are absent — no error spam, no login delay, no fingerprint prompt.
  5. **Stale terminal text colors and old header message — FIXED.**
     - `/etc/issue`: was `\e[1;37m` (classic white); now uses ALIEN NEON RGB escapes —
       violet `#7d3dff` for the NYXUS ASCII art, cool white `#eef2fa` for the tagline,
       magenta `#ff2dad` for the hostname.
     - `~/.bashrc` greeting: now shows the build stamp (ISO name / built time / commit SHA)
       in ALIEN NEON colors after the greeting so freshness is instantly visible in any
       terminal.
     - `/etc/profile.d/00-nyxus.sh`: `NYXUS_VERSION` updated from `2026.05.13` to
       `2026.07.24`; exports `NYXUS_BUILD_STAMP` from `/etc/nyxus-build` (written by
       `build-iso.sh`).
  6. **Build/commit stamp (HANDOFF PENDING item) — IMPLEMENTED.** `build-iso.sh` already
     bakes `/etc/nyxus-build` + `profile.d/nyxus-build-stamp.sh`. Updated the stamp
     display to use ALIEN NEON palette (violet header line, cool-white content). Also
     updated the `.bashrc` greeting to inline the key stamp lines so the owner sees the
     exact commit/date on every terminal open — zero ambiguity about which bake they're
     on.
  7. **Consistency audit:**
     - `/etc/jett/allowlist.conf`: replaced all `/home/cosmic` paths with `/home/nyx`
       (the live-ISO and installed-system user). Also removed `trusted_proc:cosmic-comp`
       (a GNOME Cosmic compositor — not NYXUS).
     - `/etc/jett/model.sha256`: comment updated from `/home/cosmic/...` to `/home/nyx/...`.
     - `BOOTSTRAP_VERSION` bumped: `2026.07.23-r12-offline` → `2026.07.24-r13-fixes`.
       Existing installs will detect the version mismatch on next login and self-heal
       (re-run the installer to pick up the new configs/scripts).
     - Remaining non-boot Replit refs (~33) are still deferred — they're in self-update
       snippets, README curl examples, and polkit `vendor_url`; none affect the boot path.


1. **Confirm `main` has #71** (`0f866221` / merge `603139d7`) — **DONE 2026-07-24 via PR #72**.
2. **Rebuild Kage-Ryu** with live-ISO FS support (see blocker above), then
   **RE-BAKE** from this `main` (owner runs, clean+committed repo):
   `cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh`
   (Kage-Ryu is baked by default now; it hard-fails if the prebuilt kernel pkgs
   are missing. Add `NYX_WITH_KAGE_RYU=0` only for a stock-only debug ISO.)
   **Do not flash the existing `nyxus-2026.07.24` again expecting #71 fixes — rebake.**
   Owner started `makepkg -scf` for kage pkgs **2026-07-24 ~04:57** (in progress).
3. **Re-flash** — **always re-check `lsblk`** (64GB SanDisk was `/dev/sdb` on
   2026-07-24; letters move). Boot **UEFI**; until Kage pkgs are rebuilt pick
   **stock rescue**. After Kage rebuild: verify Kage entry mounts ISO (no iso9660
   error) → splash → desktop → `uname -r` shows kage-ryu.
4. ~~**Before next bake — still fix bake wipe of arsenal shard**~~ **DONE 2026-07-24**
   (`nyxus-arsenal-apps.conf` + `nyxus-reactive.conf` in bake shard loop; `source=` in
   NS + skel `hyprland.conf`). Still verify post-bake:
   `unsquashfs -l airootfs.sfs | rg 'arsenal-apps|reactive'`.
5. ~~**W1 file_permissions**~~ **DONE 2026-07-24** — regen 177 entries in `profiledef.sh`.
6. **Still open after 2026-07-24 fix pass:**
   - Greeter / hyprlock visual QA on stick (alien bg wired; needs a real boot to verify).
   - UFO/saucer notification QA on fresh boot.
   - ~~eww bars: slow first paint + transparent black box~~ **FIXED in repo (PR #71 → main via #72)** — needs rebake to appear on stick
   - ~~Visible build/commit stamp~~ **IMPLEMENTED** — needs rebake
   - Remaining W2 verify-profile asserts (label consistency / kernel-policy / cache payload) — deferred hygiene
   - **Home backup:** Ventoy stick (re-verify device letter) mid-queue — Vault /
     Projects / VMs as `.tar.zst`; fill remaining space then swap to 2nd USB.
     Also back up Docker honeypot volumes + `/opt/nyxus-*` + `/etc/jett`
     (NOT only `~`).
7. Cleanup status (2026-07-23): accent-baseline builder-home leak **removed**
   (regenerated per-user by nyxus-apply-accent). STILL deferred: ~33 non-boot
   Replit refs (self-update snippets, README curl example, polkit vendor_url —
   all non-fatal now that the boot+install path is Replit-free); ~50 GB of old
   ISOs in `iso-builder/out/` (untracked, safe to delete); 90 stale remote
   branches on GitHub (copilot/*, devin/*, cursor/*, archive/vault-*) — prune to
   avoid re-scattering. Prune non-alien walls from the payload if size matters.
8. Owner's call: fold `companion-3d` under one roof or keep separate.

### Copilot Deep Pre-Bake Audit (2026-07-24) — stored here (no separate memory store)

**ALIEN NEON + Settings completeness checklist (owner tracking):**
[`docs/ALIEN_NEON_SETTINGS_AUDIT.md`](./docs/ALIEN_NEON_SETTINGS_AUDIT.md)
— full counts + lists for (1) surfaces not ALIEN NEON, (2) empty/minimal/partial
Settings pages, (3) apps with no Settings section, (4) session features missing
from Settings. Regenerated 2026-07-24 from live `~/.nyxus` + desktop entries.

Full GO/NO-GO from Copilot audit. Cross-checked against `main` @ `fb63e2aa` (+ #71 on main).

| Gate | State |
|---|---|
| **C1** Rebuild Kage-Ryu (`ISO9660_FS` + `SQUASHFS` + `BLK_DEV_LOOP` =y); QEMU verify | ⛔ **BLOCKER** — owner `makepkg` **in progress** |
| Bake from clean committed idle `main` (has #71 via #72) | ✅ ready once C1 done |
| Boot labels / offline-cache / kernel hard-fail guards | ✅ intact |
| Palette lock (ALIEN NEON; cream / `#a06bff` clean in desktop trees) | ✅ clean |
| Desktop delivery (skel + bootstrap + `/opt/nyxus-cache`) | ✅ intact |
| **W1** Regenerate `profiledef.sh` `file_permissions` (~59 `/usr/local/bin` missing) | ✅ **DONE 2026-07-24** (177 entries regen from airootfs) |
| **W2** `verify-profile.sh`: label consistency + ban `#f4ead5` + kernel-policy + cache/daemon asserts | ⚠️ cream ban **DONE**; other W2 asserts still deferred |
| **W3** Dead Replit host fallbacks in chrome/stickies/sysmon/… | ℹ️ deferred (~33 non-boot) |
| **W4** `/home/cosmic` in jeTT/audit/arsenal `.env.example` | ℹ️ jeTT + audit **clean on current main** (#71); arsenal `.env.example` still deferred |
| **W5** `dunstrc` hard-codes `/home/nyx` icon_path | ℹ️ OK on live ISO; de-leak on install |
| **W6 (this session — Copilot missed)** bake wipes `nyxus-arsenal-apps.conf` from skel; never `source=`d | ✅ **DONE 2026-07-24** — bake shard list + `source=` in hyprland (NS+skel); also ships `nyxus-reactive.conf` |
| I1–I5 | ℹ️ cleanup / cosmetic (orphan greeter, dup python tree, Forge `#0a0a14`, stale BUILD_ID stubs restamped at bake) |

**Verdict (aligned):** GO for bake once **C1** finishes and pkgs verify. Worth landing **W1 + W6** on `main` before kickoff; W2 nice-to-have. Audit note: bootstrap is **`2026.07.24-r13-fixes`** on main (audit text said r12 — stale).

**After bake verify:** `cat /etc/nyxus-build` → commit ≥ `0f866221`; `lsblk` label `NYXUS_2026_07`; UEFI Kage mounts ISO; `uname -r` = kage-ryu; desktop offline; bars without black box / minutes-long delay.

---

## 5b. BRIEF — ALIEN NEON LOCK (2026-07-23 evening)

**What shipped to `main` this round:**
1. **Canonical palette** — `accent.json` active=`prism`, `follow_wallpaper=false`.
   Primary violet `#7d3dff`, secondary magenta `#ff2dad`, warn orange `#ff8a1e`,
   ok neon green `#39ff14`. Fixed neons for cyan/red/yellow/orchid used in
   terminals, borders, HUD, glow.
2. **Repo-wide re-skin** — purged cream `#f4ead5` + wallpaper-drift blues
   (`#1caef2`/`#6526ff`/…) from skel, artifacts, arsenal UI, GRUB/calamares/
   verify-profile. Window border sweep = violet→magenta→cyan→green.
3. **Terminals** — kitty + alacritty = ALIEN NEON ANSI (cool white default text;
   neon only on real ANSI). Alacritty dim colors use `0xAARRGGBB` (not `#rrggbbaa`).
   `nyxus-glow` palette updated to the same neons.
4. **Alien walls only** — default `wallpaper.conf` → `nyxus-urban-alien`;
   greeter `wall-rotation.list` alien-only; `nyxus-rotate-walls` searches
   `rotation/` + alien FALLBACK; autostart DEFAULT points at urban-alien.
5. **Install code-1 hardened** — optional wall dl soft-fails; SDDM never fails
   the install (greetd is live greeter); post-install wallpaper prefers
   urban-alien (not void-vortex); **summary no longer `exit 1`** on optional
   misses (that abort was killing first-boot theming).
6. **Live session** — palette applied on the owner's Hyprland session
   (`nyxus-apply-accent prism`); backup at
   `~/nyxus-palette-live-backup-*.tar.gz`.

**What does NOT update until the next bake:** greeter/splash/ISO skel on the
USB stick. Live session already shows ALIEN NEON; stick needs rebake+reflash.

**2026-07-23 (same evening, purge pass):** Old accent presets (aurora/ember/verdant/
violet/rose/ice/noir/wallpaper) **deleted** from `accent.json` — only `prism`/
ALIEN NEON remains selectable. Every leftover old-family hex (`#a06bff`,
`#ff7849`, `#ff4d6b`, cream-era void `#0a0a14`/`#050308`, …) remapped. All
"Sprint E" / "cream accent" labels renamed to ALIEN NEON. Live session
re-synced. Cursor theme name `NYXUS-Aurora` is unrelated (kept).

**Owner next:** rebuild Kage-Ryu pkgs (iso9660/squashfs/loop) → commit clean →
`sudo ./build-iso.sh` → flash → boot UEFI → verify.

---

## 6. THE BAKE → FLASH → BOOT PROCEDURE (canonical)

```bash
# 1. BAKE (owner, root). Kage-Ryu is baked BY DEFAULT. From a clean repo.
cd ~/Nyxus-Core/iso-builder
sudo ./build-iso.sh                    # Kage-Ryu primary + stock rescue
# sudo NYX_WITH_KAGE_RYU=0 ./build-iso.sh   # stock-only debug ISO (opt out)
#   → iso-builder/out/nyxus-<date>-x86_64.iso  (NO post-bake cleanup needed anymore)

# 2. FLASH (owner, root). USB = /dev/sda (SanDisk 57 GB). Internal = /dev/nvme0n1
#    — NEVER put nvme as of=. Double-check the target before Enter.
sudo dd if=~/Nyxus-Core/iso-builder/out/nyxus-<date>-x86_64.iso \
        of=/dev/sda bs=4M status=progress oflag=sync

# 3. BOOT: reboot → boot menu (MSI: F11) → pick the "UEFI: SanDisk" entry
#    (UEFI is required for the dragon menu). Login nyx / nyx.
```

Verify a flashed stick from the agent side (no sudo needed):
`lsblk -o NAME,SIZE,FSTYPE,LABEL /dev/sda` → expect `iso9660` + label `NYXUS_2026_07`
+ an `ARCHISO_EFI` vfat partition. Inspect ISO contents with `bsdtar -tf <iso>`.

---

## 7. DO-NOT-REPEAT GOTCHAS (hard-won)

- **Kage-Ryu MUST keep live-media FS support** (`CONFIG_ISO9660_FS`,
  `CONFIG_SQUASHFS`, `CONFIG_BLK_DEV_LOOP`, preferably `CONFIG_BLK_DEV_DM` /
  `CONFIG_UDF_FS`). A lean/localmodconfig pass that drops them makes the
  default live entry unbootable (`unknown filesystem type 'iso9660'`). Catch
  this in QEMU (`-kernel` + virtio ISO + `console=ttyS0`) before flashing.
- **The desktop must NOT depend on the network to come up.** Bars/wallpaper/theme
  are in skel and launch immediately; the app-install layers on after and may never
  block/break the core desktop. (Regressing this = the broken 07-22 boot.)
- **Full-screen GTK/eww overlays MUST be bottom-layer + empty input region
  re-applied per-frame**, or they TRAP the desktop (the "whispers" incident forced
  multiple hard resets). Never OVERLAY-layer a full-screen input surface.
- **iso_label identical** in profiledef + all 5 archisolabel refs, or no boot.
- **Dragon menu is UEFI-only** — Legacy boot = plain text menu (not a bug).
- **Accent does NOT follow wallpaper** (locked 2026-07-23). Active preset =
  `prism` / ALIEN NEON. `follow_wallpaper: false`. Cream `#f4ead5` is banned.
- **eww**: one daemon via `nyxus-eww-launch-safe`; watch for double bars.
- **Restore-before-bake is obsolete** now that the bake uses a throwaway copy — but
  if you ever see the repo `nyx-profile` go root-owned/dirty after a bake, the fix
  regressed; the owner must `sudo chown -R cosmic:cosmic` it, then
  `git checkout -- iso-builder/nyx-profile/ && git clean -fdx -- iso-builder/nyx-profile/`.
- **Alacritty rejects 8-digit `#rrggbbaa` hex** — use `0xAARRGGBB` (e.g.
  `0x8CEEF2FA`) or 6-digit `#rrggbb`. Hitting `#eef2fa8c` pops a red parse error.

---

## 8. KEY PATHS

- ISO builder: `iso-builder/build-iso.sh`, profile `iso-builder/nyx-profile/`
- Baked desktop: `iso-builder/nyx-profile/airootfs/etc/skel/.config/{hypr,eww,nyxus}`
- Plymouth theme: `iso-builder/nyx-profile/airootfs/usr/share/plymouth/themes/nyxus/`
- GRUB dragon (live USB boot): `iso-builder/nyx-profile/grub/{grub.cfg,fonts/,themes/nyxus/}` — ALIEN NEON theme, black-dragon bg, DejaVu fonts (the set `grub.cfg` loads). Installed-disk GRUB theme mirror: `iso-builder/nyx-profile/airootfs/usr/share/grub/themes/nyxus/` (same dragon bg; Unifont, which installed GRUB ships).
- Apps / offline payload SOURCE: `artifacts/api-server/nyxus-scripts/`
  (`nyxus_install.sh`, `nyxus-bootstrap`, `nyxus-wait-bootstrap`, `eww/`,
  `plymouth/`, `hypr-walls/`, `livewall/`)
- Kernel recipe: `kernel/` (README + `install-kage-ryu.sh` + `nyxus-bbr.conf`)
- Other docs: `docs/` (KERNEL_ISO, REBOOT_SURVIVAL, INSTALL, THEME, KEYBINDS, …),
  root `STATUS.md`, `ROADMAP.md`, `SHIPPING.md`.

---

*Keep this file honest and current. The next agent — and the owner's sanity —
depends on it.*

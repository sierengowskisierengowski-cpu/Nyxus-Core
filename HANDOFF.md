# NYXUS — AGENT HANDOFF & BUILD STATE (read this FIRST)



> **★★★★ WHERE WE STAND — 2026-07-31 ~16:50 EDT · BAKE READY ★★★★**  
> **Status: BAKE READY.** Repo is clean idle `main`, profile verified, disk
> and Kage-Ryu pkgs confirmed. Owner runs the bake (agent cannot sudo).
>
> | | |
> |---|---|
> | **HEAD** | `36f7dd41` (`docs(handoff): mark main BAKE READY for 2026-07-31 ISO`) — bake from this tip |
> | **Sync** | `main` == `origin/main` (0 ahead / 0 behind) after the push below |
> | **Tree** | Clean (only untracked `.claude/` — do not commit) |
> | **verify-profile.sh** | **PASS** (exit 0). WARNs only: customize not +x (mkarchiso chmods); Hyprland host 0.55.4 vs ISO 0.56.0 skew; optional station apps (`cursor`/`strawberry`/`audacious`/`thunar`) absent; some eww namespaces on catch-all layer-blur floor |
> | **Disk** | `/` has **~203G free** (well above the ~40G bake headroom). `iso-builder/out/` holds ~30G of older ISOs (07.26–07.29) — optional cleanup, not blocking |
> | **Kage-Ryu** | Findable at `~/Projects/arch-custom-kernel/linux-kage-ryu/` — `linux-kage-ryu-7.0.12-1` + headers (2026-07-24). Bake defaults `NYX_WITH_KAGE_RYU=1`. Opt out: `NYX_WITH_KAGE_RYU=0` |
> | **PR #83** | Squash-merged as `6e378926`. Feat-branch tip content matches `main` (docs-only delta). **No open PRs.** |
> | **Left behind (do not merge)** | `local-stash-work` (junk). Stale locals: `cursor/*`, `feat/kage-ryu-autoactivate-wiring`, `fix/overlay-gap-and-login-pickup`, `feat/settings-increment-2-no-terminal` (already squash-landed), `merge-pr-76` — all superseded or already on `main` |
>
> **Sync live session ≠ ISO boot.** Copying repo configs into `~/.config` only
> updates the Hyprland session he is *already in*. It does **not** exercise
> greetd/regreet, firstboot timing, squashfs, skel→home bootstrap, or the
> dragon UEFI menu. To see **everything** shipped: bake → flash → UEFI boot.
>
> ### Exact bake + flash (owner, root)
> ```bash
> cd ~/Nyxus-Core/iso-builder
> sudo ./build-iso.sh
> # → iso-builder/out/nyxus-2026.07.31-x86_64.iso  (date follows bake day)
>
> # Confirm USB letter EVERY time (letter moves). NEVER of=/dev/nvme*
> lsblk -o NAME,SIZE,TYPE,TRAN,MODEL,LABEL
> sudo dd if=~/Nyxus-Core/iso-builder/out/nyxus-2026.07.31-x86_64.iso \
>         of=/dev/sdX bs=4M status=progress oflag=sync
> ```
> Boot: MSI F11 → **UEFI: SanDisk** (or whatever the stick is) → dragon menu →
> Kage-Ryu entry #0 (stock `linux` = rescue). Login `nyx` / `nyx`.
>
> ### Verify on the stick after boot
> 1. **Login** — greetd greeter appears (not blank cursor). Fall-through /
>    tuigreet path if regreet fails. Contract file path exists for Settings.
> 2. **Hub / Power gap** — open Hub and NYXUS Power; no 40px top strip. Bars
>    hide/restore cleanly on `"fg"` overlays; screensaver/deepcore stay edge-to-edge.
> 3. **Settings** — Login Screen drives greetd contract (not dead SDDM path);
>    theming/glass; most former terminal escapes are native windows (~5 left).
> 4. **urban-alien** — greeter / hyprlock / screensaver / wlogout hero art.
> 5. **Stations** — HOME/START/GHOST/FORGE/LAB/ARSENAL (+ WAVE/CORE etc.);
>    launches work (guarded optional apps may no-op).
> 6. **Build stamp** — `/etc/nyxus-build` matches this bake's source commit.
> 7. **Kernel** — `uname -r` shows kage-ryu; GRUB entry #0 is Kage-Ryu.
> 8. **Bars / wallpaper / reactive** — bars up, urban-alien wall, sense/mood live.
>
> ### Known unfinished (will still show on the stick — not bake blockers)
> - Login card eye candy (time/weather polish) still incomplete vs owner wish.
> - Settings not "Windows/Apple complete"; a few terminal escapes remain.
> - Hub background redesign (owner request) not done as a separate pass.
> - Live host still on Hyprland 0.55.4; ISO ships 0.56.0 — first stick boot is
>   the real 0.56 verification.
> - Live-box blank login (SDDM bak on *installed* system) is a host repair, not
>   an ISO defect — fresh stick uses greetd. Optional:
>   `sudo bash scripts/nyxus-fix-login.sh` + reboot on the installed box.
> - Do **not** sync live session unless the owner explicitly asks; he chose ISO.

> **★★ PR #83 LANDED ON MAIN — 2026-07-31 ~16:45 EDT ★★**  
> Squash-merged https://github.com/sierengowskisierengowski-cpu/Nyxus-Core/pull/83  
> as `6e378926` (`Settings: greetd login contract, full theming, no-terminal
> (113→~5), + greetd switch (#83)`). CI was green; merge method matched #82
> (squash). Local `main` == `origin/main`. Still NOT merged: `local-stash-work`.

> **★★ BRANCH AUDIT — 2026-07-31 ~08:40 EDT (second pass) ★★**  
> Re-fetched `origin`, rechecked every local/remote tip and open PRs.  
> **Nothing new to merge.** `main` == `origin/main` at `bfb01abc` (0/0).  
> **Open:** draft PR **#83** (`feat/settings-increment-2-no-terminal`) — greetd
> login contract + no-terminal conversion; CI green; **left as draft** (greeter
> does not consume the contract yet). Branch already on origin.  
> **Accidentally duplicated (same patch-id) on** `origin/fix/overlay-gap-and-login-pickup`
> — ignore; real tip for that work is the feat branch / PR #83. Overlay pickup
> itself already merged via PR #82.  
> **Still NOT merged:** `local-stash-work`; no `babysit/land-open-prs`.  
> Archives / hyprland-055 / deep-internal / cloud-agent locals — superseded or
> already squash-landed. No stashes. Untracked `.claude/` only (ignored for commit).

> **★★ BRANCH AUDIT — 2026-07-31 ~06:30 EDT ★★**  
> Swept local + `origin` branches so nothing valuable sits only off `main`.  
> **Merged (FF) into `main`:** `fix/overlay-gap-and-login-pickup` → tip `7f54cd3a`
> (SDDM quarantine into the real `nyxus-fix-login.sh`, measured top-gap fix +
> `nyxus-overlay-open`, lock/saver security + walls staging, Hub hero scrim).  
> **Pushed:** local `main` was *behind* `origin/main` by 2 (`58cfc11a`,
> `096eeef5`) — fast-forwarded; then the 4 fix-branch commits were unpublished
> on `origin/main` and are pushed with this note.  
> **Deliberately NOT merged:** `local-stash-work` (junk); `babysit/land-open-prs`
> (**deleted** locally — would regress `nyxus_install.sh` + banned palettes;
> remote already gone); `cursor/restore-last-night-state-15e2` / cloud-agent /
> hyprland-055 / vault archives / deep-internal-audit (already on `main` via
> squash or superseded). **Stashes:** all four verified and dropped (reverse
> delta / empty / superseded / temporary fix-login WIP).  
> Still open: blank login needs **live** apply+reboot; Settings Increment 2.


> **★★★★ 2026-07-31 (latest) · HUB/POWER GAP — FIXED AND VERIFIED LIVE ★★★★**  
> Measured with `hyprctl` on the running compositor, in both phases. The three
> previous passes each *reasoned* about this and each moved the gap to the
> opposite edge; this one measured first.
>
> **What the measurement showed** (reserved `[0,40,0,158]`):
> ```
> powermenu   (shield wired) y=40 for ~2.2s, then snaps to y=0
> screensaver (no shield)    y=40 at t=0.1s ... y=40 at t=4.0s — forever
> ```
> So the original `eww.yuck` comment was **right** — Hyprland *does* re-lay-out
> the surface when `bar-top`'s zone goes away. `096eeef5`'s correction of that
> comment was **wrong**, and its `:y "-40"`-on-all-8 would have put the gap back
> at the **bottom** on every window whose bars do close. Two different causes
> shared one symptom: a ~2.2s transient on shielded windows, and a permanent
> gap on windows that never had a shield wired (`deepcore` — its `DEEP_SHIELD`
> var is defined but referenced by nothing — plus `screensaver`, `mission`,
> `snap-picker`).
>
> **★ THE RULE — the strategy follows `:stacking`.** That is what decides
> whether the bars have to move at all. Get this backwards and the gap returns
> at the other edge:
>
> | `:stacking` | renders | strategy |
> |---|---|---|
> | `"fg"` | **below** `bar-left/right` — bars must close anyway | open via **`nyxus-overlay-open <win>`**, which releases the exclusive zones **before** the surface maps → `y=0`, no margin, no timing dependency |
> | `"overlay"` | **above** the bars — they stay up | keep **`:y "-40"`** to cancel the fixed `reserved_top` |
>
> `"fg"`: `dashboard`, `powermenu`, `cheatsheet`, `nyxus-hub` (the Hub already
> did this via `nyxus-hub-open` — which is exactly why it never showed the gap).
> `"overlay"`: `screensaver`, `deepcore`, `mission`, `snap-picker`.
> `hotkey-cheatsheet` is 720x640, not fullscreen — no gap, leave it alone.
> `splash.yuck` still untouched: it opens before the bars exist.
>
> **Two bugs found while verifying** (both fixed):
> - `overlay-shield.sh` **raced the opener**. The opener creates the lock,
>   closes the bars, then maps — and in that window eww has not yet registered
>   the new window, so the shield's orphan branch reopened the bars it had just
>   closed. Bar surfaces went **4 → 6 → 8**, and the restored `bar-top` shoved
>   the overlay back to `y=40`. Fixed with a 3s grace period on the lock's age.
> - `restore_bars()` returned early on a lock dir with no `bars` file **without
>   clearing the dir**, so the later `mkdir "$lock"` failed forever and the
>   shield became a permanent no-op — bars never hid again until reboot.
>
> **Verified live** (clean run, bars settled between phases):
> `powermenu` y=0 from t=0.3s through t=4.8s, bars 4→0, all four restored on
> dismiss · `screensaver` y=0 h=1080 bars stay 4 · `deepcore` y=0 h=1080 bars
> stay 4.
>
> ⚠ `nyxus-overlay-open` had to be added to **both** installer allowlists
> (`install.sh`, `nyxus_install.sh`) — they deploy an explicit list, so a new
> script silently never reaches an installed system.

> **★★★ WHERE WE STAND — 2026-07-31 ~00:40 EDT · SESSION RECOVERY ★★★**  
> The Jul 30 evening multi-agent session died mid-flight (machine freeze + Cursor
> billing block). ~65 uncommitted paths were at risk. **Salvaged onto `main` as
> WIP commits** (art repoint `5b3d3f3b`, docs `92978719`, login greeter
> `ad15cf11`, SDDM quarantine `fcba423b`). Settings Increment 1 was already on
> main as `20953054`.  
> **Full brief (read first):** [`docs/SESSION_RECOVERY_BRIEF_2026-07-31.md`](./docs/SESSION_RECOVERY_BRIEF_2026-07-31.md)  
> **Still broken for the owner:** blank graphical login (TTY3 workaround) —
> the fix is committed and the root cause is confirmed, but it needs one root
> command + a reboot to apply (see below). Settings Increment 2 not started,
> login-card eye candy / Hub background / deep audit still queued.  
> **✅ Hub / Power gap — FIXED and verified live** (see the block above).  
> **⛔ DO NOT BAKE** until login is verified live. Do not merge
> `local-stash-work`. Do not re-do work listed as landed in the brief.
>
> **★ LOGIN — the fix shipped in a file nothing ran.** The Jul 31 salvage
> committed the SDDM quarantine to a **new** file, `scripts/nyxus-form-login.sh`
> (a byte-identical copy), instead of updating `scripts/nyxus-fix-login.sh`.
> Nothing references "form-login"; the recovery brief recorded it as a phantom
> `M` and concluded the content was committed. It was not — `HEAD`'s
> `nyxus-fix-login.sh` was still the pre-quarantine version. Now corrected: the
> quarantine lives in `nyxus-fix-login.sh` and the duplicate is gone.
>
> Root cause is **confirmed live, not inferred**:
> `/etc/sddm.conf.d/nyxus.conf.bak-2026-07-21` is still on the box, sorts after
> `10-nyxus.conf` (SDDM merges *every* file in that dir by name, last wins), and
> re-supplies `DisplayServer=wayland` (weston is not installed) while replacing
> `GreeterEnvironment` and dropping `QT_QUICK_BACKEND=software`. The journal
> shows `SDDM::Auth::HELPER_DISPLAYSERVER_ERROR` at **Jul 31 02:18**. The
> quarantine loop was tested against a replica of the live directory: it moves
> the `.bak`, keeps both NYXUS drop-ins, and continues.
> **Needs root to apply** (owner is fingerprint-only, so an agent cannot):
> `sudo bash scripts/nyxus-fix-login.sh`, then reboot with TTY3 kept as the
> escape hatch until a graphical login is confirmed.

> **Last updated: 2026-07-30 ~14:30 EDT (⛔ THE "MY BAKE LOOKS OLD" MYSTERY IS SOLVED — the ISO was right every time; the CONFIGS reached their own tools through an EMPTY `~/.local/bin`. Fixed + gate 13z. bootstrap r16 · then a SECOND pass fixed the 102s boot, the slow-everything (squashfs `xz`→`zstd`, 7.6× faster cold reads), the dead station launches and the layer-blur ordering — gates 13aa–13af. The Hub trap + dead Hub clicks are STILL OPEN and need a live session. · REBAKE REQUIRED)** · Owner: Joseph A. Sierengowski (`nyx` / `nyxus`)
> If you are a new agent picking up NYXUS: **read this entire file before touching
> anything.** It exists because this project got scattered across duplicate clones
> and the same problems got re-diagnosed and re-broken multiple times, costing the
> owner a lot of time and money. Do not veer off into a different approach. Keep the
> flow, and **update this file as you work** so the next agent re-derives nothing.
>
> **★★ LATEST — ON MAIN (Jul 29): PR #77–#81 merged · REBAKE REQUIRED**  
> Silent-failure audits (**#77**, **#80**), station decks / hacker / CAVA (**#78**),
> bootstrap r15 + btop self-install (**#79**), MESH deck + dunst hacker + pill
> font (**#81**). Headline from #80: **`nyxus-sense` was never launched** — the
> whole reactive mood layer sat on defaults. Full details below.
>
> **★★ START HERE — PICKUP BRIEF (Jul 28 evening):**  
> [`docs/PICKUP_BRIEF_2026-07-28.md`](./docs/PICKUP_BRIEF_2026-07-28.md)  
> Where the build is, what to do next and in what order. **THE INSTALLER BUG
> IS SOLVED**: calamares is a binary in [blackarch] and is now pacstrapped
> directly - four ISOs failed because every previous fix accepted the wrong
> premise (that it had to be AUR-built in the chroot). Also covers the EDR
> (Bifrost + jeTT were both blind; connection fixed, throughput still open),
> the uncommitted vault-repo work, and the traps that cost hours.
>
> **★ Security inventory (Jul 27):**  
> [`docs/SECURITY_INVENTORY_2026-07-27.md`](./docs/SECURITY_INVENTORY_2026-07-27.md) — full Arsenal / modes / GodsApp / Intel / Vault / local Projects / BlackArch list.
>
> **⚠ CRITICAL — BIFROST'S AI EDR WAS RUNNING BLIND (found Jul 27):**  
> Ollama was installed but never started, so `heimdall.guardian` got
> connection-refused on every event: circuit breaker permanently OPEN,
> **~15,000 suspicious events dropped per hour**, and 100% of verdicts
> downgraded to `severity=INFO`. It reported **`active`** to every health
> check in this build the whole time. **Run `nyxus-edr-repair`** (needs root).
> **jeTT was blind too, unrelated cause:** its eBPF sensor crashed
> (`ringbuf poll: Interrupted system call`) and `auditd` is off, so it sees
> almost no execs — a `/tmp` script it is meant to QUARANTINE went unlogged.
> NOTE there are **two jeTT installs**; the live one is
> `~/Projects/jeTT/target/release/jett-daemon`, and the live allowlist is
> `/etc/jett/allowlist.conf`, not the copy in the Projects tree.
> Full evidence + verification commands in the brief below.
>
>
> **★ NEWEST — STATIONS, APPS & HOME LAB (Jul 27 pm) — READ FIRST:**  
> [`docs/STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md`](./docs/STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md)  
> Six stations now (HOME/START/GHOST/FORGE/LAB/ARSENAL), and the GowskiNet
> vault consoles are **real apps**: each serves API + built SPA from one
> process under a systemd unit, opened by a native Tauri shell. Axiom is
> Electron and must be PACKAGED. **Contains a real security fix — all six
> console backends were listening on 0.0.0.0 and reachable from the LAN.**
> Also lists the measured gaps on this box (auditd inactive, no fail2ban /
> usbguard / MAC, Secure Boot off, no disk encryption).
>
> **★ PREVIOUS — HOME + START STATIONS (Jul 27) — READ FIRST:**  
> [`docs/HOME_AND_START_STATIONS_BRIEF_2026-07-27.md`](./docs/HOME_AND_START_STATIONS_BRIEF_2026-07-27.md)  
> The home page is the eww **`home-deck`** window on the **HOME** station
> (`Super+Home`), and the NYXUS Start menu is now the eww **`start-panel`**
> window on its own **START** station (`Super+End`), and **GHOST** (`Super+3`)
> is a live security console. START **replaces** the
> `nyxus-start` GTK4 app, which sat on the OVERLAY layer and could be neither
> closed nor moved when it lost keyboard focus. Left rail reads HOME / START /
> 1-9. Contains the eww traps that cost real time: **a window is sized to its
> CONTENT** (oversized surfaces get parked at a negative y), **`:focusable
> true` is a session-wide keyboard grab** in eww 0.5, and `pkill -f` from an
> inline `bash -c` kills its own shell. Verify layout with `hyprctl layers -j`,
> never by eye.
>
> **★ PREVIOUS — LOGIN FIXED + BARS REDESIGNED (Jul 26 eve) — READ FIRST:**  
> [`docs/BARS_AND_LOGIN_BRIEF_2026-07-26.md`](./docs/BARS_AND_LOGIN_BRIEF_2026-07-26.md)  
> The **"no login screen"** bug is finally dead: `/etc/sddm.conf.d/nyxus.conf`
> was regenerated on every run by `sddm-theme/install.sh` — fixed at the source,
> verified live. Also: hacker-mode was silently stuck on, the bar "shadow blocks"
> are gone, and the side rails / ticker / bottom hub were **redesigned at the
> owner's explicit request** (saucer↔1980s boombox flip, bass-reactive).
> **This supersedes the Jul 25→26 revert note below — do NOT revert it as if it
> were that episode.** Contains the eww toolchain traps (no `sass` installed;
> live `eww.css` has drifted from source; use append-only override blocks).
>
> **⚠ EWW hub chrome night (Jul 25→26) — historical:**  
> [`docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](./docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md)  
> Redesign + Meshy wraps were wrong; **fully reverted**. Owner confirmed restored
> desktop looks good. Do not restart saucer/time/dock/ticker work unless the
> owner explicitly asks — **on Jul 26 the owner DID ask; see the brief above.**
>
> **Live USB report + full sweep:**  
> [`docs/LIVE_BOOT_AUDIT_2026-07-25.md`](./docs/LIVE_BOOT_AUDIT_2026-07-25.md)
>
> **Last ~day of building (story + done/open):**  
> [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md)
>
> **Deep consistency audit (revised evening):**  
> [`docs/DEEP_BUILD_AUDIT_2026-07-24.md`](./docs/DEEP_BUILD_AUDIT_2026-07-24.md) —
> bake wipe gaps (`eww/assets`, `hypr/scripts`) fixed via **#76** (on `main`).
>
> **Theme + Settings workstream:**  
> [`docs/ALIEN_NEON_SETTINGS_BRIEF.md`](./docs/ALIEN_NEON_SETTINGS_BRIEF.md) then
> [`docs/ALIEN_NEON_SETTINGS_AUDIT.md`](./docs/ALIEN_NEON_SETTINGS_AUDIT.md) /
> [`docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md`](./docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md).
> Stay-as-is: Bifrost / GodsApp / Meli / Arsenal.

---

## 🪟 2026-07-30 (evening) · THE BOTTOM STRIP, THE BLUE SCREENSAVER, AND THE LIVE SYNC

> Three owner reports, all answered by measurement on his running Hyprland
> session (PID 7466, Hyprland 0.55.4, eDP-1 1920x1080). **Two of the three had
> the same root cause and it is arithmetic, not a guess.** His live `~/.config`
> was also ~700 lines behind `main` and has now been synced; backups and the
> restore command are recorded below.

### 🔢 ONE NUMBER EXPLAINS TWO BUGS: `reserved [0, 40, 0, 158]`

`hyprctl monitors -j` on this panel:

| | |
|---|---|
| monitor | 1920x1080 |
| `reserved` (l,t,r,b) | **`[0, 40, 0, 158]`** — `bar-top` y=4 h=36, `bar-bottom` y=922 h=150 |
| usable height | 1080 − 40 − 158 = **882** |

Anything that asks for a **1080-tall** box while the bars hold those exclusive
zones gets **centred in the 882**, not in the monitor:

```
y = reserved_top + (usable_h − requested_h) / 2
  = 40 + (882 − 1080) / 2
  = −59          → bottom edge at 1021 → a 59px strip of live desktop
```

**−59 was measured on three different surfaces**, two of them different
subsystems entirely. This is Hyprland's `arrangeLayerArray` / window-layout
rule: bounds are the *usable* area unless `exclusive_zone == −1`.

| Surface | Kind | measured `y` | bottom edge |
|---|---|---|---|
| `nyxus-powermenu` (Super+Escape) | eww layer surface | **−59** | 1021 |
| `nyxus-hub` opened with a bare `eww open` | eww layer surface | **−59** | 1021 |
| `com.nyxus.matrixsaver` | **toplevel window** | **−59** | 1021 |

`nyxus-hub` opened through **`nyxus-hub-open`** measured **y=0, bottom 1080** —
because that script closes the four bars *synchronously* before mapping. That
is the only reason the Hub ever looked right, and it is why the Hub and the
power menu behaved differently.

### 🐛 Bug 1 — the bottom strip under NYXUS Power (owner's report, reproduced)

`dashboard` / `nyxus-hub` / `powermenu` / `cheatsheet` were all
`:geometry (geometry :width "100%" :height "100%" :anchor "center")`.

The codebase already has a mechanism for this — `overlay-shield.sh`, referenced
by a `defpoll` per overlay, hides the bars while an overlay is up. **It works,
but it is a 2-SECOND poll**, so every open looked like this:

```
t=1s   nyxus-powermenu  y=-59  bottom=1021   ← 59px of desktop showing
t=3s   nyxus-powermenu  y=0    bottom=1080   ← shield fired, bars gone
```

That two-second window is the whole bug. "There's usually always a gap on the
bottom then you can see my regular screen" is exactly right.

**Fix: `:anchor "top center"`, not `"center"`.** With a top anchor Hyprland
puts the surface at `bounds.y` and keeps its requested height, so it runs
`40 → 1120` and the bottom of the screen is covered *from the first frame*,
independent of the shield's timing. Once the shield does fire the surface
snaps to `0 → 1080`. Measured both phases.

Applied to all **nine** fullscreen eww windows across both trees the bake
reads: `eww.yuck` (dashboard, nyxus-hub, powermenu, cheatsheet, screensaver)
plus `snap.yuck`, `mission.yuck`, `deepcore.yuck`, `splash.yuck`.

**Things that were tried and do NOT work — do not re-try them:**
- **Dropping `:initial ""` from the shield defpolls** so the poll would run at
  open time. Measured: made it *worse* — the shield did not fire at all inside
  1.6 s where it previously fired at ~2 s.
- **An exclusive-zone setting.** eww's `:exclusive` is a **bool**; it selects
  auto or 0 and can never emit the `−1` that would make Hyprland use the full
  monitor as the bounds. There is no `layerrule` for it either.
- **Guessing a margin.** Not needed — the anchor removes the dependency on the
  reserved values entirely, which is the point. Do not hardcode 40 or 158.

### 🐛 Bug 2 — `pin on` and `fullscreen on` cancel each other

**Hyprland refuses to fullscreen a pinned window** (pin implies floating). Both
savers carried `pin on` *and* `fullscreen on` in `nyxus-hyprland-rules.conf`,
so the pin won and neither saver was ever fullscreen. Measured, same session:

| | matrix saver | alien saver |
|---|---|---|
| with `pin on` | `[0,−59] 1920x1080 fullscreen 0 pinned true` | `[510,156] 900x650 fullscreen 0` |
| without | — | **`[0,0] 1920x1080 fullscreen 2`** |

The alien saver was the worse of the two: it never requests a size, so it
mapped as a **900×650 card floating in the middle of the desktop**.

`pin` bought nothing — a fullscreen saver already covers its workspace and both
savers quit on any input. **Removed from both.** Gate `13pb`.

Second, independent defect in the same chain: `nyxus_screensaver.py` calls
`self.fullscreen()` in `__init__`, which runs **before the wayland surface
exists**, and wlroots drops it. `nyxus_matrix_saver.py` already carried the
fix and says why in its own comment — *"fullscreen AFTER the surface is
mapped, else wlroots ignores it"*. The alien saver now does the same
`GLib.idle_add(win.fullscreen)` after `present()`. Honest note: with the pin
removed the window rule alone is sufficient, so the `idle_add` is belt and
braces — it keeps the saver correct if the rules shard ever falls out of the
bake again, which it has done three times.

### 👽 Bug 3 — "the screensaver was the old blue one": his LIVE session was stale

Answered definitively; it is **(a)**, not (b) or (c). No third screensaver
exists.

| Evidence | Finding |
|---|---|
| `~/.local/bin/nyxus-screensaver` (what the session resolves) | dated **Jul 22 22:49**, `exec python3 ~/.config/nyxus/nyxus_matrix_saver.py` — the **matrix-rain** saver |
| live `~/.config/hypr/hypridle.conf` | old "Comet-Fire r2" rev, 180/300/420/600, comment reads *"launch the alien **matrix-rain** screensaver"* |
| live `nyxus-hyprland-rules.conf` | had rules for `com.nyxus.matrixsaver` only — no `app.nyxus.Screensaver` block at all |
| `main` (`artifacts/.../nyxus-screensaver`) | urban-alien launcher, pins the hero, falls through three payload paths |
| **the 07.29 ISO** (`unsquashfs` of `airootfs.sfs`) | ships the **correct** urban-alien launcher **and** the 45/300/600/900 hypridle |

So the stick was right and the builder box was two revisions behind — the same
shape as the `~/.local/bin` bug, in the opposite direction. Searched for a
third implementation and there is none: the only other saver surface is the eww
`screensaver` window (a violet **starfield**, `starfield-lock-base.png`, mean
RGB 8/4/17), and **nothing on the idle path opens it** — the only callers are
rofi's "Lock Screen" entry and `rofi-scripts/power.sh`. Worth knowing if he
ever reports a "blue starfield" reached from a menu; hypridle cannot produce it.

The matrix saver's palette is mint `#26ffb7` + violet `#984dff` over the dark
wall, which is a fair match for "the old blue one".

### 🔄 The live session is now synced with `main`

His `~/.config` was measured against the **exact mapping `build-iso.sh` uses**
(not guessed): 34 config files behind, 5 absent, plus 34 differing and 61
missing `nyxus-*` tools in `~/.local/bin`. **177 files updated.**

**Backups (deletes nothing, fully reversible):**

```bash
~/nyxus-live-backup-20260730-150614.tar.gz          # 318M · .config/{eww,hypr,nyxus,wlogout,dunst,btop,cava}
~/nyxus-live-localbin-backup-20260730-150614.tar.gz # 129M · .local/bin
# restore:  tar -xzf ~/nyxus-live-backup-20260730-150614.tar.gz -C ~
#           tar -xzf ~/nyxus-live-localbin-backup-20260730-150614.tar.gz -C ~
```

**Deliberately NOT synced — these are runtime-generated and the repo ships
empty stubs. Copying them would have destroyed live state:**

- `~/.config/hypr/hyprlock-accent.conf` — live holds the **generated** PRISM
  values (`$nyxus_accent_r = 125` …); the repo copy is a three-line comment.
  Overwriting it would have left hyprlock with undefined accent variables.
- `~/.config/hypr/nyxus-monitors.conf` — Settings ▸ Displays owns this.

**Local-only files found, none destroyed:** 19 `eww.*.bak-*` snapshots (+ one
`eww.yuck.CORRUPT`), and three scripts with no counterpart in either tree —
`eww/scripts/gen-liquid-gifs.py`, `start_feed.py`, `start_search.py`. Grepped
both trees: **nothing references any of the three**, so they are unreferenced
scratch. They are still on disk.

`hypridle` was **restarted** (`hyprctl dispatch exec hypridle`) — it had been
running since login with the old 180 s matrix pipeline and would not otherwise
have picked up the new config. eww stayed at **one daemon / four bars**
throughout; `hyprctl configerrors` is clean after `hyprctl reload`.

Screenshots: **`~/Pictures/nyxus-live-sync-2026-07-30/`** — `08-BEFORE-…`
shows the 59px strip, `06/07-…` the fix at both phases, `09-…` the fullscreen
urban-alien saver, `10-…` the Hub.

### 🛡 New gates (both negative-tested)

| Gate | Asserts |
|---|---|
| `13pa` | No shipped `.yuck` on either tree declares a 100%x100% window with `:anchor "center"`; and every `NS/eww/*.yuck` is byte-identical to its skel copy |
| `13pb` | Neither saver class carries `pin on`; both carry `fullscreen on`; and `nyxus_screensaver.py` re-asserts fullscreen after `present()` on all three trees |

Negative-tested by reverting each fix in turn: `13pa` fired with the file and
line number of every centred window, `13pb` fired per class per tree. `13pb`
matches with `grep -F` on comment-stripped lines — the class patterns contain
literal backslashes (`com\.nyxus\.matrixsaver`) and an ERE built from them
matches nothing, which is how the first draft passed while asserting nothing.

### ⚠ What is NOT verified by any of this

- **Everything above is Hyprland 0.55.4.** The ISO ships **0.56.1**. The layout
  arithmetic is core wlr-layer-shell behaviour and very unlikely to move, but
  it is not proof for the stick. Gate `13x` already warns on the skew.
- **Boot-time surfaces cannot be checked live and remain unverified:** the
  greeter (runs as `greeter` under greetd before login), plymouth, first-boot
  timing, and the squashfs `zstd` switch. Those need a bake.
- `/usr/share/backgrounds/nyxus/` **does not exist on the builder box** (root
  owned, no sudo), so the saver resolved its wall through the
  `~/.config/hypr/walls/` fallback. The pinned system path is only exercised on
  a real stick.
- One line inside `nyxus_screensaver.py` in this commit (`nyxus-graffiti-space`
  → `nyxus-desktop-hero` in the wall candidate list) is **agent `4e21a37e`'s
  in-flight art work**, not mine. It is inseparable from the file and was
  committed rather than risk a write race on a shared working tree. Its other
  in-flight edits (docs, `stations.json`, `wall-rotation.list`, 20 staged image
  deletions) were left untouched.

---

## ⛔ WHERE WE STAND — 2026-07-30 · WHY EVERY STICK "LOOKED OLD" · REBAKE REQUIRED

> The owner flashed the `2026.07.29` ISO, booted it, and reported seeing "my
> older version" — again, as with several bakes before it. **The ISO was not the
> problem. It has never been the problem.** Root cause found, fixed on `main`,
> and gated. Nothing is in a stick yet.

### What was actually verified about the 07.29 stick (all CLEAN)

The stick was mounted and the squashfs inspected directly. Do **not** re-derive
this — every one of these was checked and was correct:

| Checked | Result |
|---|---|
| Build stamp `/etc/nyxus-build` | `nyxus-2026.07.29`, source commit `91b86185` = `main` tip |
| `airootfs.sfs` on the stick | 7,691,059,200 B — byte-identical to `out/nyxus-2026.07.29` |
| `/etc/skel` vs `/home/nyx` | **byte-identical** (`cp -rT` in customize_airootfs is fine) |
| `/opt/nyxus-cache` vs skel | **byte-identical** (hyprland.conf, all 8 installed shards, eww.yuck/css) |
| Newest work present? | MESH deck, `st.name` station pills, `nyxus-reactive.conf` sourced **and** autostarting sense→mood→threatd — all in the shipped files |
| Packages | hyprland **0.56.1-2** + hyprlang 0.6.8 (no 0.57 disaster), **calamares present**, eww + mpvpaper compiled into `/usr/local/bin` |

So: skel was current, the bootstrap cache was current, the live user's home was
current. The image was right. **The desktop simply could not reach its own
tools.**

### 🔴 ROOT CAUSE — the configs ran everything through an EMPTY `~/.local/bin`

`/home/nyx/.local/bin` ships **EMPTY** (nothing stages into it, and nothing
should). But the shipped Hyprland configs invoked **21 distinct nyxus tools** by
the hardcoded path `~/.local/bin/<tool>` — **26 live call sites**.

**All 21 tools exist in `/usr/local/bin` on the ISO. All 21 also exist in
`~/.local/bin` on the builder box.** That is the whole trap: on this machine
every one of them resolves, so the feature "works" and gets marked
*verified live* — and on the stick every one is silently `command not found`.

What was dead on **every** stick, on every boot:

| Call site | What died |
|---|---|
| `exec-once = ~/.local/bin/nyxus-living on quiet` | the **entire living/reflex layer** — this is the only thing that starts `nyxus-pulsed` |
| `exec-once = ~/.local/bin/nyxus-shader restore` | screen shaders never restored |
| `exec-once = ~/.local/bin/nyxus-soundd` | all UI sound design |
| ~20 keybinds | shader, tint, spray, beat, lens, accent-sync, wall-next/cycle, freeform, live-wallpaper, **and the three headline reactive features** (whispers / SUPERNOVA / graffiti wall) |
| 5 × `hyprlock.conf` | weather line, lock art, track chip/title/artist — **the lock screen loses all dynamic content**, which reads as "the old lock screen" |

Note the cruelty of the reactive one: PR #80 correctly fixed
`nyxus-reactive.conf` being *unsourced*, so the shard now loads — but its three
binds still pointed at `~/.local/bin`, so those features were **still** dead on
the stick. That is the same feature being "fixed" twice and shipping broken
twice.

**FIX:** the `~/.local/bin/` prefix is gone from every shipped call site — bare
command names now resolve through PATH to `/usr/local/bin`. This is already the
convention elsewhere in the same files (`nyxus-mission-control-toggle`, and the
newer `command -v nyxus-sense && nyxus-sense start` lines). Behaviour on the
builder box is unchanged, because `nyxus-session-start` prepends
`$HOME/.local/bin` to PATH, so the same binary still wins here.

Applied to **both** surfaces the bake reads (NS is source of truth; skel is
wiped and repopulated from it): `nyxus-signature.conf` (19), `hyprlock.conf`
(5), `hyprland.conf` (3), `nyxus-reactive.conf` (3), `nyxus-cometfire.conf` (3).
Commented-out directives were converted too, so uncommenting one can't
reintroduce the bug. The lone survivor is a prose comment in
`nyxus-freeform.conf` describing where the generator lives — harmless.

### 🛡 verify-profile gate 13z (new) — negative-tested

Hard-**FAIL**s if any shipped hypr config reaches a tool through
`~/.local/bin` / `$HOME/.local/bin`. It scans `hyprland.conf`, **every
`conf.d/` shard**, `hyprlock.conf`, *and* the NS copies (50 files today), and it
only flags lines that actually run something (`bind*`/`exec-once`/`exec`/`text`/
`reload_cmd`) — prose comments are ignored, commented-out directives WARN.

**Why 13w did not catch this** (worth internalising): 13w reads **only
`hyprland.conf`**, never the shards — and it asserts the binary *ships*, not
that the config's path to it *resolves*. Every one of these binaries shipped
perfectly. Shipping ≠ reachable.

### Also landed

- **`nyxus_install.sh` deployed only 8 of the 18 conf.d shards**, so an
  installed system re-running bootstrap would have picked up the fixed
  `hyprland.conf`/`hyprlock.conf` and kept the **broken** shards. Added
  `nyxus-signature.conf` / `nyxus-reactive.conf` / `nyxus-cometfire.conf`.
  Deliberately **not** glob-copied from the cache: `nyxus-stations.conf`,
  `nyxus-freeform.conf` and `nyxus-monitors.conf` are GENERATED at runtime and a
  glob would clobber the user's live station matrix / monitor layout.
- `BOOTSTRAP_VERSION` → **`2026.07.30-r16-localbin-path`** so installed systems
  self-heal.

### 🔎 OPEN — the login screen (read before "fixing" it)

Two separate things, neither of them a regression:

1. **The greeter genuinely has not changed since Jul 24.** `regreet.css` last
   changed in `a7af901f` (2026-07-24). So "still the older login screen" is
   *correct* — the 07.29 stick shows the same greeter as 07.26/07.27/07.28
   because **nobody has redesigned it**. If the owner wants a new login screen,
   that is net-new work, not a bug hunt. What *did* visibly degrade is the
   **lock** screen (hyprlock), via the `~/.local/bin` bug above — easy to
   conflate with the login screen.
2. **The session the greeter starts is non-deterministic.** The ISO ships
   **three** entries in `/usr/share/wayland-sessions`: `hyprland.desktop`
   (upstream → `/usr/bin/start-hyprland`), `hyprland-uwsm.desktop`, and
   `nyxus-hyprland.desktop` (→ `nyxus-session-start`). `/var/lib/regreet/` and
   `/var/cache/regreet/` ship **empty**, so regreet has no cached
   `user_to_last_sess` and no configured default — it preselects whatever is
   first in its list, which is almost certainly plain **"Hyprland"**, not
   NYXUS. The tuigreet/agreety fallbacks *do* hardcode
   `--cmd nyxus-session-start`, so only the themed path is ambiguous.
   **NOT changed** — regreet's ordering could not be verified without a live
   greeter, and guessing at login behaviour risks a no-desktop boot. Practical
   delta is now small (the PATH difference stopped mattering once the
   `~/.local/bin` bug was fixed); plain Hyprland still reads the same
   `~/.config/hypr/hyprland.conf`. Two candidate fixes when the owner wants it:
   drop the two upstream entries at bake so exactly one session exists, or
   pre-seed `/var/lib/regreet/state.toml`. **Verify which session is selected on
   the next boot before touching this** — the dropdown is right there on the
   greeter.

### 🔜 NEXT

1. **Rebake** from clean idle `main` — `cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh`
2. On the stick, verify the things that were dead and should now be alive:
   - Super+Alt+L toggles LIVING THEME; borders pulse (proves `nyxus-living`)
   - Super+O cycles shaders; Super+T tint; Super+Z spray
   - Super+Ctrl+W whispers · Super+Alt+Shift+S supernova · Super+Alt+Shift+G graffiti wall
   - lock the screen (hyprlock) → weather line + lock art + track info render
   - UI blips audible on window open/close (`nyxus-soundd`)
3. **Note which session the greeter preselects** — see OPEN item 2 above.

---

## ⛔ WHERE WE STAND — 2026-07-30 (later) · THE OTHER SEVEN SYMPTOMS · REBAKE REQUIRED

> Companion to the `~/.local/bin` section above, **not a replacement for it.**
> That one explains why the desktop looked stale. It does **not** explain the
> 102-second wait, the slow-everything, or the flicker. Those are separate and
> are fixed here. Everything below is on `main`'s working tree, `verify-profile`
> passes, and **nothing is in a stick yet.**
>
> The owner reported eight symptoms. Below is what each one actually was.
> Three of them I could not fix from here and they are flagged honestly — do
> **not** read this section as "all clear".

### 🐌 The 102s splash→greeter wait was never one bug (symptom 1)

`nyxus-firstboot.service` really was `Type=oneshot` on `multi-user.target`, and
that really was fixed in 07.29 — the shipped unit is `Type=simple` and the
`06-honeypot-stack.sh` live-media guard is present, both verified in the
squashfs. The owner saw no improvement because **two more things sat on the
same path**, and `multi-user.target` waits for all of them:

| What | Why it blocked the greeter | Fix |
|---|---|---|
| `NetworkManager-wait-online.service` | `systemctl enable NetworkManager` pulls it in. `docker.service` and `ollama.service` are both `After=network-online.target` **and** `WantedBy=multi-user.target`, so on a live stick with no configured network the whole target stalled on its 60s timeout | `systemctl disable`d in `customize_airootfs.sh` |
| `nyxus-honeypot-firewall.service` | `Requires=`+`After=docker.service`, `WantedBy=multi-user.target` — so dockerd had to *fully* start before login, in order to firewall containers that `06-honeypot-stack.sh`'s live-media guard had already skipped | `ConditionPathExists=!/run/archiso` |

`systemd.target(5)`: *"Target units will automatically complement all configured
dependencies of type `Wants=` or `Requires=` with dependencies of type
`After=`."* `graphical.target` is `Requires=`+`After=` `multi-user.target`, and
greetd sits behind it. **Anything enabled into `multi-user.target` is in front
of the login screen.** That is the general rule; the two rows above are just
today's instances of it. Gate **13ac** asserts all four items on this path.

### 🐌 Everything-is-slow was the squashfs compressor (symptoms 3 and 6)

`profiledef.sh` compressed `airootfs` with `xz`. Measured on this image's own
content (2140 MB of `/usr/bin` + `/usr/lib/systemd`, single-threaded, warm
cache, so only decode cost is compared):

| Compressor | Size | Decompress | Throughput |
|---|---|---|---|
| `xz -Xbcj x86 -b 1M -Xdict-size 1M` | 647.0 MB | 29.5 s | 72 MB/s |
| `zstd -Xcompression-level 19 -b 1M` | 716.7 MB | 3.9 s | **549 MB/s** |

**7.6× faster cold reads for 10.8% more ISO.** This matters far more than the
raw ratio suggests: squashfs inflates a whole 1 MiB block to serve a single
4 KiB read, so under `xz` *every* cold file touch costs ~14.5 ms of CPU, and
starting a desktop session touches thousands of them. Switched to `zstd`.
`NYX_SQUASH_COMP=xz ./build-iso.sh` puts it back if the owner ever wants size
over speed; gate **13ad** warns (does not fail) when `xz` is selected, since
that is a legitimate choice and not a bug.

### 🎛 Station pills, decks, and the launch chain (symptom 5)

Three genuinely separate problems, all now fixed:

1. **Two stations pointed at software that is not on the ISO.** FORGE was
   `on-created-empty:cursor` and CORE was `on-created-empty:thunar`. `cursor` is
   not packaged for Arch at all and `thunar` was never in `packages.x86_64`, so
   those two pills switched workspace and then opened nothing, with no error and
   nothing in the journal. Both now use `command -v` chains ending in a program
   that is definitely installed. `btop` was the same story from the other
   direction — the profile ships three btop themes and four launch paths fall
   back to it, and btop itself was missing; added to `packages.x86_64`.
2. **The pills dispatch by NUMBER, the deck watcher maps by NAME.** `station_pill`
   runs `hyprctl dispatch workspace 1`; `nyxus-home-deck` reads
   `activeworkspace.name` and looks up `OPS`. Those only line up because
   `nyxus-stations.conf` carries `defaultName:OPS`. One dropped or unsourced
   shard and every numbered station reports `.name` as `"1"`, no map entry
   matches, and `_sync` closes every deck and opens none — which is exactly
   "clicking a station does nothing". `nyxus-home-deck` now aliases the numeric
   ids to the same decks, read from `stations.json` at startup, so the pills work
   with or without the names.
3. **`nyxus-stations.conf` is a generated snapshot of `stations.json`** and can
   drift, in which case the first hacker-mode flip silently rewrites what the
   stations do. Regenerated, and gate **13ab** now checks both the drift and that
   the *last* fallback in every launch chain resolves to something the ISO
   installs. Earlier branches are allowed to miss — that is what `command -v`
   guards are for — but they are reported so a never-taken branch is visible.

Note **BIFROST (station 9) has no deck and that is by design** — it is not a bug
and does not need one.

### 🧨 `set -u` + an unset session variable = a daemon that dies mid-line

`nyxus-home-deck`, `nyxus-soundd` and `nyxus-tintd` all run `set -u` and then
built their Hyprland socket path from a bare `${XDG_RUNTIME_DIR}` and
`${HYPRLAND_INSTANCE_SIGNATURE}`. In all three, the *immediately preceding line*
already used `${XDG_RUNTIME_DIR:-/tmp}` — the author knew it could be unset and
the guard just never reached the next line. `nyxus-home-deck` even carries an
80-line-earlier comment saying that variable "is set in a login shell but NOT in
some exec-once/systemd contexts".

Unset either variable and bash aborts with `unbound variable` **at that line**,
which for `nyxus-home-deck` means it completes its one startup sync and then
dies: the decks appear once and no station ever opens anything again, silently.

**Honesty note:** `pam_systemd` is in the greetd PAM chain and Hyprland exports
`HYPRLAND_INSTANCE_SIGNATURE` to `exec-once` children, so both variables are
*normally* set and this is **not proven** to be what the owner hit. It is a
latent trap that produces exactly the reported symptom, it is free to fix, and
the codebase already defends against it in ten other scripts. All three now
guarded; gate **13af** covers all 114 `set -u` scripts and understands the
`export VAR="${VAR:-default}"` idiom, so it does not fire on scripts that hoist
the guard to the top.

### 🖼 Layer-blur file order was load-bearing and backwards (symptom 4)

The CSS half of the "shadow box" was genuinely fixed on Jul 26 (the ink
drop-shadow in `@mixin obsidian-vessel`) and that fix **is** in the 07.29 image —
verified, zero `0 6px 18px` in the shipped `eww.css`, bars/rails all
`background: transparent`. So that is not what regressed.

What was wrong: Hyprland applies `layerrule`s in file order, **last match wins**,
and the `^(nyxus.*)$` catch-all sat at the *bottom* of
`nyxus-hyprland-layerblur.conf` — below every explicit per-namespace rule. A rule
that calls itself "catch-all for future surfaces" was in fact a global override
silently eating all of them, which is precisely the trap
`docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md` §7.4 warns about ("the catch-all can
undo `blur off`"). **Moved to the top**, so it is now the floor it always claimed
to be and an explicit rule below it actually wins. Also added rules for the seven
numbered station decks, which shipped on 07.29 with no rule of their own. Gate
**13ae** keeps the ordering and reports namespaces that have no explicit rule.

Effective blur is **unchanged** by this — every explicit rule currently carries
the same values as the catch-all. The point is that a fix is now *possible*.
There is a ready-to-use owner A/B at the bottom of that file
(`hyprctl keyword layerrule 'blur off, match:namespace ^(nyxus-bar-.*)$'`,
instant and reversible, no rebake) plus four commented-out `blur off` lines. It
is left commented because turning bar blur off also removes the frost behind the
pills — that is a look decision, not a bug fix. **If the boxes survive this
bake, run the A/B and tell the next agent the answer.**

### 🩹 `~/.local/bin`, continued — two sites the hypr sweep did not cover

Gate 13z scans the hypr tree. The same bug class lives in every other shipped
config that names an executable, and two real instances were still there after
13z went green:

- `skel/.config/dunst/dunstrc` → `script = /home/nyx/.local/bin/nyxus-notif-to-eww`.
  **This was the worse of the two.** That rule also sets `skip_display=true`, so
  dunst suppressed its own popup *and* the eww bridge could not start —
  notifications were swallowed outright on the stick, which is also why nothing
  ever surfaced an error toast for any of the other broken features. Now an
  absolute `/usr/local/bin` path, because dunst's PATH is not ours to assume.
- `eww/scripts/hotkey-record.sh` → `exec "${HOME}/.local/bin/nyxus-hotkey"`, now
  a bare name.

Gate **13aa** scans the 517 shipped configs *outside* the hypr tree for this.

Also hardened `nyxus-session-start` to guarantee `/usr/local/bin` and
`/usr/local/sbin` are on PATH. greetd currently hands us a PATH that happens to
contain them, but nothing asserted it, and if that ever stopped being true every
bare-name keybind and `exec-once` would die silently and identically to the
`~/.local/bin` bug. This is **not** the banned hardcoded
`env = PATH,/home/cosmic/...` from PR #77 — that pinned an absolute path for a
user who does not exist on the stick.

### 🕳 Three Hub controls jumped to a workspace you cannot see (part of symptom 8)

Hyprland resolves a **numeric** `name:0` into the SPECIAL workspace range
(id `-1337`) — a hidden overlay. HOME was moved off it to `name:HOME` on
2026-07-26 and the reason is written out in the header of
`nyxus-stations-named.conf`, but **three call sites kept the old form** and were
only found on 2026-07-30. All three are inside the Hub or its data, which is a
real part of why the Hub read as "nothing in here works":

| Site | Effect |
|---|---|
| `eww.yuck` `hub_home_pill` | the Hub's own HOME pill went somewhere invisible |
| `nyxus-hub-search` `home\|dash\|dashboard` | same, from the Hub search box |
| `stations-hacker.json` `.home.hypr` | HOME broke on the first hacker-mode flip |

Also in `nyxus-hub-search`: the `files|thunar|fm` command ran bare `thunar`,
which **is not on the ISO** — the same miss as the CORE station's
`on-created-empty`. Now a `command -v` chain ending in `alacritty`.

Gate **13ag** scans 1059 shipped files for `name:0` and hard-fails.

### 🚫 STILL OPEN — not fixed, needs the owner or a live session

Be clear with the owner about these three. They are **not** addressed by this
rebake.

1. **The Hub trap (symptom 7) and dead Hub clicks (symptom 8).** Every Hub
   `:onclick` target was traced and **all of them resolve on the ISO** — bare
   names in `/usr/local/bin`, no `~/.local/bin`, no `${EWW_CMD}`. Escape and
   `Super+Shift+Escape` are real, sourced binds and `nyxus-hub-close` hard-
   restarts a wedged eww. polkit allows `poweroff`/`reboot`/`suspend` for the
   active session and `nyx` is in `wheel`, so power actions *should* work. Two
   concrete suspects, neither safe to change blind:
   - `nyxus-hub` is a full-screen **`overlay`**-layer input surface with no
     input region — a direct violation of the rule in §7 of this file, and the
     same shape as the `nyxus-start` GTK4 trap that was already killed once.
   - `defwidget nyxus_hub_layout` wraps **every** Hub control, close buttons
     included, in `(eventbox :onclick "true")`. It is there to stop clicks
     reaching the outer dismiss handler, but if it consumes pointer events
     instead of propagating them, *nothing* inside the Hub works — which is
     symptom 8 exactly, and would also explain symptom 7, from one cause.

   **Do not "fix" this by guessing.** Layer/focus changes to a full-screen eww
   surface are how this build trapped the desktop before and forced hard resets.
   Reproduce it in a live session, confirm with `hyprctl layers -j` whether the
   eventbox is eating the clicks, then change one thing. `nyxus-panic` is the
   escape hatch; tell the owner it exists.

2. **`nyxus-hub-open` closes all four bars before mapping the Hub.** It has a
   real reason (releasing gtk-layer-shell exclusive zones so the Hub is not laid
   out short) and it *does* restore them if the Hub fails to map. But if the Hub
   maps and then cannot be dismissed, the user is on bare wallpaper with no bars
   and no hub — that is the "trapped" report. Left alone because removing it
   reintroduces the dead-strip bug it was written to fix.

3. **The login screen (symptom 2) — nothing newer was ever built.** Searched
   every local and remote ref: there are exactly four `regreet.css` blobs in all
   of history, all the same "Void Sign-In" design. `main`'s is the newest and
   the best of them — it is the only one carrying ALIEN NEON *and* the fix that
   narrowed the over-broad `frame, .frame, box.horizontal > box` selector, which
   in the older variants also matched regreet's clock and message boxes and
   painted them as stray frosted panels shoved 720 px right. The newest off-main
   greeter commit is Jul 14. **"The login screen is the one before the fix" has
   no lost work behind it — a new greeter is net-new work, not a bug hunt.**

### 🌿 Branch audit — nothing valuable is missing from `main`

Asked and answered: every branch `git cherry` flags is a squash-merge false
positive, junk, or content `main` has moved past. Verified by comparing blob
hashes file-by-file, not by trusting `git cherry`. **Zero open PRs** (81 total,
68 merged); the closed-unmerged ones were all superseded by later consolidations.

- **`babysit/land-open-prs` — do not merge; delete it.** All three things
  HANDOFF said it was holding are already on `main` byte-identical (the recovery
  gate, the path-traversal fix, the offline GTK4 deploy). Merging it would
  *regress* three files: `nyxus_install.sh` would lose 239 lines of newer
  offline logic, `Main.qml` would revert to the DARK MIRROR palette, and
  `nyxus-sync` would revert to the banned violet `#a06bff`. Its remote is
  already `[gone]` and PR #56 is closed as merged.
  Note the recovery gate would not have helped symptom 7 anyway — it is a
  password bypass for the *login and lock screens*, it targets SDDM (abandoned
  for greetd on Jul 14), and nothing invokes `nyxus-recovery-setup` on a shipped
  ISO, so it is inert until run by hand.
- **`origin/nyxus-hyprland-055-fixes` looks alarming at 44 commits and is not.**
  It branched May 19, its newest commit is Jul 10, and its content was absorbed
  by `471c1c50` on Jul 12. `main` has since replaced the palette entirely.
- **All three stashes are safe to drop.** `stash@{0}` is a reverse delta that
  would rip out Arsenal, the C2 teamserver and the BlackArch wiring (251,603
  deletions); `stash@{1}` has an empty tracked diff; `stash@{2}` is superseded
  live tuning. **Do not apply any of them.**
- **`local-stash-work` — confirmed junk, still do not merge.**
- The only genuinely missing tracked file in the whole repo is
  `iso-builder/hardening/nyxus-fim.rules` (+ its `.example`), 32 lines of audit
  rules from `a9b40cc1`. Real, absent, and irrelevant to all eight symptoms.

### 🛡 New verify-profile gates (all negative-tested)

`13z` is the concurrent agent's. These are additive and named to stay clear of it:

| Gate | Asserts |
|---|---|
| `13aa` | No shipped config **outside** the hypr tree reaches a tool through `~/.local/bin` (517 files) |
| `13ab` | Every station launch chain ends in a program the ISO installs; `nyxus-stations.conf` has not drifted from `stations.json` |
| `13ac` | The four things on the splash→greeter path stay off it |
| `13ad` | Warns when the squashfs compressor is `xz` |
| `13ae` | The layer-blur catch-all stays **above** the explicit rules; reports namespaces with no rule of their own |
| `13af` | No `set -u` script uses a bare `${XDG_RUNTIME_DIR}` / `${HYPRLAND_INSTANCE_SIGNATURE}` it never defaults |
| `13ag` | Nothing dispatches `workspace name:0`, which is Hyprland's hidden special workspace |

### 🔜 NEXT (this section)

1. **Rebake.** `verify-profile` passes. Expect the ISO ~70 MB larger and the bake
   itself noticeably faster (zstd compresses far quicker than xz too).
2. **Time the boot.** Splash→greeter should drop a long way. If it does not,
   `systemd-analyze critical-chain graphical.target` on the stick names the next
   offender — that command is the whole diagnostic, do not guess again.
3. **Then test the Hub deliberately, knowing `nyxus-panic` is the way out.**
   Confirm whether clicks inside it register at all. That single answer settles
   symptoms 7 and 8 and is the one thing that could not be determined from the
   image.
4. Click every station pill and confirm a deck appears — except **BIFROST**,
   which has none by design.

---

## 👽 URBAN-ALIEN THEME — WHERE IT ACTUALLY SHIPS (audit 2026-07-30)

> The owner asked, plainly: *"where does the urban-alien theme actually exist,
> where does it ship, and where was it never built?"* Audited against the
> **baked 07.29 squashfs**, not the repo. Headline: **four of the five surfaces
> were already right on that stick** — the theming work in `e5c381d1` (Jul 24)
> is real, is on `main`, and does ship. One surface was being undone at
> runtime. Nothing is stranded on an unmerged branch.

`e5c381d1 feat(theme): urban-alien on login/lock/screensaver + reworked
hypridle pipeline` is on `main` and every one of its ten files is present in
the 07.29 image (the only delta is `hyprlock.conf`, which differs solely by the
five `~/.local/bin` call sites fixed afterwards in `c0be97f2`).

| Surface | Verdict | Evidence from the 07.29 squashfs |
|---|---|---|
| **Login (greetd + regreet)** | **Ships, correct** | `nyxus-greeter` copies `/usr/share/backgrounds/nyxus/nyxus-urban-alien.png` → `/var/cache/regreet/nyxus-login-bg.png` on **every** greeter start; the art is present (3.6 MB); `/var/cache/regreet` + `/var/lib/greetd` are `drwxr-xr-x` **uid 950 = `greeter`** (the `4c7b52ca` bake fix worked — `unsquashfs` shows them as `brltty` only because this host's brltty happens to be uid 950); `regreet.css` `window` is a 0.35 scrim so the art reads through |
| **hypridle** | **Ships, correct** | shipped `hypridle.conf` is byte-identical to the NS source of truth (`7c5738b5`) — 45 s idle-glass, 300 s dim + urban-alien saver, 600 s `loginctl lock-session` + dpms off, 900 s suspend. `exec-once = hypridle` is in the shipped `hyprland.conf` (line 97). `brightnessctl` + `nyxus-idle-glass.sh` both ship |
| **Screensaver** | **Ships, correct** (staging hardened) | `nyxus-screensaver` execs `nyxus_screensaver.py` (not the retired matrix-rain saver) and pins `NYXUS_SCREENSAVER_WALL`; the payload ships in skel and is byte-identical across NS / skel / `/opt/nyxus-cache`; GTK4 + libadwaita + PyGObject all present; the four `app.nyxus.Screensaver` windowrules ship **and** `nyxus-hyprland-rules.conf` is `source=`d |
| **NYXUS Power** | **wlogout was BROKEN AT RUNTIME — fixed.** eww overlay ships art (scrim lightened since — see the owner-decisions section) | see below |
| **Backgrounds throughout** | **Ships** | desktop `wallpaper.conf` + `wallpaper.json` → urban-alien; `livewall.conf` is `LIVE=on` and the loop renders **from that still**; all 10 station wallpapers are alien art; lock/login/saver/wlogout all resolve to the same hero |

### 🔴 The one real regression — the power menu was un-theming itself

`nyxus-gen-backdrop` (STARFALL, Jul 11) rewrote the **first**
`background-image: url(...)` in `~/.config/wlogout/style.css`, whatever it
pointed at. When it was written the shipped stylesheet said
`background-image: none`, so the regex never matched and it was a harmless
no-op. On **2026-07-25** `af1acb85` gave wlogout the deliberate "URBAN-ALIEN
CANVAS" (`url("/usr/share/backgrounds/nyxus/nyxus-urban-alien.png")`) — which
became the first match. `nyxus-set-wallpaper` calls gen-backdrop on **every**
wallpaper change, and that includes the one at login and one per station
switch, so the crisp hero was replaced by a 42px-blurred / 0.42-brightness /
violet-tinted derivative within seconds of every boot, on every stick since.
**The stylesheet was correct in git the whole time.** Same shape as the
`~/.local/bin` bug: shipped correctly, defeated at runtime.

**Fixed:** the wlogout rewrite is now opt-in — only a url that is already
`…starfall-backdrop.png` (or the `BACKDROP_HOME` placeholder the code still
expects) gets refreshed. A pinned system wall is left alone.

### Also fixed this pass

- **The bake never staged `nyxus_screensaver.py`.** It staged only the retired
  `nyxus_matrix_saver.py`. The urban-alien saver shipped purely because
  `skel/.config/nyxus` is not in the bake's `rm -rf` list — so an edit to the
  **NS copy, the source of truth, would silently never have reached a stick.**
  Both savers are staged now.
- **`nyxus-screensaver` hard-coded one of three payload locations.** skel puts
  it in `~/.config/nyxus/`, `nyxus_install.sh` puts app python in `~/.nyxus/`
  (→ `/opt/nyxus`). One missing copy and the idle screen did nothing at all,
  silently, while hypridle reported success. It falls through all three now.
- **verify-profile gate `13ua`** (negative-tested) asserts the whole chain on
  both trees the bake reads: hero art present · hyprlock pinned to it ·
  greeter pins it · `customize_airootfs.sh` still provisions
  `/var/cache/regreet` · saver launcher + payload + bake staging ·
  hypridle launches the saver and locks · `exec-once = hypridle` ·
  wlogout keeps the canvas · **gen-backdrop cannot clobber a pinned hero** ·
  NS ↔ airootfs byte-identity for all seven files.

### 🎨 OWNER DECISIONS — ✅ ALL THREE ANSWERED AND IMPLEMENTED 2026-07-30

> The owner answered all three the same afternoon: move the login card off the
> alien, lighten the NYXUS · POWER scrim, give the standalone GTK power window
> the art. See **"👽 THE THREE OWNER DECISIONS — IMPLEMENTED"** below for what
> was done, how each was verified, and the screenshots. The three items are
> left below as written so the reasoning behind each decision is still legible.

1. **The greeter art and the greeter LAYOUT no longer match.**
   `regreet.css` pushes the login card to the right third
   (`margin-left: 720px`) and its own comment says that is *"so the alien art
   on the left stays visible"* — it was composed against the seed
   `/etc/greetd/nyxus-login-bg.png`, a purpose-built **1920×1080** wall with the
   alien on the LEFT and clean sky on the right. `e5c381d1` repointed the live
   background at `nyxus-urban-alien.png`, which is **1536×1024** with the alien
   dead CENTRE, cover-cropped to 16:9. The login card will land on top of the
   alien. Options: (a) keep urban-alien and move the card back toward centre or
   left; (b) point the greeter at `nyxus-login-wall.png` / the existing seed,
   both of which are composed for a right-side card; (c) crop a 16:9
   urban-alien variant with the subject on the left. **Not changed.**
2. **"NYXUS Power" is three different surfaces** and only one of them is
   wlogout:
   - `Super+Shift+E` → **wlogout** — the urban-alien hero canvas (the one that
     was being clobbered; now fixed).
   - `Super+Escape` → the **eww `powermenu` overlay**, the one actually
     labelled **"NYXUS · POWER"**. It *does* carry alien art —
     `assets/nyxus-hero-ufo-shop.png`, aliens spraying a UFO in a graffiti body
     shop — but behind a `rgba(5,1,13,0.76)`→`0.82` ink scrim, so roughly 20%
     of it survives. The Hub uses the same trick at `0.95`→`0.98`, i.e. all but
     invisible. If the owner wants the art to actually read, that is a scrim
     number, not missing work. **Not changed** — chrome opacity is exactly the
     kind of unrequested visual edit this file warns against.
   - `nyxus-powermenu` → `/opt/nyxus/nyxus_powermenu.py`, a standalone GTK4
     window reachable from the app menu. Flat `rgba(5,1,13,0.96)`, **no art at
     all**. Owner's call whether it should match.

### Noted, not touched

- `skel/.config/wlogout/nyxus-palette.css` is committed but wiped at bake and
  never restaged, so it does not ship. It is also unreferenced — wlogout's GTK
  CSS parser does not follow `@import` and `style.css` says so. Dead either way.
- `nyxus-scripts/nyxus-wlogout.tar.gz` still contains a **DARK MIRROR rev
  2026-05-07** monochrome stylesheet with `background-image: none !important`.
  The Jul-23 brand purge missed it. Nothing extracts it (only the api-server
  download route names it), but it would revert the canvas if anything ever did.
- `/usr/share/nyxus/wall-rotation.list` is now dead for its stated purpose —
  `nyxus-greeter` stopped reading it when the login background was pinned.
- `.power-btn` in `eww.css` loads `url("assets/fog-vessel.png")` from the
  **stylesheet**, which per the Jul-28 finding does not resolve; only inline
  `:style` urls do (which is why the powermenu backdrop above works). Cosmetic.
- **Nothing relevant is stranded on a branch.** Every unmerged commit touching
  these files is older Obsidian-Prism / copper / Eclipse / cream-era work that
  was deliberately purged. `babysit/land-open-prs` still holds the unrelated
  login/lock **anti-lockout recovery gate**.
- `BOOTSTRAP_VERSION` deliberately **not** bumped again — r16 was already
  bumped today, so installed systems will re-pull these two scripts anyway.

---

## 👽 THE THREE OWNER DECISIONS — IMPLEMENTED (2026-07-30, later)

All three of the items flagged above were answered by the owner and are now on
`main`. Screenshots for every one of them:
**`~/Pictures/nyxus-theme-2026-07-30/`**.

| # | Surface | Change | Verified |
|---|---|---|---|
| 1 | greeter login card | `margin-left` 720px → **1360px**, `margin-right` 120px → **40px**, plus a per-panel rescale in `nyxus-greeter` | **`regreet --demo`**, real binary, real CSS, real art, at 1920×1080 on the owner's display |
| 2 | eww `powermenu` (`Super+Escape`) | scrim `0.76/0.82` → **`0.52/0.60`** | **LIVE** on the owner's own eww daemon |
| 3 | `nyxus_powermenu.py` (app menu) | urban-alien wall behind the tiles, ramped scrim | **LIVE**, window launched and screenshotted on the owner's session |

### 1 · The login card was sitting on the alien

The old margins were written for art with the subject on the LEFT.
`nyxus-urban-alien.png` is centre-composed: measured on the actual
`fit = "Cover"` crop at 1920×1080 (source 1536×1024, ×1.25, 100 px off top and
bottom), the figure runs **x≈460 → x≈1550**, peace-sign hand to sneaker, and
the graffiti wordmark spans the whole top band. `margin-left: 720px` put the
card straight through the alien's legs and cut the figure in half. **That is
what the owner was seeing when he said the login screen looked old** — the
background was already correct on the 07.29 stick; the card was in the wrong
place on it.

`1360px / 40px` parks the card in the starfield right of the sneaker and below
the tail of the wordmark's S. The whole figure and the whole wordmark stay
visible.

**The greeter now rescales those margins for the detected panel.** GTK4 CSS has
no percentage margins and no `halign`, so the position can only be expressed in
absolute pixels — and absolute pixels tuned for 1920 wide would push the card
**off the right edge of a 1366×768 laptop, where the operator cannot type a
password.** That is a lockout, i.e. exactly what the rest of `nyxus-greeter`
exists to prevent. So before launching regreet it reads the panel's preferred
mode straight from `/sys/class/drm/*/modes` (no compositor is up yet),
recomputes the two margins, writes the sheet into the greeter-writable
`/var/cache/regreet/`, and passes it with `regreet -s`. Fully guarded — any
failure and regreet falls back to `/etc/greetd/regreet.css` unchanged.
Card centre lands at 0.845·W down to about 1600 wide, then clamps so the 520 px
card always fits (1024 wide → `480/24`, 1920 → `1360/40`, 3840 → `2729/80`).

**`greetd/regreet.css` and `regreet.toml` were never staged by the bake.** NS
carried a full copy of both and `build-iso.sh` installed neither, so the login
screen shipped whatever was committed under `airootfs/etc/greetd/` and an edit
to the source of truth reached no stick. They are staged now. (`regreet.toml`
had already silently drifted — a copyright line.)

**How this was verified, and its limit.** The greeter runs as the `greeter` user
under greetd *before* login, so it cannot be exercised on a running desktop and
nobody should try — restarting greetd risks the session. Instead:
`regreet --demo -c … -s …`, which is the real 0.5.0 binary the ISO also ships
(`greetd-regreet 0.5.0-1` in the squashfs pacman db — same version, confirmed),
rendering the real stylesheet over the real wall at the real 1920×1080. Three
candidate placements were rendered and compared before picking this one. This
is a faithful render of the layout; it is **not** proof of the greetd/cage/DRM
path, which only a boot can give.

### 2 · NYXUS · POWER scrim — 0.76/0.82 → 0.52/0.60

Roughly doubles what survives of the ufo-shop mural. Rendered at four values on
the owner's display (`0.76/0.82`, `0.52/0.60`, `0.44/0.52`, `0.36/0.44`) and
judged from the screenshots: at `0.36/0.44` the card's edges dissolve into the
mural and it stops reading as a panel; `0.52/0.60` is the point where the art is
fully legible and the card is still clearly a card.

**Label legibility does not depend on this number** and the measurement says so:
`.powermenu-root` and `.power-btn` stack their own fills over the scrim, so even
over the **brightest 1 %** of the art the white glyph holds 18.5:1 and the
grey label 11.5:1 (WCAG AA wants 4.5). Confirmed visually with a 1:1 crop of the
button row before and after — indistinguishable.

### 3 · The app-menu power window had no art

`nyxus_powermenu.py` now uses the same construction as `nyxus_screensaver.py` —
`Gtk.Overlay` + `Gtk.Picture` at `ContentFit.COVER` + a scrim box — resolving the
wall from `/usr/share/backgrounds/nyxus` → `~/.config/hypr/walls` →
`/opt/nyxus-cache/hypr-walls`, with `NYXUS_POWERMENU_WALL` to override. No wall,
no change: it falls back to the flat `rgba(5,1,13,0.96)` it always had.

Two things that only showed up by running it:

- **`overlay.set_measure_overlay(root, True)` is mandatory here.** The Picture is
  `set_can_shrink(True)` and therefore requests no size, so the overlay measured
  nothing, the window collapsed to `set_default_size(680, 540)`, and the outer
  tiles and the ESC hint were clipped off the edge. With the measure flag the
  window is 758×646 again, byte-for-byte the pre-change layout.
- **The scrim is ramped, not flat.** `ESC TO DISMISS` is 9 px `#6a6e78` sitting
  directly on the wall, and at a flat `0.55` it was unreadable over the nebula.
  A `text-shadow` outline was tried first and GTK did not carry it far enough.
  The gradient inks the top and bottom bands where the loose text lives and runs
  **lighter than 0.55** through the middle where only tiles and gutters are — so
  it shows more art, not less.

No colour was introduced or changed on any of the three surfaces. ALIEN NEON
holds; the only new values are ink alphas of the existing void `rgba(5,x,1x)`.

### Gate `13ub` — "visible", not just "pinned"

`13ua` proves the hero is *wired up*. It says nothing about whether you can see
it, and on this date the answer on all three surfaces was no. `13ub` asserts the
part `13ua` cannot: login-card `margin-left` ≥ 1200 **and** in the plain
one-declaration-per-line shape the greeter's rescale rewrites · the greeter
still generates that per-panel sheet · `build-iso.sh` stages `regreet.css` ·
NS ↔ airootfs identity for both greetd files · the powermenu scrim is not back
above 0.70 · `nyxus_powermenu.py` keeps both its wall and its
`set_measure_overlay`.

### ⚠ Two things the next agent should not repeat

- **eww 0.5.0 hot-reloads on config file change — writing `~/.config/eww/eww.yuck`
  IS an `eww reload`.** Proven here: with a window open, editing the yuck
  changed 93.5 % of its pixels with no `eww reload` command issued. So the
  "never `eww reload` the real daemon" rule in Section 7 must be read as "never
  *write* his live eww config while deck windows are up". Work in a throwaway
  `eww --config /tmp/<dir> daemon` instead — a separate config dir gets a
  separate socket and a separate daemon, and only the windows you open.
  (The live write here was done deliberately, at a moment when only the four
  bars were up; all four survived and the daemon count stayed at 1.)
- **A throwaway eww probe must be closed, and `eww … kill` is not enough.**
  An `eww --config … open <win>` client can outlive the daemon it started and
  keep its layer surface mapped. One was left up for ~10 minutes here and,
  being a fullscreen `overlay`-layer surface with no input region, it swallowed
  every pointer event on the desktop — which a second agent then had to
  diagnose from scratch (it is the incident behind gate `13ai`). Kill the
  `eww … open` **process by PID** and confirm with `hyprctl layers` that the
  namespace is gone.

### Fidelity caveat on everything above

This box is **Hyprland 0.55.4**; the ISO ships **0.56.1**. `~/.local/bin` is
fully populated here and ships **EMPTY**. Live confirmation on this machine is
strong evidence for **visual / CSS / widget** questions — which is all three of
these items — and is **not** evidence for path resolution or
compositor-version-specific behaviour. That exact false confidence is what
produced the `~/.local/bin` bug fixed earlier the same day. Anything in the
second category gets checked against the extracted squashfs at
`/home/cosmic/iso-inspect/airootfs.sfs`, which is how the regreet version match
above was established.

---

## 🎨 URBAN-ALIEN ART-STYLE AUDIT (2026-07-30, evening) — ⛔ DECISION NEEDED

> Owner: *"I want all urban theme alien images to be like those, that same
> style urban alien and same style picture… and everything else, for all urban
> alien images."* The body-shop mural behind NYXUS · POWER
> (`eww/assets/nyxus-hero-ufo-shop.png`) is the reference he likes.
> **Assessment only — no artwork was generated or restyled.** Boards:
> `~/Pictures/nyxus-style-audit-2026-07-30/`.

### The reference style, measured (this is the spec)

Not impressions — numbers, from `nyxus-hero-ufo-shop.png`:

| property | reference value |
|---|---|
| mean luma | **0.086** (median 0.061) |
| frame below luma 0.10 | **70%** |
| frame above luma 0.65 | **0.2%** — there is essentially no white in it |
| mean saturation (non-black px) | **0.79** |
| hue weight, sat×val weighted | blue **50%** · violet **30%** · magenta **16%** · rose **4%** |
| off-arc hue weight (red/orange/yellow/green/cyan) | **0.1%** |

So the style is: **a near-black night frame, one narrow hue arc from blue
through violet to magenta, extreme saturation inside that arc, and no white.**
Subject is aliens in a lived-in urban night environment — signage, wet
reflective ground, a saucer — rendered semi-photographic with neon rim light.
No giant wordmark.

**Note the spec is narrower than the palette.** ALIEN NEON legitimately
contains `#39ff14` green, `#ff8a1e` orange, `#ffe600` yellow, `#2bd2ff` cyan —
those are *UI accent* colours. The reference *artwork* uses effectively none of
them. Do not "fix" a wall by grading brand colours out of it, and do not treat
a green pill in a bar as off-style.

### Scoring every shipped image against that spec

`off-arc%` = colour weight outside blue→rose. `TVD` = hue-histogram distance
from the reference (0 = identical).

| family | count | verdict |
|---|---|---|
| `hypr-walls/rotation/nyxus-rot-*.png` | 28 | **23 on-spec, 4 marginal, 1 dead.** off-arc ≈ 0.0%, TVD 0.08–0.35, dark 50–97%. **This set already IS the style.** |
| `eww/assets/nyxus-hero-crew-meet.png` | 1 | **On-spec, TVD 0.11** — the reference's closest sibling, same world, different scene |
| `nyxus-urban-alien` / `-desktop-hero` | 2 | on-spec by numbers (off-arc 4–7%, TVD 0.26) but a **different sub-genre**: alien posed over a giant NYXUS wordmark, brighter (luma 0.14–0.17, dark 46–56%) |
| `nyxus-login-wall` | 1 | same wordmark sub-genre, off-arc 11%, TVD 0.44 — the cyan wordmark is the deviation |
| **`nyxus-graffiti-01…24`** | **24** | **ALL OFF-STYLE, badly.** Rainbow paint-splatter stock art. off-arc 16–74%, TVD 0.51–0.94. Six are **>55% white**. And they are **192×108 to 300×168 pixels** |
| `nyxus-graffiti-space` | 1 | off-arc 30%, TVD 0.61 — bright pop-art sticker collage, a different universe |
| `nyxus-login-stars` · `nyxus-demon` · `nyxus-hyprlock-eye` | 3 | off-arc 28–85%. A B&W galaxy, a horned red-eyed demon (not alien, not urban), a stone eye |
| `nyxus-bg-01…16` | 16 | not walls at all — neon splatter **UI strips** (586×116, 573×69 …). Only the api download route and `manifest.tsv` reference them. Out of scope, but they are off-spec if ever surfaced |
| hacker-mode `-a` / `-b` / `-mono` | 3 | deliberately desaturated; judged against the mono treatment, not this spec |

### 🔴 The finding that matters

**The 24 `nyxus-graffiti-*` murals are the incoherence.** They are:

- used as **5 of the 10 station wallpapers** (WAVE, CORE, MESH, SCRIBE, BIFROST
  in `stations.json`), and
- `nyxus_chrome._IMAGE_POOL` — i.e. the **signature background of every NYXUS
  GTK app**, picked per-app by hash.

They cannot be colour-graded onto the spec. Hue-rotating rainbow splatter to
violet produces violet splatter, not an urban-alien scene — and at 192×108
there is nothing to upscale to a 1920×1080 station wall (a 6.4× blow-up).
**These need new artwork.**

**`nyxus-graffiti-02.png` ships a visible "VectorStock" watermark and the URL
`vectorstock.com/62536757` baked into the image.** That is a licensing problem
on the ISO, not just a style problem. It is one of the 24. See board `F-`.

### ✅ Fixed this pass (staging, not art)

**`nyxus-urban-alien-mono.png` had no source the bake could reach.** It is the
`unified_wallpaper` in `stations-hacker.json` — hacker mode puts it on **all ten
stations**. The wallpaper staging glob is `install "${NS}"/nyxus-*.png`, which
only sees the ROOT of `nyxus-scripts`; the mono wall lived one level down in
`nyxus-scripts/hypr-walls/`. Exactly the bug the 2026-07-29 fix patched for
`hypr-walls/rotation/`, still live for this file. It shipped anyway because
`usr/share/backgrounds/nyxus` is not in the wipe list and a committed copy sat
there — so hacker mode *looked* fine while the art had no source of truth, and
`skel/.config/hypr/walls`, which IS wiped, simply lost it. Canonical copy is now
at the NS root.

**Gate `13uc`** (negative-tested) asserts the general property: every wallpaper
name any shipped config references — `stations.json`, `stations-hacker.json`,
`wallpaper.json`, `wall-rotation.list`, 38 names — must resolve to a file one of
the bake's staging globs actually installs. It distinguishes "exists in
`hypr-walls/` but unstaged" from "no source at all" and says which.

### ⚠ Aspect-ratio trap — read before commissioning anything

Every on-style image in this project is **1536×1024, i.e. 3:2**. Every surface
that shows one — greeter `fit = "Cover"`, hyprlock, the screensaver, wlogout,
the eww backdrops at `background-size: cover` — crops it to **16:9**. At
1920×1080 that scales by 1.25 and throws away the top and bottom 100 scaled px:
**15.6% of the authored image is never seen**, and the surviving band is source
rows 80–944 of 1024. This is precisely what put the login card on the alien
earlier today.

**New art should be authored 16:9 (1920×1080 minimum, 2560×1440 preferred), or
composed 3:2 with a deliberate 16% dead band top and bottom.**

### 🛑 WHAT NEEDS NEW ART — owner decision, nothing invented

There is **no tool in this tree that can produce scene artwork.** The three
generators under `eww/scripts/` (`gen-graffiti-assets.py`,
`gen-cosmic-flyout-assets.py`, `gen-starlight-assets.py`) are procedural PIL
texture makers — spray strips, bar underlays, starfields. They cannot draw an
alien in a body shop. The existing murals came from an external image
generator. So this is a commissioning decision, not a scripting task.

| # | slot | needs | size | why |
|---|---|---|---|---|
| 1 | **24 app / station murals** replacing `nyxus-graffiti-01…24` | new art | **1920×1080** | wrong style, 192×108–300×168, one carries a stock watermark |
| 2 | `nyxus-graffiti-space` (PULSE station) | new art or repoint | 1920×1080 | bright pop-art collage, off-spec at 30% off-arc |
| 3 | `nyxus-demon` (in `wall-rotation.list`) | drop or replace | 1920×1080 | a demon; not alien, not urban |
| 4 | `nyxus-login-stars` | drop or replace | 1920×1080 | monochrome galaxy, no subject |
| 5 | `nyxus-rot-black-void` | drop | — | 99.8% pure black, one star; a dead slot in the rotation |

**Cheaper alternative worth considering before commissioning 24 images:** the
28-image rotation set is already on-spec and already 1536×1024. Repointing the
five graffiti stations and `nyxus_chrome._IMAGE_POOL` at the rotation set is a
**config change, not new art**, and would make the whole desktop coherent
immediately. It changes which mural ~20 app windows wear, so it is his call —
flagged, not done.

---

## WHERE WE STAND — 2026-07-29 · ON MAIN · REBAKE REQUIRED

> **PR #77–#81 are all on `main`.** Next step is a clean rebake — none of this
> is in a stick yet.
>
> - **#77 / #80** — silent bake/wallpaper/PATH bugs; reactive bus finally
>   started (`nyxus-sense` → mood → `nyxus-threatd`); unsourced hypr shards fixed
> - **#78 / #81** — all station decks incl. **MESH**; CAVA borders; dunst
>   hacker flip; pill font fix
> - **#79** — `BOOTSTRAP_VERSION` → `2026.07.29-r15-station-decks`;
>   `nyxus-hacker-mode` self-installs the btop theme (skel / cache / inline
>   heredoc) so the first toggle always works

### ⚠ SILENT FAILURES LANDED VIA PR #77 (do not rediscover)

These all shipped looking correct and never threw. Re-read before touching
wallpaper / bake wipe / PATH / eww handlers:

1. **Per-station wallpapers never changed** — matrices ship literal `~/...`
   paths; bash does not tilde-expand variable contents. Fixed in
   `nyxus-workspace-wallpaperd` + `nyxus-set-wallpaper` (also searches
   `walls/rotation/`).
2. **`env = PATH,/home/cosmic/...`** clobbered PATH on every login for a user
   that does not exist on the stick. Removed; session entrypoint already
   prepends `${HOME}/.local/bin`. Do **not** reintroduce a hardcoded PATH env.
3. **Bake wipe gaps (again)** — `rm -rf skel/.config/eww` then whitelist
   dropped `cava.conf`, `_nyxus_accent.scss`, `nyxus-palette.css` → bar
   visualizer + CAVA_BASS dead on every stick. Rotation wallpapers under
   `NS/hypr-walls/rotation/` were never staged (27/32 missing). Catch-all
   + staging added; gates **13c-eww** / **13c-rot** assert it.
4. **Dead eww controls** — undefined `${EWW_CMD}`, hub toggle wrote the wrong
   flag file, hotkeys targeted `mission-control`/`quick-settings` (windows are
   `mission`/`quicksettings`), focusmode closed `bar_top` (real name
   `bar-top`), Settings cheatsheet called a missing binary. Eight unused
   defpoll/deflisten producers removed (APP_RAIL every 0.5s, etc.).
5. **Off-canon hex** — eww `$neon-blue` was `#4d9fff`; canon is `#2bd2ff`.

### ✅ DONE this session (Jul 29)

#### Station rail — names instead of numbers
- `station_pill` now shows `st.name` (OPS/FORGE/GHOST/PULSE/WAVE/CORE/MESH/
  SCRIBE/BIFROST/ARSENAL) with the `ws-word` class → same Permanent Marker
  font + per-hue neon glow as HOME and START. Zero visual style change.
- Companion half-station Tifinagh glyphs **removed from the rail** — they
  were not rendering reliably and the owner was uncertain about them.
  Companion stations (RELAY/ANVIL/TRACE/etc.) still reachable via
  `Super+Alt+N` and tooltip. Widget definition left in eww.yuck for future use.

#### All 10 stations now have eww decks (wired into nyxus-home-deck)
Previously only HOME/START/GHOST/FORGE/LAB had decks. Six were bare workspaces.

| Station | Deck |
|---|---|
| **OPS (1)** | CPU/RAM/GPU/TEMP vitals + sparklines, load/fan/swap, network throughput, quick-launch grid (btop/journal/dmesg/ports/procs/disk/cron) |
| **PULSE (4)** | Network status, weather + moon, time/date, quick-links hub (browser/email/Discord/GitHub/YouTube/Reddit/Calendar/Maps) |
| **WAVE (5)** | Full-width CAVA hero visualizer (orange glow), large now-playing text, bass-reactive play button, transport, volume/mic panel |
| **CORE (6)** | Disk usage (/, ~, ~/Projects) + RAM/swap, directory quick-nav bookmarks |
| **MESH (7)** | Network ops: throughput + SSID, connections (ss), NOC/HoneyHive status, toolkit grid (sharknoc/iftop/nmap/wireshark/…) |
| **SCRIBE (8)** | Writing focus: clock + moon, scrollable scratchpad, notepad/stickies/vim toolkit |
| **ARSENAL (10)** | Security console mosaic — 2 large hero tiles (CIPHER + RedForge), 3 medium tiles (Forge/GSL/Trainer), live port-status dots, 10s refresh |

Data feeds:
- `eww/scripts/disk-info.sh` — probes /, ~, ~/Projects with df -h
- `eww/scripts/arsenal-feed.sh` — probes GowskiNet ports with `nc -z -w1`
- `eww/scripts/mesh-feed.sh` — `ss -s` TCP/UDP, listening, foreign established

`nyxus-home-deck` watcher covers OPS/PULSE/WAVE/CORE/MESH/SCRIBE/ARSENAL
(+ HOME/START/GHOST/FORGE/LAB already present).

#### CAVA bass-reactive Hyprland border animation
`cava.sh` `push_bass()` now also adjusts `borderangle` animation speed across
4 tiers (quiet 240s → medium 180s → loud 110s → peak 60s). Calls `hyprctl`
only on tier transitions, never per-frame. `hacker_off` resets to 240s.

**Trap:** `_CAVA_LAST_TIER` must persist within the cava pipe's subshell
(not the outer restart loop). It's initialized before `while :;` so it
resets cleanly when cava dies and restarts.

#### Hacker mode — complete (btop + dunst)
- `nyxus-hacker.theme` (new): 42-key btop theme. Black structure, white data,
  `#ff2d55` red as the ONLY surviving hue. All graph gradients: grey → white
  → red at peak. Stored at `skel/.config/btop/themes/nyxus-hacker.theme`.
- `nyxus-hacker-mode on`: **self-installs** the theme (skel → cache → inline
  heredoc) then `sed`s `color_theme` to `nyxus-hacker`; records previous
  theme in STATE. Also flips dunst urgency frame colors to mono hairlines
  and `pkill -USR1 dunst`.
- `nyxus-hacker-mode off`: restores btop theme + dunst frames; resets
  border animation to 240s.

#### Three-surface sync — all done
Every file landed on all three surfaces the bake reads:
- `artifacts/api-server/nyxus-scripts/` (NS, source of truth)
- `iso-builder/nyx-profile/airootfs/etc/skel/.config/eww/`
- `iso-builder/nyx-profile/airootfs/usr/local/bin/`

### ⚠ ROUND 2 — THE BAKE WAS *REVERTING* COMMITTED FIXES (Jul 29, follow-up)

Continuation of the same audit. New class of bug: not just files lost at bake, but
**committed fixes actively undone** because they were applied to the copy the bake
does not read.

1. **Polkit `vendor_url` — the Jul-23 Replit purge was being reverted on every
   bake.** That pass edited `airootfs/usr/share/polkit-1/actions/*` but NOT the
   `nyxus-scripts/polkit-policies/*` copies the bake installs from, so every ISO
   since re-shipped `https://nyxus-core.replit.app` in the loginscreen, plymouth
   and sound policies (plus `nyxus-welcome.policy`). Fixed at the source.
   **Lesson: fixing `airootfs` alone is not fixing anything for most paths.**

2. **The greetd SESSION entry shipped as a launchable app.** The wave-4 loop globs
   every `nyxus-*.desktop` into `usr/share/applications`, so `nyxus-hyprland.desktop`
   appeared in the app menu — clicking it tries to start a **nested compositor**
   inside the running session. The loop now skips entries carrying `DesktopNames=`,
   which is exactly the distinction `verify-profile`'s parity gate already makes.
   nyxus-scripts was ALSO missing `DesktopNames=Hyprland`, so the bake was dropping
   it from the real session entry in `wayland-sessions/`.

3. **Five buttons still opened the app that was deleted for trapping the desktop.**
   `eww.yuck`'s own comments say the START panel "replac[ed] the nyxus-start GTK4
   app" because it "sat on the OVERLAY layer and could be neither closed nor moved
   when it lost keyboard focus" — yet both brand buttons, the app-rail entry, the
   NYXUS Start tile and a deck button still ran `nyxus-start`. They now dispatch to
   the **START station**.

4. **Stale duplicates deleted:** `nyxus-scripts/com.nyxus.parental.policy` (stale
   copy of the `polkit-policies/` one, and the only file in the repo with a
   malformed DTD — `PolicyKit/1/` instead of `1.0/`), two stale `nyxus-start` trees
   (`skel/.config/nyxus/` and `skel/.nyxus/`, the latter wiped+symlinked at bake
   anyway), and a vim `.save` dropping under `opt/arsenal`.

### 📕 THE DOCS WERE TELLING AGENTS TO USE THE PURGED PALETTE

`THEME.md` was titled **DARK MIRROR** and presented the **purged** palette as
current — section 3 was literally headed *"Accent tokens (LIVE — follow the
wallpaper)"* listing `#7949f2` / `#ff2667` / `#ffb026` / `#26ffb7`, claimed the
active preset was `wallpaper`, and advertised eight presets that were **deleted**
from `accent.json`. `DESIGN_CONTRACT.md` §4 — the "single quality bar" — gave the
accent pair as `#a06bff` / `#3ad8ff`.

**Any agent following either would have reintroduced banned colour.** Both are now
rewritten from `nyxus_palette.py` + `accent.json` (so the values are the real ones)
and each carries an explicit banned-hex list. Two factual errors fixed en route:
`WHITE_OFF` was documented `#e8edf5` when the constant is `#eef2fa`, and the HUD
void fills did not match `HUD_VOID` / `HUD_CARD_BG`.

Also corrected in `THEME.md` §11: station pills were listed `OP/FG/GH/.../BL/ED`
(BLAST and EDGE were renamed BIFROST/ARSENAL on 2026-07-27), and the HOME dashboard
was described as the GTK app on `name:0` — that app is **disabled** (rendered an
empty window), the eww `home-deck` replaced it, and `name:0` was renamed because a
numeric name resolves into Hyprland's SPECIAL range and was never visible.

Brand strings purged from shipped surfaces: `gen-graffiti-assets.py` was stamping
the words **"dark mirror" into the generated graffiti art**; nyxus-web showed
"DARK MIRROR" in the Settings window, notifications, panel flyout, build manifest
and three page headers; rofi configs, `nyxus-prism-pulse.sh` and
`gen-cosmic-flyout-assets.py` carried "Obsidian Prism". Historical references that
*describe* the purge (the ALIEN_NEON audit docs, `legacy-visuals.md`) and the
palette ban-list comments are deliberately left alone.

> **Do not recompile `eww.css` casually.** It has drifted **~3500 lines** from
> `eww.scss.source`. Regenerating buries any real change in unrelated churn and
> risks the live-verified bar styling. Patch it surgically until someone reconciles
> it on purpose.

### ⚡ ROUND 3 — THE REACTIVE LAYER WAS NEVER STARTED (Jul 29)

**`nyxus-sense` is the state bus the whole reactive layer reads, and NOTHING in
the tree launched it.** No systemd unit, no exec-once, no script. On a real boot:

- `~/.config/nyxus/sense.json` was never written
- `nyxus-mood` never ran, so it never pushed `eww update SENSE=...`
- the bars' `SENSE` defvar sat on its built-in default **forever** - which is why
  the mood glow never changed and the wordmark/clock classes were static
- `nyxus-whispers` and `nyxus-graffiti-wall` polled a file that did not exist

The consumers were fine the whole time. **The producer was simply never
launched.** Only `nyxus-pulsed` was, via `nyxus-living on quiet` in
`nyxus-signature.conf`. `nyxus-reactive.conf` now autostarts sense -> mood ->
threatd, staggered off the critical path, each pidfile-guarded.

#### Four hypr shards shipped UNSOURCED (conf.d is not auto-globbed)

Two of them say *"sourced from hyprland.conf"* in their own header. Between them
**9 keybinds and 24 window rules were dead on arrival**:

| Shard | What was dead |
|---|---|
| `nyxus-reactive.conf` | Machine Whispers, SUPERNOVA, Graffiti Memory Wall - **three of the four headline reactive features had no working keybind** |
| `nyxus-arsenal-apps.conf` | 19 window rules that float/size/park the native security tools. **THIRD time this shard fell through** - it was the W6 fix on 2026-07-24 and it regressed |
| `nyxus-hyprland-aurora.conf` | X-RAY PEEK + 3 other binds |
| `nyxus-cometfire.conf` | 2 binds + 5 window rules |

Verified before enabling: **zero chord collisions**, 156 binds active, 17 shards
sourced. `nyxus-safemode.conf` stays unsourced - standalone recovery profile.

**One real duplicate found doing that:** `Super+Alt+0` was bound BOTH to
`workspace name:RANGE` and to the zoom-lens reset. hyprland.conf binds
`Super+Alt+1..0` to the ten companions as a set, and the flair shard is sourced
afterwards, so the lens won and **companion 10 was the one station the keyboard
could not reach**. Lens reset moved to `Super+Alt+BackSpace`.

#### The threat signal (new) - `nyxus-threatd`

Turns the REAL security probes into desktop state. It **reimplements no probe**:
`ghost-feed.py` already probes cowrie/journalctl/docker and states that every
number is real, so threatd invokes it and derives a level. One place knows how to
read those sources.

**Two scoring buckets, on purpose.** A honeypot exists to be attacked, so decoy
traffic is the system *working* - loud, informative, not an emergency - and it is
**capped so it can never on its own exceed `alert`**. Only host-affecting signals
(auth failures on the real host, defence daemons down, failed units) reach
`breach`. Otherwise the desktop goes red during normal operation, and a console
that cries wolf gets ignored as fast as one that lies. Measured: 300 honeypot
hits/hr + 30 probes = `alert`; that **plus two defence daemons down = `breach`**.
Being attacked *while blind* is the only non-panic path to breach, which is
exactly the Bifrost scenario.

**BLINDNESS IS A STATE, NOT A DEFAULT.** Quiet and blind must never render the
same. `blind` is true when the feed cannot be read; sense treats a `threat.json`
older than 90s as UNKNOWN rather than republishing a stale `calm`; the eww defvar
**defaults to blind**; and the GHOST pill draws blind as a **dashed cyan rim**.

Rendered on the **GHOST pill only** (station 3 is the security console; a colour
on every pill would mean nothing). The class is APPENDED, so a calm desktop looks
exactly as it does today. Canon ramp only: watch `#ffe600`, alert `#ff8a1e`,
breach `#ff2d55`.

> **Two traps hit and avoided - read before touching this:**
> 1. **jq's `//` treats `false` as empty**, so `.threat.blind // true` returned
>    TRUE even when the bus said false - inverting the one field that exists to
>    prevent a misreport. Caught by testing. Use an explicit null check.
> 2. **`+` string concat appears nowhere else in `eww.yuck`**, so it is
>    unverified against the eww the ISO ships and a bad simplexpr takes out the
>    whole rail. Use interpolation. Same for a nested `${}` inside a ternary
>    branch (zero existing uses) - flatten instead.
>
> Also: the threat CSS **must** sit after the LAST `.ws-pill` rule. `eww.css`
> defines `.ws-pill` more than once and the threat class is appended, so equal
> specificity means an earlier rule is silently dead. Gate 13y checks the line
> numbers.

**Gate 13y** asserts every link: shard sourced, each producer autostarted AND
parsing, threatd pushes, eww declares, a widget consumes, all four classes have
CSS, the CSS ordering, and the jq null-check. Negative-tested.

#### Swept for other "built but never wired" cases - clean

Every `nyxus-*` in `/usr/local/bin` was checked for callers. Five have none:
`nyxus-battery` and `nyxus-netusage` are launchable from their `.desktop`
entries; `nyxus-setup-apps`, `nyxus-store-install` and `nyxus-oath-register` are
CLI-only helpers by design. No orphaned apps.

Observation, not a bug: battery is on the **HOME deck** (`dcard_power`), not on
the persistent bar - the redesigned bars dropped the pill row. Owner's call.


### 🧾 STILL OPEN after this audit (found, deliberately not fixed)

- ~31 unused bar-pill widgets from the pre-redesign bar (dead code, zero runtime cost)
- 4 windows nothing opens: `cheatsheet` (superseded by `hotkey-cheatsheet`),
  `quicksettings-daemon`, `hotkey-recorder`, `dock-reveal`
- `/etc/nyxus/nyxus.conf` still points `resync_base` / `manifest_url` at Replit —
  it is **not** nyxus-scripts-managed, so the bake does not touch it
- `attached_assets/` holds ~40 unreferenced files >2MB (design scratch)


### 🔜 NEXT
1. **Rebake** from clean idle `main` (installer + #77/#78 all need a stick)
2. **Verify on stick:**
   - station wallpapers change on switch (tilde expand)
   - cava bar visualizer + boombox bass react (cava.conf staged)
   - rotation set has all 32 images
   - each station deck appears; hacker mode flips btop; bass speeds borders
   - START search / hub ALL APPS / Super+M / Super+A / focusmode top bar
3. Do **not** merge `local-stash-work` — parked bake.log / `.env` / db junk

### ⚠️ Things NOT done (out of scope per owner)
- Bifrost / jeTT — explicitly off-limits this session
- 3D saucer/boombox asset rendering (needs Blender on builder box)
- Boombox v2 geometry conflict (needs owner decision on 3 options in HANDOFF)
- Left/right 3D dock rail integration (models in Downloads, not started)

---

## WHERE WE STAND — 2026-07-28 · REBAKE REQUIRED (the 07.27 stick is broken)

> The `nyxus-2026.07.27` ISO booted with real faults. All root causes are found
> and fixed on `main`; **none of the fixes are in a baked ISO yet.**

### ⛔ Why the 2026.07.27 ISO booted broken — read before touching the bake

**The bake wipes `skel/.config/hypr` and repopulates it from
`artifacts/api-server/nyxus-scripts` (NS) via a hand-maintained whitelist.**
Committing a shard in `airootfs` is NOT enough to ship it. Three fell through:

| Shard | State in the shipped ISO | Symptom the owner saw |
|---|---|---|
| `nyxus-consoles.conf` | **absent** (not in NS, not in the whitelist) | Hyprland error banner: `source= ... found no match` at **line 592** |
| `nyxus-stations.conf` | **Jul 17 revision** | no `name:HOME` / `name:START` / `name:LAB`; 9=BLAST, 10=EDGE. Rail pills rendered (eww was current) but switched to workspaces the compositor never knew |
| `nyxus-hyprland-layerblur.conf` | **Jul 26 revision** | the five station decks shipped with no `blur`/`ignore_alpha`, falling through to the `^(nyxus.*)$` catch-all |

This is the **third** time this exact bug shipped (`nyxus-arsenal-apps.conf`,
Jul 24 W6). So `verify-profile.sh` gained **gate 13w**, which does *not* read
the whitelist — it derives the requirement from `hyprland.conf` itself and
fails if the bake cannot satisfy it. Adding a shard needs no edit there.

**⏱ The 102-second wait between splash and the login screen** —
`nyxus-firstboot.service` was `Type=oneshot` + `WantedBy=multi-user.target`, so
`multi-user.target` could not complete until ExecStart *returned*, and
`graphical.target` is `Requires`+`After multi-user.target` with greetd behind
it. Fragment `06-honeypot-stack.sh` does a **~1 GB `docker load`** off the USB
plus `docker compose up -d` on **ten containers** — all of it in front of the
greeter. `build-iso.sh` had already raised `TimeoutStartSec` to 900s for that
work; nobody noticed the budget sat on the critical path to login. It also ran
on *every* live boot (nothing pre-creates the marker, and on live media it
lands in the tmpfs overlay). Now `Type=simple` + a live-media guard.

**🧨 No installer on either stick.** `pkglist.x86_64.txt` inside both the 07.26
and 07.27 ISOs contains **no calamares, no yay, no howdy, no pamtester**. The
AUR fix (`6b264be1`) landed at 23:27; the ISO finished at 23:36, long past that
stage. Committed, needs a rebake. **Verify after the next bake.**

**⚠ Hyprland VERSION SKEW — this invalidates "verified live".** The ISO ships
**0.56.1**; this builder box runs **0.55.4**. The bake pulls Hyprland from the
Arch repos at bake time, so config is developed and "verified" against a
compositor that is *not* the one that boots. That is why `hyprctl configerrors`
is clean here and the ISO showed a banner. **Either pin Hyprland in the ISO
(the `[nyxus-local]` + `repo-add` mechanism already used for Kage-Ryu — and
`hyprland-0.56.1-2` is already in the pacman cache) or bring this box up to the
ISO's version. Until one of those happens, live verification means little.**

**☠️ hyprlang is being REMOVED in Hyprland 0.57.** Lua configs landed in 0.55
and the old `.conf` syntax is supported for "1-2 releases" after that. NYXUS is
`hyprland.conf` + 17 hyprlang shards, so when Arch ships 0.57 a fresh bake
produces an ISO where **the entire desktop config stops loading**. Migration is
big-bang (if `hyprland.lua` exists, `hyprland.conf` is never read) and the hard
part is that three shards are *generated at runtime* — `nyxus-stations.conf`
(nyxus-hacker-mode), `nyxus-freeform.conf` (nyxus-freeform),
`nyxus-monitors.conf` (Settings). **Owner decision (2026-07-28): do NOT migrate
yet — pin the version first, stabilise the build, migrate on a branch after
0.57 actually ships.** `hyprlock`/`hypridle` keep hyprlang indefinitely, so
only the compositor entry point moves.

### 🕶 HACKER MODE — real mode flip, now MONOCHROME (2026-07-28)

Owner's brief: **near-black with very little white — thin white lines, just
enough to see what you are doing.** One colour survives: `#ff2d55` for genuine
danger, so a red thing is the *only* colour on screen. The earlier
matrix-green pass is superseded (kept in history at `cd45a2ac`).

`.nyx-hacker` is wired onto all **nine** surface roots (4 bar layouts + 5 deck
roots). Layered blacks: `#000000` root, `#08080a` cards, `1px
rgba(255,255,255,0.14)` hairlines, text at `.92/.72/.44/.26`. No glow —
emphasis is brightness only.

**Four separate bugs were why it "never felt finished":**
1. **The background never flipped.** `workspaces.json` carried a **literal
   `~`** (`wall_dir` is `~/.config/hypr/walls`), and the wallpaper daemon
   passes that to `nyxus-set-wallpaper` *as a variable* — bash does not expand
   a tilde in a variable. Every lookup missed, the daemon silently kept the
   previous image. `nyxus-sync-stations` + `sync_workspaces` now emit
   **absolute** paths.
2. `matrix_wallpaper` never searched **`walls/rotation/`**, where every
   `nyxus-rot-*.png` actually lives — 8 of 10 station wallpapers plus the
   hacker `unified_wallpaper` failed to resolve. Path list extended.
3. **The green halo was the window DROP SHADOW**, not the border.
   `decoration:shadow:color` is `#39ff14` at range 42 in normal mode and
   hacker mode never touched it (`col.active_border` was already monochrome —
   `getoption` proved it). Now set + restored with the borders.
4. **GTK3 CSS has no `filter: grayscale()`**, and the saucer/boombox/notif art
   paths are set via **inline `:style`**, which outranks any stylesheet rule.
   So `*-mono.png` variants ship and the paths are swapped **conditionally in
   eww.yuck**, not in CSS.

Background is `nyxus-urban-alien-mono.png` — the same alien graffiti art,
greyscaled and gamma-pulled (mean luma 33, 4% highlights). Verified live:
wallpaper sampled **R=32 G=32 B=32**.

**Station identity must never differ between the matrices.** `stations-hacker.json`
still had 9=BLAST/10=EDGE, and it ships from a **third** tree
(`artifacts/nyxus-config`, not skel) — so fixing only the skel copy was
silently discarded at bake. Gate 13w now asserts both trees match and that
normal/hacker names are identical.

**Also fixed: hacker mode used to destroy the named stations.**
`nyxus-stations.conf` is regenerated from scratch on every flip and its
generator only emits the numbered matrix, so HOME/START/LAB and the Bifrost
window pins — hand-appended to a generated file — were deleted on the first
toggle. They now live in **`nyxus-stations-named.conf`**, which no generator
writes. Verified: a full on→off cycle leaves all three intact.

### 👽 SAUCER ALIEN + hacker glow + boombox art (2026-07-28 late)

**Saucer alien — DONE.** An urban alien in a hoodie and snapback throwing a
peace sign, white outline only, strikes into the saucer's transparent cockpit
window like lightning and is gone. `GLITCH.alien` in
`eww/scripts/random-glow.sh` fires at **6% per 7s poll** (~once every two
minutes) — deliberately far rarer than the other glitches, because the point is
that it catches you off guard. `@keyframes nyxus-alien-strike` uses
`steps(1, end)` so GTK cannot interpolate the opacity jumps into a crossfade.

Two traps worth remembering:
- **A relative `url()` in `eww.css` does not resolve.** The box rendered
  (proved with a debug border: 199×61 at x=859 y=972, exactly the cockpit) but
  the image never painted. `saucer_base` loads its band art from an inline
  `:style`, and that works — so the alien's `background-image` lives in the
  inline style too. Only the flicker is in CSS.
- The strike **darkens the cockpit** (`rgba(0,0,0,0.86)`), otherwise the
  wallpaper showing through the transparent window drowns a white outline. That
  plate is **elliptical and inset** (`border-radius: 96px/29px`, 8px side
  margins) — a square plate spills past the oval and looks exactly like the
  rectangular "shadow box" this build has fought twice.

**Hacker glow — DONE.** Owner: *"bright white and/or glow to the bars and some
of the saucer so it shows more."* The three art PNGs now carry a **baked 3px
white outline** (CSS cannot stroke a PNG), and hacker mode adds white text-glow
on the clock, rails, ticker and metric values, with brighter structural
hairlines (0.14 → 0.26/0.30). The danger red is the only colour allowed to glow.

**⚠ BOOMBOX v2 — ART DONE, NOT WIRED (geometry conflict, owner decision).**
New 1980s boombox exists at `eww/assets/nyxus-boombox-band-v2.png` (+ `-mono`):
twin speaker grilles, carry handle, transport row, sliders, alien glyphs, ALIEN
NEON violet/magenta, and an **empty transparent display window** like the
saucer's cockpit.

It is **not wired in** because of a measured conflict — do NOT guess a margin
here, that drifted wrong twice before:

| | |
|---|---|
| Art (trimmed) | **1516×891**, aspect **1.70:1** |
| Display window | **528×286**, `fill=1.00` (a true rectangle) |
| Window box | x=492..1020, y=356..642 |
| Window as fraction of art | width **0.3483**, height **0.3210** |
| Window centre offset | dx **−0.0013**, dy **+0.0600** of art |
| Band slot today | 551×150 for the saucer = **3.67:1** |

So: undistorted at 150px tall the boombox is only **255px wide** (much smaller
than the saucer) and its window shrinks to **89×48**, while the current music
face was laid out for **146×100**. Matching the saucer's width needs a **324px**
tall bar — 30% of a 1080p screen. `bar-bottom` is declared `74px` but the layer
measures **150px** because eww sizes a window to its CONTENT, so the bar *can*
grow; whether it should is the owner's call.

**Three options, all needing a visual OK:** (a) render at 150px and move the
title/transport/cava *beside* the boombox using the spare band width — best
looking, most work; (b) grow the music face to ~200px only while audio plays —
but a bar that changes height mid-session shifts the desktop; (c) commission a
genuinely wider (3:1+) boombox composition. Multiply the fractions above by the
chosen render size to place the overlay — never eyeball it.

### 🩸 Hacker mode rev 2 — BLACK / WHITE / RED (2026-07-28, owner-directed)

Owner refined it live: *"different shades of black so you can see all the
details"*, *"the graphs need to be glowing white number and icons and ticker"*,
*"throw more red throughout to key feature or icons — I like that red with the
dark"*. Result: **black structure, white data, red landmarks.**

- **Art is layered blacks, not flat greyscale.** The first mono pass left the
  hull mid-grey and the wallpaper's galaxy core blown to white, so a
  white-outlined ship on a bright background vanished. Now the body is crushed
  (`luma**3.1 * 0.30`) and only the top ~38% of luma survives as white detail
  lines, plus a baked 3px white silhouette ring. Reads on light *and* dark.
- **The wallpaper is genuinely shades of black now**: mean luma **12.3**,
  **0.000%** above 200, 1.74% above 100. Every white pixel on screen now
  belongs to the interface, not the background.
- **Graphs/icons/ticker are lit**, not dimmed — the earlier grey ramp made the
  bottom bar look switched off.
- **Red = the landmark colour** (`#ff2d55`, palette canon): card and section
  glyphs, the GHOST threat readout, the active station pill, status dots when
  down, progress fill, the play/pause control. Everything else greyscale, so
  red is the only thing that pulls the eye anywhere on screen.
- **The music face is monochrome too** — it had its own magenta and green
  speaker rings, green transport buttons and a green artist line that the deck
  rules never reached. Measured **0.00%** coloured pixels after.

**TWO TRAPS that cost real time here — read before touching hacker CSS:**

1. **Inline `:style` beats every stylesheet rule.** The violet rim the owner
   kept pointing at was NOT CSS: `ghost_card` and `deck_card` carry hard-coded
   `box-shadow: ... rgba(125, 61, 255, ...)` in an inline style, and so did the
   boombox speaker glow, a row wash and a `◆` marker. An `!important` probe on
   `.nyx-hacker .nyxus-surface` produced **zero** effect, which is what proved
   it. All 5 are now `SECSTATE.hacker`-conditional in the yuck; CAVA bass
   reactivity is preserved, only the hue swaps. Grep for
   `:style` + a hard-coded hex before assuming CSS can fix a colour.
2. **`.nyx-hacker` is ON the deck root, so the root needs a COMPOUND selector.**
   `.nyx-hacker .gh-root` (descendant) never matches the element that carries
   the class — it must be `.nyx-hacker.gh-root`. Everything *inside* the deck
   themed correctly while the root itself kept its rim, which is a very
   misleading symptom. Same applies to `.deck-root` and `.start-root`. The bar
   roots were already correct (`.nyx-hacker.ws-rail` etc.) — match that form.

**Debugging note:** `eww reload` CLOSES the deck windows, and
`nyxus-home-deck` only reopens them on the next workspace event. So a
screenshot straight after a reload can catch an empty station or a stale window
and produce measurements that contradict each other. Toggle to another
workspace and back before capturing, or you will chase ghosts — this happened
repeatedly during this pass.

### 🛡 verify-profile gate 13x — Hyprland version guard (2026-07-28)

Hard-**FAIL**s the bake if the repos offer Hyprland **≥ 0.57**, because that
release drops hyprlang and this profile is `hyprland.conf` + 17 hyprlang
shards — a bake would silently produce an ISO with no desktop config at all.
Override deliberately with `NYX_ALLOW_HYPRLAND=1`.

It also **WARN**s on build-host skew, which is the deeper process bug: the bake
installs Hyprland from the repos at bake time, so "verified live on the builder
box" can be verification against a compositor that never boots. Current state
is exactly that — repos offer **0.56.0-2**, this box runs **0.55.4-1**.

A true pacman *pin* was considered and rejected: pacman resolves by version, so
a pin fights the resolver and fails quietly. A guard cannot be bypassed by
accident, which is the property that actually matters here.

### 🗂 OWNER'S OTHER PROJECTS — located 2026-07-28 (owner had lost track of both)

Recorded here because the owner asked where they went, twice. Neither is part
of the ISO build; both are **alive on disk** and neither is finished.

**SharkDash — a btop FORK (C++).** This is why it "used the same code": it *is*
btop's source. btop itself is upstream `btop 1.4.7-1` from Arch and is NOT an
owner app — but NYXUS *does* theme it (`~/.config/btop/btop.conf` →
`color_theme = "nyxus-prism"`, shipped in skel with `nyxus-prism.theme` and
`SharkDash.theme`).

| Path | State |
|---|---|
| `~/.local/build/sharkdash-btop` | 22M, 310 files — full btop tree at upstream `6c0cedd` (v1.4.0, 2024-09-22) with `src/sharkdash_pages.{cpp,hpp}` added. **The real fork.** |
| `~/sharkdash-fork` | 64K — the *patch set*: `sharkdash.patch`, `patch_btop.py`, `build_sharkdash.sh`, `sharkdash_pages.{cpp,hpp}`, `SharkDash.theme`. The reproducible way back in. |
| `~/sharkdash` | 3.8M, git `5567d49` (2026-07-12) — later NYXUS-branded work (`nyxus/`, `nexus/`) |
| `~/Downloads/sharkdash_src (1)` | 268K, 19 files — `collectors/config/engine.{cpp,hpp}` — a from-scratch attempt |
| Built binary | **none found** — it has never been compiled to a shipped binary |

**SharkNOC — the NOC TUI (Python/curses).** Not lost, and it still works:
`~/.local/bin/sharknoc.py` (`SharkFin NOC (Network Operations Console)
mini-view v2.0`, curses, 2026-06-29) plus a newer bash reporter
`~/.local/bin/sharknoc` (`--json` / `--watch`, 2026-07-10). Its dependency
`~/.local/bin/sharkdash_state.py` is present and **`import sharknoc` succeeds**,
so it is runnable today — just run `sharknoc`.
`~/Projects/gowskinet-noc` and `~/gowskinet-noc` hold only its *state* (
`honeypot.sqlite`, `honeyhive.state.json`, `alerter.state.json`), not source;
an older copy is at `~/Projects/archive/GowskiNet-Hub/noc`.

**Opportunity, not a task:** GHOST/LAB already surface honeypot and VM data as
eww decks, and SharkNOC reads the same `honeypot.sqlite` + HoneyHive state. If
the owner wants the NOC back, wiring `sharknoc` into a station is cheap; a
btop-fork rebuild is a much larger job and would need the patch set above.

**Pending polish:** btop is a TUI, so no eww CSS reaches it — in hacker mode it
stays violet/magenta/green from `nyxus-prism.theme`. A `nyxus-hacker.theme`
(42 keys, mono + `#ff2d55`) swapped by `nyxus-hacker-mode` would make even the
terminal monitors flip. **Not started.**

### 🧭 "Half-station" workspaces (1, 1½, 2, 2½ …) — assessment + recommendation

Owner asked whether inserting half-steps between stations to "open up more
workspaces for more tools" is a good idea. Straight answer: **the literal
fractional form is not possible, and 9 inserted half-stations is not
recommended** — but the underlying goal (more room for tools) is already mostly
solved and is cheap to extend the right way.

**Why fractional is impossible:** Hyprland workspace IDs are integers.
`workspace = 1.5` is not a valid id; there is no "between 1 and 2" slot. Any
"1½" has to be either a *named* workspace (`name:1B`) or just another *number*
(11-20).

**Why 9 half-stations is a poor trade:**
- The left rail already shows HOME + START + 1-10 (12 pills on a 70%-height
  column). Adding 9 halves → **21 pills**, ~33px each — cramped and hard to hit.
- Halves get **no natural keybind**. `Super+1..0` map to 1-10; there is no
  `Super+1½`. They would be rail-click-only unless you burn a modifier layer.
- It piles onto the **single most fragile subsystem in the build** — the station
  matrix generated by `nyxus-hacker-mode` — which broke twice this session and
  is now guarded by gate 13w precisely because drift here is expensive. Each new
  station must stay consistent across stations.json (×2 matrices),
  nyxus-stations.conf, the eww rail (`workspaces.sh` + `station_pill`),
  layerblur namespaces, and the verify gate.
- `station_pill` currently renders **`st.id` as the label** and dispatches to
  it, so a named half-station would show "name:1B", not "1½", without a
  rail-widget change (add a separate display-label field).

**What already covers the goal:**
- **`Super+S` magic scratchpad** (`togglespecialworkspace magic`) — a transient
  overlay space for extra tools, zero rail cost. Already shipped.
- **Named annex stations** — the exact HOME/START/LAB mechanism. They cost
  none of the 1-10 slots and can be added a couple at a time as real needs
  appear. This is the recommended path for *permanent labeled* extra stations.

**Recommendation:** keep 1-10 as-is; use `Super+S` for scratch; add a *handful*
of **named annex stations with real names** (not fractions) only when a tool
actually needs a permanent home. Do NOT bulk-create 9 halves.

**Implemented now (embodies the recommendation, fixes a real gap):** LAB
shipped as a named station with **no keybind and no rail pill** — reachable only
via `hyprctl`. Added `Super+Delete → name:LAB` (completing Home=HOME /
End=START / Delete=LAB). To make named stations *fully* first-class in the rail
later, `station_pill` needs a display-label field and `workspaces.sh` needs to
emit named stations — noted, not done (out of scope for a "is this a good idea"
question, and it touches the fragile rail).

### 🔜 OWNER QUEUE (next session)

1. **REBAKE** from clean `main`, then verify: calamares present, no line-592
   banner, HOME/START/LAB switch, login screen inside ~15s not 102s.
2. **Pin Hyprland 0.56.1** in the ISO before anything else config-related.
3. **Ten-app login storm** — every station 1-10 has an `on-created-empty`, several
   pointing at dev-only services (`localhost:5173/3000/8080`) and station 5 runs
   `sudo bandwhich`, which prompts for a password at login. Live-proven: a
   "Unable to connect — localhost:5173" Firefox window appeared during a hacker
   flip. Likely contributor to the ~3-minute bar delay. **Behaviour decision
   still owner's — not changed.**
4. ~~white outlines on the art~~ **DONE** · ~~peace-sign alien flicker~~ **DONE**
   · **boombox v2 art DONE but NOT WIRED** — pick one of the three geometry
   options in the boombox section above; the measurements are recorded so the
   overlay is placed, not guessed.
5. Unmerged on `babysit/land-open-prs` (Jul 13, never landed): login/lock
   **anti-lockout recovery gate**, a path-traversal fix in the nyxus-web static
   server, offline GTK4 app deploy fix.
6. **SharkFin mini-NOC — DONE + shipped on MESH (station 7).** `sharknoc` was
   broken (f-string `\"` SyntaxError on the GPU line; and `read_health()`,
   `human_bytes()`, `maze_stats()`, plus jeTT/health keys that no longer
   existed). Rewritten against the real `sharkdash_core`/`sharkdash_health`
   API; all three modes (plain / `--json` / `--watch`) render clean.
   It + its two stdlib-only deps (`sharkdash_core.py`, `sharkdash_health.py`)
   now stage to `/usr/local/bin`, and MESH's `on-created-empty` opens it
   **fail-safe** (`command -v sharknoc … || btop`), so a bake without them
   degrades to btop rather than a dangling command. This shipped a slice of the
   otherwise-unversioned `~/.local/bin` shark suite (39 tools) into the ISO —
   flagged as an owner call in `docs/PROJECT_INVENTORY_2026-07-28.md`; easy to
   pull (drop the staging block + revert station 7) if unwanted.
7. **Half-station idea — assessed, recommended AGAINST bulk 9-halves** (see the
   section above). Implemented the useful, safe part: `Super+Delete → LAB`
   keybind, since LAB was keyboard- and rail-unreachable. If you want permanent
   extra stations, add named annex stations a couple at a time; for transient
   space, `Super+S` scratchpad already exists.
8. **Full project inventory → [`docs/PROJECT_INVENTORY_2026-07-28.md`](./docs/PROJECT_INVENTORY_2026-07-28.md).**
   47 GitHub repos + local checkouts cross-referenced against what the build
   ships. Headlines: **~18 `Nyxus-*` micro-repos are superseded** by Nyxus-Core
   (archive on GitHub); **5 AI-assistant repos are one idea renamed** (pick one);
   **3 EDRs** jeTT/Bifrost/Cerberus overlap (decide the split); **axiom exists 3×**
   and **c2 == ghost-relay** and **BAASIC/android-hub are double checkouts**;
   the **39-tool shark suite is unversioned** and should be put under git;
   ~~**Bifrost has 58 uncommitted files** locally~~ → **COMMITTED + PUSHED, see 9.**
   All advisory — nothing deleted.
9. **Bifrost's 58 dirty files are COMMITTED AND PUSHED** (`~/Projects/bifrost`,
   `main` → `github.com/…/Bifrost`, `75b4235..a29fb1d`, tree now clean, in sync).
   This was the highest risk-of-loss item on the box — station 9 is BIFROST and
   the ISO stages a Bifrost payload, so it was live, load-bearing and existed in
   exactly one place. Three commits, nothing rewritten, nothing force-pushed:
   - `chore(gitignore)` — the only thing deliberately **NOT** committed. All three
     files under `app/bifrost-desktop/src-tauri/resources/guardian/` are outputs of
     the committed `package_monolithic.sh`: a **21MB stripped PyInstaller ELF**
     (`--onefile --strip`, also rebuilt by `build-release.yml` in CI) plus
     `reasoner.py` and `security.py` that are **byte-identical `install -m 644`
     copies of tracked `bifrost/` source**. The binary would have been an
     undiffable permanent blob; the two `.py` copies are the worse trap, because
     git would let them drift from the real modules while still being bundled into
     the installer. This was an *inconsistency*, not new policy — the same script
     writes the same binary to `binaries/guardian-${TARGET_TRIPLE}`, which was
     already ignored, and only the second destination was missed. Ignored the
     directory *contents* with a `!.gitkeep` negation, since the placeholders are
     the tracked contract and `tauri.conf.json` globs `resources/**/*` at bundle
     time. **Nothing was deleted** — the payload is still on disk and still
     bundles; a fresh clone regenerates it with `./package_monolithic.sh`.
   - `feat(guardian)` — the deterministic rules floor (`rules_analyst.py`) and
     Jett verdict ingestion (`jett_ingest.py`). Fixes a real ambiguity that ties
     straight into the "**BIFROST'S AI EDR WAS RUNNING BLIND**" warning at the top
     of this file: when the analyst was down, every event still got
     `threat_class="parser_error"` at LOW, so *"analyst offline"* and *"analyst
     says this is fine"* rendered **identically**. Now the rules floor classifies
     from already-extracted indicators and stamps
     `reasoner_model="deterministic_rules"`, `_safe_fallback` splits
     infrastructure-offline from genuine parse errors, and the dashboard derives
     `online / degraded / offline / unknown`. Jett's verdicts are ingested
     pre-decided (the router does not re-run the LLM on an already-decided
     verdict), and process events are no longer shoehorned into the "IP attacker"
     shape.
   - `feat(desktop)` — 52 files: Bifrost the EDR window becomes **NYXUS the hub**,
     7 new Rust Tauri modules (`nyxus`/`jett_intel`/`honeypot`/`meli_ops`/`sysctl`/
     `heimdall`/`forge`, 42 commands all wired into `invoke_handler`), a real
     embedded PTY (`portable-pty` + `@xterm/xterm`), 11 new React pages, and
     Orbitron / Permanent Marker / JetBrains Mono **vendored** in `public/fonts`
     (~300KB) because a local-first EDR console must render with no network and
     must not make outbound CDN calls.

   **NO SECRETS FOUND.** Scanned for `sk-`/`ghp_`/`github_pat_`/`AKIA`/`xox`/
   `AIza`/JWT/`BEGIN … PRIVATE KEY` and for hardcoded credential assignments:
   clean. Bifrost's `.gitignore` was already good (`.env`, `*.db`, `*.log`,
   `__pycache__`, `.venv/`, `node_modules/`, `bifrost_tokens.env`,
   `heimdall_config.json`), which is why only 58 files were ever exposed. Two
   non-secrets worth knowing: `dashboard.py`'s `"token":"localhost-session"` is a
   **pre-existing unchanged** loopback sentinel, not a leaked credential; and the
   new Rust modules use `env::var(…).unwrap_or_else(|| "/home/cosmic/…")` — the env
   override is the real mechanism but the **fallbacks are this machine's paths**,
   so they are not portable to another user. Left exactly as they run today.
   **Bifrost does NOT need a remote** — `origin` already existed and is current.

   **The live daemon was not touched.** `bifrost-guardian` (PID 942,
   `python3 -m bifrost.guardian --dashboard --dashboard-port 8766`) stayed `active`
   with its socket listening across the whole operation, and the payload files kept
   their original mtimes. Version control only — no restart, no refactor, no moves.
   **The running process is therefore still executing the previously loaded code
   and will pick up the guardian changes on its next natural restart.**

---

## WHERE WE STAND — 2026-07-27 · bake READY (superseded by the block above)

> Short status for the owner. Detail lives in §5 / §6 below. **Update this block
> whenever bake readiness changes.**

| | |
|---|---|
| **Repo** | `~/Nyxus-Core` · **`main`** |
| **HEAD** | `7289a761` — confirm with `git rev-parse --short HEAD` |
| **Open PRs** | **none** |
| **Chrome night brief** | [`docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](./docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md) |
| **Stations / vault brief** | [`docs/STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md`](./docs/STATIONS_APPS_AND_LAB_BRIEF_2026-07-27.md) |
| **Security inventory** | [`docs/SECURITY_INVENTORY_2026-07-27.md`](./docs/SECURITY_INVENTORY_2026-07-27.md) |
| **Repo state for bake** | **READY.** Tip includes stations (HOME/START/GHOST/FORGE/LAB/ARSENAL), vault desktop apps, localhost bind for consoles, ollama+suricata on ISO, welcome `exec-once` restored. `verify-profile` **PASS**. Owner runs bake (sudo/fingerprint). |
| **Last ISO on disk** | `nyxus-2026.07.26-x86_64.iso` @ **02:26** — **stale once 07.27 bake finishes**. |
| **Kage-Ryu on stick** | Packages in `iso-builder/local-repo/` + Projects tree |
| **Gates** | ✅ `iso-builder/verify-profile.sh` |
| **Disk note** | Builder root ~**58G free / 94%** — free space before bake (old ISOs in `out/` are ~38G); squash workdir needs headroom. |

### Bake command

```bash
# Repo must be clean: git status  →  nothing to commit
cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh
# → iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso
```


### 🛑 EWW chrome night — reverted (2026-07-25 → 26) — DO NOT REPEAT

**Intent (owner):** swap hub art to livewall UFO + **normal time/date** in cockpit;
music face = boombox-v4 with UI fitted in the screen; optionally wrap docks/ticker
in Meshy “transparent” PNGs. **Not** a redesign.

**What went wrong:** prior agent pushed marquee/`SAUCER_CLOCK` + lowrider redesign
(`ecdcc952`, `c73caae0`). Follow-up (`0bf2d06c`) tried the real brief + live
`sync-eww` — docks/ticker looked wrong; tall bar + Hyprland layer-blur catch-all
painted a frosted **shadow box** behind the saucer. Owner: restore everything,
bake the good tip, leave chrome alone.

**Resolution:** full revert of `ecdcc952`…`058ee2c4` chain. Tree matches
pre-redesign evening baseline. Live session synced; owner: “perfect / looks good.”
**Next chrome pass only when owner restarts it** — small, visual OK before push.

Full narrative + bake notes → [`docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](./docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md).

### 🔦 ALIEN NEON palette/brand audit — this pass (2026-07-24 PM)

**Every shipped surface is now the ONE ALIEN NEON palette** (no gold `#d4b87a`,
no cream, no old violet `#a06bff`, no `DARK MIRROR`/`OBSIDIAN PRISM` brand)
outside the deliberate carve-outs (Arsenal/Bifrost/GodsApp/Meli/Security Center,
`nyxus_palette.py` ban-statement, `docs/legacy-visuals.md` history).

- **Shell apps** — killed local gold; `nyxus_account/backup/clipboard/drop/files/updater`
  now import `ACCENT_PRIMARY` (prism violet, fallback `#7d3dff`); `nyxus_toast`
  accents → canon green/orange/red/cyan; desktop icon-select + rofi context menu → violet.
- **Brand** — `DARK MIRROR`/`OBSIDIAN PRISM` → **ALIEN NEON** across the whole
  desktop (login `issue`/`motd`, eww ticker + boot-splash label, `.desktop`
  tooltips, cursor theme, hypr/eww/greetd/sddm/wlogout, locale `.po`, bootstrap,
  install.sh, cava, btop, nyxus-home HUD, asset generators, calamares slideshow).
- **Installer** — Calamares branding synced to the ALIEN-NEON `show.qml`; stale
  gold `stylesheet.qss` cleared.
- **Build wiring (key finding)** — `build-iso.sh` regenerates skel + `/opt/nyxus`
  from `artifacts/api-server/nyxus-scripts` (**NS = source of truth**) at bake.
  NS lagged the baked profile, so a bake would have **stripped the Welcome-
  Transmission windowrules** and shipped the old wlogout/greeter — synced NS back
  up so the offline payload matches what boots. Bumped `BOOTSTRAP_VERSION` →
  `2026.07.24-r14-alien-neon` so installed systems re-pull the retheme.
- **verify-profile.sh** — fixed a stale assertion (grepped `nyxus welcome` space
  vs the real `nyxus-welcome` hyphen exec-once) that was **failing the gate on `main`**.

**Deferred (documented, NOT bake-blocking):**
SDDM `Main.qml` offline-payload copy drifts from the baked theme (fallback
greeter, not the live greetd path). WaybarMockup `#/waybars` **deleted** this
pass. Settings Phase 3/4 deepened on branch (Kernel/Kage + MINIMAL/PARTIAL
controls; `APP_REV` r16) — **on-device QA still required** after bake.

### 🧹 Pre-bake cleanup + Settings coverage — same branch (2026-07-24 PM)

Roadmap + owner-confirm list: **[`docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md`](./docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md)**.

- **Stripped dead cruft** (safe): 32 duplicate app `.py` from committed
  `skel/.config/nyxus/` (apps run from `~/.nyxus`→`/opt/nyxus`; kept the
  screensaver chain), stale `.bootstrapped` + `NYXUS_STATUS.md`, orphan
  `wlogout-theme/`. Riskier deletions (download-portal-mapped orphans,
  `dist/` bake-host tree) are listed as owner-confirm — **do NOT** delete
  the `nyxus-recovery-*`/`sddm-themes` cluster (it's live via the shipped
  `pam.d/sddm-recovery-snippet`).
- **Settings master coverage + deepen:** 57 sections; KernelPage =
  Kage-Ryu + stock rescue; MINIMAL/PARTIAL pages deepened (`APP_REV` r16);
  `empty_group` bug fixed; helpers/fastfetch/safemode/orphans cleaned per
  roadmap. **GUI pages still need on-device QA** (`nyxus-settings`).

**Owner next:** merge PR #75 → clean idle repo → `sudo ./build-iso.sh` →
flash → verify (`/etc/nyxus-build`, bars, welcome, Kage/stock); QA Settings
(esp. Kernel + new shell sections + deepened pages).  
**Next agent:** on-device Settings QA notes + any bake regressions only.

### 🛸 Bottom-bar eww redesign + audio detection — this pass (2026-07-25 evening)

Owner reported a live-boot punch list (login-screen background missing, ~5min
wallpaper delay, saucer clock off-center, rainbow kitty, black box around eww
bars, arsenal apps hanging ~90s each). Investigated each individually instead
of assuming they were all one thing — three turned out to be **already-correct
code** (kitty.conf, greeter background wiring, eww bar CSS all verified clean
via a live Hyprland session on the builder box — see §0 note below on how).
Two were real bugs, now fixed. Commits `4c7b52ca`, `bb11fb6a`, `99aa77af`,
`8013121a`, all pushed:

- **Login screen had no background on a truly fresh bake** — `nyxus-greeter`
  runs as the unprivileged `greeter` user and needs `/var/lib/greetd` +
  `/var/cache/regreet` to exist, but neither `customize_airootfs.sh` nor
  regreet's own tmpfiles rule (which covers different paths) ever created
  them. `greeter` can't create dirs under root-owned `/var/lib`/`/var/cache`
  itself, so every `mkdir`/`cp` in the script silently no-op'd. Fixed:
  `customize_airootfs.sh` now pre-creates + chowns both, as root, at bake time.
- **Wallpaper ~5min blank on first boot** — the exec-once wiring
  (`command -v nyxus-live-wallpaper && nyxus-live-wallpaper auto || nyxus-wallpaper-autostart`)
  never fell through to the fast static-image script (the command always
  exists), so first boot blocked the whole background on a synchronous
  ffmpeg render of the flagship loop. Fixed: show the still immediately,
  render in the background, swap to the animated loop once ready.
- **nyxus_screensaver.py redesigned** — was plain white text on a dim
  wallpaper (didn't even use the ALIEN NEON palette it imports). Now a glass
  card matching hyprlock's Prism HUD language, with a violet↔magenta
  breathing pulse. Verified live with a real screenshot.
- **Saucer clock/music screen recentred** — measured the actual
  `nyxus-saucer-band.png` pixel-by-pixel: the transparent cockpit window
  sits ~31px *below* image centre, not above as the old margin assumed (that
  margin had been re-guessed twice already against different art revisions
  and drifted wrong each time). Fixed with a measured `margin-top: 10px`
  instead of another guess. Flip transition swapped `crossfade` →
  `rotate-left-right` (GTK's real card-flip, not a fade standing in for one).
- **Left/right rail "plain white box" look** — `.float-island` was painting
  its own faint single-hue rim and explicitly stripping the pills' real
  per-hue `obsidian-vessel` glass/glow styling (deep fill, neon hairline, 2px
  accent top-rule, real glow — already built, just suppressed) down to
  transparent. Removed the override; the existing rich design shows through.
- **Arsenal apps (CIPHER/Forge/RedForge/GSL/Trainer/Bifrost) hanging ~90s
  each with a cryptic port-timeout message** — root cause: they need
  `~/GowskiNet-Vault`/`~/Projects/bifrost`, dev-machine-only projects never
  shipped on live media. `nyxus-app-shell` now runs the starter synchronously
  and surfaces its actual failure reason immediately instead of blindly
  polling the port for 90s (`nyxus-app-shell/src-tauri/src/lib.rs`, rebuilt +
  redeployed to the airootfs binary). Decision: **hide/fail-fast on live
  media**, not attempt to bundle the vault. AXIOM found to have **zero**
  `nyxus-webapp` backend wired at all (separate, deeper gap, now fails fast
  too instead of hanging).
- **Universal audio detection** — `player.sh` only checked MPRIS
  (`playerctl`), so the saucer never flipped to the music face for players
  that don't implement it (bare `mpv` without `mpv-mpris`, verified live).
  Added a `pactl`-based fallback: any live PipeWire/Pulse sink-input now
  triggers "Playing" with a generic title if MPRIS finds nothing.
- **`CAVA_BASS`** — new 0-100 live scalar pushed from `cava.sh` every frame
  (loudest bar across the spectrum, not a fixed low-frequency index — tested
  live against an 80Hz tone that peaked in bars 4-9, not 0-1, so "bass = low
  bars" doesn't hold generally). Currently drives the CSS boombox speaker
  dots' size/glow; this plumbing is reusable regardless of what replaces the
  visual layer (see below).

**⚠️ IN PROGRESS, NOT WIRED IN — 3D saucer + boombox (owner's call, this
session):** the CSS-only boombox restyle in `99aa77af` was a stopgap; the
owner wants real 3D-modelled assets instead, same pipeline as the alien
companion (Meshy → render hero shot → wire in as an image, same as
`nyxus-saucer-band.png`). Live-3D-in-Godot was discussed and explicitly
rejected in favor of image-based for this — see the conversation, not
re-litigated here. **Status:** owner generated 4 new GLB models, dropped in
`~/Downloads/`:
`Meshy_AI_nyxus_oblong_saucer_3_0725230844_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_boombox_3d_fina_0725230853_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_left_dock_3d_0725230915_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_right_dock_3d_0725230902_image-to-3d-texture.glb` (left/right
NOT started yet — owner said do saucer+boombox first). Rendered hero shots
for saucer + boombox with Blender (`blender --background --python`, EEVEE,
transparent PNG) — **Blender 5.1.2 is installed on the builder box**, this is
the render pipeline now, not a live Godot overlay. Found the boombox's true
front by rendering a full 12-angle turntable rather than guessing an azimuth
(front-facing render is `az=225 el=16 dist=2.5 lens=34`, see
`render_hero.py`-style script in conversation — not yet committed anywhere,
was a scratch job-tmp script). **Not yet done:** neither render has been
saved into the repo or wired into `saucer_base`/`bar_hub_music` — that's
still the flat `nyxus-saucer-band.png` shipping today. **Next agent, if
picking this up:** (1) get the final hero renders from wherever they landed
(job scratch dir, or re-render from the GLBs in Downloads — script logic is
in this session's transcript), (2) crop/trim transparent margins, (3) wire
in as background-image the same way `saucer_base` does today, (4) figure out
where the display/text overlay sits on the new art (old measurement approach
— pixel-scan the PNG for the transparent/dark region — won't directly apply
to a differently-shaped asset), (5) **hard requirement, owner was burned by
this before:** whatever click-handling exists must keep hub-open and
transport-controls (prev/play/next) as separate hit-regions — do NOT let a
transport click fall through to hub-open. (6) Left/right dock 3D (rail
redesign) — models exist, zero integration work started.

**⚠️ Also not committed:** none — everything discussed in this session that
reached a working state is committed and pushed as of `8013121a`. The 3D
work above is scratch-only (Blender renders in job tmp, never copied into
the repo) — treat it as **not started from the repo's perspective**.

### Bake command (reminder)

```bash
# Repo must be clean: git status  →  nothing to commit
cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh
# → iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso
```

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
  **⚠ 2026-07-23:** older `7.0.12` pkgs lacked iso9660/squashfs/loop. PKGBUILD
  patched; rebuilt pkgs present ~08:53 EDT 2026-07-24 — **still verify** on stick
  before trusting Kage as live default (stock rescue if iso9660 fails).
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

## 5. CURRENT STATE (2026-07-24)

> **See also the top-of-file [WHERE WE STAND](#where-we-stand--2026-07-24--1146-edt) block**
> for the bake-ready snapshot (time-stamped).

### Last-day chronicle (moved)

**Full story of Jul 23–24 building** (timeline, done/open, gotchas, PRs):

→ [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md)

Do **not** re-expand a second diary here — append new surprises to the day brief
or to WHERE WE STAND above.

### The `nyxus-2026.07.22` stick booted BROKEN — and why (post-mortem)
Two overlapping causes: (1) that stick was baked from a **partial/stale** profile
(missed the ungate-bars fix), and (2) the deeper bugs above (dead Replit + install
`set -e`/`clear` + eww.scss + wallpaper path). All are now fixed in the repo but
**not yet in a baked ISO** — needs a fresh bake. `nyx@nyxus` + auto-login are
correct/expected (it's a live ISO, not an install).

### ⛔ Kage live-ISO substrate (status 2026-07-24 midday)

**History:** QEMU 2026-07-23 confirmed default Kage entry died with
`mount: unknown filesystem type 'iso9660'` (lean config stripped iso9660/squashfs/loop).

**Now:** PKGBUILD forces those options; rebuilt `7.0.12` pkgs on disk (~08:53 EDT).
Owner reported kernel done. **Still verify on the next baked stick** — if Kage
fails again, boot **"stock linux (rescue)"** and re-check module config.

### Live-boot fixes (#71 → #72) — summary

Landed on `main` via PR **#72** after a near-miss ( #71 merged to a branch that
was already on main). Covers: eww first-paint (`npx sass` skip), black-box path,
hyprpm header guard, ALIEN NEON `/etc/issue` + bashrc stamp, jeTT `/home/nyx`
de-leak, `BOOTSTRAP_VERSION` `2026.07.24-r13-fixes`.

Detail + timeline → day brief. Flashed `nyxus-2026.07.24` @ 03:05 was **before**
these commits — rebake required.

### Pending / owner queue

1. ~~Confirm `main` has #71~~ **DONE** via PR #72.
2. **RE-BAKE** from idle `main`: `cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh`  
   **Do not flash** the 03:05 `nyxus-2026.07.24` ISO for today’s work.
3. **Re-flash** — re-check `lsblk` (USB letter moves). Boot **UEFI**. Verify Kage
   mounts ISO (or use stock rescue) → splash → desktop → stamp in `/etc/nyxus-build`.
4. ~~W6 arsenal/reactive shards~~ **DONE** — still verify post-bake with `unsquashfs`.
5. ~~W1 file_permissions~~ **DONE**.
6. **Still open on stick QA:** greeter/lock/UFO/welcome-note; home backup to Ventoy.
7. **Deferred hygiene:** ~33 non-boot Replit refs; prune stale remotes / old ISOs in `out/`.
8. Owner’s call: companion mascot; fold `companion-3d`.

### Copilot Deep Pre-Bake Audit (2026-07-24) — stored here (no separate memory store)

**ALIEN NEON + Settings completeness checklist (owner tracking):**
[`docs/ALIEN_NEON_SETTINGS_AUDIT.md`](./docs/ALIEN_NEON_SETTINGS_AUDIT.md)
— full counts + lists for (1) surfaces not ALIEN NEON, (2) empty/minimal/partial
Settings pages, (3) apps with no Settings section, (4) session features missing
from Settings. Regenerated 2026-07-24 from live `~/.nyxus` + desktop entries.
**Stay as-is (no ALIEN NEON / no Settings required):** Bifrost, GodsApp, Meli,
Arsenal/security lab apps (CIPHER/Forge/GSL/RedForge/Trainer/AXIOM/c2/Shield/…).

Full GO/NO-GO from Copilot audit. Cross-checked against `main` @ `fb63e2aa` (+ #71 on main).

| Gate | State |
|---|---|
| **C1** Rebuild Kage-Ryu (`ISO9660_FS` + `SQUASHFS` + `BLK_DEV_LOOP` =y); QEMU verify | ⚠️ **PKGS PRESENT** (`7.0.12` @ 08:53 EDT 2026-07-24; PKGBUILD enables live FS). Owner said kernel done; **still verify** mount before trusting. `makepkg` idle. |
| Bake from clean committed idle `main` | ✅ **READY NOW** — tip after day-brief docs; `git rev-parse --short HEAD` |
| Boot labels / offline-cache / kernel hard-fail guards | ✅ intact |
| Palette lock (ALIEN NEON; cream / `#a06bff` clean in desktop trees) | ✅ clean |
| Desktop delivery (skel + bootstrap + `/opt/nyxus-cache`) | ✅ intact |
| Welcome Transmission + Dream Protocol | ✅ **DONE** on `main` (`1af1a65f`) |
| ALIEN NEON Phase 1 (PR #73) | ✅ **MERGED** on `main` |
| **W1** Regenerate `profiledef.sh` `file_permissions` (~59 `/usr/local/bin` missing) | ✅ **DONE 2026-07-24** (177 entries regen from airootfs) |
| **W2** `verify-profile.sh`: label consistency + ban `#f4ead5` + kernel-policy + cache/daemon asserts | ⚠️ cream ban **DONE**; other W2 asserts still deferred |
| **W3** Dead Replit host fallbacks in chrome/stickies/sysmon/… | ℹ️ deferred (~33 non-boot) |
| **W4** `/home/cosmic` in jeTT/audit/arsenal `.env.example` | ℹ️ jeTT + audit **clean on current main** (#71); arsenal `.env.example` still deferred |
| **W5** `dunstrc` hard-codes `/home/nyx` icon_path | ℹ️ OK on live ISO; de-leak on install |
| **W6 (this session — Copilot missed)** bake wipes `nyxus-arsenal-apps.conf` from skel; never `source=`d | ✅ **DONE 2026-07-24** — bake shard list + `source=` in hyprland (NS+skel); also ships `nyxus-reactive.conf` |
| I1–I5 | ℹ️ cleanup / cosmetic (orphan greeter, dup python tree, Forge `#0a0a14`, stale BUILD_ID stubs restamped at bake) |

**Verdict (2026-07-24 ~11:50 EDT):** **GO for bake** from idle `main`.
Kage pkgs present; verify mount on stick (stock rescue fallback). Old ISO @ 03:05
is **not** this tip — rebake. Full day story → [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md).

**After bake verify:** `cat /etc/nyxus-build` → matches bake tip; label `NYXUS_2026_07`; UEFI Kage or stock rescue; desktop offline; bars OK; welcome transmission once.

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
- **NEVER invoke a shipped tool through `~/.local/bin/` in any config.**
  `/home/nyx/.local/bin` is **EMPTY on the ISO**; `/usr/local/bin` is where
  tools actually land. Use the **bare command name** and let PATH resolve it.
  This bit for weeks: `~/.local/bin` is fully populated on the builder box, so
  every such call "works" when verified live here and is dead on every stick —
  it silently killed the living/reflex layer, soundd, shader restore, ~20
  keybinds and all five hyprlock widgets. Gate **13z** now hard-fails it.
  Corollary: **"the binary ships" ≠ "the config can reach it."** Gate 13w only
  proved the former, and only for `hyprland.conf`, never the `conf.d/` shards.
- **When a stick "looks old", verify the IMAGE before theorising.** Mount it
  (`udisksctl mount -b /dev/sda1`, no sudo needed) and check
  `/etc/nyxus-build` for the source commit, then diff `/etc/skel` against
  `/home/nyx` and `/opt/nyxus-cache` inside `airootfs.sfs`. On 2026-07-30 all
  of those were perfect and the bug was in how the configs resolved paths —
  hours go missing re-auditing the bake when the bake was never wrong.
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
- **EWW hub chrome (2026-07-26):** do **not** re-land `ecdcc952` / `c73caae0` /
  `0bf2d06c` (marquee clock, lowrider redesign, Meshy dock/ticker wraps). Owner
  reverted; restored tip looks good. Layer-blur catch-all `^(nyxus.*)$` can
  frost a rectangular “shadow box” behind tall transparent bars — see
  [`docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](./docs/EWW_CHROME_REVERT_BRIEF_2026-07-26.md).
  Saucer/time only when owner explicitly restarts that workstream.
- **Hyprland `layerrule` order is LAST-MATCH-WINS (2026-07-30).** The
  `^(nyxus.*)$` catch-all in `nyxus-hyprland-layerblur.conf` must stay at the
  **top** of the file. It spent months at the bottom, where it silently
  overrode every explicit per-namespace rule below it — so a `blur off` written
  anywhere in that file was dead on arrival. Gate `13ae` enforces the ordering.
- **`set -u` + `${XDG_RUNTIME_DIR}` / `${HYPRLAND_INSTANCE_SIGNATURE}`
  (2026-07-30).** Neither is guaranteed in an `exec-once`/systemd context.
  Under `set -u` a bare reference aborts the script *on that line*, before any
  of its own error handling — a daemon can complete its startup work and then
  vanish with no log. Always `${VAR:-fallback}`, or hoist
  `export VAR="${VAR:-…}"` to the top the way `nyxus-eww-launch-safe` does.
  Gate `13af`.
- **Anything enabled into `multi-user.target` is in front of the login screen
  (2026-07-30).** `systemd.target(5)`: targets auto-complement `Wants=`/
  `Requires=` with `After=`, and `graphical.target` is `Requires=`+`After=`
  `multi-user.target` with greetd behind it. This is how a honeypot firewall
  unit and `NetworkManager-wait-online` put ~100s in front of the greeter on a
  live stick. Live-only work belongs behind
  `ConditionPathExists=!/run/archiso`. Gate `13ac`.
- **eww kills a widget handler after 200 ms (2026-07-30).** `:timeout`
  defaults to 200ms and eww SIGKILLs the `/bin/sh -c` it spawned. Never put a
  NYXUS script in the FOREGROUND of an `:onclick` — `nyxus-hub-close` alone
  measured 231ms-3.7s, so `nyxus-hub-close; do-the-thing` never does the
  thing. Background the whole handler: `(nyxus-hub-close; do-the-thing) &`.
  Gate `13ah`.
- **eww has no `:onkeydown` (2026-07-30).** Not in 0.5.0, not in 0.6.0. It is
  accepted, logged as a warning, and dropped. Keyboard escape from any eww
  overlay must be a compositor bind.
- **`(eventbox :onclick "true")` blocks nothing (2026-07-30).** eww's eventbox
  returns `gtk::Inhibit(false)`. It does not shield nested buttons and does not
  stop the click reaching an outer eventbox. Measured, not assumed — see the
  dated section below. Do not reach for it again.

### 2026-07-30 · The Hub trap, the dead Power buttons, and the bar "shadow box"

Three findings, all measured on a live Hyprland session rather than reasoned
about. The first one overturns what the previous two sessions believed.

**1 · `(eventbox :onclick "true")` never swallowed anything — DISPROVEN.**
The wrapper around `nyxus_hub_layout` was blamed for the Hub's dead controls
across two sessions. It is not the cause and never was. A throwaway eww config
reproducing the exact nesting, driven by synthetic clicks through
`/dev/uinput`, gives a deterministic answer (6/6, then 8/8 per zone):

| clicked | handlers that fired |
| --- | --- |
| button inside the wrapper | the button only |
| wrapper's own padding | wrapper **and** the outer backdrop dismiss |
| outer backdrop | outer dismiss |

eww's eventbox handler returns `gtk::Inhibit(false)` (identical in 0.5.0 and
0.6.0), so it stops nothing; `GtkButton`'s own class handler is what keeps a
tile click from reaching the backdrop. The wrapper neither blocked buttons nor
did the job its comment claimed. It has been deleted. **Do not re-add it, and
do not blame it again.**

**2 · The real killer: eww SIGKILLs a handler after 200 ms.**
`run_command()` spawns `/bin/sh -c <cmd>` and kills it once `:timeout`
elapses — and `:timeout` **defaults to 200 ms**. `nyxus-hub-close` measured
**231 ms – 3723 ms** on a live session on its *fast* path (Hub not even open,
bars already up); it makes half a dozen eww socket round-trips and can
relaunch four bars. Six shipped handlers were written `nyxus-hub-close; X`,
which put the slow script in the foreground, so `X` was killed before it ever
started. Verified directly: `sh -c 'nyxus-hub-close; echo REACHED'` killed at
200 ms never writes REACHED.

That is the whole explanation for "NYXUS Power does nothing": Shutdown,
Restart, Suspend, Logout and Lock all ran `nyxus-hub-close; (${cmd}) &`, so the
menu dismissed and the action never happened. The powermenu's own Cancel and
the dashboard's Close were bare `nyxus-hub-close` with no `&` at all — killed
mid-flight every time. The hub tiles were always written `(${cmd}) &` and were
the only handlers doing it right.

Fix: one backgrounded subshell, `(nyxus-hub-close; X) &`. Gate **`13ah`**
fails any handler that leaves a slow NYXUS command in the foreground. Note the
rule is per-segment, not per-handler: `hyprctl dispatch ...; nyxus-hub-close &`
is fine because the slow half is the detached half.

**3 · The Hub was a fullscreen OVERLAY-layer input surface (Section 7 again).**
`:stacking "overlay"` at 100%x100% puts it above everything with no input
region. While it is up, nothing else on the desktop can be clicked — so any
Hub action that opens an ordinary window (`nyxus-settings`, `wdisplays`,
anything via `nyxus-hub-launch`) lands *behind* it and reads as dead. This was
demonstrated by accident during this session: a concurrent agent's fullscreen
OVERLAY probe was up and every synthetic click on every other surface silently
vanished until it closed.

`nyxus-hub`, `dashboard`, `powermenu` and `cheatsheet` are now `:stacking "fg"`
(TOP). They still cover ordinary windows, but OSDs, notifications and hyprlock
stay above them, so the session can always reach the user. `screensaver` stays
on OVERLAY deliberately. Gate **`13ai`**.

Also removed: `:onkeydown` on the Hub's backdrop. **eww has no such attribute**
in 0.5.0 or 0.6.0 — it was dropped with a log warning, so the in-widget Escape
it appeared to provide never existed. Escape lives in `hyprland.conf`, which is
the only layer that can guarantee it. `Super+Shift+Escape` now runs a bare
`eww close nyxus-hub` *first* and on its own, and a new
`Super+Ctrl+Shift+Escape` closes every eww window and relaunches via
`nyxus-eww-launch-safe` without touching a single NYXUS script. Before this,
every route out of the Hub — both close buttons, the backdrop, both Escape
binds — funnelled through `nyxus-hub-close`, so one slow script was the only
thing between the owner and a surface he could not dismiss.

**4 · The bar "shadow box" is what NO alpha clip looks like — 0.2 is correct.**
A/B'd live with `hyprctl keyword layerrule 'ignore_alpha <v>, match:namespace
nyxus-bar-*'` and screenshots at 0.0 / 0.2 / 0.45 / 0.6. At **0.0** the
wallpaper behind each metric cluster and behind the whole left rail turns into
a solid frosted slab — that *is* the shadow box, and it is the blur bleeding
into the near-zero-alpha halo around each pill (blur is `size 14, passes 4`, so
it travels a long way past content edges). At 0.2, 0.45 and 0.6 the wallpaper
is crisp and only the pills carry frost; the three are visually
indistinguishable.

So **the shipped value was already right and no threshold change was made.**
Bar/window roots are `background: transparent` (alpha 0) and the pill fills are
`rgba(8,3,16,0.55)` / `rgba(24,10,44,0.62)`, so any clip strictly between 0 and
0.55 works; at 0.6 and above the pills lose their frost too. If the boxes come
back, the rule is not reaching the compositor — check that, not the number.
Gate **`13aj`** pins all four bars into that window.

**5 · A third tree, again.** `artifacts/api-server/nyxus-scripts/hypr/conf.d/`
held copies of `nyxus-hyprland-layerblur.conf` and `nyxus-stations.conf` that
**nothing reads** — `build-iso.sh` installs shards from the *root* of
`nyxus-scripts`. Both had drifted; the layerblur twin was still the pre-reorder
ordering. Its path looks canonical, so it is exactly the file an agent greps
for, edits, and ships nothing from. Deleted; gate **`13ak`** fails if any
`.conf` reappears there.

**Still open / not proven.**
- Everything above is proven for eww widget, event and CSS behaviour on this
  box (Hyprland **0.55.4**, eww 0.5.0). It is **not** proof for path resolution
  or compositor-specific layer handling: the ISO ships Hyprland **0.56.1** and
  a **`~/.local/bin` that is empty**. Gate `13x` already warns on that skew.
- Why the owner sees shadow boxes on the ISO when the shipped shard does carry
  `ignore_alpha 0.2` for all four bars (confirmed by extracting the 07.29
  `airootfs.sfs`) is **not** established. The rule not applying under 0.56.1 is
  the leading suspect and needs a boot to settle.
- The Hub's controls were never exercised end to end on the real fullscreen
  surface: the one attempt was invalidated by a concurrent agent's fullscreen
  OVERLAY probe absorbing the clicks.
- `verify-profile.sh` gate `13ub` (agent 4e21a37e) reads the powermenu scrim
  with a fixed `grep -A4 '^(defwindow powermenu'`. Two comment lines added
  inside that block are enough to fail a gate that is actually satisfied. It
  wants a wider window or a block-aware read.

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

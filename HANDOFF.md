# NYXUS — AGENT HANDOFF & BUILD STATE (read this FIRST)

> **Last updated: 2026-07-28 ~04:00 EDT (07.27 ISO was broken · all causes fixed · REBAKE REQUIRED · hacker mode = black/white/red + saucer alien)** · Owner: Joseph A. Sierengowski (`nyx` / `nyxus`)
> If you are a new agent picking up NYXUS: **read this entire file before touching
> anything.** It exists because this project got scattered across duplicate clones
> and the same problems got re-diagnosed and re-broken multiple times, costing the
> owner a lot of time and money. Do not veer off into a different approach. Keep the
> flow, and **update this file as you work** so the next agent re-derives nothing.
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
   **Bifrost has 58 uncommitted files** locally. All advisory — nothing deleted.

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

# SESSION RECOVERY BRIEF — 2026-07-31

> **Read this before doing anything else.** The Jul 30 evening session died
> mid-flight (machine freeze + Cursor billing block). Uncommitted work was at
> risk of being lost. This brief records what was found, what was saved, and
> what is still broken / unfinished.

**Recovery performed:** 2026-07-31 ~00:30–00:40 EDT  
**Canonical repo:** `~/Nyxus-Core` only (`main`)  
**Do NOT bake** until login is verified live and the Hub/Power gap is fixed.  
**Do NOT merge `local-stash-work`.**

---

## 1. Git state when recovery started

| | |
|---|---|
| **Branch** | `main` (tracking `origin/main`) |
| **HEAD found at** | `20953054` — `fix(settings): kill the dead controls — 25 no-op Resets, 12 blank rows, blank swatches` |
| **vs origin** | Up to date (0 ahead / 0 behind) before salvage commits |
| **Working tree** | Dirty: **~65 paths** — 20 **staged** image deletions + many unstaged config/script/docs/greeter edits |
| **Stashes** | Unrelated older stashes only (do not confuse with this session) |
| **Forbidden** | Do not start a bake; do not merge `local-stash-work`; no sudo (fingerprint-only) |

### Verified already-on-`main` (pushed) commits from the Jul 30 session

| Commit | Summary |
|---|---|
| `c0be97f2` | `~/.local/bin` path fix (21 tools hardcoded to empty dir on ISO) |
| `ccd2bb62` | live-boot: NetworkManager-wait-online, honeypot firewall, xz→zstd |
| `018172f2` / `c4124ea9` | urban-alien theming inventory + handoff |
| `e48fb323` | Hub trap: eww 200ms SIGKILL; OVERLAY→TOP |
| `e18a0b76` | login card move, POWER scrim lighten, GTK power art |
| `c2032e7f` | art style audit; hacker-mode mono wall staging gate `13uc` |
| `3de4a38b` | bottom gap fix via `:anchor "top center"` — **overshot → gap moved to TOP** |
| `f65e5405` | handoff docs for bottom strip / blue screensaver / live sync |
| `20953054` | Settings Increment 1: dead controls killed (Settings agent) |

---

## 2. What was at risk of being lost

Everything below was **only in the working tree / index** when the session died.
Another crash or a naive `git restore` would have erased it.

1. **Art deletions already staged** (20 PNG paths) without a committed repoint → bake would ship missing walls **or** dangling refs if only half applied.
2. **Art repoint edits** (stations/workspaces/wallpaper/chrome pool/rotation lists/SDDM installers/download allowlist/verify gate `13ud`).
3. **Login greeter rewrite** (`nyxus-greeter` fall-through / demotion logic) — the blank-screen fix.
4. **`scripts/nyxus-form-login.sh` SDDM quarantine** — worktree went ghostly after the freeze; content recovered from agent transcript StrReplace + prior blob.
5. **Large docs rewrite** (README/STATUS/ROADMAP/SHIPPING/KEYBINDS/iso-builder README/etc.).
6. **Settings Increment 2 planning** (greetd login-settings contract) — **no code written yet**, only transcript intent.

---

## 3. What this recovery commit saved

Pushed (or to be pushed) salvage commits on `main`, in order:

| Commit | What |
|---|---|
| `5b3d3f3b` | **Art WIP** — drop demon / graffiti-02 / graffiti-space / login-stars / rot-black-void; repoint consumers to `nyxus-rot-*`; gate `13ud` |
| `92978719` | **Docs WIP** — correctness pass on top-level + deployment/theme docs |
| `ad15cf11` | **Login WIP** — greeter `STARTUP_OK_SECS` / `MAX_CRASHES` fall-through + shipped-CSS retry |
| `fcba423b` | **Login WIP** — reconstruct + commit `scripts/nyxus-form-login.sh` SDDM quarantine |

Also already on main before recovery: `20953054` Settings Increment 1.

**Phantom note:** `scripts/nyxus-form-login.sh` may still show as `M` in `git status` under cursorfs even when `git hash-object` matches `HEAD`. Content is committed (`754b2e2a`).

---

## 4. Per-agent status

Parent chat for the mid-flight swarm: [`91476bd9`](91476bd9-9c40-4149-9c6e-1c704c57ff26)  
Transcripts under:  
`/home/cosmic/.cursor/projects/home-cosmic-Nyxus-Core/agent-transcripts/`

### 4.1 Art repoint — `4e21a37e`

| | |
|---|---|
| **Transcripts** | Standalone `4e21a37e-…/4e21a37e-….jsonl` (completed theme pass) + parent subagent `91476bd9…/subagents/4e21a37e-….jsonl` (repoint follow-up) |
| **Completed earlier** | Urban-alien inventory, login card / power art (`e18a0b76`), style audit + boards in `~/Pictures/nyxus-style-audit-2026-07-30/`, hacker wall gate (`c2032e7f`) |
| **In-flight when frozen** | Owner-approved **repoint**: graffiti stations + `nyxus_chrome` app bg pool → 28-image rotation set; delete watermarked `nyxus-graffiti-02` + demon / login-stars / graffiti-space / rot-black-void |
| **What we found** | Staged deletions + nearly complete repoint (configs, chrome pool + `rotation/` search dirs, wall scripts, SDDM installers, download.ts, iso mirrors, gate `13ud` with newline fix) |
| **Saved as** | `5b3d3f3b` |
| **Still unfinished** | Live visual confirmation; optional re-key of `scene_graffiti()` in livewall (DEAD KEY kept on purpose); owner may still want Hub background redesign as a separate ask |

### 4.2 Docs audit — `bed1ec20`

| | |
|---|---|
| **Transcript** | `91476bd9…/subagents/bed1ec20-….jsonl` — **only 2 events** (started reading HANDOFF, then died) |
| **Completed** | Essentially nothing under that agent ID |
| **In-flight elsewhere** | Substantial docs edits were in the dirty tree (likely written by login agent `c5a1095a` during its docs/factuality pass, overlapping the docs agent's charter) |
| **Saved as** | `92978719` (marked WIP) |
| **Still unfinished** | Full anti-circling audit; claim-by-claim verification against live gates; may still contain small factual drift relative to post-recovery HEAD |

### 4.3 Login repair + inverted gap — `c5a1095a`

| | |
|---|---|
| **Transcript** | `91476bd9…/subagents/c5a1095a-….jsonl` (~58 events) — **stopped mid-task** (billing block / session death) |
| **Symptom owned** | Blank login (blinking cursor) → TTY3 workaround; Hub/Power gap now at **TOP** after `3de4a38b` |
| **Completed in-tree (now committed)** | Greeter fall-through rewrite; SDDM quarantine in `nyxus-form-login.sh`; fixed art gate `13ud` newline bug while verifying |
| **In-flight / not done** | Planned gates `13ra` / `13rc` (greeter chain + stray conf.d); **gap fix itself never touched eww** — working tree had **no** `eww.yuck` dirty files |
| **Saved as** | `ad15cf11` + `fcba423b` |
| **Still broken for owner** | Blank login may still need **live** apply + reboot test; top gap still present on `main` (`:anchor "top center"` from `3de4a38b`) |

**Root cause notes the login agent recorded (do not re-diagnose blindly):**
- Greeter chain treated immediate `exit 0` as success → blank-screen respawn loop (tuigreet/agreety never reached).
- SDDM reads **every** file in `/etc/sddm.conf.d`, including `*.bak-*`; a bak re-set `DisplayServer=wayland` (weston missing) and wiped `QT_QUICK_BACKEND=software`.
- ISO primary greeter path is **greetd**, not SDDM — but live box may still have SDDM artifacts that matter for repair scripts.

### 4.4 Master Settings — `d3bdd195`

| | |
|---|---|
| **Transcript** | `91476bd9…/subagents/d3bdd195-….jsonl` (~120 events) — stopped after Increment 1, before Increment 2 |
| **Completed** | Increment 1 committed + pushed as `20953054` (dead Resets / blank rows / blank swatches) — carefully avoided committing other agents' staged art deletions |
| **In-flight** | Increment 2: rewrite Login Screen settings off dead SDDM path onto a **greetd contract** (`/etc/nyxus/login-screen.conf` planned); appearance (screensaver, fonts, dark/light) |
| **Unfinished** | No Increment 2 code in the dirty tree; "Windows/Apple completeness", user-account section polish, weather/time login card eye-candy — all still open |
| **Coordination** | Must not race the login greeter agent; contract file + polkit helper + bake allowlist were the planned next steps |

### 4.5 Live sync / bottom strip — `3c1b58ea`

| | |
|---|---|
| **Transcript** | `91476bd9…/subagents/3c1b58ea-….jsonl` (short) |
| **Completed** | Work landed as `3de4a38b` + `f65e5405`; live `~/.config` sync + backups recorded in HANDOFF evening section |
| **Unfinished / regression** | Anchor change fixed bottom strip arithmetic but **owner reports gap now at TOP** — next agent must measure with `hyprctl layers -j` / monitors reserved zones, not re-guess |
| **Screenshots** | `~/Pictures/nyxus-live-sync-2026-07-30/` |

### 4.6 Earlier completed theme / Hub work

Urban-alien audit, Hub trap (`e48fb323`), localbin (`c0be97f2`), live-boot (`ccd2bb62`) — **landed on main**. Do not redo.

Parent session also noted login + Settings agents stopped on a **Cursor billing block**; owner will pay invoice soon.

---

## 5. Known broken user-facing symptoms (still open)

1. **Blank graphical login / blinking cursor** — TTY3 workaround. Greeter + SDDM quarantine are committed as WIP but **not verified on the owner's machine after reboot**.
2. **Hub + NYXUS Power gap at the TOP** — `3de4a38b` overshoot; no fix in salvage commits.
3. **Hub background** — owner still wants one (separate from art repoint).
4. **Login card redesign** — eye candy, time, weather for his location, settings for it (Settings Increment 2 + greeter UI).
5. **Settings completeness** — Increment 1 only; not Windows/Apple-complete.
6. **Custom file layout assessment** — AskQuestion interrupted; never answered.
7. **Final deep audit loop** — not started.
8. **Live session sync** — done once on Jul 30 evening; tree has moved again (`5b3d3f3b`+); needs another careful sync after login works.

---

## 6. Owner queue / next priorities (ordered)

1. **Restore reliable graphical login** — apply greeter + form-login changes live; quarantine stray SDDM drop-ins; reboot test; keep TTY3 as escape hatch until confirmed.
2. **Fix Hub / Power gap properly** — measure reserved zones + layer geometry; do not blindly revert `top center` without a replacement that covers both phases (before and after overlay-shield).
3. **Finish Settings Increment 2** — greetd login-settings contract (do not drive SDDM); appearance controls; no-terminal criterion.
4. **Login card eye candy** — time / weather / settings (depends on #1 and #3 contract).
5. **Hub background** — owner request.
6. **Docs finish pass** — verify WIP docs against gates; anti-circling.
7. **Custom file layout assessment** — re-ask owner (prior AskQuestion never answered).
8. **Live sync** so owner can see progress without waiting for bake.
9. **Deep audit loop** after the above lands.
10. **Bake** only from a clean, coherent tree after #1–#2 are green.

---

## 7. What NOT to redo (already done)

- `~/.local/bin` empty-dir PATH fix (`c0be97f2`, gate 13z)
- Live-boot NM-wait-online / honeypot / squashfs zstd (`ccd2bb62`)
- Hub eww 200ms SIGKILL / OVERLAY→TOP (`e48fb323`)
- Urban-alien login/power hero visibility (`e18a0b76`)
- Style audit measurement + boards (`c2032e7f` era); do not re-grade for fun
- Art **repoint + deletions** — now in `5b3d3f3b` (do not re-delete)
- Settings dead-control purge — `20953054`
- Bottom-strip arithmetic diagnosis in HANDOFF (the *diagnosis* is right; the *anchor overshoot* still needs a proper fix)
- ALIEN NEON palette lock — do not reintroduce banned colors
- Do not invent a new Settings app — extend `nyxus_settings.py`

---

## 8. Backups (paths)

| Path | Notes |
|---|---|
| `/home/cosmic/nyxus-live-backup-20260730-150614.tar.gz` | Live `~/.config` backup (~333 MB), Jul 30 15:06 |
| `/home/cosmic/nyxus-live-localbin-backup-20260730-150614.tar.gz` | Live `~/.local/bin` backup (~134 MB), Jul 30 15:12 |
| `/home/cosmic/nyxus-palette-live-backup-20260723-185029.tar.gz` | Older palette live backup |
| `/home/cosmic/Backups/` | `nyxus-backup-20260708-021921`, `hypr-backup-20260708-021921`, `nyxus-theme-checkpoints`, `USB-Backups`, etc. |
| `~/Pictures/nyxus-live-sync-2026-07-30/` | Live sync / saver / powermenu screenshots |
| `~/Pictures/nyxus-style-audit-2026-07-30/` | Style audit boards |
| `~/Pictures/nyxus-theme-2026-07-30/` | Theme pass screenshots |

Restore guidance for the Jul 30 live sync is in HANDOFF § "THE BOTTOM STRIP, THE BLUE SCREENSAVER, AND THE LIVE SYNC".

---

## 9. Bake / push policy for this salvage

- **Salvage commits are on `main` and should be pushed** (one-canonical-repo rule: commit + push).
- Tree is **coherent enough to preserve**, not coherent enough to bake:
  - Art repoint + `13ud` looks complete in-repo.
  - Login WIP is untested on hardware.
  - Gap still wrong.
- **Do not bake** until login is verified and gap is fixed.
- If a future agent needs an even safer quarantine, branch name reserved conceptually: `wip/session-recovery-2026-07-31` (not required if `main` holds the WIP commits clearly marked).

---

## 10. Agent / transcript index (quick)

| ID | Role |
|---|---|
| `91476bd9` | Parent Jul 30–31 session |
| `4e21a37e` | Art / theme / repoint |
| `bed1ec20` | Docs audit (barely started) |
| `c5a1095a` | Login repair + gap (incomplete) |
| `d3bdd195` | Settings (Increment 1 done, 2 not) |
| `3c1b58ea` | Live sync / bottom strip (landed; gap overshoot remains) |
| `d5c0c022` | This recovery agent |

---

*End of recovery brief. Keep this file; append rather than rewrite if a later agent continues the salvage.*

---

# APPENDIX A — 2026-07-31 (later) · PICKUP SESSION

Continues the salvage. Written by the session that picked up after the Cursor
swarm and the phone session both stopped. **Everything below was measured on
the running box, not reasoned about.**

## A.1 What the phone session did (commits authored `Claude`, on `main`)

| Commit | What | Verdict |
|---|---|---|
| `58cfc11a` | purge last DARK MIRROR palette from `nyxus_security.py` | kept as-is |
| `096eeef5` | `:y "-40"` on all 8 fullscreen windows — self-described as unverified | **half wrong, corrected** |

`096eeef5` rewrote the `eww.yuck` anchor comment to say the surface never
snaps to `y=0`. That is false — measured, `powermenu` goes 40 → 0 at ~2.2s.
Its `:y "-40"` is right only for windows whose bars never close, and would have
moved the gap to the **bottom** on the rest. Reverted for the `"fg"` windows,
kept for the `"overlay"` ones. The branch `claude/iso-bake-verification-ln6c3v`
is just that session's stale pointer at `58cfc11a`; despite the name, **no ISO
bake verification was done**.

## A.2 The recovery brief's own error (§3 "Phantom note")

§3 records `scripts/nyxus-form-login.sh` showing as `M` while `git hash-object`
matched `HEAD`, and concludes the content was committed. **It was not.** The
salvage created `nyxus-form-login.sh` as a *new* byte-identical file instead of
updating **`nyxus-fix-login.sh`**, which is the name every doc and the script's
own usage line uses. `HEAD:scripts/nyxus-fix-login.sh` was still pre-quarantine,
so the blank-screen fix shipped in a file nothing invokes. Corrected here.

## A.3 Fixed and verified in this session

1. **Login** — quarantine moved onto `nyxus-fix-login.sh`, duplicate deleted.
   Root cause confirmed live (`HELPER_DISPLAYSERVER_ERROR`, Jul 31 02:18; the
   `.bak` drop-in still present). Loop tested against a replica of
   `/etc/sddm.conf.d`. **Still needs root + reboot to apply.**
2. **Hub/Power gap** — fixed by `:stacking`, verified in both phases. See
   HANDOFF's top block for the rule and the numbers.
3. **`overlay-shield.sh` race** — the shield reopened the bars the opener had
   just closed (surfaces 4 → 6 → 8), shoving the overlay back to y=40. 3s grace
   period on the lock age.
4. **`overlay-shield.sh` permanent wedge** — `restore_bars()` left a
   bars-file-less lock dir in place, after which `mkdir "$lock"` failed forever
   and the shield never hid the bars again until reboot.
5. **Installer allowlists** — `nyxus-overlay-open` added to `install.sh` and
   `nyxus_install.sh`; they deploy an explicit list, so new scripts silently
   never reach an installed system. Worth auditing for other recent additions.

## A.4 Still open (unchanged from §6, minus the gap)

Login apply+reboot (needs root) · Settings Increment 2 (greetd contract — **no
code exists**, only transcript intent) · login-card eye candy · Hub background
· docs finish pass · custom file layout assessment (never answered) · live sync
· deep audit · bake. Plus, from the Jul 28 brief and still true: **no ISO has
ever been boot-verified** to show the "Install NYXUS" icon (four now exist), the
EDR pre-filter (~2,000 events/min still dropped), Axiom's AppImage, and the
uncommitted vault repos (RedForge/CIPHER/GSL/Forge/Trainer 5 dirty paths each,
AXIOM 19, honeypot 12) which are still one `git checkout` from being lost.

## A.5 Traps this session adds

- **A new script is not deployed just because it is committed.** Both
  installers carry an explicit script allowlist.
- **`eww reload` can desync the daemon from the compositor** — `active-windows`
  returned empty while Hyprland still had every surface mapped, including a
  stuck `screensaver`. Recovery: `pkill -9 -x eww` (destroys the orphaned
  surfaces) then `nyxus-eww-launch-safe`.
- **Do not probe overlays with bare `eww open`** — `eww open screensaver` hung
  as a live process and left the window mapped. Everything in
  `nyxus-overlay-open` / `nyxus-hub-close` is wrapped in `timeout` for this
  reason; test the same way.
- **Let the bars settle between probes.** Back-to-back open/close runs race
  `nyxus-hub-close`'s async restore and produce duplicated bars (reserved
  `[0,80,0,316]`), which looks exactly like a geometry bug and is not one.

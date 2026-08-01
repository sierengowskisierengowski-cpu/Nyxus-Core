# ISO / VM FULL AUDIT — PICKUP BRIEF (2026-07-31)

> Written ~22:10 EDT 2026-07-31 for the next agent (**Opus 5**).  
> Claude (job `90f4bb96`, Opus 4.8) hit a **session limit** mid–VM audit.  
> That mid-audit was **not pushed** and **not briefed** until this file.

---

## COPY-PASTE PROMPT

```
Pick up NYXUS ISO full audit. Do NOT start new features.

Repo: /home/cosmic/Nyxus-Core (canonical; main only unless a fix branch is required).

1. Read AGENTS.md, HANDOFF.md (WHERE WE STAND), docs/SESSION_RECOVERY_BRIEF_2026-07-31.md,
   and THIS FILE: docs/ISO_VM_AUDIT_PICKUP_BRIEF_2026-07-31.md (primary pickup).
2. Claude (daemon job 90f4bb96) booted iso-builder/out/nyxus-2026.07.31-x86_64.iso in QEMU
   and started a full click-everything audit. Session limit hit ~21:58 EDT while dismissing
   the Welcome Transmission riddle terminal. Mid-audit findings were NOT committed to main.
3. Confirm bake stamp: /etc/nyxus-build on the ISO says source commit 0f77d1c2 (matches tip
   of main when baked). ISO mtime ~19:18 EDT; stamp built 2026-07-31 16:52:09 EDT.
4. Resume / continue the ordered checklist in this brief: boot → greeter → session → bars →
   Hub → Power → stations → settings → apps → keybinds → lock/screensaver. Fill the
   pass/fail matrix BEFORE fixing anything.
5. Recover leftovers: ~/.claude/jobs/90f4bb96/tmp/ (vgl_*.png, vm*.png, qemu still may be
   on VNC 127.0.0.1:8), ~/Pictures/Screenshots/nyxus-20260731-201*.png (owner USB boot),
   uncommitted alacritty 8-digit color fix on main working tree, feat/lock-greeter-frosted
   worktree (nyxbuild fix + docs/AUDIT_2026-07-31.md — NOT in the baked ISO).
6. Fix only after documenting. Then re-verify the same checklist items. Update HANDOFF.md
   WHEN WE STAND when the audit pass is done (or when you hand off again).
```

---

## Date / time / identity

| | |
|---|---|
| **Brief written** | 2026-07-31 ~22:10 EDT |
| **Bake tip SHA (expected)** | `0f77d1c2` — confirmed in ISO `/etc/nyxus-build` |
| **ISO** | `iso-builder/out/nyxus-2026.07.31-x86_64.iso` (~7.9G, mtime **2026-07-31 19:18**) |
| **Stamp text** | `built: 2026-07-31 16:52:09 EDT` · `source commit: 0f77d1c2 (branch: main)` · `kernel: kage-ryu (default) + stock linux (rescue)` · label `NYXUS_2026_07` |
| **Repo HEAD at brief time** | `0f77d1c2` on `main` == `origin/main` (alacritty.toml dirty, untracked `.claude/`) |
| **Claude session** | `90f4bb96-b425-4c80-8d61-258e3492cf93` · job dir `~/.claude/jobs/90f4bb96/` · **state: blocked** ("session limit · resets 12:30am America/Detroit") |
| **VM at handoff** | QEMU still running (started ~21:37): `-cdrom …/nyxus-2026.07.31-x86_64.iso`, disk `~/vm-test/nyxus-install-test.qcow2`, **VNC `127.0.0.1:8`**, QMP `~/.claude/jobs/90f4bb96/tmp/vmqmp.sock`, helpers `vmqmp.py` / `vmctl.py` |

Stamp extract (no sudo): `bsdtar -xOf ISO arch/x86_64/airootfs.sfs > …/airootfs.sfs` then `unsquashfs -f -d …/root …/airootfs.sfs etc/nyxus-build`. Cached copy may exist under `/home/cosmic/iso-verify/2026-07-31/`.

---

## Explicit mandate

**Do NOT start new features.** Finish the full ISO audit first. Document pass/fail. Fix only after documenting. Re-verify. Then update HANDOFF.

Owner intent (from Claude history): drive everything already built to a **known-good baseline** — nothing blank, dead, stale, or broken — before adding more.

---

## What Claude was doing (recovered)

### Session arc
1. Earlier today: live-box login (greetd), Settings theming / no-terminal, PR #83/#84 work — separate from the ISO click-audit.
2. Owner USB-booted the new ISO; reported findings (below).
3. Claude opened `docs/AUDIT_2026-07-31.md` (flawless-baseline ledger) on branch **`feat/lock-greeter-frosted`** (worktree `Nyxus-Core/.claude/worktrees/nyxus-pickup-20260731`) — **not on `main`**, **not in the baked ISO**.
4. Claude fixed **`nyxbuild` greeter leak** as `4077bbb2` on that branch — **after** the bake of `0f77d1c2`, so **tonight's ISO still has the bug**.
5. Claude started a **KVM QEMU** boot of the baked ISO (~20:40–21:58) with VNC + QMP screenshots (`vgl_*.png`, `vmc*.png`).
6. Hit session limit mid-action: trying to dismiss the always-on-top Welcome riddle terminal (`Ctrl+C` / keys via QMP). **No pass/fail matrix committed. No audit findings pushed to `main`.**

### Owner USB boot (physical MSI) — reported to Claude ~20:16 screenshots

Photos: `~/Pictures/Screenshots/nyxus-20260731-201535.png` … `201636.png`.

| Observation | Notes |
|---|---|
| Splash → login ~**21s** | Owner: big win vs prior |
| Greeter correct (urban-alien) | PASS (visual) |
| First greeter user **`nyxbuild`** | Lockout until reboot; second boot showed `nyx` |
| Wallpaper OK; bars delayed minutes | First-boot bootstrap / slow USB |
| Livewall UFO animation eventually | PASS (late) |
| Stations mostly dead; ARSENAL opened app that wouldn't load | Likely first-boot contention — re-judge after install settles |
| Hub seemed OK | Partial |
| Polkit auth prompts; **postgresql.service** auth dialog | Real finding |
| Settings never showed after Super+Space launch | Suspect first-boot / not themed launcher |
| Notifications lagged; "still installing" + **"AI Defense Trainer did not become ready"** (ANSI codes leaked as `[]|31m`) | First-boot noise + trainer readiness |
| Shadow boxes back | Theming / layerrules |
| hyprlock lockout | Known; agents must not run hyprlock |

Claude's take: much of the "won't load" behavior on **live USB** is first-boot installing off a slow stick; honest judgment needs **installed system** (calamares → disk) or a settled VM session after bootstrap finishes.

### Claude VM audit — findings recovered from transcript + screenshots

Artifacts: `~/.claude/jobs/90f4bb96/tmp/vgl_*.png`, `vm*.png`, `verify.log` / `verify2.log` (profile verify — green, not the click-audit).

| # | Finding | Status at session death |
|---|---|---|
| V1 | Greeter boots clean, urban-alien, session `Hyprland (uwsm-managed)` | Observed PASS |
| V2 | Default user **`nyxbuild`** still on this ISO (`0f77d1c2`); dropdown also has `nyx` | FAIL (fix on branch `4077bbb2`, not baked) |
| V3 | Login as `nyx` / `nyx` works once selected (after GL VM setup) | Observed PASS |
| V4 | Desktop after dismiss: HUD top bar, stations list, dock, saucer clock, mood boombox — "show-stopper" look | Observed PASS (visual) |
| V5 | **Welcome Transmission riddle terminal always-on-top** blocks desktop / calamares / polkit until dismissed | FAIL — mid-debug when limit hit |
| V6 | Alacritty: `failed to parse rgb color 0x8CEEF2FA` (8-digit hex) | FAIL — **partial fix uncommitted on main working tree** (3 alacritty.toml paths) |
| V7 | Installer present as **"Install System"** (calamares) in launcher | Observed present; launch blocked by V5 |
| V8 | Full settings / stations / Hub / Power / keybinds / lock click-through | **NOT DONE** |

**Honest recovery limit:** There is **no written pass/fail matrix** from Claude. Findings above are reconstructed from transcript text + screenshots. Treat anything not listed as **NOT TESTED**.

### Uncommitted / off-main leftovers (do not lose)

| Item | Where |
|---|---|
| Alacritty `0x8CEEF2FA` → 6-digit hex | Dirty on `main`: `artifacts/api-server/nyxus-scripts/alacritty.toml`, theme copy, `iso-builder/.../skel/.../alacritty.toml` |
| `nyxbuild` teardown fix | `4077bbb2` on `feat/lock-greeter-frosted` / worktree — **needs merge + rebake** to land on ISO |
| Flawless audit ledger | Worktree only: `docs/AUDIT_2026-07-31.md` (copy/merge onto main when appropriate) |
| Open PR #84 | Frosted hyprlock + greeter — owner-preview; **do not promote during audit** unless owner asks |
| Live QEMU | May still be up on VNC `:8` — reconnect before spawning a second VM |

---

## Ordered checklist (finish this first)

Work top to bottom. Mark each row in the matrix. Prefer **installed** disk or a VM that has finished first-boot bootstrap before judging app/station failures.

1. **Boot** — dragon/UEFI menu → Kage-Ryu #0 → splash → greeter timing
2. **Greeter** — art, user list (must default **`nyx`**, not `nyxbuild`), session picker, login `nyx`/`nyx`, reboot/power
3. **Session** — Hyprland starts; wallpaper; first-boot notifications settle; `/etc/nyxus-build` matches `0f77d1c2` (or newer if rebaked)
4. **Bars** — top HUD + left stations + right dock + bottom saucer; no permanent reserved-zone gaps
5. **Hub** — open/close; no 40px top strip; background readable
6. **Power** — NYXUS Power; lock/logout/reboot; no top gap; Lock Screen authenticates (not fake overlay)
7. **Stations** — HOME / START / GHOST / FORGE / LAB / ARSENAL (+ WAVE/CORE/…); launches or guarded no-op only
8. **Settings** — opens themed; Login Screen = greetd contract (not dead SDDM); sample pages; no crash
9. **Apps** — terminal (no Alacritty color error), Firefox, Install System/calamares, key arsenal tools; note first-boot vs real fail
10. **Keybinds** — Super+Space launcher, Hub/Power binds, cheatsheet; no dead binds
11. **Lock / screensaver** — **owner runs hyprlock** (agents: do not); screensaver edge-to-edge; dismiss clean

Also note: Welcome Transmission / honeypot riddle terminal behavior (V5).

---

## Pass / fail matrix template

Copy into your notes / append to this file or `docs/AUDIT_2026-07-31.md` as you go.

| ID | Area | Item | Result (PASS/FAIL/SKIP/NOT TESTED) | Evidence (shot / note) | First-boot only? | Fix commit (if any) | Re-verified? |
|---|---|---|---|---|---|---|---|
| B1 | Boot | Kage-Ryu entry boots | | | | | |
| B2 | Boot | Splash → greeter | | | | | |
| G1 | Greeter | Urban-alien art | | | | | |
| G2 | Greeter | Default user is `nyx` | | | | | |
| G3 | Greeter | Login `nyx`/`nyx` | | | | | |
| S1 | Session | Desktop paints | | | | | |
| S2 | Session | Build stamp matches bake | | | | | |
| S3 | Session | Bootstrap eventually ready | | | | | |
| R1 | Bars | Top HUD present | | | | | |
| R2 | Bars | Side bars + dock | | | | | |
| H1 | Hub | Opens, no top gap | | | | | |
| P1 | Power | Opens, no top gap | | | | | |
| P2 | Power | Lock authenticates | | | | | |
| T1–Tn | Stations | Each station | | | | | |
| C1 | Settings | Opens themed | | | | | |
| C2 | Settings | Login page = greetd | | | | | |
| A1 | Apps | Alacritty no color error | | | | | |
| A2 | Apps | Calamares / Install System | | | | | |
| A3 | Apps | Browser / others | | | | | |
| K1 | Keybinds | Launcher + Hub/Power | | | | | |
| L1 | Lock | hyprlock (owner only) | | | | | |
| L2 | Saver | Screensaver fullscreen | | | | | |
| W1 | Welcome | Riddle terminal not blocking | | | | | |
| X1 | Misc | No spurious polkit (postgres) | | | | | |
| X2 | Misc | No ANSI leak in notifs | | | | | |
| X3 | Misc | Shadow boxes | | | | | |

---

## Fix policy

1. **Document first** — fill matrix rows (FAIL with evidence).
2. **Fix in small commits** on `main` (or a short-lived fix branch → PR) — one concern per commit.
3. **Re-verify** the same matrix IDs after each fix (or after rebake if ISO-only).
4. **Do not** merge `local-stash-work`. Do not treat live `~/.config` sync as ISO proof.
5. **hyprlock:** owner-only; agents have stranded the session before.
6. When the audit pass is complete (or you must stop), **update HANDOFF.md WHERE WE STAND** and append results here or to `docs/AUDIT_2026-07-31.md`.

### Likely first fixes (after documenting — not before)

1. Commit the pending Alacritty 8-digit color fix on `main` (already edited in tree).
2. Land `4077bbb2` (`nyxbuild` teardown) onto `main` and **rebake** before calling greeter PASS on a fresh stick.
3. Welcome Transmission always-on-top / focus — find launcher config; must not block calamares.
4. postgresql.service polkit prompt — rule or don't auto-start needing auth on live session.
5. ANSI codes in notify text for trainer readiness.

---

## Pointers / traps

- **One repo:** `~/Nyxus-Core` only.
- **Sync live ≠ ISO.** Stick or VM boot is the truth for ship claims.
- **Installer allowlists** — new scripts need `install.sh` / `nyxus_install.sh` entries or they never deploy.
- Profile verify was already green (`verify.log` in Claude tmp); that is **not** a substitute for click-audit.
- Cursor agent transcripts under `~/.cursor/projects/home-cosmic-Nyxus-Core/agent-transcripts/` are mostly pre-ISO-audit; the rich trail is **`~/.claude/projects/-home-cosmic/90f4bb96-….jsonl`** + job tmp screenshots.

---

*End of pickup brief. Next agent: paste the COPY-PASTE PROMPT, then work the checklist.*

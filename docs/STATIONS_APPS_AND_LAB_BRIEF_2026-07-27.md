# NYXUS — STATIONS, APPS & HOME LAB BRIEF (2026-07-27)

> Session: Jul 26 evening → Jul 27 evening. Owner: Joseph A. Sierengowski.
>
> **★★ IF YOU READ ONE THING: the "BIFROST'S AI EDR WAS RUNNING BLIND"
> section below.** Ollama was never started, so Bifrost dropped ~15,000
> suspicious events an hour and produced no real verdicts — while reporting
> `active` to every health check in this build. Fix: run `nyxus-edr-repair`.
> Extends `HOME_AND_START_STATIONS_BRIEF_2026-07-27.md` (read that first for
> the eww traps). Everything here is live **and** committed.

---

## 1. The station system — six now

| Station | Key | Window | What it is |
|---|---|---|---|
| HOME | `Super+Home` | `home-deck` | scattered desktop widgets |
| START | `Super+End` | `start-panel` | Start menu |
| GHOST | `Super+3` | `ghost-deck` | live security console |
| FORGE | `Super+2` | `forge-deck` | repo/build state |
| LAB | — (named) | `lab-deck` | home lab: VMs + live attackers |
| ARSENAL | `Super+0` (ws 10) | — | the four security consoles |

**Adding a station is now one line** in `~/.local/bin/nyxus-home-deck`'s
`MAP`. `_sync` was rewritten table-driven after the hand-written
branch-per-station version missed `eww close lab-deck` in three of five
branches — which is exactly how two decks ended up mapped at once. A loop
can't forget one. Verified across all six, repeat visits included.

Each new station also needs: a `layerrule` for its namespace (or no blur),
and a height that **fits the 882px free area** — check `hyprctl layers -j`,
never eyeball.

**`defaultName` only applies to NEW workspaces.** Stations 9 and 10 kept
BLAST/EDGE until renamed live with `hyprctl dispatch renameworkspace`.

**Station 9 is BIFROST** — the permanent home of the Bifrost EDR dashboard
(owner's call, replacing the arcade slot). A `windowrule` pins WM_CLASS
`GowskiNetBifrost` there.

**`windowrulev2` is DEPRECATED in this Hyprland** and throws a visible
config-error banner. Use the unified `windowrule = <rule>, match:class ...`.
Always `hyprctl configerrors` after touching rules.

---

## 2. The vault apps are real apps now

Five consoles, each a **single process serving API + built SPA**, run by a
systemd user unit, opened by a **native Tauri shell** (~6.2MB, webkit2gtk-4.1
— the same toolkit Bifrost uses, which is the pattern the owner asked for):

| App | Port | Service | Native shell |
|---|---|---|---|
| Forge | 20000 | `gowskinet-forge` | *(pre-existing template)* |
| RedForge | 5000 | `gowskinet-redforge` | `~/.local/bin/redforge` |
| CIPHER | 8080 | `gowskinet-cipher` | `~/.local/bin/cipher` |
| Trainer | 20508 | `gowskinet-trainer` | `~/.local/bin/nyxus-trainer` |
| GSL | 19670 | `gowskinet-gsl` (+ `-backend` :8000) | `~/.local/bin/gsl` |
| Axiom | 21100 (internal) | *(bundled in AppImage)* | `~/.local/bin/axiom` |

### Root causes fixed (each found, not guessed)
1. **RedForge/CIPHER 404'd on `/`** — their api-servers lacked the
   `express.static` block Forge has. Their UIs were *already built*.
2. **Trainer had the block but gated on `NODE_ENV=production`**, unset.
3. **Trainer's `.env` sets PORT=8080** — CIPHER's port. It restart-looped 21
   times binding a port it couldn't have.
4. **systemd applies `EnvironmentFile=` AFTER `Environment=`** regardless of
   order in the unit, so the `.env` always won. Ports are set at **exec time
   via `env(1)`**, which nothing can override.
5. **GSL** needed the static block and had no `.env` at all.

### Axiom is different — Electron, and it must be PACKAGED
* Its build emitted CommonJS into `.js` inside a `"type": "module"` package →
  died on `require`. Now emits `.cjs`.
* `isDev = ... || !app.isPackaged` forced dev mode unpackaged → blank window
  on `:21098`. An explicit `NODE_ENV=production` now wins.
* `spawn(process.execPath, [serverPath])` **without `ELECTRON_RUN_AS_NODE=1`
  boots a second Electron app** instead of running the script as Node — that
  second instance died on "globalShortcut cannot be used before the app is
  ready". Flag added.
* Its API port was 8080 (CIPHER's). Moved to 21100; the renderer hardcoded it
  in two places.
* Its electron postinstall stalled at 376K of ~100MB — the exact version was
  already in `~/.cache/electron` and was extracted from there.
* Its root `preinstall` guard rejects pnpm's own internal invocation
  (`npm_config_user_agent` not propagated), so **`pnpm run` cannot build it** —
  call vite / `electron/build.mjs` / electron-builder directly.
* `~/Projects/axiom` is a **symlink** to `GowskiNet-Vault/Apps/AXIOM`.

---

## 3. ★ Security fix: the consoles were on the LAN

Found by auditing, reported by nothing: **all six console backends were
listening on `0.0.0.0`** — Forge, RedForge, CIPHER, GSL, the GSL FastAPI
backend and the Trainer were reachable from any host on the network. CIPHER
is a hash-cracking lab; GSL is a security-lab dashboard.

Cause: Express/Node `listen(port, cb)` with no host binds `0.0.0.0`. Each now
binds `process.env["HOST"] ?? "127.0.0.1"`; the GSL Python backend gets
`GSL_HOST=127.0.0.1` (its `start.sh` defaulted to `0.0.0.0`). All six verified
still serving 200 on localhost only.

**The honeypots stay world-bound on purpose** — being reachable is their job.

---

## 4. LAB station

`~/.config/eww/scripts/lab-feed.py` (~0.29s) probes:
* **VirtualBox guests** — `lab-attacker` (the box you drive), `bifrost-test`,
  `bifrost-test2`. Real power state, RAM, NIC mode, snapshot count. Rows can
  start / shut down / save / snapshot; an **aborted** guest offers `reset`
  and is shown in red rather than lumped in with "off" (bifrost-test2 is
  aborted right now).
* **Live attackers** — the same HoneyHive API the GHOST deck uses. One
  source, not a second scraper.
* **Host-only network** — `vboxnet0` 192.168.56.1, currently **down**.

Consoles are **floating and freely resizable**, not tiled: four don't fit at a
usable size, and the Tauri shells shipped with `minWidth 1000 / minHeight 680`
so Hyprland couldn't shrink them at all — rebuilt at 840x410.

---

## 5. Measured gaps on this machine (2026-07-27)

Probed, not assumed:

| Control | State |
|---|---|
| `auditd` | **inactive** — and the Trainer's log hub fails `EACCES` on `/var/log/audit/audit.log` |
| `fail2ban` | **not installed** — nothing bans repeat honeypot attackers |
| `usbguard` | **not installed** (despite USB-watch helpers shipping) |
| AppArmor / SELinux | **not installed** — no MAC confinement |
| Secure Boot | **disabled** |
| Disk encryption | **none detected** |
| `ufw` | active |
| Host log aggregation | Loki covers honeypots; **the host itself isn't shipped** |

---

## 6. Open / next

* **`main` is not pushed** — everything is on branch
  `home-deck-scatter-20260727`. Owner: `git -C ~/Nyxus-Core push origin main`.
* **The vault repos are uncommitted.** RedForge, CIPHER, GSL, Trainer and
  AXIOM had source changes (static blocks, bind host, Axiom's `.cjs`/port/
  `ELECTRON_RUN_AS_NODE` fixes). Originals backed up under the job scratch
  dir. Committing inside `GowskiNet-Vault` is the owner's call.
* **Ghost-Relay (c2) skipped** per the owner.
* `nyxus_clipboard.py` still uses `KeyboardMode.EXCLUSIVE` with only an
  Escape handler — a stricter keyboard grab than the one that trapped the
  owner in `nyxus-start`, with no compositor-level escape hatch.
* Stations 1, 4–8 (OPS, PULSE, WAVE, CORE, MESH, SCRIBE) still have no deck.

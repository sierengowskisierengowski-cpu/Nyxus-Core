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

---

## ★★ CRITICAL — BIFROST'S AI EDR WAS RUNNING BLIND (found 2026-07-27)

**Read this before trusting any EDR verdict from before 2026-07-27.**

### What was wrong

`heimdall.guardian` (bifrost-guardian.service) calls Ollama on **every event**:

```
http://127.0.0.1:11434/api/chat   model=qwen2.5:1.5b-instruct
```

**Ollama was installed but `disabled` and had never been started.** Nothing was
listening on 11434, so every call returned:

```
<urlopen error [Errno 111] Connection refused>
```

### What that did — straight from the journal

```
[WARNING] Attempt 2/3 failed for guardian_extractor: <urlopen error [Errno 111] Connection refused>
[ERROR]   All 3 attempts failed for guardian_extractor.
[WARNING] Extractor degraded mode: extractor_error
[WARNING] CircuitBreaker guardian_extractor: OPEN          <- then stayed open
[!] AI queue full - dropped suspicious event               <- ~15,000 per hour
          action=LOG effective=LOG severity=INFO           <- EVERY verdict
```

Measured rates on a quiet desktop:
* **2,604 suspicious events dropped in a single 10-minute sample**
* ~15,000 dropped per hour
* In a 45-second window post-fix-attempt: 22 circuit-open lines, 198 dropped
* **100% of verdicts** were `action=LOG effective=LOG severity=INFO` — i.e. the
  engine never produced a real decision, only "logged it"

**So: the AI EDR logged everything, analysed nothing, and discarded the
suspicious events it could not process.** For however long Ollama has been
disabled.

### Why nothing caught it

`systemctl is-active bifrost-guardian` returns **active**. It *is* running —
it just can't think. Every health check in this build (including the GHOST
deck's DEFENSE card and the ARSENAL live dots) reports it green, because they
check the unit state, not whether its analysis pipeline works. It was found
only by asking why the host journal was 97% EDR chatter.

**Lesson for the deck design:** "unit is active" is not "component is
healthy". A future GHOST deck card could watch for
`CircuitBreaker.*OPEN` / `AI queue full` in the journal and show Bifrost as
DEGRADED rather than live — that check is now cheap, because the host journal
is in Loki.

### The fix

```
nyxus-edr-repair
```

Needs root. It enables the ollama system unit, waits for :11434, pulls
`qwen2.5:1.5b-instruct` if missing, restarts bifrost-guardian, then prints
before/after counts of circuit-open lines, dropped events and verdict types.

Verified during the session: after starting ollama in userspace and pulling
the model, the exact endpoint Bifrost calls answered correctly. The circuit
breaker will not close until the daemon restarts.

### Watch after applying

```bash
# should be zero / near zero
journalctl --since '5 min ago' -u bifrost-guardian | grep -c 'CircuitBreaker.*OPEN'
journalctl --since '5 min ago' | grep -c 'AI queue full'

# should show more than just severity=INFO
journalctl --since '5 min ago' -u bifrost-guardian -o cat \
  | grep -oE 'action=[A-Z]+ effective=[A-Z]+ severity=[A-Z]+' | sort | uniq -c
```

`gowskinet-forge.service` also declares `Wants=ollama.service`, so Forge's AI
features were affected by the same root cause.

### ⚠ Do NOT trim EDR log volume with a priority filter

jeTT + Bifrost emit **~100,000 lines/hour** and are **97% of this machine's
journal**. But they log *everything* at **priority 6 (INFO)** — severity lives
in the **message text** (`[WARNING]`, `[!]`, `✅ ALLOW`). Measured:
`journalctl --priority=5` keeps **1.3%** of lines, and would discard real
detections along with the ALLOW spam. **Tune the daemons' own log level
instead of filtering at the shipper.**

Note also that a large share of jeTT's ALLOW spam is NYXUS itself — the
station decks poll `hyprctl`, `jq` and `pgrep` on timers, and each spawn is a
process event jeTT evaluates.

### UPDATE — after Ollama came up (same evening)

Bifrost **recovered on its own retry**, no restart needed. The journal now
shows real work:

```
[INFO] heimdall.guardian - Ollama inference model=qwen2.5:1.5b-instruct duration_ms=2947
```

Circuit-open lines: **0**. But events are still being dropped, and the reason
is now completely different — **throughput, not connectivity**:

* 63 inferences in 5 minutes, **avg 3,270ms**, max 4,263ms (on the RTX 3060)
* that is **~18 events/minute of capacity**
* against **~302 events/minute arriving**

So ~94% still can't be analysed. Two things follow:

1. **`heimdall_config.json` sets `llm_timeout_seconds = 5.0`** while real
   inferences take 3.3s average / 4.3s peak. That is uncomfortably close —
   any slowdown starts timing out.
2. **A large share of the event load is NYXUS itself.** Top process events in
   a 2-minute sample: `sleep` 165, `jq` 51, `pgrep` 48, `hyprctl` 45,
   `sort` 42, `sensors` 22, `nmcli` 20, `timeout` 18 — i.e. the eww bar
   scripts and the station decks polling on timers. The new GHOST/FORGE/LAB
   decks added to this.

**The right fix is a pre-filter, not a faster model.** An AI EDR should not be
asked to reason about every `sleep` the desktop spawns. Either allowlist the
NYXUS polling binaries in Bifrost, or lengthen the deck poll intervals, or
both. Throwing a bigger model at 300 events/minute of `jq` will not help.

⚠ **Ollama persistence:** during the session it was served by a *userspace*
`ollama serve`, which dies on reboot. It must be `sudo systemctl enable --now
ollama` or Bifrost goes blind again at next boot — with no warning, because
the unit still reports `active`.

---

## ★★ jeTT WAS BLIND TOO — different cause, same result (found 2026-07-27)

**Both EDRs were degraded at once, for unrelated reasons.** Bifrost's was the
missing Ollama (above). jeTT's is **telemetry**.

### WHICH jeTT — there are TWO installs, check before you touch anything

| | Path | Built | Running? |
|---|---|---|---|
| **LIVE** | `~/Projects/jeTT/target/release/jett-daemon` | **2026-07-17** (680M) | ✅ what `jett-daemon.service` executes |
| Dormant | `/usr/lib/jett/jett-daemon` | 2026-06-12 (656M) | ❌ no unit starts it |

Different builds (`cmp` differs), 5 weeks apart, and `/usr/lib/jett` is owned
by **no package**. Always confirm with:

```bash
systemctl show jett-daemon -p ExecStart --value
```

### WHICH ALLOWLIST — the source copy is not the live one

The binary reads **`/etc/jett/allowlist.conf`** (130 lines) and
**`~/.config/jett/allowlist.txt`** (sha256 pins — currently one entry for
`~/.cache/test/mytool`). The 139-line
`~/Projects/jeTT/config/allowlist.conf` is the **source/example**. Editing
that one has no effect on the running daemon.

### The actual failure

```
[!] eBPF sensor thread exited: ringbuf poll: Interrupted system call (os error 4)
```

The sensor died **2026-07-27 10:35** after the daemon had been up since 00:21,
and never recovered. Its other source, `auditd`, is **inactive** — while the
unit env says `JETT_TELEMETRY=both`. So it has **neither**.

**Proven by probe, not inferred:** a script executed from `/tmp` — which
jeTT's own `SYSTEM_CONTEXT` says to **QUARANTINE** — was never logged at all,
and there were **zero `bash`/`sh` events in 10 minutes** on an active desktop.
Everything it still logged (`sleep`, `jq`, `hyprctl`, `pgrep`) is short-lived
spawns consistent with a `/proc` poller, not exec hooks.

### What is NOT the bug

The `0ms` verdicts are **by design**. `Trusted GowskiNet process` resolves to
`own-stack (hard allow)`, a fast path compiled into the binary, and the
allowlist docs describe a *"Daemon Trusted disposition (0ms, no model)"*.
That is correct behaviour. The bug is that nothing **unknown** ever reaches
the model, because the telemetry that would surface it is dead.

Mode is `JETT_MODE=learn` (observes, does not kill), so probing it is safe.

### ★ SEPARATE GAP — the best model is not deployed

`JETT_MODEL` points at `models/jett-r6-q4_k_m.gguf`. **r11 was trained** — but
only `jett-r11-bf16.gguf` exists on disk, and `jett-pull-r11` expects
**`r11-q4_k_m`**, which is **not present**. So the unit running r6 is not a
misconfiguration: the quantized r11 was never produced or pulled. Quantize or
pull it, then update `JETT_MODEL` in the unit.

(Note `main.rs` hardcodes `jeTT-r3-q4.gguf` as a default, but the unit's
`JETT_MODEL` env overrides it — the daemon runs **r6**, not r3.)

### Fix

`nyxus-edr-repair` restarts `jett-daemon` so the eBPF sensor re-attaches,
enables `auditd` (which also fixes the AI Cyber Defense Trainer's `EACCES` on
`/var/log/audit/audit.log` and closes the audit-trail gap), and prints the
`/tmp` probe to verify. If the sensor exits again, it is a kernel/BPF
permission problem rather than a crash — chase that separately.

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

### ★ The recurring "two decks at once" bug — root cause found

Symptom: FORGE's cards bleeding through GHOST (and earlier, HOME through
START). It kept coming back after each fix because the fixes addressed the
wrong layer.

**Root cause: the flock singleton guard used `$XDG_RUNTIME_DIR`.** That
variable is set in a login shell but **not** in some exec-once/systemd
contexts, so two watcher instances resolved two *different* lock files, both
acquired successfully, and then fought — one opening the deck the other had
just closed. Confirmed live: two parents (pids 6290 and 7007) running at once.

Fixed by pinning the lock to a path that always resolves the same way:

```bash
LOCK="${HOME}/.cache/nyxus-home-deck.lock"
```

Verified: a second instance now refuses with *"another nyxus-home-deck
already holds …"*, and a full station cycle (FORGE→GHOST→LAB→HOME→START→
GHOST→FORGE) gives exactly one window each.

**Lesson:** `$XDG_RUNTIME_DIR` is not dependable for lock paths in anything
launched by the compositor. Use a fixed path.

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

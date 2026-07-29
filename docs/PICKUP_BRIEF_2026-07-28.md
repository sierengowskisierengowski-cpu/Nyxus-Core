# NYXUS — PICKUP BRIEF (2026-07-28 evening)

> **Read this first, then `HANDOFF.md`.** It says exactly where things stand,
> what to do next, and in what order. Owner: Joseph A. Sierengowski.
> Written because the previous session ended mid-bake and the one before that
> ended before it could brief anything.

---

## 0. THE ONE THING TO DO FIRST

**★ RESOLVED — bake #5 (18:42) SUCCEEDED.**

```
[customize_airootfs] INSTALLER OK - calamares is installed in the ISO
installing yaml-cpp...  installing kpmcore...  installing calamares...
SYSLINUX set up for BIOS booting successfully.
GRUB set up for UEFI booting successfully.
```

**ISO:** `iso-builder/out/nyxus-2026.07.28-x86_64.iso` (7.6G, 19:28)
**sha256:** `bd55aedd10d093aabdf385e4ac31f2d31e8c2110f4fdd87610844184b6470561`

REMAINING PROOF: boot it and confirm the **"Install NYXUS"** desktop icon
appears. The log proves the package is in the image; booting proves the
launcher reaches the user. Do not skip this - three ISOs were declared fixed
on reasoning alone and all three shipped broken.

Three AUR builds still fail NON-FATALLY and are worth fixing the same way
calamares was (source a binary instead of building):
`snap-pac` (PGP key E4B5E45AA3B8C5C3 missing from the chroot keyring),
`ananicy-cpp` (C++ compile errors), `appimagelauncher` (missing dep `argagg`).

Historical detail below.

**A bake (started 18:42, log `~/nyxus-bake-2.log`) was RUNNING when this
session ended. Its outcome is UNKNOWN.** Check it before anything else:

```bash
pgrep -af build-iso.sh
grep -E 'INSTALLER OK|DID NOT INSTALL|installing calamares|exists in filesystem' ~/nyxus-bake-2.log
```

See "THE ISO INSTALLER SAGA" below for the full history, the three fixes it
carries, and how to verify properly. The historical note below is kept because
the trap it describes is what wasted an entire bake:

**A bake in flight uses the profile staged at ITS startup - it never picks up
a later fix.**

`build-iso.sh` copies the profile to `/var/tmp` **at startup**, so a bake in
flight does not pick up later fixes. The bake started ~17:08 predates the
calamares fix (commit `9649c943`), so it will print
`CALAMARES DID NOT INSTALL` after ~an hour of work.

```bash
sudo pkill -f build-iso.sh
sudo ~/Nyxus-Core/iso-builder/build-iso.sh 2>&1 | tee ~/nyxus-bake-fixed.log
```

Then, when it finishes:

```bash
grep -E 'INSTALLER OK|DID NOT INSTALL|AUR:' ~/nyxus-bake-fixed.log
```

* `✅ INSTALLER OK — calamares is installed in the ISO` → **done, ship it**
* `❌ CALAMARES DID NOT INSTALL` → read the `AUR:` lines; they now print the
  real pacman error, the mirrorlist, and a curl probe (see §2).

---

## 1. THE INSTALLER BUG — four ISOs, three wrong fixes, one wrong premise

**Symptom:** every ISO (07.26, 07.27, 07.28) booted live with **no installer**.
No "Install NYXUS" icon, no calamares.

**The three previous fixes were all real bugs, all at the wrong layer:**

1. `sudo -u nobody makepkg -s` → `nobody` is a **locked account**, so the
   `sudo pacman` that `makepkg -s` shells out to hit an unanswerable password
   prompt. Fixed with a dedicated build user. That revealed:
2. The chroot ships **no `/etc/pacman.d/mirrorlist`** while
   `airootfs/etc/pacman.conf` points `[core]`, `[extra]` and `[multilib]` at
   it. Archiso leaves it empty deliberately (reflector fills it on first
   boot), so pacman **inside the chroot had zero servers**:
   `error: no servers configured for repository: extra`.
   `calamares` needed `kpmcore` + `yaml-cpp`, both unreachable. Fixed by
   writing a temporary build mirrorlist. **Still failed.**

**The premise under all three was wrong.** Every attempt assumed calamares
*must* be built from the AUR inside the chroot. It does not:

| package | repo |
|---|---|
| `calamares` | **blackarch** |
| `kpmcore` | extra |
| `yaml-cpp` | extra |

All three are **plain binary packages**, and the profile's **build-time**
`pacman.conf` (`iso-builder/nyx-profile/pacman.conf`) **already enables
`[blackarch]`**. So `calamares` is now simply listed in `packages.x86_64` and
**pacstrap installs it directly**.

The installer no longer depends on the chroot having network, a build user, a
sudoers drop-in, or a mirrorlist. That removes the whole failure class instead
of patching a fourth symptom.

`_aur_build calamares` is left in place as a fallback — it early-returns when
`pacman -Qi calamares` already succeeds, so it is now a no-op. The existing
verdict check needed no change: it tests `pacman -Qi calamares`, which
pacstrap satisfies.

**Commit:** `9649c943`

---

## 2. Diagnostics added so this cannot hide again

The AUR `pacman -Sy` used to be `>/dev/null 2>&1`, reporting only
`WARNING pacman -Sy failed (offline build host?)` with no reason. **That one
step silently doomed three bakes.** It now prints:

* the real pacman error (last 15 lines)
* the actual `/etc/pacman.d/mirrorlist` contents
* a `curl` probe of `geo.mirror.pkgbuild.com` with HTTP code and timing

So if any AUR build fails again, the log says **why**.

---

## ★★ THE ISO INSTALLER SAGA — read before touching the bake

**A bake was RUNNING when this session ended.** Check it first:

```bash
pgrep -af build-iso.sh                      # still going?
grep -E 'INSTALLER OK|DID NOT INSTALL|installing calamares|exists in filesystem|failed to commit' \
     ~/nyxus-bake-2.log
```

* started **18:42**, log `~/nyxus-bake-2.log`, staged profile verified to carry all three fixes below
* **outcome unknown at handoff** — do not assume it succeeded

### The failure progression (each attempt died LATER than the last)

| # | Attempt | Died at |
|---|---|---|
| 1-3 | 07.26 / 07.27 / 07.28 ISOs | calamares never built — AUR unreachable inside the chroot |
| 4 | 17:28 bake | calamares **installed**, then hit a file conflict |
| 5 | 18:42 bake (running at handoff) | collider removed — should clear pacstrap |

### Fix 1 — calamares is a BINARY, not an AUR build  (`9649c943`)

Three earlier fixes were each a real bug at the wrong layer: a locked-`nobody`
sudo prompt, then an empty chroot mirrorlist. **All three accepted the same
wrong premise — that calamares must be AUR-built in the chroot.** It must not:

| package | repo |
|---|---|
| `calamares` | **blackarch** |
| `kpmcore` | extra |
| `yaml-cpp` | extra |

All binaries, and `iso-builder/nyx-profile/pacman.conf` (the **build-time**
one) already enables `[blackarch]`. `calamares` is now in `packages.x86_64`
and pacstrap installs it directly — no chroot network, build user, sudoers or
mirrorlist involved. `_aur_build calamares` stays as a no-op fallback (it
early-returns when `pacman -Qi calamares` succeeds).

### Fix 2 — the file collision that broke bake #4  (`ff23e317`)

```
error: failed to commit transaction (conflicting files)
calamares: /usr/share/applications/calamares.desktop exists in filesystem
```

Once calamares is a package it **owns** that path, and the profile was
hand-shipping its own copy. Pacman refuses to overwrite a file it does not
own, so the whole transaction aborted.

Removed `airootfs/usr/share/applications/calamares.desktop` (Version=1.0).
It was redundant: `install-nyxus.desktop` (Version=1.5, adds `TryExec` and
`X-AppStream-Ignore`) says the same thing and is better, and
`etc/skel/Desktop/install-nyxus.desktop` is the icon the user actually clicks.

**Blast radius was checked first:** pacman lists EVERY conflicting file and
named only that one, so the **27 files under `etc/calamares/`** (NYXUS
branding, partition/bootloader/users module configs) are untouched. If a
future conflict appears, read the full list before deleting anything.

### Fix 3 — the duplicate keybind that failed `validate` for a day  (`6137f9cd`)

`scripts/iso-build-verify.sh` fails the ISO-readiness gate on duplicate bind
chords. The search-overlay escape hatch was on `$mod SHIFT, S` — already the
scratchpad. Moving it to `SHIFT, X` collided with nyxus-prism-pulse. It is now
**`$mod SHIFT, Z`**, verified free against every bind. CI is green.

⚠ The validator inspects **only the skel `hyprland.conf`**, not `conf.d`.
Three pre-existing duplicates (`$mod,E`, `$mod,M`, `$mod,Q`) live in the live
`conf.d` tree, are invisible to the gate, predate this work, and were left
alone deliberately.

### ★ THE TRAP THAT WASTED A WHOLE BAKE

**`build-iso.sh` copies the profile to `/var/tmp/nyxus-profile-bake` at
STARTUP.** A bake already in flight will NEVER pick up a later fix. Always
kill and restart after changing the profile, and verify the staged copy:

```bash
P=/var/tmp/nyxus-profile-bake
grep -qxE 'calamares' "$P/packages.x86_64"                     && echo "fix1 ok"
[ ! -f "$P/airootfs/usr/share/applications/calamares.desktop" ] && echo "fix2 ok"
grep -q 'SHIFT, Z, exec, eww close start-search' \
    "$P/airootfs/etc/skel/.config/hypr/hyprland.conf"          && echo "fix3 ok"
```

### If it fails again

`pacman -Sy` in the AUR path no longer discards its output — it now prints the
real pacman error, the mirrorlist contents, and a curl probe of the mirror. So
a failure says WHY instead of leaving the next person to re-derive it for a
fifth time.

### Verifying success properly

* build log: `[customize_airootfs] ✅ INSTALLER OK — calamares is installed in the ISO`
* booted ISO: an **"Install NYXUS"** desktop icon (`pkexec calamares`)

Do **not** declare it fixed from timestamps or reasoning. Three ISOs were
called fixed that way and all three shipped broken.

---

## 3. Where the build is, right now

**Repo:** `main` in sync with GitHub. Everything below is committed and pushed.

**Six stations**, one deck each, driven by one watcher
(`~/.local/bin/nyxus-home-deck`):

| Station | Key | Window |
|---|---|---|
| HOME | `Super+Home` | `home-deck` — scattered desktop widgets |
| START | `Super+End` | `start-panel` — start menu |
| GHOST | `Super+3` | `ghost-deck` — live security console |
| FORGE | `Super+2` | `forge-deck` — repo/build state |
| LAB | named ws | `lab-deck` — VMs + live attackers |
| ARSENAL | `Super+0` (ws 10) | the four security console apps |

Plus **ten companion stations** (spare slots between 1-10, alien marks,
persistent but deliberately **no** `on-created-empty` launch — shipping them
with launches doubled the login footprint from 10 apps to 20).

**Five vault consoles are real apps** — single process serving API + built
SPA, systemd user unit, native Tauri shell:

| App | Port | Unit |
|---|---|---|
| Forge | 20000 | `gowskinet-forge` |
| RedForge | 5000 | `gowskinet-redforge` |
| CIPHER | 8080 | `gowskinet-cipher` |
| Trainer | 20508 | `gowskinet-trainer` |
| GSL | 19670 | `gowskinet-gsl` (+ `-backend` :8000) |

All verified serving 200 on **127.0.0.1 only** (they were on `0.0.0.0` and
LAN-reachable — fixed).

---

## 4. ★ EDR — was blind, now partly fixed

**Bifrost** calls Ollama on every event. Ollama was installed but **disabled
and never started** → connection refused → circuit breaker permanently OPEN →
**~15,000 suspicious events dropped per hour** → every verdict downgraded to
`severity=INFO`. It reported `active` to every health check the whole time.

**jeTT was blind too, unrelated cause:** its eBPF sensor crashed
(`ringbuf poll: Interrupted system call`) and `auditd` was off. A `/tmp`
script it is meant to QUARANTINE went completely unlogged.

**Status now:** `ollama` and `auditd` are both `enabled/active`, circuit
breaker closed, real inference happening.

**STILL OPEN — throughput, not connection:**
* inference ≈ **3,270ms average** → ~18 events/min of capacity
* arrivals ≈ **300+ events/min** → ~2,000/min still dropped
* `heimdall_config.json` sets `llm_timeout_seconds = 5.0` against 4.3s peaks

**The fix is a pre-filter, not a bigger model.** An AI EDR should not reason
about every `sleep` the desktop spawns. A large share of the load is NYXUS's
own polling (`sleep`, `jq`, `pgrep`, `hyprctl`, `sort` — the eww bar scripts
and station decks). Either allowlist those binaries in Bifrost, lengthen the
deck poll intervals, or both.

⚠ **Do NOT trim EDR log volume with a priority filter.** jeTT + Bifrost emit
~100k lines/hour at **priority 6 (INFO)** — severity lives in the message
text. `journalctl --priority=5` keeps **1.3%** of lines and would discard real
detections along with the ALLOW spam.

**Separate gap:** jeTT runs `jett-r6-q4_k_m.gguf`. **r11 was trained** but only
`jett-r11-bf16.gguf` exists; `jett-pull-r11` expects `r11-q4_k_m`, not on
disk. The best model is not deployed. (Note `jeTT:latest` is now registered in
Ollama — worth checking whether that supersedes the gguf path.)

**Two jeTT installs exist.** Live is
`~/Projects/jeTT/target/release/jett-daemon` (2026-07-17).
`/usr/lib/jett/jett-daemon` (2026-06-12) is a different build no unit starts.
Live allowlist is **`/etc/jett/allowlist.conf`**, not the copy in the Projects
tree. Always confirm with `systemctl show jett-daemon -p ExecStart`.

---

## 5. ⚠ UNCOMMITTED WORK IN THE OWNER'S VAULT REPOS

These are **live and working**, but **one `git checkout` loses them**:

| Repo | What is uncommitted |
|---|---|
| RedForge, CIPHER, GSL | `app.ts` (`express.static` fix) + `index.ts` (localhost bind) + `desktop/` Tauri shell |
| Forge, Trainer | `index.ts` (localhost bind) + `desktop/` |
| honeypot | `docker-compose.yml` + `promtail/promtail.yml` (host journal → Loki) |

Committing inside `GowskiNet-Vault` / `~/Projects` is **the owner's call** —
ask before doing it.

---

## 6. Path forward, in order

1. **Kill + restart the bake** (§0). Verify the `INSTALLER OK` line. Nothing
   else matters until the ISO has an installer.
2. **Boot the new ISO** and confirm the "Install NYXUS" desktop icon
   (`pkexec calamares`) actually appears.
3. **EDR pre-filter** (§4) — the single highest-value remaining fix. ~2,000
   events/min are still being discarded.
4. **Commit the vault repos** (§5) once the owner agrees.
5. **Axiom** — the one unfinished app. It opens an 800x600 window then hangs;
   Hyprland raises "Application Not Responding". Its API never binds. Root
   cause found: `extraResources` never shipped `api-server/node_modules`, so
   the spawned server dies on `require("better-sqlite3")`. A staged
   dereferenced copy (`.bundle-node_modules`) and a compiled
   `better_sqlite3.node` were prepared and a repack was in flight when the
   session ended — **verify the AppImage and retest**.
   NOTE `~/Projects/axiom` is a **symlink** to `GowskiNet-Vault/Apps/AXIOM`.
6. **Hacker mode** — now a real full-surface flip (decks + all four bars go
   green phosphor via a `.nyx-hacker` class driven by `SECSTATE.hacker`), and
   a later session took it to black/white/red with a saucer alien. The owner
   wants **everything** to turn: the remaining holdouts are the **PNG art**
   (saucer / boombox / notification saucer) and the **wallpaper**. CSS cannot
   recolour a PNG — generate green/mono variants with ImageMagick and swap
   them via inline `:style` on `SECSTATE.hacker`.
7. **Stations 1, 4-8** (OPS, PULSE, WAVE, CORE, MESH, SCRIBE) still have no
   deck. They should be cheap now — see §7.

---

## 7. Traps that will cost you hours if you do not know them

* **eww sizes a window to its CONTENT.** A `:geometry` height is a request,
  not a cap. Content taller than the free area between the bars (1080 − 40
  bar-top − 158 bar-bottom = **882px**) makes Hyprland centre the oversized
  surface and park it at a **negative y**. Verify with `hyprctl layers -j`,
  never by eye.
* **`:focusable true` is a session-wide keyboard grab.** eww 0.5 maps it to
  wlr-layer-shell **EXCLUSIVE**. The owner reported it twice as "froze". Only
  the short-lived `start-search` window may be focusable.
* **`pkill -f <pattern>` from an inline `bash -c` kills its own shell**
  (exit 144) — the caller's cmdline contains the pattern. Run it from a file.
* **`$XDG_RUNTIME_DIR` is not dependable for lock paths** in anything the
  compositor launches. It is unset in some exec-once contexts, which made two
  watcher instances take two different locks and fight — that was the real
  cause of the recurring "two decks at once" bug. The lock is now pinned to
  `~/.cache/nyxus-home-deck.lock`.
* **`windowrulev2` is DEPRECATED** in this Hyprland and throws a visible
  config-error banner. Use `windowrule = <rule>, match:class ...` and always
  run `hyprctl configerrors` after touching rules.
* **`defaultName` only applies to NEW workspaces** — rename existing ones with
  `hyprctl dispatch renameworkspace`.
* **No `sass` is installed.** `compile-eww-css.sh` silently no-ops and reuses
  the committed `eww.css`. Patch `eww.css` **surgically** alongside
  `eww.scss.source`; never wholesale-recompile (it shifts the palette).
* **Never `str.replace()` bare words across `eww.yuck`** — substituting
  `POWER`/`TERM`/`LOCK` once corrupted `POWERPROF` into `PROF` and broke the
  whole config. Use `@@DELIMITED@@` tokens. Snapshot `eww.yuck` first.
* **Changes must land on THREE surfaces:** live `~/.config/`, repo
  `artifacts/api-server/nyxus-scripts/`, ISO skel
  `iso-builder/nyx-profile/airootfs/etc/skel/`. A missing directory will make
  `cp` fail silently — `artifacts/.../hypr/conf.d` did not exist once and
  three station conf shards were never copied.

---

## 8. Standing instructions from the owner

* **DO NOT enable `fail2ban`.** It repeatedly locked him out. It stays off
  until he is on his final system and asks for it.
* **Skip Ghost-Relay (c2).** Explicitly out of scope.
* **Do not push to `main` on his behalf** — he pushes it himself.
* The build must stay a **daily driver** as well as a security machine, and he
  wants genuine eye candy, not just function.

---

## 9. Structural things worth raising (not yet done)

* **The honeypot stack runs on the daily driver**, in docker, bound to
  `0.0.0.0`. Moving it onto the `lab-attacker` VM does more for this machine's
  security than any additional tool.
* **No Suricata/Zeek** — nothing watches the machine's own wire.
  `nyxus-suricata-setup` is written and ships in the ISO; suricata is now in
  `packages.x86_64`.
* **Secure Boot disabled, no disk encryption** on the live box. Note that
  `auditd`, `apparmor`, `usbguard` and `firewalld` **are** in the ISO and
  enabled at bake — those gaps are live-box only, not build gaps.
* `nyxus_clipboard.py` uses `KeyboardMode.EXCLUSIVE` with only an Escape
  handler — a stricter keyboard grab than the one that trapped the owner in
  `nyxus-start`, with no compositor-level escape hatch.

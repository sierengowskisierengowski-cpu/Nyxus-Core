# NYXUS — Master Brief: Last Day of Building

> **Snapshot:** 2026-07-24 · ~11:50 EDT  
> **Repo:** `~/Nyxus-Core` · branch `main` · HEAD at write time → check `git rev-parse --short HEAD`  
> **Audience:** owner + next agent  
> **Purpose:** one place that explains *what the last ~day of build work was about*, what landed, what’s still open, and why the next bake matters.  
> Living bake status still lives in [`HANDOFF.md`](../HANDOFF.md) (**WHERE WE STAND**). Theme workstream detail: [`ALIEN_NEON_SETTINGS_BRIEF.md`](./ALIEN_NEON_SETTINGS_BRIEF.md).

---

## 1. The story in one page

The last day was not “add features for fun.” It was **closing the loop** between a broken live stick, a red CI, a locked look, and a bake that actually ships what the desktop already does on the builder machine.

**Arc:**

1. **Live stick lied.** Older ISOs (`nyxus-2026.07.22` / early `07.23` / morning `07.24` @ 03:05) booted without the repo’s real fixes — partial bakes, dead Replit bootstrap, missing launchers, wrong wallpaper paths, Kage unable to mount the ISO.
2. **Delivery model got honest.** Desktop = skel (offline) + first-boot bootstrap from `/opt/nyxus-cache` (never phone home to dead Replit). Installer must deploy the full launcher set or “eye candy” silently never starts.
3. **Look locked.** ALIEN NEON (prism-only, no wallpaper→accent drift, cream banned). Urban-alien on greeter / lock / screensaver. Alien-only walls. GRUB dragon retitled.
4. **CI / bake gates repaired.** `verify-profile` corrupted by palette sed; GitHub `build-iso` can’t see local Kage pkgs → dispatch-only stock validation. Filename `nyx-*.iso` → `nyxus-*.iso`.
5. **Live-boot pain fixed in repo.** eww minutes-long first paint (`npx sass`), black box, hyprpm header spam, build stamp in terminals — landed via PR #71 → #72 on `main`.
6. **Pre-bake hygiene.** W1 `profiledef` permissions, W6 arsenal/reactive shards actually ship, Copilot GO/NO-GO stored in HANDOFF.
7. **Theme Phase 1.** Palette + Settings chrome + Theme Packs prism-only + Welcome wizard polish (PR #73).
8. **Welcome Transmission.** Borderless kitty poem/riddle on first login; solve → Dream Protocol (`Super+Alt+D`).
9. **Stand now.** `main` clean, pushed, **0 open PRs**, bake-ready. Old ISO on disk is **stale**. Owner rebakes + reflashes.

---

## 2. Timeline (≈ Jul 23 → Jul 24 midday)

| When | What happened |
|---|---|
| **Jul 22–23** | Stick boots broken / “offline install failed”; partial bake missed ungated bars; Replit 404 mislabeled as no-internet |
| **Jul 23** | Offline-first bootstrap; install `set -e`/`clear` fix; eww.scss path; wallpaper `/home/nyx`; Kage becomes **default** kernel (stock = rescue) |
| **Jul 23 round 2** | Root cause of missing eye candy: ISO installer only deployed ~5 of ~82 launchers; restored mission/hotkey/qs/snap/dock daemons; builder-home de-leak |
| **Jul 23 evening** | ALIEN NEON lock; cream purge; `follow_wallpaper` OFF; alien-only walls; SDDM/cinematic packs purged |
| **Jul 23** | QEMU: Kage live entry fails — no iso9660/squashfs/loop in lean kernel config → PKGBUILD patched |
| **Jul 24 early** | Green-light CI: fix `verify-profile`, `build-iso.yml` stock-only on runners, rename ISO artifact |
| **Jul 24** | Urban-alien on greeter/lock/screensaver; hypridle retimed (5m saver → 10m lock → 15m suspend) |
| **Jul 24** | UFO audit: living wallpaper + notif icon wired; companion mascot still disabled by choice |
| **Jul 24 ~03:05** | ISO `nyxus-2026.07.24` baked — **before** #71/#72 and today’s work → **do not reflash for current fixes** |
| **Jul 24 AM** | PR #71 live-boot fixes stranded off `main`; PR #72 lands them; W1 + W6; Copilot pre-bake audit |
| **Jul 24 ~08:53** | Kage `7.0.12` pkgs on disk (iso9660-capable PKGBUILD); owner later reports kernel done — still verify on stick |
| **Jul 24 late morning** | Welcome Transmission + Dream egg; PR #73 Phase 1 merged; status brief; this master brief |
| **Now** | Rebake from idle `main`, flash **new** ISO, verify |

---

## 3. What’s done (grouped)

### Boot / install / delivery
- Offline-cache-first bootstrap; Replit retired from the boot path  
- `nyxus_install.sh` no longer dies on `clear` / missing eww.scss  
- Full launcher + eww-helper deploy (eye candy actually starts)  
- De-leak `/home/cosmic` → real `$HOME` on first boot  
- Build stamp `/etc/nyxus-build` + bashrc greeting (ALIEN NEON colors)  
- `BOOTSTRAP_VERSION` → `2026.07.24-r13-fixes`

### Kernel
- Kage-Ryu = default live + installed; stock = rescue only  
- Bake hard-fails if Kage pkgs missing  
- PKGBUILD forces live-ISO substrate (iso9660 / squashfs / loop)  
- Pkgs present locally (`7.0.12` ~08:53 EDT Jul 24)

### Look / surfaces
- ALIEN NEON locked (violet `#7d3dff`, magenta `#ff2dad`, green `#39ff14`, orange `#ff8a1e`, void `#05060a`, cool white `#eef2fa`)  
- Urban-alien greeter, hyprlock, screensaver; hypridle layout corrected  
- Alien-only wall sets; GRUB dragon “NYXUS · ALIEN NEON · KAGE RYU”  
- Phase 1 Settings: prism-only Theme Packs, chrome reskin, Welcome polish (PR #73)

### Desktop UX fixes (in repo; need rebake on stick)
- eww first paint no longer blocked by `npx sass`  
- Transparent bar window / black-box path addressed  
- hyprpm header spam skipped when headers absent  
- Welcome Transmission (kitty) + Dream Protocol easter egg

### Bake / CI hygiene
- Throwaway profile copy (bake doesn’t corrupt repo)  
- W1 `profiledef` file_permissions regenerated  
- W6 arsenal + reactive hypr shards actually ship + `source=`  
- `verify-profile` green again; CI `build-iso` = manual stock validation only  
- ISO naming `nyxus-*.iso` in CI docs/workflows

---

## 4. What’s still unfinished

| Item | Status |
|---|---|
| **Rebake + reflash** from current `main` | **Owner next** — only way stick matches repo |
| Verify Kage mounts ISO on real UEFI stick (or use stock rescue) | Owner |
| Greeter / lock / UFO / welcome-note QA on stick | Owner after flash |
| ALIEN NEON **Phase 2** — shell GTK apps (Home, Panel, Start, Terminal, …) | Next agent |
| Settings polish — remaining PARTIAL/MINIMAL (`vpn` first) | Next agent |
| ~33 non-boot Replit refs | Deferred (non-fatal) |
| Prune stale remote branches / old ISOs in `out/` | Hygiene |
| Companion mascot re-enable + stage | Owner call (disabled on purpose) |
| Fold `companion-3d` under one roof | Owner call |

**Stay as-is (do not restyle):** Bifrost, GodsApp, Meli, Arsenal / lab apps.

---

## 5. Bake readiness (right now)

| Check | State |
|---|---|
| `main` clean + pushed | ✅ |
| Open PRs | **0** |
| Welcome Transmission + Phase 1 on `main` | ✅ |
| #71/#72 eww/stamp on `main` | ✅ |
| W1 / W6 | ✅ |
| Kage pkgs on builder | Present — verify mount after bake |
| ISO `nyxus-2026.07.24` @ 03:05 | ❌ **Stale** — do not reflash for today’s work |

```bash
# Confirm idle
cd ~/Nyxus-Core && git status   # should be clean

cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh
# → out/nyxus-<date>-x86_64.iso

# After flash (UEFI): cat /etc/nyxus-build  →  commit matches bake tip
```

---

## 6. Gotchas burned into this day (do not repeat)

1. **Bake only from committed idle `main`.** Mid-edit bake ships a random subset.  
2. **Never flash a morning ISO expecting afternoon commits.** Check `/etc/nyxus-build`.  
3. **Skel + artifacts must stay lockstep**; bake can wipe hypr shards if not in the ship list (W6).  
4. **Don’t blind-sed hexes through `verify-profile.sh`** — it bans the palette it must enforce.  
5. **Three different “UFOs”** — live wallpaper flyby, notification icon, companion mascot (only #3 is off).  
6. **Kage without iso9660 ≠ bootable live default** — stock rescue until verified.  
7. **Archive / stash branches are not bake fuel** — vaults, secrets, `.env`, DBs.  
8. **ONE canonical repo:** `~/Nyxus-Core` on `main`.

---

## 7. Key commits / PRs (anchors)

| Ref | Meaning |
|---|---|
| PR **#70 / #72** | Green-light + re-land live-boot branch onto `main` |
| PR **#71** (`0f866221`) | eww paint / black-box / hyprpm / stamp |
| PR **#73** | ALIEN NEON Phase 1 + Settings Welcome polish |
| `1af1a65f` | Welcome Transmission + Dream Protocol |
| `09fef7bb` | W1 profiledef + W6 arsenal/reactive |
| Docs tip after status brief | See `git log -1 --oneline` on `main` |

---

## 8. Related docs

| Doc | Role |
|---|---|
| [`HANDOFF.md`](../HANDOFF.md) | Rules, architecture, **WHERE WE STAND**, bake/flash procedure |
| [`ALIEN_NEON_SETTINGS_BRIEF.md`](./ALIEN_NEON_SETTINGS_BRIEF.md) | Theme/Settings phases — start here for Phase 2 |
| [`ALIEN_NEON_SETTINGS_AUDIT.md`](./ALIEN_NEON_SETTINGS_AUDIT.md) | Counted checklist of surfaces / thin Settings pages |
| [`SHIPPING.md`](../SHIPPING.md) | Pre-flash checklist |
| This file | **Last-day narrative + done/open** — background for the whole deal |

---

*Keep this file as the day chronicle. Update HANDOFF’s WHERE WE STAND when bake/flash state changes; append a line here when a major chapter closes (bake verified, Phase 2 done, etc.).*

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

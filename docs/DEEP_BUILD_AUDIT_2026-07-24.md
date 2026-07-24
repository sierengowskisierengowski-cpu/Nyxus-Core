# NYXUS — Deep Build Audit (revised)

> **When:** 2026-07-24 · evening (second pass)  
> **Against:** `main` @ `20122725` + fix branch `cursor/bake-wipe-lockstep-ac8f`  
> **Scope:** whole ISO/desktop build consistency — git, gates, NS↔skel↔opt
> lockstep, **bake wipe/restore completeness**, palette/brand, offline cache
> poison, Settings, download portal map.

---

## Verdict

| Gate | Result |
|---|---|
| Git `main` = tip of #74+#75 merges | ✅ PASS |
| Prior audit GO on tip | ⚠️ **INCOMPLETE** — missed bake wipe gaps |
| Wipe→restore: `eww/assets` + `hypr/scripts` + hypr extras | ✅ **FIXED** this pass (was FAIL) |
| Offline cache prefers NS (not poisonous `dist/`) | ✅ **FIXED** this pass |
| `verify-profile.sh` | ✅ PASS |
| Settings 57 / APP_REV r16 / Kernel Kage+stock | ✅ PASS |
| download.ts orphans | ✅ **FIXED** (`eww.scss` → css + scss.source) |
| Bake-ready after this PR merges | ✅ **GO** (owner must merge then rebake) |

**Still non-blocking:** Theme Phase 2 GTK cascade; SDDM offline Main.qml drift;
on-device Settings QA; residual “dark mirror” art-generator graffiti tag string.

---

## 1. Critical finding (why the first GO was wrong)

`build-iso.sh` does `rm -rf skel/.config/{hypr,eww}` then restages only a
**partial** file list from NS. Committed skel looked fine in a static diff,
but a real bake would have **deleted**:

| Wiped & not restored (before fix) | Impact |
|---|---|
| `skel/.config/eww/assets/` (247 PNGs) | Blank HUD / missing overlay art |
| `skel/.config/hypr/scripts/*.sh` | idle-glass, prism-pulse, daily-line break |
| `hyprpaper.conf`, `nyxus-monitors.conf`, `nyxus-voice.conf` | monitors `source=` + wallpaper helper |

**Fix applied:**
1. Seeded NS: `hypr/scripts/`, `hyprpaper.conf`, `nyxus-monitors.conf`,
   `nyxus-voice.conf` (copied from skel — now SoT).
2. `build-iso.sh` restages those + `cp -a NS/eww/assets → skel`.
3. Dry-run wipe+restore simulation: **PASS**.

---

## 2. Offline cache poison

`artifacts/api-server/dist/nyxus-scripts/` contained **broken symlinks** to
`/home/cosmic/Nyxus-Core/scripts/...`. Old bake preferred `dist/` over NS →
poisoned `/opt/nyxus-cache` on the stick.

**Fix:** prefer NS always; reject `dist/` if dangling links. Removed local
`dist/nyxus-scripts/` in this environment. Owner should also
`rm -rf artifacts/api-server/dist/nyxus-scripts` on the bake host before
`sudo ./build-iso.sh` if it reappears.

---

## 3. Lockstep scorecard (post-fix)

| Artifact | Status |
|---|---|
| NS ↔ opt `nyxus_settings.py` r16 | ✅ |
| Tier B/C helpers NS ↔ LBIN | ✅ (+ bake install from NS) |
| Hypr shards NS ↔ skel (content) | ✅ |
| Hypr scripts / monitors / paper / voice | ✅ now in NS + bake restage |
| EWW yuck/css/scripts/assets | ✅ assets restaged at bake |
| Screensaver chain in `.config/nyxus` | ✅ only those three |
| `skel/.nyxus` app `.py` copies | ✅ stripped (bake makes symlinks) |
| `BOOTSTRAP_VERSION` | `2026.07.24-r14-alien-neon` ✅ |
| `/etc/nyxus-build` | generated at bake only ✅ |
| packages: kage (bake-append), fastfetch, usbguard, gamemode; no waybar | ✅ |

---

## 4. Palette / brand

| Check | Status |
|---|---|
| Canon hex lock (violet/magenta/green/orange/void/text) | ✅ |
| cream `#f4ead5` / old violet / shipped gold (non–Security Center) | ✅ absent |
| Stay-as-is Security Center gold | ✅ intentional |
| Residual DM/OP comments in rofi/eww/bashrc/chrome/sounds/icons | ✅ **polished** this pass |
| Graffiti generator still stamps `"dark mirror"` into art assets | ℹ️ P3 art string |

---

## 5. Settings

- 57 sections = 57 `PAGE_CLASSES`
- Kernel = `linux-kage-ryu` + `linux` only
- `empty_group` defined
- 9 shell sections present
- On-device GTK QA still required after flash

---

## 6. download.ts

- Removed orphan `eww/eww.scss`
- Added `eww/eww.css` + `eww/eww.scss.source`
- Same-name map keys present in NS: **0 missing** (spot check)

---

## 7. Keybinds / helpers / bootstrap (from earlier audit)

| Chord | Status |
|---|---|
| `Super+Shift+D` | rofi/wofi **run** only (Dream moved to Alt) |
| `Super+Alt+D` | Dream Protocol |
| `Super+Shift+N` | Welcome Transmission replay |
| Duplicate `Super+R` (saucer flip) | was 2× in skel; **resolved** by NS→skel sync |
| `Super+W` | wifi toggle; wallpaper studio line is **commented** |

Profiledef helpers present + `file_permissions` 755: `nyxus-welcome-note`,
`nyxus-dream`, `nyxus-kernel-switch`, and the Tier B/C helpers.

Builder host `/opt/nyxus-cache/nyxus_install.sh` may still be **STALE**
(2026-07-20 `set -e` + bare `clear`) — bake restages from NS; stick OK after
rebake. Marker on builder: `2026.07.24-r14-alien-neon`.

Also closed same-day HIGH gaps on `main`: battery/netusage seeded into NS;
welcome-note/dream/kitty staged at bake+install; stations.conf synced;
theme Comments → ALIEN NEON.

---

## 8. Owner bake checklist

```bash
cd ~/Nyxus-Core
git checkout main && git pull
git status   # clean / idle
rm -rf artifacts/api-server/dist/nyxus-scripts   # if present
cd iso-builder && sudo ./build-iso.sh
# flash NEW iso only — not the 03:05 file
# stick QA:
#   cat /etc/nyxus-build
#   ls ~/.config/eww/assets | head
#   ls ~/.config/hypr/scripts
#   nyxus-settings → Kernel
#   bars / welcome note / Super+Alt+D dream
```

---

*Append a line here when bake is verified on stick.*

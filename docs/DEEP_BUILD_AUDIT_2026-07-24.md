# NYXUS — Deep Build Audit

> **When:** 2026-07-24 · 14:25 EDT  
> **Against:** `main` @ `8cf3ebdd` (+ lockstep fixes in follow-up commit if present)  
> **Scope:** whole ISO/desktop build consistency — git, gates, NS↔skel↔opt lockstep, palette/brand, keybinds, profiledef, bootstrap/cache, welcome transmission.

---

## Verdict

| Gate | Result |
|---|---|
| Git `main` clean / synced / **0 open PRs** | ✅ PASS |
| `iso-builder/verify-profile.sh` | ✅ PASS |
| Critical app lockstep (settings r16, palette, welcome-note, dream, helpers) | ✅ PASS (after this audit’s skel/.nyxus strip + hypr sync) |
| Profiledef 755 for new bins | ✅ PASS |
| Welcome Transmission + Dream wiring (NS + skel rules) | ✅ PASS |
| Bake-ready repo state | ✅ **GO** (owner still must rebake; ISO on disk is stale) |

**Not bake-blocking (documented):** leftover brand strings in comments/asset names; builder `/opt/nyxus-cache` stale; local `pnpm typecheck` env quirk (CI green on #75).

---

## 1. Git / gates

| Check | Status |
|---|---|
| Branch | `main` = `origin/main` |
| Open PRs | **0** |
| Uncommitted before audit fixes | clean |
| `verify-profile.sh` | exit 0 (only soft WARN: `customize_airootfs.sh` not +x — mkarchiso chmods) |
| Last ISO on disk | `nyxus-2026.07.24` @ **03:05** — **STALE** vs tip (pre–#74/#75) |

---

## 2. Lockstep (NS = bake source of truth)

`build-iso.sh` regenerates skel hypr + many configs from `artifacts/api-server/nyxus-scripts/` (NS), and rebuilds `skel/.nyxus` as **per-file symlinks** to `/opt/nyxus`.

| Artifact | NS | opt/nyxus | skel | Notes |
|---|---|---|---|---|
| `nyxus_settings.py` APP_REV **r16** | ✅ | ✅ match | bake → symlink | Had **stale r12 copy** under `skel/.nyxus/` — **removed** this audit |
| `nyxus_palette.py` | ✅ | ✅ | ✅ `.nyxus` + `.config/nyxus` | match |
| `nyxus_welcome_note.py` | ✅ | ✅ | was in `.nyxus` | match; now via bake symlink |
| `nyxus-welcome-note` / `nyxus-dream` bins | ✅ | airootfs bin ✅ | — | md5 match |
| `nyxus-hyprland-rules/opacity` | ✅ | — | ✅ | md5 match (welcome-note windowrules present) |
| `hyprland.conf` | ✅ | — | was drift (comments + dup R) | **synced NS → skel** this audit |
| Tier helpers (kernel-switch, virt, …) | ✅ | airootfs ✅ | — | all MATCH |
| `BOOTSTRAP_VERSION` | `2026.07.24-r14-alien-neon` | same in airootfs bin | — | match |
| `kitty-welcome.conf` | ✅ | skel `.config/kitty` ✅ | — | match |
| `skel/.config/nyxus` app `.py` | — | — | screensaver chain only | ✅ (PR #75) |
| `skel/.nyxus` app `.py` | — | — | **was full stale tree** | **stripped** this audit → only `nyxus-start/` left |

---

## 3. Palette / brand

| Token | Shipped desktop trees |
|---|---|
| cream `#f4ead5` | ✅ none |
| old violet `#a06bff` | ✅ none |
| gold `#d4b87a` | ℹ️ **ban-comment only** in `nyxus_settings.py` (“never gold”) |
| `DARK MIRROR` / `OBSIDIAN PRISM` | ⚠️ **residual** in comments, sound/icon theme *names*, rofi/eww headers, prism-pulse script title, stay-as-is `nyxus_security.py` — **not** Settings chrome / Theme Packs. Non-blocking polish. |

Stay-as-is untouched by design: Bifrost / GodsApp / Meli / Arsenal.

---

## 4. Keybinds

| Chord | Status |
|---|---|
| `Super+Shift+D` | rofi/wofi **run** only (Dream moved to Alt) |
| `Super+Alt+D` | Dream Protocol |
| `Super+Shift+N` | Welcome Transmission replay |
| Duplicate `Super+R` (saucer flip) | was 2× in skel; **resolved** by NS→skel sync (one remains) |
| `Super+W` | wifi toggle; wallpaper studio line is **commented** |

---

## 5. Profiledef / helpers

All checked present + `file_permissions` 755:

`nyxus-welcome-note`, `nyxus-dream`, `nyxus-kernel-switch`, `nyxus-distrobox-helper`, `nyxus-doh`, `nyxus-mac-randomize`, `nyxus-protonup`, `nyxus-secboot`, `nyxus-usbguard-helper`, `nyxus-virt-setup`.

---

## 6. Bootstrap / offline cache

| Item | Status |
|---|---|
| Repo `nyxus_install.sh` | ✅ no `set -e`; `clear` guarded |
| Builder host `/opt/nyxus-cache/nyxus_install.sh` | ⛔ **STALE** (2026-07-20, still `set -e` + bare `clear`) — explains today’s Hyprland first-boot toast on the **builder** desktop. **Bake** restages cache from NS — stick OK if baked from this tip. |
| Marker on builder | should be `2026.07.24-r14-alien-neon` to silence refresh |

---

## 7. Settings coverage

- **APP_REV** `2026.07.24-r16` on NS + opt  
- 57 sections incl. 9 shell features (Compositor, Bars, Live Wallpaper, Lock, Idle, Reactive, Mission, Session Modes, Firewall)  
- Kernel page = Kage-Ryu + stock rescue  
- Theme Phase 2 (GTK shell app chrome cascade) still a **follow-up**, not a bake blocker  

Roadmap: `docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md`

---

## 8. Fixes applied in this audit pass

1. Synced `skel/.../hyprland.conf` ← NS (bake SoT).  
2. Stripped **42+** stale `skel/.nyxus/*.py` duplicates (bake regenerates symlinks).  
3. Left `skel/.nyxus/nyxus-start/` directory as-is.  
4. Re-ran `verify-profile` → PASS.

---

## 9. Owner checklist before / after bake

```bash
cd ~/Nyxus-Core && git status   # clean
cd iso-builder && sudo ./build-iso.sh
# flash NEW iso only — not the 03:05 file
# on stick: cat /etc/nyxus-build   # expect tip ≥ this audit
# QA: bars, welcome note once, settings Kernel page, Super+Alt+D dream if unlocked
```

**Builder desktop (optional):** refresh `/opt/nyxus-cache` from NS or ignore — not what the ISO bake uses after `build-iso.sh` restages cache.

---

## 10. Residual follow-ups (non-blocking)

| Item | Priority |
|---|---|
| Rebake + reflash | **P0 owner** |
| Purge residual DARK MIRROR / OBSIDIAN PRISM from rofi/eww *comments* & theme index names | P2 polish |
| Refresh host `/opt/nyxus-cache` | P2 builder hygiene |
| ALIEN NEON Phase 2 GTK cascade | P2 theme |
| Prune stale remote branches / old ISOs in `out/` | P3 |

---

*Append a line here when bake is verified on stick.*

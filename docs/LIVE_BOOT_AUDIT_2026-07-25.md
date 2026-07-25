# NYXUS — Live USB Boot Audit (post-#76 bake)

> **When:** 2026-07-25 · after first live boot of `nyxus-2026.07.24` ISO  
> **ISO:** baked **17:03 EDT** · sha `ed2f21e4…` · flashed to SanDisk `/dev/sda`  
> **Repo tip at bake:** `8b2fdd34` (HANDOFF bake-GO). Claude app-shell fix was **not** in that ISO.  
> **Scope:** owner live-boot report + full repo sweep against those symptoms.

---

## Verdict

| Gate | Result |
|---|---|
| Open GitHub PRs to merge | **none** — Claude’s fix was **local uncommitted** only |
| Flashed ISO includes Claude arsenal fix | ❌ no (binary stamped **00:05 Jul 25**, bake was **17:03 Jul 24**) |
| Kage-Ryu live boot | ✅ splash OK |
| Desktop usable first minutes | ⚠️ bars/saucer paint; wallpaper delayed; Settings TBD |
| Arsenal webapps on live ISO | ⛔ expected fail without `GowskiNet-Vault` (messaging fixed in tree now) |
| Login / logout eye-candy redesign | ⛔ logout (wlogout) still void/B&W tiles; login is greetd+regreet (not full redesign) |
| Rainbow terminal text | ⛔ still shipped — `nyxus-glow` greeting in `bashrc` |
| EWW black boxes | ⚠️ STILL reported on stick despite PR #71/#72 — needs on-device CSS/layer repro |
| Repo state for next bake | 🟡 land app-shell + remaining HIGH fixes → rebake |

---

## GitHub / Claude status

- **Open PRs:** 0
- **Claude session** (`~/.claude/.../1bcca1bf-…`, night of Jul 24→25) fixed **one** thread:
  - `nyxus-app-shell` fail-fast when `nyxus-webapp` cannot start (missing vault / ports)
  - Built release binary → copied into `iso-builder/.../usr/local/bin/nyxus-app-shell`
  - **Never committed / never pushed / never PR’d**
- Claude explicitly left untouched: login/logout art, eww boxes, terminal glow, Settings, wallpaper delay

---

## Issue-by-issue (owner report)

| # | Symptom | Status | Root cause / evidence | Size | Bake block? |
|---|---|---|---|---|---|
| 1 | Kage-Ryu splash | ✅ OK | Expected | — | — |
| 2 | ~1 min black + cursor before login | PARTIAL / EXPECTED-ish | greetd→cage→regreet→session handoff on hybrid GPU; long DRM settle. Not a missing wall by itself. | M | no |
| 3 | “Hyprpg couldn’t load headers” | STILL_BROKEN (noise) | `hyprpm` during bootstrap for `hyprexpo` (`nyxus-hyprland-mission.conf`). Needs matching Hyprland headers / guard when headers absent (PR #71 touched this — verify guard still fires on stick). | S | no |
| 4 | First-boot still installing | EXPECTED | Offline bootstrap + cache install | — | — |
| 5 | EWW bars/saucer fast but **boxed** | STILL_BROKEN on stick | CSS wants transparent bars (`eww.css` `.bar-* { background: transparent }`) + layer blur rules. Black box = compositor/GTK layer path or stale CSS on device. Needs live `eww` namespace + screenshot repro. | M | **yes** (UX) |
| 6 | Notification saucer | ✅ OK | Working | — | — |
| 7 | Wallpaper blank ~5 min | PARTIAL | Autostart: `nyxus-live-wallpaper auto \|\| nyxus-wallpaper-autostart`. Still wall exists (`urban-alien` in sys + skel). Delay = bootstrap/`awww`/livewall race or first-boot install fighting wallpaper. NS had **drift** (`nebula-01` DEFAULT) vs LBIN (`urban-alien`) — fixed in NS this pass. | M | **yes** |
| 8 | Deep Core / Power / QC / Hub OK; Fire missing; Bifrost OK | MIXED | Fire launcher/binary not present as `nyxus-fire*`. Bifrost works when its stack is available. | S–M | Fire: no |
| 9 | “Wired connection ethernet” box | EXPECTED (not a bug) | Claude confirmed: normal NM/network indicator chrome, not Arsenal failure UI. | — | — |
| 10 | Settings opens nothing | STILL_BROKEN / UNKNOWN | Launcher: `nyxus-settings` → `python3 ~/.nyxus/nyxus_settings.py`. Opt has `nyxus_settings.py`; skel `.nyxus` symlinks are **bake-generated**. Need stick log `~/.cache/nyxus/settings.log` / try `nyxus settings`. Possible: wrong desktop entry, GTK crash, or pre-symlink race. | M | **yes** |
| 11 | Logout B&W / old style; wanted urban-alien eye candy + new login | STILL_BROKEN | **Logout** = `wlogout` with `background-image: none` (void tiles). **Login** = greetd+regreet + `nyxus-login-bg.png` / cache path — themed CSS exists but is **not** the full urban-alien redesign described in `docs/NYXUS_BUILD_BRIEF.md` (still open checklist). | L | **yes** (owner priority) |
| 12 | Forge :23052 / GSL :23054 “open terminal…” 10–15 min later | FIXED_IN_TREE (not in flashed ISO) | App-shell used to spawn starter async and poll **90s** × N apps → staggered port banners. Claude: sync start + surface `nyxus-webapp` stderr + **15s** grace. Live ISO cannot run vault apps without `~/GowskiNet-Vault`. | S | messaging: yes for UX |
| 13 | Rainbow terminal text | STILL_BROKEN (as unwanted) | `artifacts/.../bashrc` interactive greeting calls `nyxus-glow` (“scatter random neon”). Not lolcat — **intentional glow banner** still on. Silence: `NYXUS_NO_GREETING=1` or remove greeting block. | S | yes if owner wants it gone |

---

## Extra sweeps

### Greeter / logout / lock
- Live greeter: **greetd + regreet** (`nyxus-greeter` fallback chain). SDDM disabled.
- Logout menu: **wlogout** (`Super+Shift+E`) — no wallpaper image in `style.css`.
- Lock: **hyprlock** (urban-alien pin noted in hyprland comments).

### Arsenal / app-shell
- Desktops: `Exec=nyxus-app-shell <id>` for forge/axiom/etc.
- Backend: `nyxus-webapp` expects `GOWSKINET_VAULT` / `~/GowskiNet-Vault` for CIPHER/GSL/etc.
- Portable ISO will **never** silently run those without vault or bundled services — fail-fast messaging is the correct product behavior.

### Wallpaper lockstep
- LBIN (baked path used on stick): `DEFAULT=.../nyxus-urban-alien.png` ✅  
- NS (source of truth for many helpers): was still `nebula-01` ❌ → **aligned this pass**.

### Rainbow / stamp
- `/etc/issue` + bashrc ALIEN stamp work from #71 is separate from **glow greeting**.
- Glow greeting is the rainbow the owner still sees.

---

## Priority for next bake (owner)

1. **Commit + push** Claude `nyxus-app-shell` fix (done this pass if landed).  
2. **Kill or default-off** `nyxus-glow` bashrc greeting.  
3. **Settings** on-stick repro → fix launcher/crash.  
4. **EWW black boxes** on-stick repro (layer namespace + CSS).  
5. **Wallpaper first paint** — don’t wait on bootstrap; guarantee `awww`/`swaybg` urban-alien in first 2s.  
6. **wlogout + login eye-candy** redesign (urban-alien full-bleed) — large, explicit art/CSS work.  
7. **hyprpm headers** — soft-fail / skip when headers missing.  
8. Rebake → reflash → re-QA.

---

## Stick QA checklist (next live boot)

```bash
cat /etc/nyxus-build
uname -r                          # expect kage-ryu
ls ~/.config/eww/assets | head
hyprctl layers | head
nyxus-settings ; echo exit:$?
tail -50 ~/.cache/nyxus/settings.log 2>/dev/null
cat ~/.config/nyxus/wallpaper.conf
pgrep -a awww; pgrep -a swaybg; pgrep -a mpvpaper
nyxus-app-shell forge             # should fail FAST with vault message after new bake
```

---

*Append bake/flash verification lines below when the next ISO is proven.*

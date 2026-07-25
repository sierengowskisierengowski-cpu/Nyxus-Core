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
| 5 | EWW bars/saucer fast but **boxed** | STILL_BROKEN on stick | Bars use `:exclusive true` full-width zones (black slabs especially with no wall). Transparent `window` CSS already present; PR #71 only fixed sass stall — **not** exclusive-zone chrome. Saucer cockpit fill is intentionally near-opaque. | M | **yes** |
| 6 | Notification saucer | ✅ OK | Working | — | — |
| 7 | Wallpaper blank ~5 min | PARTIAL | Wall asset OK (`urban-alien`). First-boot `nyxus_install.sh` **pkills** wallpaper daemons then restarts after long install → wall returns when bootstrap ends. Don’t tear down wallpaper during install. | M | soft / **yes** UX |
| 8 | Deep Core / Power / QC / Hub OK; Fire missing; Bifrost OK | MIXED | Fire launcher/binary not present as `nyxus-fire*`. Bifrost works when its stack is available. | S–M | Fire: no |
| 9 | “Wired connection ethernet” box | STILL_BROKEN (noise) | Most likely **`network-manager-applet`** xdg-autostart (`nm-applet.desktop`) — classic Wired/Ethernet toast. Not fixed by app-shell. Disable/override on Hypr live; EWW wifi is enough. | S | soft |
| 10 | Settings opens nothing | STILL_BROKEN | **Dual desktops disagree:** `io.nyxus.settings` → `nyxus-settings` → `~/.nyxus/…`; `nyxus-settings.desktop` → `nyxus settings` → `/opt/nyxus/…`. Bootstrap can churn `~/.nyxus`. Fix: one Exec + `/opt` fallback + toast on fail. | S | **yes** |
| 11 | Logout B&W / old style; wanted urban-alien eye candy + new login | STILL_BROKEN | **Logout** = `wlogout` with `background-image: none` (void tiles). **Login** = greetd+regreet (urban-alien staged). Lock = hyprlock (alien). Full redesign in `NYXUS_BUILD_BRIEF` still open. | M–L | **yes** |
| 12 | Forge :23052 / GSL :23054 “open terminal…” 10–15 min later | STILL_BROKEN (fail-fast only in tree) | **Port mismatch** app-shell vs `nyxus-webapp`: forge `23052`≠`20000`, gsl `23054`≠`19670`, redforge `23053`≠`5173`, trainer `23055`≠`20508`. Also needs Vault/`/opt/arsenal` wiring; `nyxus-webapp` not staged to LBIN at bake (arrives via bootstrap). Claude patch = faster wrong-failure, not green apps. | L | **yes** |
| 13 | Rainbow terminal text | STILL_BROKEN (as unwanted) | `bashrc` interactive greeting calls `nyxus-glow`. PR #71 only added build stamp — did not remove glow. Silence: `NYXUS_NO_GREETING=1` or remove greeting. | S | soft / owner-want |

---

## Extra sweeps

### Greeter / logout / lock
- Live greeter: **greetd + regreet** (`nyxus-greeter` fallback chain). SDDM disabled.
- Logout menu: **wlogout** (`Super+Shift+E`) — no wallpaper image in `style.css`.
- Lock: **hyprlock** (urban-alien pin noted in hyprland comments).

### Arsenal / app-shell
- Desktops: `Exec=nyxus-app-shell <id>` for forge/axiom/etc.
- **Port table (broken):** forge 23052≠20000, gsl 23054≠19670, redforge 23053≠5173, trainer 23055≠20508 (cipher 23051 OK).
- Backend: `nyxus-webapp` expects Vault / `/opt/arsenal`; not staged to LBIN at bake (bootstrap path).
- Claude `1951f365` = fail-fast UX only — **not** green arsenal apps.

### Wallpaper lockstep
- LBIN (baked path used on stick): `DEFAULT=.../nyxus-urban-alien.png` ✅  
- NS (source of truth for many helpers): was still `nebula-01` ❌ → **aligned this pass**.

### Rainbow / stamp
- `/etc/issue` + bashrc ALIEN stamp work from #71 is separate from **glow greeting**.
- Glow greeting is the rainbow the owner still sees.

---

## Priority for next bake (owner)

1. ~~Commit Claude app-shell fail-fast~~ — landed `1951f365` (incremental only).  
2. **Align app-shell ↔ `nyxus-webapp` ports** + stage `nyxus-webapp` / `/opt/arsenal` (or hide arsenal desktops until setup).  
3. **wlogout** urban-alien background (match hyprlock/greeter).  
4. **Settings** — one desktop Exec + `/opt` fallback.  
5. **EWW** — exclusive-zone / black-box (retest with wallpaper up).  
6. Soft: kill `nyxus-glow` greeting; disable nm-applet autostart; stop wallpaper pkill during install; hyprpm residual.  
7. Rebake → reflash → re-QA.

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

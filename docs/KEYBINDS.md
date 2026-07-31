# NYXUS — Keybindings

**Source of truth** for every active keybind in the NYXUS Hyprland session.
Mod key (`$mod`) = **SUPER** (Windows key).

> **Last audited: 2026-07-30** — re-derived mechanically from the shipped
> configs (`iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/`), not from
> the previous revision of this file. The 2026-07-14 revision of this document
> was wrong in six places; see "Corrections" at the bottom so nobody
> re-discovers them.

Binds live in `~/.config/hypr/hyprland.conf` plus the **17** shards sourced
from it out of `~/.config/hypr/conf.d/`. Sourced shards that carry binds:
`nyxus-signature.conf`, `nyxus-hyprland-flair.conf`,
`nyxus-hyprland-mission.conf`, `nyxus-hyprland-aurora.conf`,
`nyxus-reactive.conf`, `nyxus-cometfire.conf`.

**`nyxus-safemode.conf` is the only unsourced shard** — it is a standalone
recovery profile, and its binds (`Super+Return`, `Super+E`, `Super+Q`,
`Super+Ctrl+R`, `Super+Ctrl+S`, `Super+M`) are inactive in a normal session by
design. `conf.d/` is **not** auto-globbed by Hyprland: a shard that is not
`source=`d contributes nothing, which is how nine binds and 24 window rules
shipped dead through several ISOs (see HANDOFF "ROUND 3").

> **Reserved for the login agent (do not reassign):**
> `Super+L` (lock) and `Super+Space+Enter` (greeter backdoor, greeter-side only).

---

## Apps & launching
| Keybind | Action |
|---|---|
| `Super+Return` | Terminal (kitty → alacritty → foot) |
| `Super+Shift+Return` | Terminal, alternate (alacritty first) |
| `Super+Space` | App launcher (`~/.nyxus/nyxus_launcher.py`, rofi/wofi drun fallback) |
| `Super+Shift+D` | Run a command (rofi/wofi run prompt) |
| `Super+Tab` | Window switcher (rofi window) |
| `Super+E` | File manager (nautilus → thunar → dolphin → `xdg-open $HOME`) |
| `Super+B` | Browser (chromium → firefox → chrome) |

> `Super+E`'s chain is a `command -v` fallback chain. **Neither `nautilus` nor
> `thunar` nor `dolphin` is in `packages.x86_64`**, so on a stock ISO this lands
> on `xdg-open $HOME`. That is intentional fail-safe behaviour, not a bug — but
> do not document it as "opens Thunar".

## Window management
| Keybind | Action |
|---|---|
| `Super+Q` | Close active window |
| `Super+V` | Toggle floating |
| `Super+P` | Pseudo-tile |
| `Super+J` | Toggle split direction |
| `Super+F` | Fullscreen |
| `Super+Shift+F` | Maximize (fullscreen mode 1) |
| `Super+Shift+C` | Center window |
| `Super+U` / `Super+Shift+U` | Group: toggle / move out of group |
| `Super+]` / `Super+[` | Group: cycle active forward / back |
| `Super+Alt+T` | Freeform ↔ tiling mode toggle (`nyxus-freeform`) |

## Focus / move / resize
| Keybind | Action |
|---|---|
| `Super+←↑↓→` / `Super+H` `Super+K` `Super+;` | Move focus (left / up / right) |
| `Super+Shift+←↑↓→` | Move window |
| `Super+Ctrl+←↑↓→` | Resize active window (±40px) |
| `Super+LMB` / `Super+RMB` (drag) | Move / resize window |

## Stations (workspaces)
| Keybind | Action |
|---|---|
| `Super+1`…`Super+0` | Stations 1–10 (OPS · FORGE · GHOST · PULSE · WAVE · CORE · MESH · SCRIBE · BIFROST · ARSENAL) |
| `Super+Shift+1`…`Super+Shift+0` | Move window to station 1–10 |
| `Super+Home` | **HOME** station (`workspace name:HOME`) |
| `Super+Shift+Home` | Relaunch the eww `home-deck` watcher (`nyxus-home-deck`) |
| `Super+End` | **START** station (`workspace name:START`) |
| `Super+Shift+End` | Kill the retired `nyxus-start` GTK window if one is somehow up |
| `Super+Delete` | **LAB** station (`workspace name:LAB`) |
| `Super+Alt+1`…`Super+Alt+0` | Companion ("half") stations: RELAY · ANVIL · TRACE · BEACON · MIXER · VAULT · SCAN · BOARD · SENTRY · RANGE |
| `Super+Alt+Shift+1`…`Super+Alt+Shift+0` | Move window to a companion station |
| `Super+'` (apostrophe) | Previous workspace |
| `Super+scroll` | Next / previous workspace |
| `Super+S` / `Super+Shift+S` | `magic` scratchpad: toggle / move window to |
| `Super+F3` · `Super+Alt+A` | Mission Control (`nyxus-mission-control-toggle`) |

> **`name:HOME`, not `name:0`.** Hyprland resolves a *numeric* `name:0` into the
> SPECIAL workspace range (id `-1337`), a hidden overlay you cannot see. HOME was
> moved off it on 2026-07-26; gate `13ag` hard-fails any `workspace name:0`.
> The old GTK4 `nyxus-home` app is **disabled** — the eww `home-deck` replaced it.

## Flyouts, Hub & system panels
| Keybind | Action |
|---|---|
| `Super+A` | Quick Settings (eww `quicksettings`) |
| `Super+N` | Notifications (eww `notifications`) |
| `Super+W` | WiFi (eww `wifi`) |
| `Super+M` | Audio mixer (eww `mixer`) |
| `Super+C` | Calendar (eww `calendar`) |
| `Super+Shift+B` | Bluetooth (eww `bluetooth`) |
| `Super+Escape` | NYXUS · POWER menu (eww `powermenu`) |
| `Super+grave` (\`) | Dashboard (eww `dashboard`) |
| `Super+G` | DEEP CORE (eww `deepcore`) |
| `Super+/` · `Super+Shift+/` | Keybind cheatsheet (eww `hotkey-cheatsheet`) |
| `Super+D` | **X-RAY PEEK** — hold-to-see-through: drops window opacity + blur, press again to restore |
| `Super+I` | Eyedropper (`hyprpicker -a`, warns if not installed) |
| `Super+Alt+D` | Dream Protocol (`nyxus-dream`) |
| `Super+Shift+N` | Re-show the Welcome Transmission note (`nyxus-welcome-note --force`) |
| `Super+Shift+Z` | Close the START search overlay |

### Escaping the Hub (three separate routes — all real)
| Keybind | Action |
|---|---|
| `Escape` (no mod) | Closes any open eww overlay via `nyxus-hub-close` (bars/OSDs are excluded from the check) |
| `Super+Shift+Escape` | Bare `eww close nyxus-hub` **first**, then `nyxus-hub-close` |
| `Super+Ctrl+Shift+Escape` | `eww close-all` then `nyxus-eww-launch-safe` — hard recovery, touches no NYXUS script |

> **eww has no `:onkeydown`** in 0.5.0 or 0.6.0 — it is accepted, logged as a
> warning, and dropped. Keyboard escape from an eww overlay **must** be a
> compositor bind. That is why these three exist here and not in `eww.yuck`.

## Security & modes
| Keybind | Action |
|---|---|
| `Super+Shift+Y` | Security Center (`nyxus-security`) |
| `Super+Ctrl+Alt+L` | PANIC lockdown (`nyxus-security --panic`) |
| `Super+Alt+G` | Game mode toggle (`nyxus-gamemode`) |
| `Super+Alt+F` | Focus mode toggle (`nyxus-focusmode`) |
| `Super+Shift+H` | NYXUS Doctor (diagnostics, in alacritty) |

> ⚠ **Hacker Mode, Ghost Mode and Panic Lock have NO keybind.** All three
> binaries ship (`nyxus-hacker-mode`, `nyxus-ghost`, `nyxus-panic` in
> `/usr/local/bin`) and all three are reachable — from the **GHOST station deck**
> (`Super+3`, the `security_toggle` row), from the **Hub**, and from
> **Settings → Keybinds**. But `Super+Ctrl+X` / `Super+Ctrl+G` /
> `Super+Ctrl+Delete` **do not exist in any shipped config** and never have.
> Verified 2026-07-30 by grepping every bind in `hyprland.conf` + all 18 shards.
> Earlier revisions of this file and of `HANDOFF.md` §4 both claimed
> `Super+Ctrl+X` toggles hacker mode; that is false. Adding the binds is a
> reasonable change but it is a **config** change, not a docs change — it needs
> a collision check against the ~156 existing binds first.

## Lock / logout / session
| Keybind | Action |
|---|---|
| `Super+L` | Lock session (`loginctl lock-session` → hypridle's `lock_cmd` → hyprlock) |
| `Super+Shift+E` | Logout menu (wlogout, urban-alien canvas) |
| `Super+Shift+M` | Exit Hyprland (plays the logout sound first) |
| `Super+Shift+A` | UI sound design toggle (`nyxus-sound toggle`) |

## Media / volume / brightness
| Keybind | Action |
|---|---|
| `XF86AudioRaise/Lower/Mute` | Volume up / down / mute (+ OSD) |
| `XF86AudioMicMute` | Mic mute (+ OSD) |
| `XF86AudioPlay/Next/Prev` | Media play-pause / next / previous (playerctl) |
| `XF86MonBrightnessUp/Down` | Screen brightness ±10% (+ OSD) |
| `Caps_Lock` | Caps-lock OSD (`bindn`, does not consume the key) |

## Screenshots
| Keybind | Action |
|---|---|
| `Print` | Region (`~/.nyxus/nyxus_screenshot.py region`) |
| `Shift+Print` | Full screen |
| `Super+Print` · `Super+Shift+Print` · `Super+Ctrl+Print` | Region · fullscreen · active window |

## Wallpaper & visual FX (signature / flair / cometfire shards)
| Keybind | Action |
|---|---|
| `Super+Alt+S` | Wallpaper Studio (`nyxus wallpaper_studio`) |
| `Super+Alt+W` | Next wallpaper (`nyxus-wall-next`) |
| `Super+Alt+Shift+W` | Wallpaper auto-cycle toggle (`nyxus-wall-cycle`) |
| `Super+Alt+V` | Live (video) wallpaper toggle (`nyxus-live-wallpaper`) |
| `Super+O` / `Super+Shift+O` | Shader: next / off (`nyxus-shader`) |
| `Super+Ctrl+O` | Shader: `ember` preset directly |
| `Super+T` | Per-app border tint toggle (`nyxus-tint`) |
| `Super+Alt+B` | Music-reactive border toggle (`nyxus-beat`) |
| `Super+Alt+L` | Living theme toggle (`nyxus-living`) |
| `Super+Alt+P` | Pulse toggle (`hypr/scripts/nyxus-pulse.sh`) |
| `Super+Shift+P` | Wallpaper FX toggle (`nyxus-wall-fx`) |
| `Super+Z` | Spray-paint overlay (`nyxus-spray`) |
| `Super+Shift+X` | Prism border pulse (easter egg) |
| `Super+Shift+W` | Recompute accent from wallpaper — **see the warning below** |

> ⛔ **`Super+Shift+W` is a locked-off path.** The bind exists and points at
> `nyxus-accent-from-wallpaper`, but the ALIEN NEON palette is **LOCKED** and
> `accent.json` has `follow_wallpaper: false` with `prism` as the only preset.
> The tool is dev-only behind `NYXUS_ALLOW_WALLPAPER_ACCENT=1`, so pressing this
> should be a no-op. Wallpaper→accent extraction is precisely the drift that kept
> dragging the desktop off-theme (old blues, cream "Sprint E"). **Do not
> re-enable it.** Apply accent with `nyxus-apply-accent prism`.

### Screen magnifier (lens)
| Keybind | Action |
|---|---|
| `Super+Alt+scroll` | Lens in / out |
| `Super+Alt+=` / `Super+Alt+-` | Lens in / out |
| `Super+Alt+BackSpace` · `Super+Alt+MMB` | Lens **reset** |
| `Super+Shift+T` / `Super+Shift+Q` | Lens OCR text / QR scan |

> Lens reset used to be `Super+Alt+0`. It **moved to `Super+Alt+BackSpace`** on
> 2026-07-29 because `Super+Alt+0` collided with companion station RANGE —
> `hyprland.conf` binds `Super+Alt+1..0` as a set and the flair shard is sourced
> afterwards, so the lens won and **RANGE was the one station the keyboard could
> not reach.** Do not move it back.

## Reactive suite (the `nyxus-sense` living desktop)
The **Mood Engine** (`nyxus-sense` → `nyxus-mood`) runs automatically with no
keybind, shifting bar glow and resting wallpaper through moods (GHOST / DRIFT /
PROWL / OVERCLOCK, plus MATRIX under hacker mode). `nyxus-reactive.conf`
autostarts `nyxus-sense` → `nyxus-mood` → `nyxus-threatd`, staggered off the
critical path. The rest are on-demand:

| Keybind | Action |
|---|---|
| `Super+Ctrl+W` | **Machine Whispers** — click-through overlay drifting glowing fragments of live state (bottom layer, safe) |
| `Super+Alt+Shift+S` | **Supernova** — beat-locked whole-rig show mode (play audio first) |
| `Super+Alt+Shift+G` | **Graffiti Memory Wall** — accrete recent commits / tracks as spray tags onto the alien wall |

---

## Corrections to the 2026-07-14 revision of this file

Recorded so no agent re-derives them:

| Was documented | Reality |
|---|---|
| `Super+D` → NYXUS Start (`nyxus-start`) | `Super+D` is **X-RAY PEEK** (`nyxus-hyprland-aurora.conf`). The `nyxus-start` GTK4 app was retired for trapping the desktop; the START **station** (`Super+End`) replaced it |
| `Super+Home` → `name:0` | `name:HOME`. A numeric `name:0` is Hyprland's hidden SPECIAL range |
| `Super+Alt+0` → lens reset | `Super+Alt+0` is companion station **RANGE**; lens reset is `Super+Alt+BackSpace` |
| `Super+Ctrl+X` → Hacker Mode | **No such bind exists.** Reachable from the GHOST deck / Hub / Settings only |
| `Super+Ctrl+G` → Ghost Mode; `Super+Ctrl+Delete` / `Super+Ctrl+Shift+Delete` → Panic | **No such binds exist.** Same three surfaces as above |
| `Super+R` → force saucer clock/music flip | **No such bind exists.** The flip is automatic, driven by `player.sh` (MPRIS + a `pactl` sink-input fallback) |
| "`nyxus-cometfire.conf`, `nyxus-safemode.conf`, `nyxus-stations.conf` are not sourced" | Only `nyxus-safemode.conf` is unsourced. cometfire / stations / reactive / arsenal-apps / aurora were all fixed on 2026-07-29 — that miss cost 9 binds and 24 window rules |
| Only 3 shards listed | 17 shards are sourced (plus the runtime-generated `nyxus-monitors.conf`) |

---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

# NYXUS — Keybindings

**Source of truth** for every active keybind in the Nyxus Hyprland session.
Mod key (`$mod`) = **SUPER** (Windows key).

Binds live in `~/.config/hypr/hyprland.conf` plus the sourced shards in
`~/.config/hypr/conf.d/` (`nyxus-hyprland-flair.conf`, `nyxus-hyprland-mission.conf`,
`nyxus-signature.conf`). `nyxus-cometfire.conf`, `nyxus-safemode.conf`, and
`nyxus-stations.conf` exist but are **not** sourced — their binds are inactive.

Last audited: 2026-07-14 (Phase 3) — `hyprctl configerrors` clean, 0 duplicate binds.

> **Reserved for the login agent (do not reassign):**
> `Super+L` (lock / hyprlock) and `Super+Space+Enter` (greeter backdoor, greeter-side only).

---

## Apps & launching
| Keybind | Action |
|---|---|
| `Super+Return` | Terminal (kitty → alacritty → foot) |
| `Super+Shift+Return` | Terminal, alternate (alacritty first) |
| `Super+Space` | App launcher (`nyxus_launcher.py`, rofi/wofi fallback) |
| `Super+Shift+D` | Run a command (rofi/wofi run prompt) |
| `Super+Tab` | Window switcher (rofi window) |
| `Super+E` | File manager (nautilus → thunar → dolphin) |
| `Super+B` | Browser (chromium → firefox) |

## Window management
| Keybind | Action |
|---|---|
| `Super+Q` | Close active window |
| `Super+V` | Toggle floating |
| `Super+P` | Pseudo-tile |
| `Super+J` | Toggle split direction *(moved off `Super+T` in Phase 3)* |
| `Super+F` | Fullscreen |
| `Super+Shift+F` | Maximize (fullscreen mode 1) |
| `Super+Shift+C` | Center window |
| `Super+U` / `Super+Shift+U` | Group: toggle / move out of group |
| `Super+]` / `Super+[` | Group: cycle active forward / back |
| `Super+Alt+T` | Freeform ↔ tiling mode toggle |

## Focus / move / resize
| Keybind | Action |
|---|---|
| `Super+←↑↓→` / `Super+H` `Super+K` `Super+;` | Move focus |
| `Super+Shift+←↑↓→` | Move window |
| `Super+Ctrl+←↑↓→` | Resize active window |
| `Super+LMB` / `Super+RMB` (drag) | Move / resize window |

## Workspaces
| Keybind | Action |
|---|---|
| `Super+1`…`Super+0` | Switch to workspace 1–10 |
| `Super+Shift+1`…`Super+Shift+0` | Move window to workspace 1–10 |
| `Super+Home` | NYXUS Home workspace (`name:0`) |
| `Super+Shift+Home` | Relaunch NYXUS Home |
| `Super+scroll` | Next / previous workspace |
| `Super+S` / `Super+Shift+S` | Scratchpad: toggle / move window to |
| `Super+F3` · `Super+Alt+A` | Mission Control |

## Flyouts, Hub & system panels
| Keybind | Action |
|---|---|
| `Super+A` | Quick Settings |
| `Super+N` | Notifications |
| `Super+W` | WiFi |
| `Super+M` | Audio mixer |
| `Super+C` | Calendar |
| `Super+Shift+B` | Bluetooth |
| `Super+Escape` | Power menu |
| `Super+grave` (\`) | Dashboard |
| `Super+G` | DEEP CORE (kernel/security observatory) |
| `Super+/` · `Super+Shift+/` | Keybind cheatsheet |
| `Super+Shift+Y` | Security Center |
| `Super+Ctrl+Alt+L` | PANIC lockdown |

## Lock / logout / session
| Keybind | Action |
|---|---|
| `Super+L` | Lock screen (hyprlock) — **login-agent domain** |
| `Super+Shift+E` | Logout menu (wlogout) |
| `Super+Shift+M` | Exit Hyprland |

## Media / volume / brightness
| Keybind | Action |
|---|---|
| `XF86AudioRaise/Lower/Mute` | Volume up / down / mute (+ OSD) |
| `XF86AudioMicMute` | Mic mute (+ OSD) |
| `XF86AudioPlay/Next/Prev` | Media play-pause / next / previous (playerctl) |
| `XF86MonBrightnessUp/Down` | Screen brightness (+ OSD) |

## Screenshots
| Keybind | Action |
|---|---|
| `Print` / `Shift+Print` | Region / fullscreen (`nyxus_screenshot.py`) |
| `Super+Print` · `Super+Shift+Print` · `Super+Ctrl+Print` | Region · fullscreen · active window |

## Wallpaper & visual FX (signature / flair shards)
| Keybind | Action |
|---|---|
| `Super+Alt+S` | Wallpaper Studio *(moved off `Super+Alt+W` in Phase 3)* |
| `Super+Alt+W` | Cycle wallpaper (nyxus-wall-next) |
| `Super+Shift+W` | Recompute accent from wallpaper |
| `Super+Alt+V` | Live (video) wallpaper toggle |
| `Super+O` / `Super+Shift+O` | Shader: next / off |
| `Super+T` | Per-app border tint toggle (nyxus-tint) |
| `Super+Alt+B` | Music-reactive border toggle (nyxus-beat) |
| `Super+Alt+L` | Living theme toggle |
| `Super+Shift+P` | Wallpaper FX toggle |
| `Super+Z` | Spray-paint overlay |
| `Super+Alt+P` | Pulse toggle |
| `Super+Shift+X` | Prism border pulse (easter egg) |
| `Super+Alt+scroll` · `Super+Alt+=/-/0` | Screen magnifier (lens) in / out / reset |
| `Super+Shift+T` / `Super+Shift+Q` | Lens OCR text / QR scan |

## Modes & diagnostics
| Keybind | Action |
|---|---|
| `Super+Alt+G` | Game mode toggle |
| `Super+Alt+F` | Focus mode toggle |
| `Super+Shift+H` | NYXUS Doctor (diagnostics) |

---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

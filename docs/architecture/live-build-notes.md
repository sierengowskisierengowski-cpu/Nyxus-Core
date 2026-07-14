# Live Build Notes — Hard-Won Constraints & Design Decisions

**Source:** consolidated from agent memory files (Claude Code project memory,
2026-07-06 through 2026-07-08 sessions) during the 2026-07-14 file-sprawl
consolidation pass. These are tribal-knowledge notes captured while building
the live desktop — kept here so they survive beyond any one agent session.

---

## 1. Source of truth & sync workflow

The live machine is the source of truth, not the repo — the repo mirrors it:

- Live configs: `~/.config/{hypr,eww,rofi,dunst,swaync,wlogout,alacritty,kitty,cava,btop,qt5ct,qt6ct,gtk-3.0,gtk-4.0,nyxus}`
- Nyxus scripts: `~/.local/bin/nyxus-*` (shadowed at `/usr/local/bin/nyxus*`)
- Python GTK app suite (~35 apps): `~/.nyxus/nyxus_*.py`, plus app dirs `nyxus-home/`, `nyxus-panel/`, `nyxus-start/`
- Workflow: edit live files → run `scripts/sync-live-config.sh` from the repo/worktree → review `git status` → commit. The sync script pulls live → `iso-builder/nyx-profile/airootfs/etc/skel` (+ `/usr/local/bin`).
- ISO skel tree lives at `iso-builder/nyx-profile/airootfs/etc/skel`.
- Helper binaries of note: `nyxus-livewall-generate` (renders the seamless animated wallpaper loop, scene-aware) and `nyxus-live-wallpaper on|off|toggle|auto` (mpvpaper controller).
- Monitor reference: eDP-1, 1920×1080 laptop panel.
- The `eww` daemon must be **restarted** (not just reloaded) to pick up newly installed fonts.
- EWW bar open order matters: `bar-left`, `bar-right`, `bar-top`, `bar-bottom` (layer-shell exclusive zones) — restart procedure is `eww kill; eww daemon; eww open-many bar-bottom bar-top bar-left bar-right`, order defined in `~/.config/eww/nyxus.conf` (`NYXUS_EWW_BARS`).

---

## 2. Theme spec — "DARK MIRROR"

- Triple-black glass surfaces (`nyx_black_smoke` / `nyx_black_ink` / `nyx_black_void`), white glow, neon accent.
- Accent color follows the current wallpaper — computed via `~/.config/nyxus/accent.json`, applied by `/usr/local/bin/nyxus-apply-accent`.
- Palette source of truth: `nyxus-palette.css` + `nyxus_palette.py` — **must be edited in lockstep**, they are not auto-generated from each other.
- Newest direction (as of the July 2026 home-page rebuild): a borderless "ghost HUD" look — transparent, no boxes, glow text only.
- Current wallpaper reference: `nyxus-graffiti-space.png` (5120×2880); animated loops live at `walls/live/<stem>-live.mp4`.

---

## 3. Typography — the three-font graffiti system

Fonts installed at `~/.local/share/fonts/nyxus/` (synced to the ISO at `/usr/share/fonts/nyxus`):

| Font | Voice | Used for |
|---|---|---|
| **Permanent Marker** | graffiti marker hand | titles, brand, button labels, rofi prompt |
| **Caveat** | loose handwriting | dates, subtitles, hints, empty states |
| **Orbitron** | sci-fi display | hero clocks (dashboard, screensaver, hyprlock, bar clock) |
| JetBrainsMono Nerd Font | — | data readouts (unchanged) |

**Why:** the build intentionally mixes handwritten fonts through the UI to match the graffiti-space wallpaper motif.

**How to apply:**
- Hand fonts hate wide letter-spacing — pull tracking down to ≤0.14em wherever a marker face replaces spaced all-caps.
- Caveat needs roughly 1.5× the pixel size of the sans-serif font it replaces.
- Applied via the "GRAFFITI TYPE SYSTEM" block at the **end** of `~/.config/eww/eww.scss` — it must stay last in the cascade. Also applied in `hyprlock.conf` and `rofi/startmenu.rasi`.

---

## 4. EWW bar constraints (hard-won, 2026-07-07)

The build runs 4 EWW bars: `bar-bottom` (main), `bar-top` (ticker), `bar-left` (workspaces), `bar-right` (app rail). Violating any of the below **silently** breaks the bars (grey/unthemed, shoved sideways, or blank icons) — no error, just broken visuals.

- `eww.scss` must stay **pure ASCII**. Any non-ASCII character — `·`, `—`, `…`, curly quotes, even inside comments — makes the Sass compiler emit `@charset "UTF-8"`, which EWW's underlying GTK CSS parser rejects. The entire theme silently drops to default grey when this happens. *(This is the same class of bug hit again during the 2026-07-13 grey-bar incident with `justify-content`/`text-align`/`width: 100%` — GTK's CSS parser is strict about web-standard CSS properties in general, not just charset.)*
- The horizontal bars use `:stacking "bottom"`; the vertical rails use `"fg"`. Hyprland arranges layer levels bottom→top, applying exclusive zones cumulatively. If all four bars share one level, arrangement follows surface creation order — which reshuffles on every `eww reload` — and the full-width bars get re-centered against the rails' 66px zones (visible as x=53/33/-33 drift). **Never move `bar-top`/`bar-bottom` back to `"fg"`.**
- The bars' floating "island" inset comes from CSS `margin: 0 12px` on `.bar-bottom`/`.bar-top` combined with a 100%-width surface — never from a `<100%` geometry width.
- `letter-spacing` on bar labels/pills makes GTK ellipsize them (e.g. `"× NYX…"`); the right cluster overflows above roughly a 10px pill font size.
- Watch for `:glyph ""` strings in `eww.yuck` silently losing their Nerd Font glyphs (renders as blank tiles) — restore with Font Awesome-range codepoints.
- Reference backups from that hardening pass: `eww.{scss,yuck}.bak-20260707`.

---

## 5. Living wallpaper / FX runtime layer (added 2026-07-07)

- `nyxus-live-wallpaper on` starts `mpvpaper` with `input-ipc-server=$XDG_RUNTIME_DIR/nyxus-mpv.sock`, then runs `nyxus-wall-fx auto`. Autostart hook lives around line 45 of `hyprland.conf` (`nyxus-live-wallpaper auto || stock autostart`).
- `nyxus-wall-fx` (Python, `~/.local/bin`): cava audio pulse → mpv saturation/gamma/speed; Hyprland `socket2` `workspacev2>>ID,NAME` events → per-workspace hue tints. Workspaces are **named** (1 WEB, 2 CODE, 3 TERM, 4 FILES, 5 MEDIA, 6 COMMS) — always key off the numeric ID, never the name. Toggle: `SUPER+SHIFT+P`.
- `nyxus-spray` (Python, GTK3 + GtkLayerShell + cairo): spray-paint overlay, `SUPER+G`. Trail mode (`T` / `--trail`) paints on cursor move without a click. The paint surface must grow with `size-allocate` — layer-shell maps small then expands, otherwise paint gets stuck in one corner.
- FX binds live in `~/.config/hypr/conf.d/nyxus-fx.conf`. **`conf.d` files are sourced explicitly at the end of `hyprland.conf`, not via glob** — new drop-in files need an explicit `source =` line added, or they're silently ignored.
- `nyxus-livewall-generate` scenes: `nyxus-graffiti-space` and `nyxus-void-vortex` (counter-rotating churn, vortex core at 935,545 on a 1920×1080 grid) have dedicated logic; everything else uses the generic engine.
- Probing the mpv IPC socket: use `socat - UNIX-CONNECT:/path`. Plain `socat - /path` **creates a regular file** if the socket is gone, which masks the real problem.
- `pkill`/`pgrep -f "nyxus-..."` run from a tool call can match the tool's own bash eval line — anchor the pattern or use pidfiles instead.
- `nyxus-workspace-wallpaperd` (systemd user unit, parallel session) swaps `swaybg` per workspace from `~/.config/nyxus/workspaces.json`. Currently all workspaces map to graffiti-space — idempotent, harmless to leave running under mpvpaper.

---

## 6. Addon layer status (verified/pushed 2026-07-08)

The 12-addon eye-candy layer was verified end-to-end and pushed on 2026-07-08 (commits `aa18551`, `1771f76`, `a8ffbe4` on `nyxus-hyprland-055-fixes`).

**Verified working:** accents/palette-extract (Python 3 — **not** bash, don't `bash -n` it), `swww` (started on-demand by `nyxus-set-wallpaper`; idle while mpvpaper runs is expected/correct), OSD, shaders, `nyxus-beatd` (pure-bash rewrite, exact border restore), lock trio, boot cinematic (rewired into autostart with a fail-safe), plugins, sounds, extras.

**Bugs fixed that session:**
- `nyxus-plugins`'s `loaded()` check grepped for `"<name>.so"`, but Hyprland 0.55 lists plugins as `"Plugin <name> by <author>"` — unload/toggle were silently dead. Fixed to match both forms.
- `.gitignore` had an unanchored `.local/` rule (a Replit leftover) that was silently ignoring the skel `.local/` tree — the sounds pack and plugin `.so` trio never shipped as a result. Anchored to `/.local/`, added `artifacts/**/.local/`.
- `sync-live-config.sh` now also syncs `~/.local/share/nyxus/sounds` and `~/.local/lib/nyxus-plugins` into the skel tree.
- `mpvpaper`/`wall-fx` had silently died; `nyxus-live-wallpaper auto` restored them (`LIVE=on` in `livewall.conf`).

**Still open (as of 2026-07-08, unconfirmed current status):**
- Packages never installed (require interactive sudo password): `sudo pacman -S --needed satty tesseract tesseract-data-eng zbar` + `yay -S wshowkeys`. Blocks Shot/Lens OCR+QR and the keystroke-display overlay.
- A graffiti wallpaper-pack worktree/branch with uncommitted work (3 category dirs, `nyxus-fluid-wallpaper`, a generator script) vanished mid-session on 2026-07-08 — likely clobbered by a parallel agent session, nothing recoverable in git history. Would need regenerating if still wanted.
- `home-hud-rebuild` branch was merged; the live `nyxus-home` was newer than the branch at merge time (had MPRIS `MusicCard`) — live state was synced into skel instead. `Super+Home` (not `Super+0`) opens the HOME workspace (`name:0`).
- User requested a fully reactive "living theme": all colors (borders/bars/buttons) pulse and shift with notifications, email, music, and the focused/hovered app. Partial pieces exist — `nyxus-beatd` (music→border spin), `nyxus-tintd` (per-app border tint, off by default, publishes `$XDG_RUNTIME_DIR/nyxus-border-colors`), `nyxus-wall-fx` (audio+workspace→wallpaper), the accent engine. **Missing piece:** a notification/event→color-pulse daemon plus EWW bar reactivity. Not started as of last record — this maps to the "premium/rich features" backlog in the build brief (`docs/NYXUS_BUILD_BRIEF.md` §9).

---

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

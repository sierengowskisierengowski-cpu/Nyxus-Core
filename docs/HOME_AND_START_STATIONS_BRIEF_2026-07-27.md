# NYXUS — HOME & START STATIONS BRIEF (2026-07-27)

> Session: overnight Jul 26 → 27. Owner: Joseph A. Sierengowski (`nyx` / `nyxus`).
> Supersedes nothing — this **extends** `BARS_AND_LOGIN_BRIEF_2026-07-26.md`.
> Everything below is live on the machine **and** committed. Read the traps
> section before touching eww; several of them cost real time this session.

---

## TL;DR — what changed

Two eww "stations" now exist, each a full-screen widget surface pinned to a
named workspace and shown/hidden by one watcher:

| Station | Key | Window | What it is |
|---|---|---|---|
| **HOME** | `Super+Home` | `home-deck` | Scattered desktop widgets (the home page) |
| **START** | `Super+End` | `start-panel` | The Start menu, replacing the GTK4 app |

The left rail now reads **HOME**, **START**, then numbered stations **1–9**.

---

## 1. The HOME deck — restored, not rebuilt

**The owner opened the session thinking a reboot had destroyed the deck.
Nothing was lost.** `eww.yuck`, the `.deck-*` styles and the watcher script
were all still on disk. What was missing: **nothing launched the watcher at
login.** An eww layer-shell window is bound to a *monitor*, not a workspace,
so the watcher is the only thing that can open it. Added the `exec-once`.
The watcher had also **never been committed** — which is why it felt like
data loss. It is tracked now on both the api-server and ISO surfaces.

Layout is a **loose scatter** (owner's explicit pick over a grid): flexible
struts push cards apart, fixed shims bias each row, so the wallpaper's alien
(x ≈ 350–760, full height) and the UFO stay visible through the middle.
Cards carry a **depth tier** — `.deck-near` / `.deck-mid` / `.deck-far` —
driving size, opacity and rim strength, because **GTK3 CSS has no
`transform: scale`**; distance is painted, not transformed.

Cards: CLOCK, WEATHER (+moon), VITALS, NOW PLAYING, NETWORK, CALENDAR,
POWER, SYSTEM, ALERTS, LAUNCH. All read vars the bars already poll — no new
polling cost.

Also fixed this session:
* `Super+Home` still dispatched `name:0`. The station was renamed to
  `name:HOME` on Jul 26, so the key landed on a stray workspace. The
  cheatsheet claimed HOME was `Super+0` — that is workspace 10. Both fixed.
* `workspaces.sh` detected HOME by `name:0` / id `-1337`, so after the
  rename **the HOME pill could never highlight**. It matches on station
  NAME now — named workspaces get arbitrary negative ids, so an id test is
  fragile.
* Clock is **12-hour** (`%-I` so the string never gets wider than the old
  `00:46` and the measured bar clock slots still fit; `ampm` is a separate
  field). Weather is **Fahrenheit** (`temp_F`). Bust
  `~/.cache/nyxus-weather.json` after changing units.

---

## 2. The START panel — why the GTK app was replaced, not rethemed

`~/.nyxus/nyxus-start` ran on the **OVERLAY** layer with
`KeyboardMode.ON_DEMAND` and exactly **one** dismissal path: Escape. A prior
agent had deliberately removed click-outside dismissal (`main.py:905-911`),
and the other documented path — "click the Start button again" — died when
eww replaced waybar. So whenever the surface did not hold keyboard focus it
could be neither closed **nor moved**. The owner hit this live and could not
get rid of it.

`Super+Shift+End` now runs `pkill -f 'nyxus-start/main.py'` as a
compositor-level escape hatch. **The old app is still installed as a
fallback but is no longer the way in.**

The panel carries: identity chip, search, PINNED grid, ALL APPS grouped into
labelled category cards, RUNNING windows (click to focus), the GowskiNet
**ARSENAL** with live state, PLACES, PENDING updates, and the scratchpad.

**The right column is deliberately NOT the machine vitals / weather /
now-playing that the HOME deck already shows.** The owner called this out
directly: duplicating them makes the two stations interchangeable.

**ARSENAL reads the same `~/Arsenal/registry.toml` the Arsenal TUI reads** —
add a `[[tool]]` block there and it appears in the panel with no code
change. Status probes mirror the TUI (`systemctl` system/user, `docker`,
`curl`), all short-timeout because they run on a poll: 14 tools resolve in
~0.15s.

### Search is a separate window on purpose

**eww 0.5 exposes `:focusable` as a BOOL that maps to wlr-layer-shell
EXCLUSIVE keyboard interactivity — there is no on-demand.** A text field
inside the panel therefore holds the keyboard for as long as the panel is
mapped. The first build did exactly that and swallowed every keystroke
session-wide; **the owner reported it twice as a freeze.**

So the search box lives in its own short-lived `start-search` window that
takes the keyboard only while open and closes on Enter, on the X, on leaving
START, or via `Super+Shift+S`. Those escape hatches deliberately do **not**
depend on the window's own key handling.

---

## 3. Traps — read before touching eww

1. **★ eww sizes a window to its CONTENT.** A `:geometry` height is a
   request, not a cap. Content taller than the free area between the bars
   (1080 − 40 bar-top − 158 bar-bottom = **882px**) makes Hyprland centre
   the oversized surface and park it at a **negative y** — this silently ate
   the deck's brand line and slid its top row under bar-top (`y=-59`), and
   later pushed the Start panel to 950px. Neither `100%`, nor `80%` (eww
   resolved it to 959!), nor an explicit px height fixed it — **only
   shrinking the content did.** Always verify with `hyprctl layers -j`,
   which gives real x/y/w/h per namespace. Never eyeball a screenshot.
2. **Anything that can grow will break the layout.** An unbounded feed
   (notifications, app catalogue) drags the whole surface taller. Wrap in a
   fixed-height `(scroll :height N)`.
3. **`:focusable true` is a session-wide keyboard grab.** See above. Do not
   set it on a layer window in this eww except for the search overlay.
4. **`pkill -f <pattern>` from an inline `bash -c` kills its own shell.**
   The caller's `/proc/self/cmdline` contains the pattern (exit **144**), so
   every "restart the watcher" attempt silently did nothing and looked like
   a broken watcher. Run the kill from a **script file**.
5. **Never `str.replace()` bare words across `eww.yuck`.** Substituting
   glyph placeholders named `POWER`/`STORE`/`TERM`/`LOCK` corrupted
   `POWERPROF` into `PROF` and broke the whole config (`Invalid token`). Use
   `@@DELIMITED@@` tokens and assert none survive. **Snapshot `eww.yuck`
   before any scripted rewrite** — recovery came from a `.bak-prestart` copy.
6. **A block replace can eat a widget.** `station_pill` is defined *between*
   `workspace_home_pill` and `workspaces_rail`; replacing that span deleted
   it and stations 1–9 vanished from the rail.
7. **Unicode escapes must be resolved before writing.** Writing eww.yuck
   from a Python `r'''...'''` block leaves `\U000f0954` as *literal text* on
   screen. 25 escapes rendered as visible garbage before this was caught.
8. **Blank glyphs are usually empty strings, not a missing font.** Four
   launcher buttons rendered as empty boxes because their glyph args were
   literally `""`. Verified codepoints: arch `0xf08c7`, terminal `0xf120`,
   firefox `0xf269`, files `0xf07b`, notepad `0xf040`.
9. **CSS `letter-spacing` makes GTK ellipsize labels** ("CLOC…"). Pango does
   not add it to a label's natural width request. **Lowering the value does
   not help** (0.10em still tripped it) — remove it and bake the tracking
   into the string.
10. **GTK3 overlay scrollbars draw on top of content** and cannot be
    disabled from CSS. Inset the *rows* (`margin-right`), not the scroller
    (padding on a scroll widget does not move its child).
11. **`sass` is not installed** — `compile-eww-css.sh` silently no-ops and
    reuses the committed `eww.css`. Patch `eww.css` **surgically** alongside
    `eww.scss.source`; never wholesale-recompile (it shifts the palette).

---

## 4. The watcher — `~/.local/bin/nyxus-home-deck`

Name kept so the existing `exec-once` and `Super+Shift+Home` bind still
work. It maps station → window and had **two real bugs**, both of which
showed up as *both* stations' windows being mapped at once:

1. **Not a singleton.** Two instances fought — one opened what the other had
   just closed. `flock` now makes a second instance exit.
2. **It branched on `eww active-windows`,** which lags its own open/close, so
   a fast station switch read stale state. It now **asserts** the desired
   state unconditionally every sync.

Verified: `FORGE → neither`, `HOME → home-deck`, `START → start-panel`.

---

## 5. Other fixes

* **UI chime flipped the bottom bar to the boombox.** `player.sh` fell back
  to "any live sink-input means Playing", and the NYXUS chime
  (`nyxus-sound` → `pw-play`) is a sink-input — so every hotkey sound
  flipped the bar for ~1s. `media.role` does **not** discriminate (pw-play
  announces `role=music`), so the guard ignores fire-and-forget sound tools
  by **`application.name`** — *not* `application.process.binary`, which a
  first cut used and which silently broke real playback because **mpv
  publishes `application.name` but no `process.binary`.** Verified all four
  states: silent, chime, mpv playing, after stop.
* **Notepad buttons were broken.** `/usr/local/bin/nyxus-notepad` execs
  `/opt/nyxus-notepad/main.py`, which is not the notepad that works. Both
  the panel and the HOME deck LAUNCH row now run
  `~/.nyxus/nyxus_notepad.py` with the wrapper as fallback.
* **Pulse + transparency (owner request):** deck cards and the panel carry a
  bass-reactive rim driven by `CAVA_BASS` **inline** (same formula as the
  boombox — `eww.yuck` ~line 599) plus a slow `@keyframes` breathe when
  nothing plays. GTK's CSS engine here **does** run `@keyframes` (proven by
  `boombox-led-pulse`). Background alphas dropped so the wallpaper reads
  through — still above the `ignore_alpha 0.2` blur threshold.
* App catalogue is **cached** (`~/.cache/nyxus-start-apps.json`, 600s TTL).
  The first build re-enumerated ~400 desktop entries per keystroke: 30s+ →
  **0.10s**.

---

## 6. Where things live

```
~/.config/eww/eww.yuck                    home_deck + start_panel + rail
~/.config/eww/eww.css / eww.scss.source   patch BOTH, surgically
~/.config/eww/scripts/start-feed.py       meta | status | apps | live | arsenal
~/.config/eww/scripts/start-search.py     cached matcher, pushes STARTFOUND
~/.config/eww/scripts/workspaces.sh       rail state (HOME/START/1-9)
~/.config/eww/scripts/player.sh           MPRIS + sink-input fallback
~/.local/bin/nyxus-home-deck              station -> window watcher
~/.config/hypr/conf.d/nyxus-stations.conf HOME + START workspace rules
~/.config/nyxus/stations.json             stations 1-9 (10 dropped)
~/Arsenal/registry.toml                   ARSENAL source of truth
~/.config/nyxus-start/                    pins.json, recent.json, scratchpad.txt
```

The feed scripts **reuse the GTK app's own `apps.py` / `status.py` /
`settings.py`** via `sys.path.insert` rather than reimplementing discovery —
a second copy would drift.

Three surfaces must stay in sync: live `~/.config/`, repo
`artifacts/api-server/nyxus-scripts/`, ISO skel
`iso-builder/nyx-profile/airootfs/etc/skel/`.

---

## 7. Open / next

* **`main` is not pushed.** Commits are on branch
  **`home-deck-scatter-20260727`** (agent cannot push `main`). Owner
  fast-forwards with `git -C ~/Nyxus-Core push origin main`.
* The deck shows **only on HOME** by design. Owner was offered an
  everywhere mode and has not asked for it.
* eww has **no multiline editable text**, so the scratchpad is read-only
  with an "open in editor" button. Owner chose this over a fake editor.
* App tile glyphs are mapped by category/name keyword — crude. Real themed
  icons would need eww to resolve GTK icon themes, which it cannot.
* `nyxus-home` GTK app remains disabled (builds its grid, never paints).
  The deck supersedes it; do not revive it without being asked.

# NYXUS — EYE CANDY: FEASIBILITY STUDY & DESIGN SPECIFICATION

> **Written:** 2026-07-31 · **Status:** SPECIFICATION ONLY — nothing in this
> document has been implemented, and no config, eww, theme or asset file was
> touched to produce it.
>
> **Scope:** an honest capability map for a distinctive NYXUS visual /
> interaction language, plus a concrete design spec the next agent can build
> from. Written against the versions the ISO **actually ships**, not from
> memory: every capability claim below cites the source file it was verified
> in.
>
> **Read first:** [`HANDOFF.md`](../HANDOFF.md) §7,
> [`THEME.md`](./THEME.md), [`DESIGN_CONTRACT.md`](./DESIGN_CONTRACT.md),
> [`EWW_CHROME_REVERT_BRIEF_2026-07-26.md`](./EWW_CHROME_REVERT_BRIEF_2026-07-26.md).
>
> **This document does not propose re-landing `ecdcc952` / `c73caae0` /
> `0bf2d06c`.** That redesign was reverted at the owner's instruction and the
> restored desktop is the baseline everything here builds on. Nothing below
> touches the saucer art, the boombox face, the dock/ticker wraps or the bar
> geometry.

---

## 0. THE BRIEF, AND THE ONE-LINE ANSWER

The owner asked for a look that is *"smooth as butter, rich in every aspect"*,
*"true one of a kind"*, with progressive hover-reveal, *"more real looking"*
controls, *"more of a 3D look"*, backgrounds that *"blend in, almost as if it's
not even there"*, and things that *"flip up or over or pop up"* — at a hard
quality bar of *"clean, super clean only — not half ass. 100%."*

**The honest answer:** roughly 70% of what he described is achievable on this
stack, and a meaningful part of it is achievable by **wiring together machinery
he already owns and is not using**. The remaining 30% splits into "achievable
only as a convincing fake" (3D, depth, filters) and "not achievable at all"
(true 3D compositing, arbitrary CSS filters, per-widget blur).

The single biggest constraint is not Hyprland. It is **GTK3**. eww is pinned to
a GTK3 release, and GTK3's CSS engine has no `filter:`, no `transform:`, no
percentage margins and no per-widget backdrop blur. Every "frosted glass"
effect in NYXUS is the compositor blurring a whole layer surface, and every
"depth" effect is *painted*, not transformed. That ceiling is fixed for this
build and cannot be raised without replacing eww.

The second biggest constraint is **restraint**, and it is self-imposed. See §6.

---

## 1. GROUND TRUTH — WHAT THIS BUILD ACTUALLY SHIPS

Everything in this document is verified against these versions. Do not
substitute what the builder box has; it differs on both counts.

| Component | ISO ships | Builder box has | Evidence |
|---|---|---|---|
| Hyprland | **0.56.1** | 0.55.4 | `HANDOFF.md` (squashfs pacman db); `hyprctl version` here |
| hyprlang | **0.6.8** | — | `HANDOFF.md` squashfs verification |
| **eww** | **v0.6.0, built from source** | **0.5.0** | `customize_airootfs.sh:112` — `NYXUS_EWW_TAG="${NYXUS_EWW_TAG:-v0.6.0}"` |
| eww's GTK | **GTK 3** | GTK 3 | eww `v0.6.0` `crates/eww/Cargo.toml:24` — `gtk = "0.17.1"` (gtk-rs 0.17 binds GTK3); `gtk-layer-shell = "0.6.1"` |
| GTK apps (`nyxus_*.py`) | GTK4 + libadwaita | same | separate stack from eww — see §3.4 |

### 1.1 ⚠ The eww skew is NOT documented anywhere else, and it matters

`HANDOFF.md` repeatedly reasons about **eww 0.5.0** because that is what the
builder box runs, and several traps are recorded as "in eww 0.5". **The ISO
builds and ships eww v0.6.0.** This is the same shape as the Hyprland
0.55.4-vs-0.56.1 skew that gate `13x` already warns about, but for eww there is
no gate and no warning.

Checked, so nobody re-derives it — the following HANDOFF rules **do still hold
on v0.6.0**, verified in the v0.6.0 source:

| HANDOFF rule | Holds on v0.6.0? | Evidence |
|---|---|---|
| `:focusable true` is a session-wide keyboard grab | **YES — unchanged** | `crates/yuck/src/config/backend_window_options.rs:112` — `focusable` is still a plain `bool`, still maps to layer-shell EXCLUSIVE. The `none`/`ondemand`/`exclusive` enum landed *after* v0.6.0 and is **not** in this build. |
| eww has no `:onkeydown` | **YES** | no such prop in `widget_definitions.rs` at either tag |
| eww SIGKILLs a handler after `:timeout` (default 200ms) | **YES** | `widget_definitions.rs` — every event prop defaults `timeout: as_duration = Duration::from_millis(200)` |
| `(eventbox :onclick "true")` blocks nothing | **YES** | handler returns `Inhibit(false)` in both tags |

So: **no HANDOFF rule is relaxed by the newer eww.** The skew is worth knowing
because it means widget behaviour verified live on the builder box is evidence
for 0.5.0, not proof for the stick — but on these four points the two agree.

---

## 2. FOUR THINGS FOUND WHILE RESEARCHING THIS — READ BEFORE DESIGNING

These are defects/latent gaps discovered while establishing the capability map.
They are reported, **not fixed** (this task is specification-only). Three of
them directly affect the eye-candy plan, and one is the cheapest win in the
whole document.

### 2.1 🔴 `nyxus-shader` ships a launcher with no payload — the shader feature is dead everywhere

`nyxus-shader` resolves `~/.config/hypr/shaders/<name>.glsl` and refuses to run
if the file is missing (`nyxus-shader:28,39`). **There is not a single `.glsl`
file anywhere in the repository**, and nothing in `build-iso.sh`,
`nyxus_install.sh` or `nyxus-bootstrap` ever creates that directory.

```
$ git ls-files | grep -i 'glsl\|shader'
artifacts/api-server/nyxus-scripts/nyxus-shader          <- the launcher
iso-builder/.../skel/.config/cava/shaders/*.frag         <- cava's own, unrelated
iso-builder/.../usr/local/bin/nyxus-shader               <- the launcher again
```

`~/.config/hypr/shaders/` **does not exist on the builder box either**, so this
is not the usual "works here, dead on the stick" trap — it is dead in both
places and always has been. The five advertised filters (`ember`, `night`,
`vignette`, `crt`, `noir`) have never existed.

Observable symptoms, all consistent with what is on the box today:
- `Super+O` (`nyxus-shader next`) → cycles to `ember` → prints
  `nyxus-shader: no shader 'ember'` and exits 1. Silent to the user.
- `Super+Shift+O` and the Hub/quick-settings "Night Light" tile → route through
  the same missing files.
- `exec-once = nyxus-shader restore` at session start is **harmless**: the
  saved state is `off`, and `off` applies `[[EMPTY]]` without touching a file.

**Why this is in an eye-candy document:** the brief identified
"system-state-reactive GLSL shaders" as the rarest opportunity in this build,
on the basis that NYXUS *already has* a shader mechanism plus a state bus. The
mechanism is a 70-line `hyprctl` wrapper; the shaders are the actual work and
none of it has been done. That is a correction to the premise — it makes the
idea **more** work than assumed, but it also means there is no legacy shader
art to stay consistent with. Greenfield.

### 2.2 🔴 The saucer "card flip" is not a flip — it is a hard cut

`eww.yuck:762` declares:

```
(stack :class "saucer-stack" :transition "rotate-left-right" :same-size true
```

and the comment above it claims *"Verified live (rev 2026-07-25): reads as a
real flip at the default ~200ms GTK stack duration"*.
`BARS_AND_LOGIN_BRIEF_2026-07-26.md` §5 records the same claim: *"Flip
transition swapped `crossfade` → `rotate-left-right` (GTK's real card-flip, not
a fade standing in for one)."*

**`rotate-left-right` is not a valid eww stack transition — in v0.6.0 or in
v0.5.0.** The complete accepted set, identical at both tags, is:

```rust
// crates/eww/src/widgets/widget_definitions.rs:1258 (v0.6.0)
// crates/eww/src/widgets/widget_definitions.rs:1170 (v0.5.0)
"slideright" | "slideleft" | "slideup" | "slidedown" | "fade" | "crossfade" | "none"
```

Anything else hits `enum_parse!`'s fallthrough and returns
`Err("Couldn't parse transition: '<value>'. Possible values are …")`
(`crates/eww/src/util.rs:48`). That error surfaces inside the prop listener
closure generated by `def_widget!`, so **`set_transition_type()` is never
called** and the `gtk::Stack` keeps its constructor default,
`StackTransitionType::None`.

Net effect: the music face does not flip, and it does not even crossfade — it
**hard-cuts**, which is worse than the `crossfade` that was replaced. The
`:selected` and `:same-size` props are separate listeners and still work, which
is why the face changes at all and why this reads as "working".

- **Impact on this plan:** the owner explicitly wants *"things that flip up or
  over"*. He currently has exactly one flip in the build and it is inert. This
  is the cheapest possible visible win in the entire document — a one-word
  change — and §11 ranks it first.
- **Honest limit:** GTK3's `GtkStack` has **no rotation/flip transition at
  all**, at any value. `slideleft`/`slideright` with `:same-size true` is the
  closest thing to a card turn that this toolkit can produce. See §5 for what a
  real flip would cost.
- **To confirm on the stick without changing anything:**
  `grep -i "couldn't parse transition" ~/.local/share/eww/eww.log` (or
  `journalctl --user -t eww`). The line should be present on every daemon start.

### 2.3 🟡 `:onhover` / `:onhoverlost` exist and are used **once, in a window nothing opens**

```
$ grep -c 'onhover' eww.yuck        ->  0        (the bars and all 12 decks)
$ grep -n  'onhover' dock.yuck      ->  1        (defwindow dock-reveal, §4.2)
```

The one use is the dormant dock auto-hide strip — see §4.2, which is the most
important entry in the whole wiring audit. **Across every surface the owner
actually sees today, hover-reveal is used exactly zero times.**

The props are real in the shipped eww and take a command plus the pointer x/y:

```rust
// crates/eww/src/widgets/widget_definitions.rs:768-787 (v0.6.0) — on `eventbox`
// @prop onhover     - event to execute when the user hovers over the widget
// @prop onhoverlost - event to execute when the user losts hovers over the widget
prop(timeout: as_duration = Duration::from_millis(200), onhover: as_string) { … }
prop(timeout: as_duration = Duration::from_millis(200), onhoverlost: as_string) { … }
```

`eventbox` also carries `:cursor` (a GDK3 cursor name, line 789) and
`:onscroll` (line 755). **The entire progressive-disclosure design space the
owner described is untouched greenfield**, and the widget-level primitives for
it are already in the binary. This is the single most important enabling fact
in this document; §7 specifies the whole behaviour on top of it.

### 2.4 🟡 Hyprland 0.56.1 has a native window **glow** that NYXUS does not use

```cpp
// src/config/values/ConfigValues.cpp:218-224 (v0.56.1)
MS<Bool>    ("decoration:glow:enabled",        "enable inner glow on windows", false, …),
MS<Int>     ("decoration:glow:range",          "glow range (size) in layout px", 10, …),
MS<Int>     ("decoration:glow:render_power",   …),
MS<Gradient>("decoration:glow:color",          …, CHyprColor{0xee33ccff}, …),
MS<Gradient>("decoration:glow:color_inactive", …),
```

`nyxus-hyprland-general.conf` sets `shadow` (with a neon-green
`rgba(39ff143a)` — already a glow-by-shadow hack) but never touches
`decoration:glow`. There is also a dedicated **`glowangle`** animation node
(`src/config/shared/animation/AnimationTree.cpp:25`), i.e. a rotating gradient
glow, exactly parallel to the `borderangle` NYXUS already drives from CAVA.

This is a real, native, zero-dependency neon halo around every window, in the
ALIEN NEON palette, that the build is currently leaving on the table.

---

## 3. CAPABILITY MATRIX

Cost is engineering effort. Risk is risk to the stability the owner just spent
days recovering. "Where" names the surfaces it would apply to.

### 3.1 Hyprland 0.56.1 — compositor-side

| Effect | Possible? | Mechanism (verified) | Cost / Risk | Where |
|---|---|---|---|---|
| Frosted glass behind panels | **Already shipped** | `layerrule = blur on` + `ignore_alpha 0.2`, `decoration:blur` size 14 / passes 4 | — / — | all `nyxus-*` layers |
| Window **inner glow**, neon | **YES — unused** | `decoration:glow:{enabled,range,render_power,color,color_inactive}` (`ConfigValues.cpp:218`) | S / **Low** | every toplevel window |
| **Rotating** glow halo | **YES — unused** | `animation = glowangle, …, loop` (`AnimationTree.cpp:25`) + gradient `glow:color` | S / Low | every toplevel |
| Rotating border gradient | **Already shipped** | `animation = borderangle, 1, 240, linear, loop`; CAVA retunes it in 4 tiers | — / — | every toplevel |
| Squircle corners | **Already shipped** | `decoration:rounding_power = 3.0` (2 = circle) | — / — | every toplevel |
| Layer surfaces animate in/out | **YES — unused** | `layersIn` / `layersOut` / `fadeLayersIn` / `fadeLayersOut` nodes (`AnimationTree.cpp:31-48`) | S / Low | every eww window |
| Per-surface animation override | **YES — unused** | `layerrule = animation <name>, match:namespace …` (`LayerRuleEffectContainer.cpp`) | S / Low | per eww namespace |
| Dim the desktop around a panel | **YES — unused** | `layerrule = dim_around on` + `decoration:dim_around` (default 0.4) | S / **Medium** — see §12.4 | Hub, powermenu, decks |
| Panel sees wallpaper only, not windows | **YES — unused** | `layerrule = xray on` | S / Low | bars, decks |
| Panel above the lock screen | **YES — unused** | `layerrule = above_lock on` | S / **High** — security | *not recommended* |
| Panel excluded from screen share | **YES — unused** | `layerrule = no_screen_share on` | S / Low | GHOST/ARSENAL decks |
| Layer stacking order within a layer | **YES — unused** | `layerrule = order <int>` | S / Low | bars vs decks |
| Custom easing curves | **Already shipped** | 8 `bezier =` curves in `hyprland.conf:294-303` | — / — | all animations |
| Full-screen GLSL post-process | **YES — mechanism only** | `decoration:screen_shader`, hot-swappable (`REFRESH_SCREEN_SHADER`) | **M** (shaders must be written from scratch — §2.1) / Medium | whole screen |
| Shader reacts to **time** | **YES, but see cost** | `uniform float time` (`Shader.cpp:204`) | S / **HIGH — see §12.1** | whole screen |
| Shader reacts to **cursor** | **YES, but see cost** | `pointer_position`, `pointer_last_active`, `pointer_pressed_{positions,times}`, `pointer_hidden`, `pointer_shape` … (`Shader.cpp:213-225`) | S / **HIGH — see §12.1** | whole screen |
| Shader reacts to **system state** | **YES — by file swap only** | no custom uniforms exist; bake constants into a generated `.glsl` and `hyprctl keyword decoration:screen_shader <path>` | **M** / **Low** | whole screen |
| Per-window opacity by state | **Already shipped** | `decoration:{active,inactive}_opacity`, `dim_inactive`/`dim_strength 0.12` | — / — | every toplevel |
| Special-workspace overlay (drawer) | **YES — partly used** | `specialWorkspace` animation, `decoration:dim_special 0.35` | S / Low | scratchpads |
| Zoom / lens | **Already shipped** | `cursor:zoom_factor` via `nyxus-lens.sh` | — / — | whole screen |

**Not available as a layer rule:** there is **no `opacity` layerrule**. The
complete effect list for 0.56.1 is exactly ten entries —
`no_anim, blur, blur_popups, ignore_alpha, dim_around, xray, animation, order,
above_lock, no_screen_share` (`src/desktop/rule/layerRule/LayerRuleEffectContainer.cpp`).
Panel translucency therefore has to come from eww CSS alpha, never from
Hyprland. Layer rules also **match on `namespace` only** (`LayerRule.cpp:107`)
— there is no title/class/state matching for layers.

### 3.2 eww v0.6.0 / GTK3 — widget-side

| Effect | Possible? | Mechanism (verified) | Cost / Risk | Where |
|---|---|---|---|---|
| Hover enter/leave events | **YES — unused** | `eventbox :onhover / :onhoverlost` (`widget_definitions.rs:768,779`) | S / Low | anything |
| Animated show/hide of a child | **YES — unused** | `revealer :transition :reveal :duration` (default 500ms, `widget_definitions.rs:326-340`) | S / Low | anything |
| Slide/fade between two faces | **YES — mostly unused** | `stack :transition :selected :same-size` | S / Low | saucer, decks |
| Per-widget CSS transitions | **YES** | GTK3 CSS `transition: <prop> <dur> <easing>` | S / Low | anything |
| CSS `@keyframes` animation | **YES — proven live** | GTK3 CSS animations (`boombox-led-pulse` already works) | S / Low | anything |
| `:hover` / `:active` CSS states | **YES** | GTK3 pseudo-classes | S / Low | anything |
| Custom mouse cursor per widget | **YES — unused** | `eventbox :cursor "<gdk3 name>"` (`widget_definitions.rs:789`) | S / Low | interactive widgets |
| Scroll events | **YES — unused** | `eventbox :onscroll` | S / Low | sliders, decks |
| Drag & drop target | **YES — partly used** | `eventbox :ondropped` | S / Low | dock |
| Live value → inline style | **Already shipped** | `:style` interpolation from `CAVA_BASS` etc. | — / — | decks, boombox |
| Colour / glow / shadow transitions | **YES** | `box-shadow`, `border-color`, `background` are all animatable in GTK3 CSS | S / Low | anything |
| **`filter: blur()` / `backdrop-filter`** | **NO** | GTK3 CSS has no `filter` property at all | — | — |
| **`transform: scale/rotate/translate`** | **NO** | GTK3 CSS has no `transform` property | — | — |
| **Percentage margins/padding** | **NO** | GTK3 CSS rejects them | — | — |
| **Per-widget blur** | **NO** | blur is a compositor effect on a whole layer surface | — | — |
| **Relative `url()` in `eww.css`** | **NO** | does not resolve; only inline `:style` urls do | — | — |
| **`background-size` from the stylesheet** | **NO** | the compile step strips it — pre-scale the PNG or use inline `:style` | — | — |
| **Multi-line editable text** | **NO** | eww has no such widget | — | — |
| **Rotate / flip stack transition** | **NO** | GTK3 `GtkStack` has no rotation transition; eww accepts only 6 names (§2.2) | — | — |

### 3.3 The inline-`:style` rule that outranks everything

**An inline `:style` beats every stylesheet rule**, at any specificity. This is
already load-bearing: `deck_card`, `start_panel` and `ghost_card` all set
`box-shadow` inline from `CAVA_BASS`, which is exactly why `.nyx-surface`
deliberately does **not** declare `box-shadow`
(`HOME_AND_START_STATIONS_BRIEF_2026-07-27.md` §2b).

**Design consequence, and it is a hard one:** any property you intend to
animate from CSS (`:hover`, `transition`, `@keyframes`) must **not** also be
written inline on the same widget. Pick one owner per property, per widget.
This single rule decides most of the architecture in §7 — the hover system uses
`opacity` and `border-color`, and deliberately leaves `box-shadow` to the
existing inline bass driver.

### 3.4 GTK4 apps are a separate, more capable stack — and stay out of scope

The `nyxus_*.py` apps are GTK4 + libadwaita, which *does* have
`filter`-adjacent effects, `Gtk.GLArea`, and real transforms. They are a
different toolkit from eww and share only the palette. Mixing the two design
languages would make the desktop read as two products. **Recommendation: the
eye-candy language is specified for eww + Hyprland; GTK4 apps adopt only the
palette, radii and motion timings, and get no bespoke effects.**

---
## 4. THE WIRING AUDIT — WHAT IS BUILT BUT NOT CONNECTED

> The owner's read is correct: **a previous agent left real machinery
> half-wired.** This section is the audit. Every row was verified in the tree,
> not taken from the docs — and in three cases the docs were wrong.
>
> Legend: **WIRED** = runs and is consumed · **PARTLY** = runs but almost
> nothing consumes it, or exists but is only reachable by hand ·
> **DORMANT** = built, shipped, and started by nothing.

### 4.1 The reactive chain — `sense` → `mood` → `threatd`

| Link | State | Evidence |
|---|---|---|
| `nyxus-sense` (4 Hz bus → `sense.json`) | **WIRED** | `nyxus-reactive.conf:24` — `exec-once … sleep 3; nyxus-sense start` |
| `nyxus-mood` | **WIRED** | `nyxus-reactive.conf:25` — `sleep 5; nyxus-mood start` |
| `nyxus-threatd` | **WIRED** | `nyxus-reactive.conf:29` — `sleep 12; nyxus-threatd start` |
| `mood` → eww `SENSE` var | **WIRED** | `eww.yuck:57-60` — `nyxus-mood` pushes `eww update SENSE=…` on every mood change |
| **eww actually *using* `SENSE`** | 🔴 **PARTLY — 3 call sites** | `eww.yuck:227`, `:237`, `:310` |

**So the chain runs end to end. The problem is the last inch.** After all that
plumbing — a 4 Hz sampler, EMA smoothing, 6-second hysteresis, a 5-state mood,
a threat feed with an explicit blind/quiet distinction — the mood signal
reaches the interface and paints **three labels**: the two `NYXUS` wordmarks
and the clock date, via a `mood-${SENSE.mood}` CSS class.

Nothing else on the desktop knows what mood the machine is in. Not the bars,
not one of the twelve station decks, not a single pill, not the borders, not
the wallpaper, not the blur. **This is the single largest gap between what
NYXUS has built and what NYXUS shows**, and closing it is the spine of the
design in §6.

#### 4.1a 🔴 `sense-poll.sh` is an orphan — and it is the one carrying the threat signal

`eww/scripts/sense-poll.sh` is a careful 30-line bridge that emits
`{mood, energy, hacker, threat, threat_blind, threat_reason}`. Its comments
show real thought — including a `jq` footgun writeup explaining why
`threat_blind` cannot use `//` because `false // true` is `true`, and an
explicit note that *"quiet and blind must never render the same"*, citing the
Bifrost guardian incident.

**Nothing polls it.** There is no `defpoll` or `deflisten` referencing
`sense-poll.sh` anywhere in any `.yuck`. The `SENSE` defvar's default is
`{"mood","energy","hacker"}` — it has no `threat` field at all, because it is
fed by `nyxus-mood`'s `eww update`, not by this script.

Net effect: **the desktop cannot show threat state**, and the script written to
let it do so is dead code. Cheap to connect (one `defpoll`), and it is the
honest-by-construction data source GHOST already proved the value of.

### 4.2 🔴 The dock — an entire Windows-class taskbar, fully built, launched by nothing

This is the biggest dormant asset in the build and the most relevant one to the
owner's *"like Windows but better"* north star.

`eww/dock.yuck` (180 lines) implements a **macOS-style magnifying dock**:

```
deflisten DOCK_STATE   <- nyxus-dockd -> unix socket -> dock-state.sh
defvar    DOCK_HOVER
defwidget dock-icon [entry index size hover-index mag-max falloff show-ind show-badge]
defwidget dock-divider / dock-stack / dock-trash / dock-row
defwindow dock          94% x 84px, bottom centre
defwindow dock-reveal   100% x 4px, bottom edge, :onhover "eww open dock"
```

Supporting cast, all present: `nyxus_dockd.py`, and eight helper scripts —
`dock-state.sh`, `dock-action.sh`, `dock-menu.sh`, `dock-preview.sh`,
`dock-stack.sh`, `dock-drop.sh`, `dock-enrich-icons.py`, plus `taskbar.sh`.
It even has **layer rules already written**:

```
layerrule = no_anim on,          match:namespace nyxus-dock-reveal
layerrule = ignore_alpha 0.05,   match:namespace nyxus-dock-reveal
```

That `0.05` clip is the tell — somebody deliberately tuned the threshold down
from the standard `0.2` so a *nearly invisible* strip would still register.
This is hover-reveal, already thought through.

**Why it never appears:** `nyxus-eww-launch-safe:21` reads
`BARS_WANTED=(bar-bottom bar-top bar-left bar-right)`. `dock` and `dock-reveal`
are not in the list, and nothing else opens them.

**Two real defects to fix before wiring it, not after:**

1. **There is no `:onhoverlost`.** `dock-reveal` opens the dock and nothing
   ever closes it. Wired as-is, the dock appears on first mouse-to-bottom-edge
   and stays forever. The reveal is half-written.
2. **`dock` and `dock-reveal` are both `:stacking "overlay"`.** `dock-reveal`
   is a 100%-wide overlay strip. It is only 4px tall so it is not the
   full-screen trap of HANDOFF §7, but it is an overlay-layer input surface
   spanning the whole screen width along the bottom edge, which will sit above
   `bar-bottom` and can eat clicks aimed at the bar's bottom 4px.
   **Recommend `:stacking "top"` for `dock` and `"bottom"` for the strip**, and
   verify with `hyprctl layers -j` before and after.

**Where it counts most:** this is the answer to "like Windows." A taskbar that
is not there until you reach for it, then rises out of the wallpaper, is
simultaneously the most familiar and the most NYXUS thing in this document. It
is also the reference implementation for §7 — build the disclosure language
here first, then apply it everywhere.

### 4.3 The reflex layer — `living` / `tintd` / `beatd` / `pulsed` / `wall-fx`

| Daemon | What it does | State | Evidence |
|---|---|---|---|
| `nyxus-living` | supervisor | **WIRED** | `nyxus-signature.conf:106` — `exec-once = sleep 2 && nyxus-living on quiet` |
| `nyxus-pulsed` | event pulses on the border ring | **WIRED** | `nyxus-living:27` — `nohup nyxus-pulsed &` |
| **`nyxus-tintd`** | **per-app border neon — borders follow the focused app** | 🔴 **DORMANT** | see below |
| `nyxus-beatd` | border angle from audio | **DORMANT (manual)** | `nyxus-living:14` — *"manual plumbing … `nyxus-beat` (Super+Alt+B)"* |
| `nyxus-wall-fx` | cava → mpv wallpaper reaction | **DORMANT (manual)** | same line — *"wall-fx (Super+Shift+P)"* |
| `nyxus-soundd` | UI sound design | **WIRED** | `nyxus-signature.conf:121` |

**`nyxus-tintd` is the standout.** `nyxus-living`'s own header block advertises
it as part of the living layer:

```
#   nyxus-tintd    per-app border neon (colors follow the app you're
```

…but `start()` (`nyxus-living:24-30`) launches **only** `nyxus-pulsed`. Every
reference to `nyxus-tintd` in the tree is either a comment, an installer
allowlist, a Settings row, or `nyxus-tint` — the manual front door bound to
`Super+T`. **Nothing starts it at login.** The launcher's own documentation
describes behaviour the launcher does not produce.

This is a two-line fix with a large payoff: window borders that take the hue of
whatever app you are in is exactly the *"rich, cohesive, reactive"* quality the
owner is asking for, and it is already written and tested.

⚠ **Coordination hazard, already documented, do not rediscover:** `tintd`,
`beatd` and `pulsed` all write the same border colours.
`nyxus-beatd:14` says it *"coexists with nyxus-tintd"*, `nyxus-apply-accent:268`
notes all three *"snapshot the border"*, and `nyxus-hacker-mode:79` SIGSTOPs
`nyxus-tintd` and `nyxus-pulsed` together because they *"re-tint the border ring
every focus/pulse"*. Turning `tintd` on at login means **three** writers on one
property. Decide the precedence explicitly (recommendation in §6.2) rather than
letting last-writer-wins decide it at runtime.

### 4.4 `CAVA_BASS` — wired, correct, and under-spent

`cava.sh:21-48` pushes a 0-100 scalar every frame and retunes `borderangle`
across 4 tiers. Consumers today: the two boombox speaker rings, deck-card
inline rims, and the border angle. That is **three** consumers of a signal
available to every widget on screen.

The `push_bass` tier logic is the best-engineered reactive code in the build —
edge-triggered, never calls `hyprctl` per frame, and `_CAVA_LAST_TIER` is
scoped inside the cava pipe subshell so it resets cleanly on restart. **Use it
as the template for every state→compositor binding in this document.** Do not
add a second audio path; there is already exactly one and it is correct.

### 4.5 `random-glow.sh` — wired, and the right shape already

7 s poll, 35% per channel for `brand`/`stamp`/`clock`/`ticker`/`search`, and
**6% for `alien`** — the rare saucer-alien strike, with a comment explaining
the tuning: *"the whole point is that it catches the owner off guard, so it
must not become wallpaper."* Consumed via `GLITCH.*` in `eww.yuck`.

This is a working, tuned rare-event channel. §6.3 reuses it rather than
inventing a second randomiser.

### 4.6 Pre-rendered 3D (Meshy → Blender) — pipeline exists, two jobs never started

`HANDOFF.md:1578-1580` lists as explicitly out of scope at the time:
*"3D saucer/boombox asset rendering (needs Blender on builder box)"* and
*"Left/right 3D dock rail integration (models in Downloads, not started)."*

This is the **only** route to the owner's "3D look" (§5.1/§5.2) and it is a
content pipeline, not a code one. Note the owner has since said **do not use
Meshy** — design in-house (`BARS_AND_LOGIN_BRIEF_2026-07-26.md` §6) — and that
agents have no image generator, only ImageMagick. So this is a
**commissioning** decision, and it should be sequenced *after* the geometry
questions in §4.7 are answered, because rail art has the same aspect-ratio trap
that already killed the last attempt (937×1678 art for a 56×756 rail).

### 4.7 Boombox v2 — art done, not wired, blocked on a geometry decision

`eww/assets/nyxus-boombox-band-v2.png` (+ `-mono`) exists and is on-palette.
**It is not wired because the geometry genuinely does not fit**, and HANDOFF
records that this margin drifted wrong twice from eyeballing. The measurements
(`HANDOFF.md:1728-1749`) are reproduced here so nobody re-measures:

| | |
|---|---|
| Art (trimmed) | 1516×891 — aspect **1.70:1** |
| Display window | 528×286, `fill=1.00` (true rectangle) at x 492..1020, y 356..642 |
| Window as fraction of art | width **0.3483**, height **0.3210** |
| Window centre offset | dx **−0.0013**, dy **+0.0600** of art |
| Band slot today | 551×150 for the saucer — aspect **3.67:1** |

At 150 px tall the v2 boombox is only **255 px wide** and its display shrinks to
**89×48**, against the **146×100** the current music face was laid out for.
Matching the saucer's width would need a **324 px** bar — 30% of a 1080p screen.

**This is an owner decision, not an engineering one.** The three recorded
options stand, and my recommendation is **(a)**:

- **(a) Render at 150 px, move title/transport/CAVA *beside* the boombox** into
  the spare band width. Best looking, most work. **Recommended** — it is the
  only option that changes nothing about the bar's height, and bar height is
  load-bearing (the 40/158 reserved zones are baked into nine windows' layout
  arithmetic and two verify-profile gates).
- **(b) Grow the music face to ~200 px only while audio plays.** **Advise
  against.** A bar that changes height mid-session re-triggers the exclusive-zone
  arithmetic that produced the `y=-59` bug three separate times. Do not put that
  on a timer driven by whether music is playing.
- **(c) Commission a wider (3:1+) boombox.** Clean, but it is new art and
  it invalidates the measurements above.

**Multiply the fractions by the chosen render size to place the overlay. Never
eyeball it.**

### 4.8 Dormant eww windows — wire, repurpose, or delete

| Window | Defined in | Opened by | Verdict |
|---|---|---|---|
| **`dock`** / **`dock-reveal`** | `dock.yuck:161,172` | **nothing** | **WIRE** — §4.2. Highest value in this table by a wide margin. |
| **`cheatsheet`** | `eww.yuck:2905` | **nothing** | **REPURPOSE.** Both `Super+/` binds (`hyprland.conf:444-445`) open `hotkey-cheatsheet`, a *different*, correctly-sized 720×640 window. `cheatsheet` is the orphaned full-screen version — and it is the natural home for the **keybind viewer** that §9.1 shows is the actual fix for "can I move work between stations". |
| **`hotkey-recorder`** | `hotkey.yuck:86` | **nothing** | **WIRE or DELETE.** It has a working close button and is already in `overlay-shield.sh`'s regex, so somebody intended it to be reachable. Low value on its own; genuinely useful if the keybind viewer gains "rebind this". |
| **`quicksettings-daemon`** | `quicksettings.yuck:27` | **nothing** | **DELETE.** `quicksettings` (the real one) is wired via `qs-toggle.sh`. This is a leftover second copy and is exactly the kind of near-duplicate that gets edited by mistake — the same failure mode as the third `hypr/conf.d/` tree that gate `13ak` now guards against. |
| ~31 unused bar-pill widgets | `eww.yuck` | n/a — `defwidget`s, not windows | **KEEP, do not delete.** They cost nothing at runtime (an unreferenced `defwidget` is never instantiated), and the rail's companion-station widget is explicitly documented as *"left in eww.yuck for future use."* Deleting widgets from `eww.yuck` by script is how `station_pill` was destroyed once already (`HOME_AND_START_STATIONS_BRIEF` trap #6). **The risk of removal exceeds the cost of keeping them.** |

⚠ **Note on the four "windows nothing opens":** three of them
(`cheatsheet`, `hotkey-recorder`, `quicksettings`) are listed in
`overlay-shield.sh`'s `OVERLAY_RE`, which hides the bars while an overlay is
up. If any is wired later it must also obey the `:stacking` rule from HANDOFF —
`"fg"` surfaces open via `nyxus-overlay-open`, `"overlay"` surfaces keep
`:y "-40"`. Getting that backwards moves the gap to the other edge. That table
is in HANDOFF and is not optional reading.

### 4.9 Summary — the connect-first list

Ranked by (visible impact ÷ effort), all of it reusing existing code:

| # | Connect | Effort | Why it counts |
|---|---|---|---|
| 1 | Saucer stack transition → a **valid** value (§2.2) | ~1 min | Restores a visible animation that is currently a hard cut |
| 2 | `nyxus-tintd` at login (§4.3) | ~2 lines | Borders follow the focused app — instant "alive" |
| 3 | `sense-poll.sh` → a `defpoll` (§4.1a) | ~3 lines | Unlocks threat + energy for every widget |
| 4 | `SENSE` beyond 3 labels (§4.1) | small | The spine of §6 |
| 5 | `dock` + `dock-reveal` (§4.2) | small-medium | The Windows-familiar taskbar, and the §7 reference build |
| 6 | `decoration:glow` + `glowangle` (§2.4) | ~6 lines | Native neon halo, zero dependencies |
| 7 | Layer in/out animations (§3.1) | ~8 lines | Every panel stops popping and starts arriving |
## 5. WHAT IS NOT POSSIBLE — PLAINLY

The owner asked to be told the real limits. These are they.

### 5.1 True 3D compositing — NO

There is no depth buffer, no perspective transform, and no per-window 3D
placement in Hyprland 0.56.1, and no plugin in this build provides one.
Windows are flat textures composited in 2D.

**Closest achievable:** *painted* depth. NYXUS already does this correctly —
`.deck-near` / `.deck-mid` / `.deck-far` drive size, opacity and rim strength
because "GTK3 CSS has no `transform: scale`; distance is painted, not
transformed"
(`HOME_AND_START_STATIONS_BRIEF_2026-07-27.md` §1). Extend that tier system
rather than trying to fake perspective.

### 5.2 A real 3D look on controls (toggles, scrollbars) — NO, but a good fake

GTK3 cannot rotate, scale, skew or light a widget. A "real looking" toggle
cannot be modelled at runtime.

**Closest achievable, and it is genuinely good:** pre-render the control in
Blender (the pipeline already exists) as a **sprite sheet** — off, hover,
mid-travel, on — and swap frames with a `stack` or an image swap, exactly the
way `starlight-anim.sh` already animates the starfield. A 6–8 frame throw at
GTK's ~200 ms stack duration reads as a physical switch. This is the only way
to get the "real looking toggle buttons" he asked for, and it is a **content**
task (art) far more than a code task.

⚠ Two traps from the tree that apply directly: Meshy "transparent" PNGs are
**not** transparent (solid black matte) and needed a four-corner alpha
floodfill; and hard-cut edges through a chassis read as "not clean" and needed
feathering (`BARS_AND_LOGIN_BRIEF_2026-07-26.md` §5).

### 5.3 Arbitrary CSS filters in eww — NO

GTK3 CSS has no `filter`, no `backdrop-filter`, no `mix-blend-mode`. This is
precisely why the `-mono.png` asset variants exist: a greyscale hacker-mode
image had to be **pre-rendered** because it could not be computed.

**Closest achievable:** pre-render the variant, or move the effect to the
compositor (layer blur, screen shader) where it *can* be computed.

### 5.4 Per-widget blur — NO

Blur is applied by the compositor to an entire layer surface. You cannot blur
one card inside a panel and leave its sibling sharp.

**Closest achievable:** put the thing that must be blurred on its **own eww
window** with its own namespace and its own `layerrule`. This costs a surface,
an exclusive-zone consideration and a watcher, so spend it rarely.

### 5.5 A rotate/flip transition in eww — NO

Covered in §2.2. `GtkStack` has six transitions and none of them rotate.

**Closest achievable:** `slideleft`/`slideright` with `:same-size true`, which
reads as a card being pushed aside; or a pre-rendered flip sprite sequence
(§5.2) if a true turn is worth the art budget.

### 5.6 Custom uniforms into a screen shader — NO

Hyprland feeds the final screen shader a fixed set: `tex`, `v_texcoord`,
`time`, `wl_output`, and the `pointer_*` family
(`src/render/Shader.cpp:150-225`). **There is no mechanism to pass an
application value — mood, CPU, `CAVA_BASS` — into a shader.**

**Closest achievable, and it is the right answer anyway:** generate the `.glsl`
with the constants baked in and hot-swap the file. `decoration:screen_shader`
is marked `REFRESH_SCREEN_SHADER` (`ConfigValues.cpp:231`) so
`hyprctl keyword` re-links it live. Swapping on a 5-state mood change is a
handful of re-links per hour — effectively free — whereas a `time`-driven
shader is not (§12.1).

### 5.7 Animated screen shaders at acceptable cost — NO (on this hardware)

See §12.1. This is the most important "no" in the document and it is quantified
there.

### 5.8 Hyprland plugins (hyprexpo, hyprfocus, dynamic-cursors, hyprbars) — NOT RECOMMENDED

Not "impossible" — but this build already went down that road and reversed:
`nyxus-signature.conf:82` carries the hyprexpo bind **commented out** with the
note *"hyprexpo disabled — crash risk"*, and `nyxus-hyprland-mission.conf`
documents the `hyprpm` install path that was abandoned in favour of the
in-house `nyxus-mission-control`.

Plugins are ABI-locked to the exact Hyprland build, must be recompiled on every
bump, and take the compositor down with them when they fault. `nyxus-shader`'s
own header states the build's philosophy: *"Pure compositor: no daemon, no
plugin, nothing to break on update."* **Follow it.** Every effect proposed in
this document is plugin-free.

---

## 6. THE DESIGN LANGUAGE

### 6.0 North star: *"like Windows, but fucking better"*

The owner's overarching goal reframes everything above. He does not want an
art project. He wants a system that is **as comfortable and predictable as a
mainstream OS**, and then unmistakably better and unmistakably NYXUS.

That has a concrete design consequence, and it is the most important sentence
in this document:

> **Familiarity is a feature, and eye candy must never cost it.**
> Every effect specified below is applied to a control that already behaves
> the way a Windows or macOS user expects. Nothing here changes *what*
> anything does. It changes how it arrives, how it responds, and how it
> recedes.

Three practical rules follow, and they resolve most future arguments:

1. **Nothing hides that a new user needs to find.** Progressive disclosure
   applies to *secondary* affordances — scrollbars, transport controls,
   per-card actions, the dock. Never to primary navigation. The station rail
   and the clock stay lit.
2. **Every disclosed thing has a non-hover route.** A keybind, or a click
   target that is visible without hovering. Hover is an accelerator, never the
   only door. (This is also an accessibility requirement — `DESIGN_CONTRACT.md`
   §11: *"every action reachable with Tab + Enter"*.)
3. **Motion is the same everywhere or it is noise.** One in-curve, one
   out-curve, three durations, applied globally. Detailed in §6.4.

### 6.1 The argument for restraint — why "few effects everywhere" beats "many effects scattered"

The owner said *"clean, super clean only — not half ass. 100%."* Those two
sentences are in tension unless you resolve them deliberately, because the
intuitive way to get "rich" is to add effects, and adding effects is exactly
what makes a desktop read as amateur.

The reason is not taste, it is information theory. **A visual effect carries
meaning only if its presence is informative.** If hover-glow means "this is
interactive" on the bars, and elsewhere means "this is a heading", and
elsewhere is decorative, then the glow tells the eye nothing and the user stops
reading it. It becomes texture. Texture that moves is noise. Noise reads as
cheap — and *that* is the actual difference between a rice that looks like a
product and one that looks like a config dump.

**This build has already paid for this lesson twice**, and both receipts are in
the tree:

- The **EWW chrome night** (`ecdcc952` → `0bf2d06c`) added a marquee clock,
  lowrider ellipse math, and Meshy wraps on the docks and ticker — several
  unrelated ideas at once. It was reverted in full, and
  `EWW_CHROME_REVERT_BRIEF_2026-07-26.md` §3 records the verdict: *"looked
  wrong."*
- The **`.float-island` incident** was the inverse and is more instructive: a
  rail wrapper painted *its own* faint rim and stripped the pills' real
  `obsidian-vessel` glass, glow and accent top-rule. **The rich design was
  already there and a competing effect was suppressing it.** Removing the
  extra effect is what fixed the look (`BARS_AND_LOGIN_BRIEF_2026-07-26.md` §5).

So the recommendation is not "be minimal." It is: **pick a very small number of
behaviours, and apply them with total consistency to every surface.** Coherence
is what makes a small number of effects read as *designed*, and it is the only
version of "rich" that survives contact with 4 bars, 12 decks, ~14 flyouts and
a dock.

### 6.2 The three signature behaviours

Everything visual in NYXUS should be one of these three, or none of them.
Anything that is not one of these three needs an argument.

---

#### ★ SIGNATURE 1 — **THE VEIL** (progressive disclosure)

*Surfaces and controls are present but withdrawn until attended to, then
return to the substrate when released.*

This is the owner's clearest single idea and it becomes the desktop's primary
interaction texture. Full spec in §7. It is the behaviour a user will
experience thousands of times a day, so it gets the most design attention and
the tightest timing budget.

**Applies to:** the dock (§4.2), scrollbars, card action rows, transport
controls, bar-pill secondary readouts, deck card chrome. **Never** to the
station rail, the clock, or anything in the top bar's left cluster.

---

#### ★ SIGNATURE 2 — **THE PULSE** (one reactive spine)

*The whole desktop shares one slow, system-derived colour/intensity state, and
one fast audio-derived one. Nothing has a private animation.*

Today the desktop has **five uncoordinated reactive systems**: `SENSE` mood on
three labels, `CAVA_BASS` on speaker rings and card rims, `borderangle` tiers,
`random-glow` glitches, and `pulsed`'s event flashes. They do not know about
each other. That is precisely the "many effects scattered" failure — it is just
currently invisible because four of the five barely surface.

**The proposal is to make them one system with a strict hierarchy:**

| Tier | Source | Rate | Owns | Rationale |
|---|---|---|---|---|
| **Slow — "the room"** | `sense.json` `mood` + `energy` | mood: ~6 s hysteresis; energy: 4 Hz EMA | The **hue and intensity** of every accent rim, glow and hairline, desktop-wide | This is the "how is the machine feeling" layer. It must be slow enough to never distract. `nyxus-sense` already guarantees this — it will not flap. |
| **Fast — "the beat"** | `CAVA_BASS` | per frame | **Amplitude only** — glow radius / opacity, never hue | Audio should modulate what is already there, not introduce new colour. Keeps music reaction from fighting the mood hue. |
| **Event — "the strike"** | `pulsed`, `random-glow`, `threat` transitions | rare, discrete | One-shot flashes, ≤ 400 ms, on a single surface | Rare by construction. `random-glow` is already tuned this way (6% alien). |

**Precedence for the border ring must be declared, because three daemons write
it (§4.3):**

```
threat: alert/breach   >   pulsed event flash   >   tintd per-app hue   >   mood hue
   (rare, must win)        (transient, ~400ms)      (per focus change)     (ambient floor)
```

`beatd` should stay **off** — `CAVA_BASS`'s `borderangle` tier retune already
owns audio→border, and running both puts two writers on the same property for
no visual gain. This is a decision, not an oversight; record it.

**What this buys:** the desktop stops looking like several widgets that each
happen to animate, and starts looking like one organism. It is also almost
entirely a *wiring* job (§4.9), not new machinery.

---

#### ★ SIGNATURE 3 — **THE SUBSTRATE** (everything emerges from one material)

*Every surface is the same smoked glass over the same starfield, at one of
three depths. Nothing has its own material.*

NYXUS already has this and mostly follows it: `obsidian-vessel`,
`flyout-glass`, `.nyx-surface`, the triple-black elevation stack, the
`starfield-veil` motif. The work is not inventing a material — it is
**eliminating the exceptions** and making depth mean one thing. Spec in §8.

**Applies to:** all 4 bars, all 12 decks, all flyouts, the Hub, the dock,
hyprlock, the greeter.

---

### 6.3 What is deliberately excluded

Saying no is the substance of a design language. These are all technically
possible and are **not** recommended:

| Excluded | Why |
|---|---|
| Per-widget bespoke animations | Signature 2 exists so nothing needs one. Any widget that "needs" its own animation is a request to change the language, not an exception to it. |
| A second randomiser | `random-glow.sh` exists, is tuned, and is consumed. Add channels to it; do not add a rival. |
| A second audio path | `CAVA_BASS` exists and `push_bass` is the best reactive code in the build. |
| Animated screen shaders | Not affordable — §12.1. |
| Hyprland plugins | §5.8 — settled, crash risk, ABI-locked. |
| New accent colours | Palette LOCKED. Every effect below uses only the nine ALIEN NEON hues. |
| Bar height changes at runtime | §4.7(b) — three separate bugs came from the reserved-zone arithmetic. |

### 6.4 The one motion system

Every animation, GTK-side and compositor-side, uses this table. There are no
other values. This is the smallest possible change that makes the desktop feel
like one product.

| Token | Value | Use |
|---|---|---|
| `t-reveal` | **180 ms** | anything appearing on hover/focus |
| `t-conceal` | **420 ms** | anything withdrawing (deliberately ~2.3× the reveal) |
| `t-state` | **280 ms** | colour / glow / opacity state changes |
| `ease-in` | `cubic-bezier(0.16, 1, 0.2, 1)` — the existing `$ease-glass` / `nyx-glass` | everything arriving |
| `ease-out` | `cubic-bezier(0.4, 0, 1, 1)` — the existing `nyx-out` | everything leaving |

**These are the values already in the tree**, deliberately: `$ease-glass` is in
`eww.scss.source`, and `nyx-glass` / `nyx-out` are already declared in
`hyprland.conf:296,299`. Nothing new is introduced; they are simply applied
everywhere instead of in three places.

**Why conceal is slower than reveal.** This is the owner's own instinct —
*"then when you're not hovering it slowly goes back into hiding and you can see
it slowly start disappearing into the system itself."* It is also correct UI
practice: a fast reveal feels responsive, and a fast conceal feels like the
interface is snatching things away and punishes an imprecise mouse. The
asymmetry is the effect.

**No spring, no bounce, no overshoot on disclosure.** `DESIGN_CONTRACT.md` §6
already bans *"bouncing, spring overshoot, carnival animations."* Note the
tree currently contradicts itself: `nyx-spring` (0.34, 1.36, …) and `overshoot`
(…, 1.18) *are* declared and used on `windowsIn` and `workspaces`. Those are
window-manager motions and are fine. **The disclosure language must not use
them** — an overshooting scrollbar is exactly the "half ass" the owner is
trying to avoid.

---

## 7. SIGNATURE 1 IN FULL — "THE VEIL"

> The owner: *"an effect so you just see the names of things until you hover
> over them, then it appears and shows where you'd click, or a scrollbar then
> appears... frost it out or blur and then it reveals itself, then when you're
> not hovering it slowly goes back into hiding and you can see it slowly start
> disappearing into the system itself."*

This section makes that implementable.

### 7.1 The four states

Every VEIL-participating element is in exactly one of four states. The
*identity* of the element (its name/label) is visible in all four — only its
**affordances** (buttons, handles, scrollbars, values) change.

| State | Trigger | Label | Affordances | Surface |
|---|---|---|---|---|
| **DORMANT** | default | 100% | `opacity: 0`, no border | fill at rest alpha |
| **WAKING** | pointer enters the group | 100% | 0 → 1 over `t-reveal` | rim lifts to accent |
| **AWAKE** | pointer inside ≥ `t-reveal` | 100% | 100%, accent rim, cursor changes | full accent rim |
| **FADING** | pointer left, within `t-conceal` | 100% | 1 → 0 over `t-conceal` | rim settles back |

**The label never fades.** That is what makes this legible rather than a
guessing game, and it is exactly what the owner described — *"you just see the
names of things until you hover."*

### 7.2 The hover group — the single most important decision here

**Hover is detected on the CARD, and reveals everything inside it.** Not
per-button.

This is not a stylistic choice; per-element hover produces a strobing card as
the pointer crosses six children, each with its own 180/420 ms cycle. One
eventbox wrapping the card, revealing all of its affordances together, is the
difference between "designed" and "twitchy".

```
(eventbox :onhover "..." :onhoverlost "..."      <- ONE per card
  (box :class "nyx-surface deck-card ..."
    (label ...)          ; identity - always visible
    (revealer ... )))    ; affordances - all revealed together
```

### 7.3 Two mechanisms, and when to use which

There are two ways to build this in eww v0.6.0 and they are **not**
interchangeable. Choosing wrong is the main implementation risk.

#### Mechanism A — **CSS-only** (preferred; use for ~90% of cases)

Pure GTK3 CSS `:hover` + `transition`. **No eww events, no state variables, no
shell commands, no `:timeout` exposure.**

```css
/* affordances start withdrawn */
.veil-affordance {
  opacity: 0;
  transition: opacity 420ms cubic-bezier(0.4, 0, 1, 1);   /* t-conceal / ease-out */
}
/* ...and arrive when the CARD is hovered */
.veil-group:hover .veil-affordance {
  opacity: 1;
  transition: opacity 180ms cubic-bezier(0.16, 1, 0.2, 1); /* t-reveal / ease-in */
}
```

Note the transition is declared **twice, asymmetrically** — the base rule owns
the conceal and the `:hover` rule owns the reveal. That is the standard CSS
idiom for different in/out timings and it is what produces the owner's slow
fade-back.

**Why this is strongly preferred:**

- **Zero runtime cost.** No poll, no subprocess, no `eww update` round-trip.
- **It cannot hit the 200 ms handler kill.** eww SIGKILLs `:onhover` commands
  at `:timeout` like any other handler (HANDOFF gate `13ah`) — CSS never
  invokes one.
- **It cannot desync.** An `:onhover`/`:onhoverlost` pair that misses its
  `hoverlost` (pointer leaves via a screen edge, window unmaps, handler killed)
  leaves the element stuck AWAKE forever. CSS `:hover` is owned by GTK and
  cannot get stuck.

⚠ **The blocker for Mechanism A, and it is real:** an inline `:style` beats
every stylesheet rule (§3.3). `deck_card`, `start_panel` and `ghost_card`
already set `box-shadow` inline from `CAVA_BASS`. **Therefore the VEIL must
animate `opacity` and `border-color`, and must not touch `box-shadow` on those
widgets.** Signature 2 keeps `box-shadow` as the bass channel. These two
signatures were designed to not collide; keep it that way.

#### Mechanism B — **`:onhover` + `revealer`** (use only when geometry must change)

```
(eventbox :onhover     "eww update VEIL_<id>=true"
          :onhoverlost "eww update VEIL_<id>=false"
          :timeout "1s"
  (box ...
    (revealer :transition "slideup" :duration "180ms" :reveal VEIL_<id>
      (affordance_row))))
```

Use this **only** when the revealed content must take space it did not
previously occupy — i.e. the card grows. CSS `opacity` reserves layout space;
`revealer` does not.

**Four hard constraints on Mechanism B:**

1. **Set `:timeout` explicitly** (e.g. `"1s"`). The default is 200 ms and an
   `eww update` round-trip on a loaded desktop can exceed it. A killed
   `onhoverlost` is a permanently-open card.
2. **The command must be `eww update` and nothing else.** Never a NYXUS script
   — `nyxus-hub-close` alone measured 231 ms–3.7 s (HANDOFF).
3. **`revealer` has one `:duration`**, so it cannot express the 180/420
   asymmetry. Either accept symmetric timing here, or pipe the duration from
   the same var: `:duration {VEIL_x ? "180ms" : "420ms"}`. **Verify the latter
   on the stick** — it depends on eww re-evaluating `:duration` on the same
   update that flips `:reveal`, and prop listeners are independent (§2.2), so
   ordering is not guaranteed. Fall back to symmetric 280 ms if it flickers.
4. **⚠ Anything that grows re-opens the layout trap.** A card that gets taller
   can push a deck past the 882 px free area, at which point Hyprland centres
   the oversized surface and parks it at negative y — the `y=-59` bug, three
   times over. **Every Mechanism-B card must be verified with
   `hyprctl layers -j`, in the revealed state, before it ships.** This is the
   single largest risk in the VEIL and it is why Mechanism A is the default.

### 7.4 What reveals, and what never does

| Element | VEIL? | State DORMANT | State AWAKE | Mech |
|---|---|---|---|---|
| **Station rail pills** | **NO** | — | — | primary nav — always lit |
| **Clock / date** | **NO** | — | — | always lit |
| Top-bar ticker | **NO** | — | — | it is the content |
| **Scrollbars** | **YES** | `opacity 0` | `opacity 1`, accent thumb | A |
| **Deck card action rows** | **YES** | `opacity 0` | full | A |
| Deck card secondary values | **YES** | `opacity 0.35` | `opacity 1` | A |
| **Bar-pill detail readouts** | **YES** | `opacity 0` | full | A |
| **Transport controls** (saucer/boombox) | **YES** | `opacity 0` | full | A |
| **The dock** (§4.2) | **YES** | not mapped | mapped, magnifying | **window** |
| Quick-settings tile sublabels | **YES** | `opacity 0` | full | A |
| Close buttons on overlays | **NO** | — | — | escape routes stay visible (HANDOFF) |
| Anything in an error state | **NO** | — | — | never hide a problem |

**The scrollbar case is worth calling out** because the owner named it
specifically and because there is a documented trap: *"GTK3 overlay scrollbars
draw on top of content and cannot be disabled from CSS. Inset the rows
(`margin-right`), not the scroller"*
(`HOME_AND_START_STATIONS_BRIEF_2026-07-27.md` trap #10). The VEIL treatment
for scrollbars is therefore **opacity only** — the row inset stays permanent so
nothing reflows when the bar appears. A scrollbar that shifts text when it
fades in is worse than one that is always visible.

### 7.5 The dock is the reference implementation

Build the VEIL on the dock first (§4.2), for three reasons: the scaffolding
already exists, it is a *window*-level reveal so it exercises the compositor
half (`layersIn`/`fadeLayersIn`, §3.1) as well as the CSS half, and it is the
single most Windows-familiar element in the build — which makes it the best
possible proof of the north star.

**Window-level VEIL differs from widget-level in one way:** the conceal is a
real unmap, so it needs a **dwell timer**, not just `onhoverlost`. Leaving the
dock the instant the pointer exits makes it feel skittish and makes it
impossible to reach an icon near the edge.

```
reveal:   pointer enters the 4px strip  ->  eww open dock
                                            layerrule = animation slide  (layersIn)
conceal:  pointer leaves the dock       ->  start 600ms dwell timer
          pointer re-enters             ->  cancel timer
          timer expires                 ->  eww close dock
```

600 ms is a starting value, not a measured one — it should be tuned live and
the final number recorded.

⚠ **The dwell timer must live in a script file, not an inline handler.** Two
reasons, both already paid for: eww kills a handler at `:timeout`, so a
600 ms sleep inside `:onhoverlost` is killed at 200 ms by default; and
`pkill -f <pattern>` from an inline `bash -c` kills its own shell because the
caller's `/proc/self/cmdline` contains the pattern (`HOME_AND_START_STATIONS`
trap #4). A tiny `nyxus-dock-veil` script with a PID/flock guard is the correct
shape.

### 7.6 Honest limits of the VEIL

- **No blur transition.** The owner asked to *"frost it out or blur and then it
  reveal itself."* GTK3 cannot animate blur, and Hyprland's layer blur is
  per-surface and binary. **A widget cannot fade from blurred to sharp.** The
  achievable substitute is opacity + rim, which reads as the same thing when
  the element sits on already-blurred glass — the affordance appears to
  *surface out of* the frost. This is a genuine downgrade from what he
  described, and it is worth him knowing that the "frost dissolving" version
  would require the element to be its own layer surface (§5.4), which is far
  too expensive to spend per-card.
- **No hover on layer surfaces without pointer focus.** A layer surface with
  no keyboard focus still receives pointer events, so hover works — but a
  surface under another surface does not. Stacking order matters; check
  `hyprctl layers -j`.
- **Touch/keyboard parity is mandatory, not optional.** Rule 2 of §6.0.

---

## 8. SIGNATURE 3 IN FULL — "BLEND INTO THE SYSTEM"

> *"blend in, almost as if it's not even there until you're really looking at
> it."*

### 8.1 The rule: three depths, and nothing else

Every surface in NYXUS sits at exactly one of three depths. The depth
determines fill alpha, rim alpha, and whether it blurs. These are the values
already in `THEME.md` §2 — the proposal is to **use only these three and audit
out the exceptions.**

| Depth | Token | Fill | Rim | Blur | Used by |
|---|---|---|---|---|---|
| **SUBSTRATE** | `nyx_black_smoke` | `rgba(14,14,22,0.55)` | `rgba(255,255,255,0.10)` | yes | bars, rails, dock, deck backgrounds |
| **RAISED** | `nyx_black_ink` | `rgba(8,8,14,0.78)` | `rgba(125,61,255,0.18)` | inherited | cards, pills, buttons, inputs |
| **MODAL** | `nyx_black_void` | `rgba(0,0,0,0.92)` | `rgba(125,61,255,0.32)` | yes | popovers, tooltips, the Hub, powermenu |

**Do not add a fourth.** The `.deck-near`/`-mid`/`-far` tiers are a *within-a-
surface* refinement of RAISED and stay as they are — they modulate size and rim
strength, not the material.

### 8.2 Concrete blur / alpha values, and how they interact with what ships

The layer-blur configuration currently in the tree is **correct and must not be
casually changed.** Recording why, because it has been re-litigated twice:

```
layerrule = blur on,          match:namespace ^(nyxus.*)$   # catch-all: FLOOR, stays at TOP of file
layerrule = ignore_alpha 0.2, match:namespace ^(nyxus.*)$
decoration:blur { size 14 · passes 4 · brightness 0.92 · contrast 1.05
                  vibrancy 0.18 · vibrancy_darkness 0.30 · noise 0.06 }
```

| Value | Keep / change | Reason |
|---|---|---|
| `ignore_alpha 0.2` | **KEEP — do not touch** | A/B'd live with screenshots at 0.0 / 0.2 / 0.45 / 0.6. At 0.0 the blur bleeds into the near-zero-alpha halo around each pill and paints the frosted "shadow box"; at 0.6+ the pills lose their own frost. Any value strictly between 0 and 0.55 works and 0.2/0.45/0.6 are visually indistinguishable. Gate `13aj` pins all four bars into that window. **If the boxes reappear, the rule is not reaching the compositor — check that, not the number.** |
| catch-all at **top** of file | **KEEP** | Last-match-wins. Gate `13ae`. |
| `size 14 / passes 4` | **KEEP** | Note this is a *wide* blur — it travels far past content edges, which is exactly why `ignore_alpha` matters. Raising it raises the halo problem. |
| `vibrancy_darkness 0.30` | **candidate to raise → 0.40** | On a near-black desktop (reference art mean luma 0.086) this is the control that decides whether the neon behind glass survives. Cheap, reversible, `hyprctl keyword`-testable. |
| `noise 0.06` | **KEEP** | This is the "etched glass" grain and it is a large part of why NYXUS glass looks like a material rather than a rectangle of transparency. |

**The "not even there" treatment, concretely.** For a surface to disappear into
the wallpaper and still be findable, three things must be true at once:

1. **Fill at or just above the clip.** SUBSTRATE at `0.55` is well above
   `ignore_alpha 0.2`, so it blurs. Do **not** chase invisibility by dropping
   fill below `0.2` — the surface stops blurring entirely and you get a sharp
   ghost instead of frost. **`0.2` is a floor, not a target.**
2. **Rim carries the edge, not the fill.** At rest the rim is
   `rgba(255,255,255,0.10)` — a hairline that reads as a seam in the glass, not
   a border. On hover it becomes the accent at `0.32`. **The rim doing the work
   is what lets the fill go quiet.**
3. **No shadow at rest.** The ink drop-shadow (`0 6px 18px rgba(0,0,0,0.62)`)
   was removed from `obsidian-vessel` for exactly this reason — on a 38 px pill
   a shadow with no falloff room reads as a rectangular block. Do not
   reintroduce it. Glow, not shadow.

### 8.3 The state-reactive grade — the one genuinely rare idea

This is where NYXUS can legitimately be first, and §2.1 changed what it costs.

**The idea:** the *entire screen* is graded by a full-screen GLSL post-process
whose look is derived from `sense.json`. Not a filter the user picks — a grade
the machine chooses, continuously, from what it is actually doing.

**Why it is rare.** The Hyprland ecosystem's standard tool, `hyprshade`, is a
**scheduler** — it switches shaders by time of day. `hyprglaze` is closer but
it is a *wallpaper daemon* rendering to the background layer, so it grades the
wallpaper, not the composited desktop. **A full-screen post-process driven by
live system state is not something the ecosystem ships.** NYXUS is unusually
well placed for it because it already has both halves: a shader switcher and a
smoothed, hysteresis-guarded state bus. It just has no shaders (§2.1).

**How it must be built — file swap, not uniforms.** There is no way to pass a
value into the shader (§5.6). So:

```
nyxus-sense  ->  sense.json  ->  nyxus-mood  ->  (on mood CHANGE only)
     render ~/.config/hypr/shaders/nyxus-<mood>.glsl   (5 pre-written files)
     hyprctl keyword decoration:screen_shader <path>
```

Five static shaders, one per mood, swapped on transition. **Edge-triggered,
exactly like the `CAVA_BASS` `borderangle` tier retune** — that is the proven
pattern in this build and it must be copied rather than reinvented.

**The grades, all inside ALIEN NEON:**

| Mood | Grade | Intent |
|---|---|---|
| `GHOST` | −8% luma, −15% saturation, slight violet lift in shadows | idle at night; the desktop settles |
| `DRIFT` | +6% saturation, gentle magenta→violet split-tone | music playing; warmer |
| `PROWL` | neutral — **an empty pass-through** | the default; must be indistinguishable from no shader |
| `OVERCLOCK` | +10% contrast, +8% saturation, faint cyan rim-lift | machine working hard |
| `MATRIX` | desaturate to luma, hold `#ff2d55` only | hacker mode; matches the existing black/white/red treatment exactly |

`MATRIX` is the strongest argument for the whole idea: **hacker mode currently
achieves black/white/red by pre-rendering `-mono.png` art variants and hand-
editing CSS.** A shader does it to the *entire composited screen* — every app,
every window, art nobody pre-rendered — in one pass, for free. That is a
capability the current approach cannot reach at any price.

**Hard requirements, all source-verified:**

- **`PROWL` must be a genuine no-op** and, better, should `hyprctl keyword
  decoration:screen_shader "[[EMPTY]]"` rather than load a pass-through — one
  less full-screen pass in the common case. `nyxus-shader` already does exactly
  this for `off` (`nyxus-shader:37`).
- **No `time` uniform. No `pointer_*` uniforms.** The moment a shader declares
  one, Hyprland demands `debug:damage_tracking = 0` (§12.1) and the cost stops
  being acceptable. These are **static grades**.
- **`#version 320 es` is supported** in 0.56.1 — `applyScreenShader` selects
  `TEXVERTSRC320` when the source starts with that directive
  (`src/render/OpenGL.cpp:938`), otherwise the default vertex source. Historic
  advice to use `#version 300 es` came from the 0.48-era parser error and no
  longer constrains this build. Pick one and use it in all five files.
- **Swapping may need a damage nudge.** A known upstream behaviour is that
  changing `screen_shader` does not repaint a static screen until something
  else damages it. `decoration:screen_shader` is flagged
  `REFRESH_SCREEN_SHADER` in 0.56.1, which *should* handle it — but this is
  **unverified on 0.56.1** and must be checked on the stick. If it is a problem
  the workaround is a forced damage right after the swap.

**Effort: Medium.** Five short fragment shaders written from scratch (~40 lines
each), a small renderer/switcher in `nyxus-mood`, and staging so
`~/.config/hypr/shaders/` actually ships — the staging gap in §2.1 is a bake
issue and will bite exactly the way the wallpaper-staging glob did unless a
gate covers it.

---

## 9. THE FOUR INTERACTION FEATURES

These are the owner's four new asks. **One of them he already has**, two are
straightforward, and one needs care because of a documented trap.

### 9.1 Carrying work between stations — ✅ **HE ALREADY HAS THIS**

> *"Can I move what I'm working on from station 1 to station 5?"*

**Yes, and it has been bound the whole time.** This is a discoverability
failure, not a missing feature. Verified in `hyprland.conf`:

| Bind | Dispatcher | What it does |
|---|---|---|
| `Super+Shift+1…9,0` | `movetoworkspace, 1…10` | Send the focused window to station N **and follow it** (`hyprland.conf:503-512`) |
| `Super+Alt+Shift+1…0` | `movetoworkspace, name:RELAY…RANGE` | Same, for the ten named companion stations (`:536-545`) |
| `Super+Shift+S` | `movetoworkspace, special:magic` | **The "take this with me" pin he described** — the scratchpad (`:552`) |

There are **163 active binds** in the shipped config. He is discovering them by
asking, which means the real problem is that the keybind surface is not
reachable when he needs it.

**What is genuinely missing — two things, both small:**

1. **`movetoworkspacesilent` is not bound anywhere.** The difference matters in
   daily use and is exactly the "carry work" nuance:
   - `movetoworkspace` = **take it there** (window moves, you follow)
   - `movetoworkspacesilent` = **send it away** (window moves, you stay)

   The second is the one you want when you are triaging — push a finished
   window to CORE and keep working. **Recommend binding it to
   `Super+Ctrl+1…0`.** Cheap, no conflict, immediately useful.
2. **No way to move a whole group.** `Super+U` toggles a group
   (`nyxus-hyprland-flair.conf`), and `movetoworkspace` on a grouped window
   moves the whole group already — so this works, and is also just
   undiscovered.

**The actual fix is the keybind viewer, and it should be the dormant
`cheatsheet` window (§4.8).** Requirements:

- Reachable from the **right-click desktop menu** (§9.3) and from the Hub, not
  only from `Super+/` — because if he cannot remember `Super+Shift+5`, he
  cannot remember `Super+/` either.
- **Generated from the config, never hand-maintained.** The current cheatsheet
  has already drifted once — it claimed HOME was `Super+0`, which is workspace
  10 (`HOME_AND_START_STATIONS_BRIEF` §1). Parse `bind*=` lines out of the
  shipped `conf.d/` at build time, or read `hyprctl binds -j` live. A
  hand-written list of 163 binds will be wrong within a week.
- **Searchable**, grouped by task ("move a window", "switch station",
  "windows", "media"), not by modifier.

⚠ `hyprctl binds -j` is the robust source because it survives the hyprlang→Lua
migration (§12.5); a parser for `.conf` syntax does not.

### 9.2 Mouse move/resize without a modifier — **possible, but do not do it the obvious way**

> *"press down on whatever I'm on and move or resize it"*

**What exists today** (`hyprland.conf:555-556`):

```
bindm = $mod, mouse:272, movewindow     # Super + left-drag
bindm = $mod, mouse:273, resizewindow   # Super + right-drag
```

**Why removing the modifier is a bad idea, plainly.** `bindm` with no modifier
binds the *bare* mouse button globally. Every plain left-click-drag anywhere on
screen becomes "move the window":

- You cannot select text in a terminal or browser.
- You cannot drag a file, a tab, a slider, or a selection box.
- You cannot drag-resize a column in any app.
- Clicking a NYXUS bar pill and twitching 2 px moves the window instead.

That is not a tuning problem, it is what the binding means. **It would make the
desktop less like Windows, not more** — which fails the north star directly.

**Four viable options, in the order I would try them:**

#### Option A — Touchpad gestures ★ RECOMMENDED

Hyprland 0.56.1 has **native trackpad move and resize gestures**, verified in
source — `CMoveTrackpadGesture` and `CResizeTrackpadGesture`
(`src/config/legacy/ConfigManager.cpp:1985-1991`). Syntax:

```
gesture = <fingers>, <direction>, [mod:MOD], [scale:F], <action> [args]
```

Actions available: `dispatcher`, `workspace`, `resize`, `move`, `special`,
`close`, `float`, `fullscreen`, `cursorZoom`, `scrollMove`, `unset`.
Directions: `swipe`, `left/right/up/down`, `horizontal`, `vertical`, `pinch`,
`pinchin`, `pinchout` (`src/managers/input/trackpad/TrackpadGestures.cpp:13-38`).

Proposed:

```
gesture = 4, swipe, move       # 4-finger drag  -> move the focused window
gesture = 4, pinch, resize     # 4-finger pinch -> resize it
```

**This is exactly what he asked for — grab it and move it, no modifier, no
keyboard — with zero cost to text selection**, because a 4-finger gesture
cannot be confused with a click-drag. It is also the most "better than Windows"
answer available: Windows has no equivalent.

⚠ **Correction to an assumption in the brief:** the config contains exactly
**one** gesture — `gesture = 3, horizontal, workspace` (`hyprland.conf:219`).
There is **no 4-finger gesture bound to mission control**; mission control is
`Super+F3` and `Super+Alt+A` (`nyxus-hyprland-mission.conf:64`,
`nyxus-signature.conf:83`). So 4-finger is **free**, and this proposal
conflicts with nothing.

#### Option B — A more comfortable modifier

`bindm = ALT, mouse:272, movewindow`. Alt-drag is the long-standing X11/Linux
convention and many apps expect it. Cheap, familiar, safe.
**Downside:** conflicts with Alt-drag inside some apps (GIMP, Blender).

#### Option C — Edge/corner drag zones

Hyprland already ships `general:resize_on_border = true` — **this build already
has it enabled** (`nyxus-hyprland-general.conf`). Dragging a window border
resizes it with no modifier at all, exactly like Windows. There is no
equivalent for *moving*, because there is no titlebar (`hyprbars` would add one
and is excluded, §5.8).

**Worth telling him: border-resize already works today.** Another
discoverability item.

#### Option D — A toggleable "arrange mode"

A keybind flips a submap where bare mouse buttons move/resize, with a clear
on-screen indicator, and Escape exits. Hyprland `submap` supports this cleanly.

**Pro:** gives him literally what he asked for, safely, because it is scoped.
**Con:** it is a mode, and modes need an unmistakable indicator or they trap
people — this build has already been trapped twice by surfaces it could not
escape. If built: the indicator must be a compositor-level change (e.g. a
border colour flip via `hyprctl`) so it is visible even if eww is wedged, and
Escape must be bound *outside* the submap's own logic.

**Recommendation: A + B together, and tell him C already works.** D only if he
still wants it after trying the gestures.

### 9.3 Right-click desktop context menu — **possible; the safe design is not the obvious one**

> *"right-click anywhere on the desktop and a small sleek menu pops up at the
> cursor — not a whole window."*

#### The real constraint

**There is no desktop in Hyprland.** The wallpaper is a layer-shell surface
(`swww`/`mpvpaper`) on the background layer, and it does not accept input.
There is nothing to right-click *on*. So the menu needs (a) something to
receive the click, and (b) something to draw the menu at the cursor.

#### ⚠ The safety constraint, which decides the design

HANDOFF §7 is unambiguous, and it was bought with hard resets:

> *"Full-screen GTK/eww overlays MUST be bottom-layer + empty input region
> re-applied per-frame, or they TRAP the desktop (the 'whispers' incident
> forced multiple hard resets). Never OVERLAY-layer a full-screen input
> surface."*

And it happened again during a later session: a leftover full-screen overlay
probe *"swallowed every pointer event on the desktop"* until it was killed
(gate `13ai`).

**A full-screen click-catcher is therefore the one implementation that must not
be built.** It is also unnecessary.

#### ★ Recommended: no catcher surface at all — bind the button

Hyprland can bind a mouse button globally, the same way `bindm` already does:

```
bind = , mouse:273, exec, nyxus-desktop-menu
```

…with the critical refinement that it must **not** fire inside applications. Two
ways to achieve that, and the second is better:

1. `bind` with a `windowrule`-style guard — fragile.
2. **`nyxus-desktop-menu` decides for itself.** It runs
   `hyprctl activewindow -j` and **exits immediately** unless the result is
   empty (no focused window = the pointer is over bare desktop). One `hyprctl`
   call, ~5 ms, no surface, nothing to trap. If a window is focused, the
   right-click is simply not consumed and the app sees it normally.

This is the correct shape: **the menu costs nothing when it is not wanted, and
there is no persistent input surface anywhere in the design.**

#### Renderer: rofi, not eww ★

He already has rofi themed to ALIEN NEON — five `.rasi` themes ship
(`rofi-nyxus`, `rofi-launcher`, `rofi-power`, `rofi-config`, `rofi-startmenu`)
plus `rofi-scripts/`.

| | rofi at cursor | bespoke eww popup |
|---|---|---|
| Cursor anchoring | **native** — `-theme-str 'window {location: north west; x-offset: Npx; y-offset: Npx;}'` fed from `hyprctl cursorpos` | eww `:geometry` is monitor-anchored; you must compute offsets and it is still a layer surface |
| Traps the desktop? | **No** — normal window, its own keyboard grab, dies on Escape/focus loss | **Yes, potentially** — this is exactly the `start-search` exception HANDOFF already flags as breaking two rules at once |
| Keyboard nav | free | must be built; **eww has no `:onkeydown`** (HANDOFF), so Escape must be a compositor bind |
| Theming | already ALIEN NEON | would need new CSS |
| Effort | **hours** | days |

**Recommend rofi.** The one thing to verify is the blur — rofi is an
`xdg-toplevel`, not a layer surface, so it is covered by
`decoration:blur`/window rules, not by the `nyxus-*` layerrules. A
`windowrule = opacity …, match:class ^(Rofi)$` may be needed to match the
glass. Small, and it keeps the menu out of the layer-shell trap space entirely.

#### Proposed contents

Keep it to one screen, no submenus (he said *small and sleek*):

```
  New terminal here
  Open file manager
  ─────────────
  Change wallpaper          -> nyxus-wall-next
  Display settings          -> nyxus-settings (Displays)
  ─────────────
  Keybinds  (Super+/)       -> the §9.1 viewer
  Stations                  -> station switcher
  ─────────────
  NYXUS Settings
  Lock / Power              -> nyxus-powermenu
```

**Every entry must show its keybind** where one exists. A context menu that
teaches its own shortcuts is the direct fix for §9.1's discoverability problem
— which is the coherence point in §10.

### 9.4 Single-station / "normal desktop" mode — **possible; the highest-risk item here**

> *"an option to run as one ordinary desktop with no stations, switchable back"*

#### Precedent exists and is good

`nyxus-hacker-mode` already performs a full mode flip and the mechanism is
sound (`nyxus-hacker-mode:34-44, 165-208`):

```
stations.json          <- the ACTIVE matrix
stations-hacker.json   <- the alternate matrix
stations-normal.bak.json           <- backup of the active one, taken on flip
nyxus-stations.conf                <- GENERATED from the active matrix
nyxus-stations.conf.normal.bak     <- backup of the generated shard
gen_stations_conf()    <- regenerates the shard from scratch, every flip
```

So a third matrix — `stations-solo.json` — is the natural implementation, and
it is mostly **data**, not code.

#### ⚠ But this is the most fragile subsystem in the build

The receipts, all in HANDOFF:

- **`nyxus-stations.conf` is regenerated from scratch on every flip**, and
  hand-appended content in it was destroyed until the named stations were moved
  to the separate `nyxus-stations-named.conf`. Note `gen_stations_conf()`'s own
  banner: *"Do not hand-edit — edit the matrix JSON."*
- **Gate `13w`** exists specifically because station identity must stay
  identical across `stations.json` and `stations-hacker.json`.
- **Gate `13ab`** exists because the generated shard **drifts** from
  `stations.json`, and *"the first hacker-mode flip silently rewrites what the
  stations do."*
- Pills dispatch **by number**; the deck watcher maps **by name**. They line up
  only because the shard carries `defaultName:OPS`. Drop or fail to source that
  shard and *"every numbered station reports `.name` as `"1"`, no map entry
  matches, and `_sync` closes every deck and opens none"* — i.e. clicking a
  station does nothing.
- A numeric `name:0` resolves into Hyprland's **hidden SPECIAL range**; gate
  `13ag` scans 1059 files for it.

#### The design that cannot damage station identity

Five rules. Together they mean SOLO mode is a *view*, not a rewrite.

1. **SOLO must not write `stations.json`.** Hacker mode swaps the active matrix
   file; SOLO must not. Instead add a top-level `"mode"` key read by consumers,
   or keep `stations-solo.json` strictly as a *presentation* overlay. **The
   station identity table stays exactly one thing, always.** This alone removes
   most of the risk, because every gate above is about identity drift.
2. **SOLO changes what is *shown*, not what *exists*.** Concretely: the rail
   renders one pill instead of twelve; `nyxus-home-deck` opens no deck. The ten
   workspaces still exist and every `movetoworkspace` bind still works — so
   nothing can strand a window on a station he can no longer reach. **This is
   also the recovery path if SOLO misbehaves.**
3. **Never regenerate `nyxus-stations.conf` for SOLO.** The workspace rules are
   harmless when unused. Regenerating it is what destroys things.
4. **Named stations stay in `nyxus-stations-named.conf`, untouched.** That file
   exists precisely because generated content ate hand-written content once.
5. **Extend gate `13w` to a third file** *before* shipping a third matrix, if
   one is used at all. A new matrix that no gate compares is exactly how the
   drift in `13ab` happened.

#### What SOLO should actually look like

Not an empty desktop — a **familiar** one, per the north star:

| Element | Stations mode | SOLO mode |
|---|---|---|
| Left rail | 12 station pills | **hidden** (or one HOME pill) |
| Decks | per-station | **none** |
| Dock (§4.2) | optional | **on by default** — this is the Windows-familiar surface |
| Top bar | unchanged | unchanged |
| Bottom bar | unchanged | unchanged |
| Alt-Tab / taskbar | window list | **window list becomes primary** (`taskbar.sh` already exists, §4.2) |
| `Super+1…0` | switch station | still work — undiscoverable but not broken |

**SOLO mode is where the dock stops being optional.** With no station rail,
the dock is how you move between windows — and it makes SOLO genuinely the
"normal Windows-like desktop" he described rather than a stripped one. The two
features are the same project, which is the strongest argument for doing §4.2
first.

**Effort: Medium**, and mostly in `nyxus-home-deck` and `workspaces.sh`, not in
the matrix. **Risk: Medium-High** if it touches `stations.json`; **Low** if it
follows rule 1.

---

## 10. HOW IT FLOWS TOGETHER

> *"blend it all together so it just flows like a river going downstream."*

The four features in §9 are not bolt-ons. Each one is either a consumer of
machinery that already exists, or the delivery vehicle for one of the three
signatures. That is what makes this a system rather than a feature list.

**One input spine.** `nyxus-sense` is the only source of ambient state. Mood
sets hue (Signature 2 slow tier); `CAVA_BASS` sets amplitude (fast tier);
`threat` and `pulsed` own rare strikes. The **screen grade** (§8.3), the
**border ring** (§4.3), the **card rims**, and the **glow** (§2.4) are four
renderings of the *same* number. Nothing has a private animation, so nothing
can disagree.

**One disclosure grammar.** The dock (§4.2), scrollbars, card actions and the
transport row all use the same four states and the same 180/420 ms pair (§7).
Once he learns it on the dock, he already knows it everywhere. The right-click
menu (§9.3) is the same grammar at pointer scale — appear at the cursor, do the
job, withdraw.

**One material.** Three depths, one glass, one starfield (§8.1). Rofi is the
one deliberate exception and it is made to match by a window rule, rather than
being allowed to look like a different product.

**The features reinforce each other rather than stacking:**

- The **right-click menu** (§9.3) is the fix for the **discoverability
  failure** in §9.1 — it is where the keybind viewer lives, and every entry
  teaches its shortcut. Two of his four asks are one solution.
- The **keybind viewer** reuses the dormant **`cheatsheet` window** (§4.8) —
  no new surface.
- **SOLO mode** (§9.4) is only convincing because the **dock** (§4.2) exists —
  and the dock is the **reference implementation of the VEIL** (§7.5). Three
  asks, one build.
- The **dock's reveal** exercises `layersIn`/`fadeLayersIn` (§3.1), which then
  applies to every flyout in the build for free.
- **`tintd`** (§4.3) makes borders follow the app; the **mood grade** (§8.3)
  makes the screen follow the machine. Same idea at two scales, and they use
  the precedence table in §6.2 so they never fight.

**The single sentence that ties it to the north star:** every one of these is a
thing Windows also does — a taskbar, a right-click menu, a keyboard shortcut
list, drag to move, one desktop — done with a coherent material, a coherent
motion, and a reactive layer that no mainstream OS has. **Familiar shape,
better execution.** That is the whole design.

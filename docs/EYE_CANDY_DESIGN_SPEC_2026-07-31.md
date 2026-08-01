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
  change — and §9 ranks it first.
- **Honest limit:** GTK3's `GtkStack` has **no rotation/flip transition at
  all**, at any value. `slideleft`/`slideright` with `:same-size true` is the
  closest thing to a card turn that this toolkit can produce. See §5 for what a
  real flip would cost.
- **To confirm on the stick without changing anything:**
  `grep -i "couldn't parse transition" ~/.local/share/eww/eww.log` (or
  `journalctl --user -t eww`). The line should be present on every daemon start.

### 2.3 🟡 `:onhover` / `:onhoverlost` exist and are used **zero** times

```
$ grep -c 'onhover' eww.yuck
0
```

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
| Dim the desktop around a panel | **YES — unused** | `layerrule = dim_around on` + `decoration:dim_around` (default 0.4) | S / **Medium** — see §10.4 | Hub, powermenu, decks |
| Panel sees wallpaper only, not windows | **YES — unused** | `layerrule = xray on` | S / Low | bars, decks |
| Panel above the lock screen | **YES — unused** | `layerrule = above_lock on` | S / **High** — security | *not recommended* |
| Panel excluded from screen share | **YES — unused** | `layerrule = no_screen_share on` | S / Low | GHOST/ARSENAL decks |
| Layer stacking order within a layer | **YES — unused** | `layerrule = order <int>` | S / Low | bars vs decks |
| Custom easing curves | **Already shipped** | 8 `bezier =` curves in `hyprland.conf:294-303` | — / — | all animations |
| Full-screen GLSL post-process | **YES — mechanism only** | `decoration:screen_shader`, hot-swappable (`REFRESH_SCREEN_SHADER`) | **M** (shaders must be written from scratch — §2.1) / Medium | whole screen |
| Shader reacts to **time** | **YES, but see cost** | `uniform float time` (`Shader.cpp:204`) | S / **HIGH — see §10.1** | whole screen |
| Shader reacts to **cursor** | **YES, but see cost** | `pointer_position`, `pointer_last_active`, `pointer_pressed_{positions,times}`, `pointer_hidden`, `pointer_shape` … (`Shader.cpp:213-225`) | S / **HIGH — see §10.1** | whole screen |
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

## 4. WHAT ALREADY EXISTS AND IS UNDER-USED — THE CHEAP WINS

The brief's instinct is right: a large share of the "one of a kind" goal is
reachable by connecting things already in the tree.

| Asset | What it is | State today | What it could drive |
|---|---|---|---|
| **`nyxus-sense`** | 4 Hz JSON state bus → `~/.config/nyxus/sense.json`: `mood` (GHOST/DRIFT/PROWL/OVERCLOCK/MATRIX), `energy` 0-1 (EMA-smoothed, 6 s hysteresis), `cpu`, `phase` (dawn/day/dusk/night), `audio.playing`, `window.app`, `threat.level` | **Running** (fixed in PR #80 — it was never launched before). Consumers: mood engine, whispers, DROP, graffiti wall | The master input for **every** state-reactive effect in this document. Its hysteresis is the reason effects driven from it will not flicker. |
| **`CAVA_BASS`** | 0-100 audio scalar, pushed to eww every frame by `cava.sh:21-28` | **Live**, drives boombox cones + deck card rims inline | Already the right shape. Do **not** add a second audio path. |
| **CAVA→`borderangle` tiers** | `cava.sh:35-48` retunes `borderangle` duration 240/180/110/60 s on tier change only (never per frame) | **Live** | The template for every future state→compositor binding: **tiered, edge-triggered, never per-frame**. Copy this pattern exactly. |
| **`nyxus-shader`** | `decoration:screen_shader` switcher | **Launcher only — no shaders exist (§2.1)** | The delivery vehicle for the state-reactive grade in §8.3. |
| **`random-glow.sh`** | 7 s poll → JSON of booleans, 35% each for brand/stamp/clock/ticker/search, **6% for `alien`** (deliberately rare easter egg) | **Live** | An existing, tuned "rare event" channel. Reuse it rather than inventing a second randomiser. |
| **Layer blur + `ignore_alpha 0.2`** | Per-namespace, catch-all pinned to top of file | **Live**, gate `13ae`/`13aj` | The substrate for §8. The 0.2 clip is correct and must not be changed (proven by A/B, `HANDOFF.md`). |
| **`.nyx-surface`** | Shared CSS class: background, gradient, rim, radius for every station surface; deliberately omits `box-shadow` | **Live**, GHOST proved a whole station costs ~45 lines on top of it | The single insertion point for a desktop-wide hover language. Add the disclosure rules **here** and all 12 decks inherit them at once. |
| **`starlight-anim.sh`** + 16-frame twinkle PNGs | Pre-rendered frame swap under a translucent veil | **Live** | The proven pattern for "animate something GTK3 cannot animate": pre-render frames, swap the image. |
| **Meshy→Blender pre-rendered 3D art** | Offline 3D render pipeline | Available | The **only** viable route to a "3D look" (§5.2). |

**The most under-used asset is `nyxus-sense`.** It publishes a smoothed,
hysteresis-guarded mood at 4 Hz and almost nothing consumes it visually. Every
signature idea in §6 is a consumer of that one file.

---

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
shader is not (§10.1).

### 5.7 Animated screen shaders at acceptable cost — NO (on this hardware)

See §10.1. This is the most important "no" in the document and it is quantified
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

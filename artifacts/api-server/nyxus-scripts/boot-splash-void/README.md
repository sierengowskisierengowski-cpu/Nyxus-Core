# NYXUS VOID · Boot Splash · "THE INFALL" · rev 4 enterprise

> The universe arranges itself into the brand.
> NYX-J5W-2026-SIERENGOWSKI-LOCKED

A premium Plymouth theme. Not a "splash screen" — a **3-second story** the user watches every time they power the machine on. Designed to be remembered.

---

## The story (3 seconds, then steady-state)

| Phase | Time | What you see |
|---|---|---|
| **0** | 0.0–0.4s | The cosmic void fades in — black hole / ink swirl background reveals from pure black. |
| **1** | 0.4–0.8s | A **single dark diamond** materialises at the eye of the swirl. Stillness. |
| **2** | 0.8–1.8s | **THE INFALL.** Twelve micro-stars seed across the screen — and one by one, each is pulled inward toward the diamond. They *brighten as they accelerate* (ease-in-cubic), then vanish as they're absorbed. The void is *eating light*. |
| **3** | 1.8–2.2s | When the last star is consumed → **shockwave**. The diamond halo blooms outward as a single bright white pulse. A starlight beam sweeps L→R across the wordmark area, **igniting the wordmark** in tandem. The wordmark is a dark silhouette with a white rim glow — it appears *as if condensed from the released energy*. |
| **4** | 2.2–3.0s | The aperture settles. Etched rules fade in above and below the wordmark. **Four corner brackets** appear (top-left, top-right, bottom-left, bottom-right) framing the screen as a HUD. **Build stamp** `NYXUS · BUILD 2026.05 · ENTERPRISE` settles into the top-left. **Orbit ring** of 24 dim micro-dots cascades in around the wordmark. The 480 × 2px progress hairline appears with **3 subtle tick marks at 25/50/75%** and a **pure-white glowing leading edge**. The watermark `NYX-J5W-2026` sits in the bottom-right. |
| **5** | 3.0s+ | Steady state. Orbit ring slowly rotates clockwise. Diamond breathes (low-amplitude, slow inhale-exhale). Progress fills. |

Every motion uses `ease-out-cubic`, `ease-in-cubic`, `smooth-step`, or `sin`. No linear, no bounces, no wobble.

---

## Visual specification — TRIPLE BLACK + LIGHT GREY + WHITE GLOW (locked rev 4)

Pure monochrome. Three shades of black for void depth, light grey for HUD chrome, white as the only true light source. **No gold. No color. Black-on-black-on-black with white halos.**

### Palette

| Role | Hex | Notes |
|---|---|---|
| Void center | `#000000` | True black at the eye of the swirl |
| Faded black | `#0a0e16` | Sub-vignette, +1 in lightness |
| Charcoal mid | `#0a0a0c` | Mid-vignette, +2 |
| Graphite edge | `#14141a` | Outer ring, +5 |
| Wordmark fill | `#1a1a1f` | The letters are *darker than the page edges* |
| Wordmark rim | `#e8eaf2` @ 0.55 blur 5 | Cool starlight rim light |
| Wordmark aura | `#ffffff` @ 0.18 blur 14 | Outer bloom layer |
| Diamond fill | `#1f1f24` | Dark form with 1px white stroke |
| Diamond halo | `#ffffff` @ 0.85 blur 22 | Pure-white shockwave |
| Light grey | `#6a6e78` | Rules / corner brackets / build stamp / progress ticks |
| Progress fill | `#2a2a30` | Mid charcoal — *not* bright |
| Progress lead | `#ffffff` @ 1.0 blur 4 | The single lit point in motion |
| Orbit dots | `#c8ccd6` @ 0.45 | Faint pinpricks |
| Watermark | `#2a2a30` | Just legible against `#14141a` corner |

### What's in the bundle

```
boot-splash-void/
├── plymouth/nyxus-void/
│   ├── nyxus-void.plymouth      # Theme manifest
│   ├── nyxus-void.script        # Animation logic (~300 lines)
│   ├── background.png           # 1920×1080 cosmic ink swirl void
│   ├── wordmark.png             # Tri-layer-glow NYXUS VOID composite
│   ├── diamond.png              # 22×22 dark diamond + white edge
│   ├── diamond_halo.png         # 140×140 white shockwave halo
│   ├── beam.png                 # 70×200 white reveal beam (blurred)
│   ├── star.png                 # 3×3 white pinprick (12 instances animate)
│   ├── rule_top.png             # 600×3 etched hairline + center pip
│   ├── rule_bottom.png          # 600×3 etched hairline + center pip
│   ├── corner_tl.png            # 28×28 HUD bracket (top-left)
│   ├── corner_tr.png            # mirrored
│   ├── corner_bl.png            # flipped
│   ├── corner_br.png            # flipped + mirrored
│   ├── buildstamp.png           # 380×18 NYXUS · BUILD 2026.05 · ENTERPRISE
│   ├── orbit_dot.png            # 4×4 dim white dot (24 instances orbit)
│   ├── progress_track.png       # 480×2 dim hairline
│   ├── progress_fill.png        # 480×2 mid-charcoal fill
│   ├── progress_lead.png        # 48×18 white-glow leading edge
│   ├── tick.png                 # 1×6 light grey tick
│   └── watermark.png            # 320×18 NYX-J5W-2026
├── install.sh                   # Two-mode installer (system / --iso)
└── README.md                    # This file
```

---

## Install

### On the live NYXUS box

```bash
sudo bash install.sh
sudo reboot     # to see it in anger
```

### Bake into the archiso ISO

```bash
sudo NYX_PROFILE_ROOT=/path/to/nyx-profile bash install.sh --iso
sudo mkarchiso -v -w /tmp/archiso-work -o ./out /path/to/nyx-profile
```

The `--iso` mode patches:
- stages the theme into `airootfs/usr/share/plymouth/themes/nyxus-void/`
- adds `plymouth` to `packages.x86_64`
- inserts `plymouth` hook into `mkinitcpio.conf` after `udev`
- writes `/etc/plymouth/plymouthd.conf` with `Theme=nyxus-void`

The kernel cmdline already has `quiet splash` in the existing
`syslinux.cfg` / `loader/entries/01-nyx.conf` / `grub.cfg` — no edits needed.

### Preview without rebooting

```bash
sudo plymouthd
sudo plymouth --show-splash
sleep 8
sudo plymouth quit
```

---

## Why this isn't "another linux splash"

1. **The story.** Three seconds tells a complete narrative arc — discovery, accumulation, release, manifestation, settlement. Most splashes are static logos. This is a *moment*.
2. **The Infall.** Twelve stars converging into the void with accelerating ease-in-cubic motion is a scene people will subconsciously process as *gravitational physics*. They won't be able to articulate why it feels right — it just will.
3. **Negative-space wordmark.** The letters are *darker than the page* with white rim light. Your eye has to lock in to read them — and the moment it does, the image burns in. Like the badge on a Space Black MacBook in shadow.
4. **The HUD.** Etched rules, corner brackets, build stamp, orbit ring, progress ticks — six pieces of light grey chrome that say *this is engineered*, not decorated. Aerospace HUD restraint, not "linux distro".
5. **The progress lead.** A single 48 × 18 pure-white blurred segment that rides the dark-charcoal fill. The only thing on screen that's truly bright in motion. Eye-magnet.
6. **The watermark.** `NYX-J5W-2026` in `#2a2a30` against `#14141a`. Almost invisible. The kind of person who runs NYXUS will see it and respect it. It's a flex.
7. **The breath.** In steady state, the diamond does a low-amplitude inhale-exhale. The screen is *alive*. You don't notice it — until you see another splash and realize how dead they are.

---

© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED

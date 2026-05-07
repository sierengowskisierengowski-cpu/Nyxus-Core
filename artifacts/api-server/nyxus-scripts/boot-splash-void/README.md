# NYXUS VOID · Premium Boot Splash

> Pure void. One detail you'll remember.
> NYX-J5W-2026-SIERENGOWSKI-LOCKED

A Tesla/Apple-tier Plymouth theme. Not a "splash screen" — a moment.

---

## The reveal (2.5 seconds, then steady-state)

| Time | What happens |
|------|---|
| 0.0 – 0.4s | Black void. A single **gold diamond** fades in dead-center, where your eye lands. |
| 0.4 – 0.7s | The diamond breathes once — soft warm halo expands and fades. *This is the detail you remember.* |
| 0.7 – 1.7s | A thin **starlight beam** sweeps left → right across the wordmark area. The wordmark "ignites" in tandem with the beam — letter by letter as the light passes. |
| 1.7 – 2.2s | Beam fades. **Orbit ring** of 24 micro-dots fades in around the wordmark, dots cascading clockwise. |
| 2.2s+ | Orbit slowly rotates. Ultra-thin 480px progress hairline appears below the wordmark, with a **warm-gold leading edge** that rides the fill. Discreet `NYX-J5W-2026` watermark settles into the bottom-right corner. |

Every motion uses `ease-out cubic` or `smooth-step`. No linear, no bounces, no wobble.

---

## Visual specification (locked)

- **Background** — solid `#080808` (true void, not just dark).
- **Wordmark** — `N Y X U S    V O I D` in DejaVu Sans Regular, 64pt, kerning 32, fill `#f0f4ff`. No bold. The space lets it breathe.
- **Brand diamond** — 12 × 12px gold rhombus, `#d4a73a`. Halo at full breath: 80 × 80px, blurred 14px, opacity 0 → 0.95 → 0.
- **Beam** — 60 × 180px white pillar, blurred 10px (so it reads as bloom not a stripe).
- **Orbit ring** — 24 cool-white 3px dots, ellipse `wordmark_w/2 + 80` × `wordmark_h/2 + 50`, opacity 0.45.
- **Progress hairline** — 480 × 2px, track `#1c1c1c` @ 0.65, fill `#f0f4ff` @ 1.0, gold lead segment 12 × 6px @ 0.85.
- **Watermark** — `NYX-J5W-2026` in DejaVu Sans Mono 9pt, kerning 4, fill `#2a2a2a`. Almost invisible, exactly as intended.

Color discipline: **starlight cool-white** + **warm-gold jewelry accent**. Nothing else, ever.

---

## Theme structure

```
nyxus-void/
├── nyxus-void.plymouth      # Theme manifest
├── nyxus-void.script        # Animation logic (~250 lines)
├── background.png           # 1920×1080 #080808
├── wordmark.png             # NYXUS VOID glyph layer
├── diamond.png              # 18×18 gold diamond
├── diamond_halo.png         # 80×80 blurred halo for the breath
├── beam.png                 # 60×180 reveal beam (blurred)
├── orbit_dot.png            # 4×4 white dot
├── progress_track.png       # 480×2 dim hairline
├── progress_fill.png        # 480×2 starlight fill (sliced at runtime)
├── progress_lead.png        # 12×6 gold leading edge
└── watermark.png            # NYX-J5W-2026 metadata stamp
```

Drop the `nyxus-void/` folder into `/usr/share/plymouth/themes/` and you're done.

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

---

## Preview without rebooting

```bash
sudo plymouthd
sudo plymouth --show-splash
sleep 6
sudo plymouth quit
```

---

## What makes this top-tier (and not "another linux splash")

1. **One detail rule.** The gold diamond is the only thing on screen for the first half-second. Apple's apple. Tesla's T. NYXUS' diamond.
2. **Reveal physics.** The wordmark doesn't *fade in* — it's *uncovered* by a beam moving across it. Every letter ignites in sequence. Subconscious wow.
3. **No center-aligned stack.** The diamond sits 60px above the wordmark, the progress hairline sits 60px below. Three vertical zones, breathing room everywhere. Nothing is crowded.
4. **The orbit ring is barely there.** 0.45 opacity, slow rotation. You don't notice it consciously — you notice when it's gone.
5. **The progress bar has a personality.** It's 2px tall (a hairline, not a "bar") and the leading edge is *warm gold* against the cool-white fill. A single jewelry detail in motion.
6. **The watermark is a flex.** `NYX-J5W-2026` in `#2a2a2a`. Almost invisible against the void. The kind of person who installs NYXUS will see it and respect it.

---

© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED

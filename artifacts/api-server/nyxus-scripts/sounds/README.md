# NYXUS Sound Theme

The dispatcher (`nyxus-sound.sh`) resolves events in this order:

1. `~/.local/share/sounds/nyxus/<event>.oga` — user override
2. `/usr/share/sounds/nyxus/<event>.oga` — system theme (this dir)
3. `canberra-gtk-play -i <freedesktop-id>` — generic fallback

## Event manifest (must match `nyxus-sound.sh`)

| Event              | When played                          | Suggested length |
|--------------------|--------------------------------------|------------------|
| boot               | System startup chime                 | 1.5 – 2.5 s      |
| login              | Successful SDDM login                | 1.0 – 1.8 s      |
| logout             | Session end                          | 0.8 – 1.5 s      |
| notification       | Generic notification                 | 0.4 – 0.8 s      |
| message            | High-priority chat / mail            | 0.5 – 0.9 s      |
| error              | Failed action / dialog-error         | 0.5 – 0.9 s      |
| lock               | Screen locked                        | 0.3 – 0.6 s      |
| unlock             | Screen unlocked                      | 0.3 – 0.6 s      |
| battery-low        | < 15% remaining                      | 0.6 – 1.0 s      |
| battery-critical   | < 5% remaining                       | 0.8 – 1.4 s      |
| plug               | AC connected                         | 0.3 – 0.5 s      |
| unplug             | AC disconnected                      | 0.3 – 0.5 s      |
| screenshot         | Shutter                              | 0.2 – 0.4 s      |
| trash              | File moved to trash                  | 0.2 – 0.5 s      |
| alert              | Attention required                   | 0.5 – 0.9 s      |

## Format

- Container: Ogg Opus (`.oga`)
- Sample rate: 48 kHz
- Channels: stereo
- Loudness: -18 LUFS integrated, true peak ≤ -2 dBTP
- Encode: `ffmpeg -i in.wav -c:a libopus -b:a 96k <event>.oga`

## Bake on MSI host

Place finalized files in this directory then ship them via the ISO:

```sh
sudo install -Dm644 sounds/*.oga /usr/share/sounds/nyxus/
sudo install -Dm644 sounds/index.theme /usr/share/sounds/nyxus/index.theme
```

After install, `nyxus-sound.sh boot` will pick up the new theme without restart.

## Wiring

- Settings → Sound page exposes Master toggle + volume + per-event mute.
- All NYXUS apps call `nyxus-sound.sh <event>` instead of any direct backend.
- A user override at `~/.local/share/sounds/nyxus/<event>.oga` always wins.

---

# NYXUS Cosmic UI Sound Theme (`nyxus-sound`) — rev 2026-07-14

A cohesive sci-fi / UFO / cosmic sound set for the Nyxus desktop
(black-void + violet `#7949f2` + magenta `#ff2667` galaxy theme), matched
to system events. This is the ACTIVE set wired into the live desktop and is
separate from the legacy `nyxus-sound.sh`/`.oga` manifest above.

## Assets (this directory, `*.ogg`, Ogg Vorbis, 48 kHz, stereo, peak −6.5 dB)

Synthesized from pure math with **ffmpeg `aevalsrc`** (this host has **no
`sox`**; `ffmpeg` is present and does the synthesis). Regenerate any time:

```sh
nyxus-sound-bake                 # writes into this repo sounds/ dir
nyxus-sound-bake ~/.local/share/nyxus/sounds   # or bake straight to deploy
```

| Event          | Character                              | ~Length |
|----------------|----------------------------------------|---------|
| `startup`      | warm rising 3-partial pad (boot chime) | 0.8 s   |
| `login`        | bright rising UFO power-up             | 0.6 s   |
| `logout`       | falling power-down                     | 0.7 s   |
| `lock`         | short descending seal blip + tick      | 0.3 s   |
| `unlock`       | short ascending release blip + tick    | 0.3 s   |
| `notification` | warm plucked fifth chime               | 0.5 s   |
| `alert`        | pulsing alien warble (critical)        | 0.7 s   |
| `app-open`     | quick soft rising blip                 | 0.3 s   |
| `error`        | low descending "denied" tone           | 0.5 s   |
| `success`      | ascending 3-note arpeggio chime        | 0.6 s   |

Deployed to `~/.local/share/nyxus/sounds/<event>.ogg`.

## Player: `nyxus-sound <event>`

`~/.local/bin/nyxus-sound` — one shim every event calls. Non-blocking
(detached), idempotent, fails silent when audio is unavailable or muted.
Player preference: `pw-play` → `paplay` → `ffplay -nodisp -autoexit` →
`aplay`. Resolution: `<event>.ogg` → `.oga` → `.wav` → freedesktop fallback
via `canberra-gtk-play`.

- On/off flag: `~/.config/nyxus/sound.state` (`on`/`off`, missing == on).
  Toggle: `nyxus-sound toggle` (bound to **Super+Shift+A**). Also `on`,
  `off`, `status`, `list`, `test`.
- Volume: `~/.config/nyxus/sound.volume` (0–100) or `$NYXUS_SOUND_VOLUME`
  (default 90).

## Wired events (live + repo configs)

- **login / startup** — `hyprland.conf`: `exec-once = sh -c 'sleep 4; nyxus-sound login'`.
- **lock / unlock** — `hypridle.conf` `general{}`: `lock_cmd = nyxus-sound lock ; ...`
  and `unlock_cmd = nyxus-sound unlock`. `hyprland.conf` Super+L now routes
  through `loginctl lock-session` so every lock path (Super+L, wlogout lock,
  before-sleep) hits `lock_cmd`, and logind's unlock fires `unlock_cmd`.
- **logout** — `wlogout-layout` logout button + `hyprland.conf` Super+Shift+M
  exit bind both play `nyxus-sound logout` (with a 0.7 s grace) before tearing
  the session down.

## DEFERRED integration points (do NOT wire until the owning agent is done)

These files were being edited live by another agent, so the hooks are left
for the parent to drop in later. Each is a single idempotent line; place it
at the point the event is emitted:

- **Notification bridge** (`nyxus-notif-to-eww`) — for a normal notification,
  right after the notification is dispatched to eww:

  ```sh
  nyxus-sound notification &
  ```

- **Critical alerts** (`nyxus-notif-to-eww` / `nyxus-dunstrc`) — on the
  urgency=critical branch:

  ```sh
  nyxus-sound alert &
  ```

  (dunstrc alternative: in a `[urgency_critical]` rule use
  `script = nyxus-sound alert` — dunst runs it detached.)

- **Volume / brightness OSD** (`eww/scripts/osd-*.sh`) — one tick per OSD show,
  ideally debounced by the OSD's own repeat guard:

  ```sh
  nyxus-sound app-open &   # reuse the soft blip as the OSD tick
  ```

## Settings / Hub toggle integration point

The Settings "Sound" page (owned by another agent — `nyxus_settings.py` /
`eww/*` were off-limits) should drive the theme purely via the flag file:

- **Read state:** `nyxus-sound status` → prints `on`/`off` (exit 0 when on).
- **Write state:** `nyxus-sound on` / `nyxus-sound off` / `nyxus-sound toggle`,
  or write `on`/`off` directly to `~/.config/nyxus/sound.state`.
- **Volume slider:** write 0–100 to `~/.config/nyxus/sound.volume`.

No daemon restart needed — `nyxus-sound` reads the flag on every play.

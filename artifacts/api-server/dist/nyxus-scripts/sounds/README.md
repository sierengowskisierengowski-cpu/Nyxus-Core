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

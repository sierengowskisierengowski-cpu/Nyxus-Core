# NYXUS Voice Control

Offline, wake-word voice assistant for the NYXUS Hyprland desktop. Say
**"Nyxus, &lt;command&gt;"** to drive the desktop hands-free. 100% local — no
audio ever leaves the machine, and there is no network code path in the daemon.

## Components

| File | Role |
| --- | --- |
| `nyxus-voiced` | The daemon: mic capture → offline STT (Vosk) → command parser/dispatcher. Never crashes the session. |
| `nyxus-voice` | Control CLI: `start / stop / restart / status / toggle / mute / unmute / calibrate / test / run / selftest / config / logs / model`. |
| `nyxus-voice-model` | One-time helper to download + install the offline Vosk model (binary is **not** committed). |
| `nyxus-voice.conf` | Dedicated Hyprland include with the `exec-once` autostart (kept out of the main `hyprland.conf` autostart block). |
| `nyxus-voice-install` | Idempotent deploy/restore: installs the three bins to `~/.local/bin`, copies the include, optionally wires autostart. |

## STT backend

**Vosk** (`python-vosk` + a small model). Vosk is the lightest always-on
option: streaming recognition, a ~40 MB English model, fully offline, ideal
for continuous wake-word + command capture. `whisper.cpp` / `faster-whisper`
are heavier and batch-oriented, so Vosk is preferred for an always-listening
daemon. If Vosk or its model is absent, the daemon logs
`no STT backend; install vosk model` and **idles** — the desktop is never at
risk.

Mic capture prefers `python-sounddevice`; if that's missing it falls back to
PipeWire's `pw-record` as a raw-PCM subprocess.

## What the user must install

```bash
# 1. Python Vosk module (offline STT engine)
pip install --user vosk          # or use a venv/pipx

# 2. The offline model (~40 MB, one-time download)
nyxus-voice-model                # installs vosk-model-small-en-us-0.15

# Optional, already present on this box but listed for portability:
#   pipewire (pw-record)         mic capture fallback
#   python-sounddevice           preferred mic capture  (pip install --user sounddevice)
#   espeak-ng                    spoken TTS feedback (optional)
#   wpctl (wireplumber)          volume/mute control
```

Everything else (`hyprctl`, `loginctl`, `nyxus-sound`, `nyxus-companion`,
`nyxus-live-wallpaper`) already ships with NYXUS.

## Command grammar

Every command must be preceded by the wake word (default `nyxus`). Examples of
the accepted phrasings (matching is keyword/regex based, so natural variants
work):

| Intent | Say | Runs |
| --- | --- | --- |
| Lock | "lock down", "lock", "lock the screen" | `loginctl lock-session` |
| Launch app | "launch terminal", "open files", "start firefox" | app map → exec |
| Workspace | "workspace three", "go to workspace 5", "switch to desktop two" | `hyprctl dispatch workspace N` |
| Screenshot | "take a screenshot", "capture the screen" | `nyxus_screenshot.py` (grimblast/grim fallback) |
| Living wallpaper | "toggle living wallpaper", "toggle the wallpaper" | `nyxus-live-wallpaper toggle` |
| Mute | "mute", "unmute", "silence the audio" | `wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle` |
| Volume | "volume up", "louder", "volume down", "set volume to forty percent", "max volume" | `wpctl set-volume …` |
| Say hi | "say hi", "wave at me", "greet me" | `nyxus-companion nudge wave` + alien chirp |
| Sleep/wake | "go to sleep" / "wake up" | push-to-talk mute toggle |
| Help | "what can you do" | spoken list of commands |

Numbers work as digits or words (one…ten). App aliases are configurable — add
`app spotify = spotify` lines to the config.

## Configuration

`~/.config/nyxus/voice.conf` (auto-created with documented defaults on first
run). Key options: `wake_word`, `model`, `samplerate`, `device`, `feedback`
(`sound|tts|both|none`), `tts` (`auto|espeak-ng|espeak|piper|off`),
`require_wake`, `cooldown_ms`, `volume_step`, `start_muted`, and `app <alias>`
entries.

## Autostart

Autostart lives in the dedicated include `nyxus-voice.conf` so the main
`hyprland.conf` autostart block is never touched. Enable with one line in
`~/.config/hypr/hyprland.conf`:

```
source = ~/.config/hypr/nyxus-voice.conf
```

`nyxus-voice-install --wire-autostart` will append that line (and reload
Hyprland) for you; the plain `nyxus-voice-install` just prints it.

## Privacy & mic permissions

- Fully local: recognition runs on-device via Vosk. The daemon opens no
  sockets and makes no outbound connections. The only download is the
  user-initiated `nyxus-voice-model`.
- The mic is only read while the daemon runs. Push-to-talk: `nyxus-voice
  toggle` (or say "Nyxus, go to sleep") sets a mute flag so the daemon stops
  processing audio without exiting.
- Under PipeWire no special permission is needed for a user session to read
  the default source; pick a specific device with `nyxus-voice calibrate` if
  the default is wrong.

## Testing without a mic

```bash
nyxus-voice selftest              # built-in dispatcher unit tests (28 cases)
nyxus-voice test "nyxus lock down"    # dry-run: show the resolved action
nyxus-voice run  "nyxus say hi"       # actually execute a simulated transcript
```

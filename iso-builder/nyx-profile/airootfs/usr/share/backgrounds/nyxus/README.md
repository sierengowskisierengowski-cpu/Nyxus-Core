# NYXUS · default wallpaper bucket

This directory ships with the NYXUS profile and is the canonical location
for wallpapers referenced by the skel `~/.config/hypr/hyprpaper.conf`.

## Required files (added before ISO bake)

| File | Resolution | Purpose |
|------|-----------|---------|
| `nyxus-bg-darkmirror.png` | 3840×2160 | Default desktop wallpaper (DARK MIRROR aesthetic). Loaded by `hyprpaper` on first session via skel config. |
| `nyxus-lock-darkmirror.png` | 3840×2160 | Hyprlock background (referenced by skel `hyprlock.conf`). Optional — falls back to the desktop wall if absent. |
| `nyxus-sddm-darkmirror.png` | 3840×2160 | SDDM theme background (referenced by `Main.qml`). Optional — falls back to the solid `#0A0810` panel if absent. |

## Why these aren't in git

NYX repository policy keeps binary art assets in the release artifact
bucket, not in source control. The CI release workflow
(`.github/workflows/release.yml`) downloads the brand pack from the
NYXUS release bucket and drops the PNGs into this directory before
`mkarchiso` is invoked.

For local ISO bakes:

```bash
# from repo root
mkdir -p iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus
curl -fL "https://assets.nyxus.os/brand/2026.05/nyxus-bg-darkmirror.png" \
  -o iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus/nyxus-bg-darkmirror.png
```

If the file is missing at bake time, `iso-builder/verify-profile.sh`
emits a WARNING (not a hard error) so users without the brand bucket
can still bake; first-boot will then show a flat black background until
the user picks a wallpaper from Settings → Appearance.

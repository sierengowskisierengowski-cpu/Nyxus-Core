# Phase 7 — Center Widget + The Hub: implementation spec

> **Why this doc exists:** Phase 7's UI all lives in `eww.yuck`, which the
> Phase 5/6 (theme/bars) agent owns and is actively editing. To respect the
> disjoint-ownership rule and avoid clobbering their work, the Phase 7 agent
> built the **backend engines + this spec** first. The eww wiring below is a
> **clean drop-in** to be done by whoever owns `eww.yuck` once it's free (the
> theme agent, or the Phase 7 agent after the theme pass lands). **Do not edit
> `eww.yuck` from two agents at once.**

## Backends (DONE — live-tested, in `artifacts/api-server/nyxus-scripts/`)

### `nyxus-nowplaying` — music-mode feed (7.5)
Source-agnostic MPRIS via `playerctl` (picks up YouTube/Spotify/mpv/vlc/etc).
- `nyxus-nowplaying` → one-shot JSON. `nyxus-nowplaying --follow` → 1 line/sec for `deflisten`.
- Contract (stable):
  ```json
  {"playing":true,"status":"Playing","title":"","artist":"","album":"",
   "player":"","art":"/path","position":0,"length":0,"pct":0,
   "elapsed":"1:23","duration":"3:45"}
  ```
  Idle → `{"playing":false,"status":"Stopped", ...empty}`.

### `nyxus-hub-apps` — launcher data (7.3)
Enumerates visible `.desktop` apps (honours NoDisplay/Hidden, strips Exec field codes).
- `nyxus-hub-apps` (all) · `--nyxus` (NYXUS apps only) · `--filter <q>` (search box).
- Contract: JSON array of `{name,exec,icon,categories,terminal,id}`.

## eww wiring (TO DO — `eww.yuck` owner)

### 7.1 Center widget: clock ↔ music
```
(deflisten np "nyxus-nowplaying --follow")     ; JSON stream
(defwidget center []
  (box
    (revealer :reveal {np.playing == false} (nyxus-clock))     ; default state
    (revealer :reveal {np.playing}          (music-card np)))) ; music mode
```
- **Default:** polished "Nyxus" wordmark + `${time}` + `${date}` (Orbitron/Permanent Marker/Caveat per THEME.md).
- **Music:** `np.title` / `np.artist`, album art `np.art` (fallback to a branded card), a progress bar bound to `np.pct`, `np.elapsed`/`np.duration`, and prev/play-pause/next via `playerctl previous|play-pause|next`.
- Reverts to the clock automatically when `np.playing` goes false.

### 7.2 The Hub (rename + high polish)
- Rename the popup from "Nyxus Main Hub" → **"The Hub"** (window/def name + any label).
- Clicking the center widget opens The Hub (bind on the center box).
- Keep existing categories (Connect / Sound / Display / System / Stations / Power). No dead buttons — every control must call a real handler (7.6).
- Apply the Phase 5 frosted-glass tokens + starfield veil (consume, don't redefine).

### 7.3 App-launcher area inside The Hub
- A section that `(defpoll apps :interval "30s" "nyxus-hub-apps")` (or on-open) and renders a grid of app tiles: icon + `name`, click → `exec`.
- Optional search box → `nyxus-hub-apps --filter {search}`.

### 7.4 Quick-access (from §9 open items)
- Placeholder until the user answers §9 Q1 (what to pin). Leave a clean slot.

## Hub settings (STANDING RULE — must ship with the feature, §10)
Add to the Hub's settings surface (or `nyxus_settings` now + surface at Hub build):
- **Music mode**: on/off; "revert to clock when paused" vs "stay on music while paused".
- **App launcher**: show-all vs NYXUS-only default; grid size.
- These toggles are part of "done" — a feature with no Hub control is incomplete.

## Status
- [x] 7.5 backend (`nyxus-nowplaying`) — done, live-tested
- [x] 7.3 backend (`nyxus-hub-apps`) — done, live-tested
- [ ] 7.1 / 7.2 / 7.3-ui / 7.4 — eww wiring (gated on `eww.yuck` being free)
- [ ] 7.6 verify every Hub button works
- [ ] settings entries (standing rule)
- [ ] 7.7 safepoint

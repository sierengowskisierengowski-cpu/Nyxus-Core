# NYXUS — EWW chrome night: what we tried, what broke, full revert

> **When:** 2026-07-25 night → 2026-07-26 ~01:45 EDT  
> **Repo:** `~/Nyxus-Core` · `main` · tip at write → check `git rev-parse --short HEAD`  
> **Audience:** owner + next agent  
> **Living bake status:** [`HANDOFF.md`](../HANDOFF.md) (**WHERE WE STAND**)  
> **Do not re-litigate this into another redesign tonight.** Owner said leave chrome as restored.

---

## 1. One-paragraph verdict

A prior agent pushed a **saucer/boombox redesign** (marquee clock, lowrider art, ellipse math) that was **not** what the owner asked for. A follow-up pass tried to honor the real brief (PNG swap + time/date in the cockpit + dock/ticker wraps) and synced it live — it looked **wrong** (frosted shadow box, opaque “transparent” Meshy frames, wrong rails/ticker). Owner ordered a **full revert** to the **pre-redesign evening baseline**. That restore looks good. **Bake that tip.** Leave saucer/time chrome alone until a later, small, owner-directed pass.

---

## 2. What the owner actually wanted (original brief)

Not a redesign. Roughly:

1. **Bottom hub idle:** same flying saucer as the live wallpaper (`nyxus-livewall-ufo.png` / `assets/nyxus-saucer-livewall.png`) with **normal time + date** in the cockpit (not a sliding marquee).
2. **Music flip:** Downloads boombox `Meshy_AI_nyxus-boombox-transparent-v4.png` → fitted player UI inside the screen.
3. **Also from Downloads (later):** left dock / right dock / ticker “transparent” Meshy PNGs as wraps.

**Constraint the owner reinforced after the mess:** only the idle **time/date on the saucer** felt correct in the experimental pass; everything else (shadow box, dock/ticker wraps, frosted rectangle) was wrong. Then: **put everything back** how it was before those changes; fix saucer/time later, separately.

---

## 3. What landed (and why it was bad)

| Commit | What it did | Problem |
|---|---|---|
| `ecdcc952` | “Real” lowrider/livewall saucer + boombox + **SAUCER_CLOCK marquee** | Redesign / marquee — not the brief |
| `c73caae0` | Ellipse-fit math, boombox screen shrink, outline tweaks | Still redesign path; overfitted UI |
| `0bf2d06c` | Livewall UFO + time/date; boombox-v4; dock/ticker Meshy wraps; bigger bar geometries | Time/date OK; Meshy “transparent” art + wraps looked wrong live; tall bar + layer-blur = frosted **shadow box** |
| `b6774d53` | Kill cockpit plate; blur-off bars; strip wraps | Partial cleanup; owner still wanted **full** restore |

**Live-session lesson:** `sync-eww.sh` applies NS → `~/.config/eww` immediately on Hyprland. Bad tip = bad desktop in seconds. Hyprland `layerrule = blur on` for `nyxus-bar-*` plus a catch-all `^(nyxus.*)$` frosts a rectangular slab behind mostly-transparent bars when the bottom window is tall (saucer ~150px). Meshy “transparent” dock/ticker PNGs were largely **opaque** after matte and read as checkered/gray frames.

---

## 4. Full revert (what “back” means)

All of the above was **reverted on `main`** (revert commits `cfc16d9f` … `efb09aae`, plus handoff notes).

- **Content baseline:** tree for eww/chrome matches **pre-`ecdcc952`** (evening tip around `9146f123` / `28a121ff` era).
- **Still in git history** as ancestors (revert ≠ erase). Do **not** re-merge or cherry-pick those experiment commits.
- **Live builder session** was synced back to that tip; owner confirmed it **looks good**.
- **Deferred on purpose:** saucer time/date / boombox PNG swap. Owner: leave it; bake the restored tip.

---

## 5. What this bake *does* include

Everything that was good **before** the saucer redesign night, including (non-exhaustive):

- Live-boot audit fixes (Settings `/opt` fallback, app-shell ports, stage `nyxus-webapp`, side-rail glass, greeter cache dirs, non-blocking livewall, glow greeting off, etc. — see [`LIVE_BOOT_AUDIT_2026-07-25.md`](./LIVE_BOOT_AUDIT_2026-07-25.md))
- Evening eww/audio work that landed **before** `ecdcc952` (center/flip, boombox face of that era, `CAVA_BASS` wiring as of that tip)
- ALIEN NEON / Settings / offline bootstrap / Kage-default bake path from the Jul 24 briefs

**What this bake does *not* include:** livewall-saucer-as-hub with static time/date, boombox-v4 swap, Meshy dock/ticker wraps, marquee `SAUCER_CLOCK`, ellipse “lowrider” chrome experiments.

---

## 6. Bake / flash (owner)

```bash
# Gate (agent can run)
cd ~/Nyxus-Core && bash iso-builder/verify-profile.sh

# Bake (owner — needs sudo; agents cannot)
cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh
# → iso-builder/out/nyxus-<date>-x86_64.iso
```

- Tip at bake GO docs: confirm `git rev-parse --short HEAD` (expect post-revert tip, e.g. `97d1bcab`+).
- **Do not flash** `nyxus-2026.07.25` @ 15:00 (stale) for this work.
- After flash: UEFI boot; `cat /etc/nyxus-build` should match bake tip; bars/wallpaper/Settings smoke as in live-boot audit.

---

## 7. Next agent — hard rules

1. **Read this + [`HANDOFF.md`](../HANDOFF.md) before touching eww hub art.**
2. **Do not** reintroduce `ecdcc952` / `c73caae0` / `0bf2d06c` behavior without a fresh, narrow owner brief.
3. **Do not** “improve” saucer/time/docks/ticker unless the owner explicitly restarts that workstream.
4. If chrome work resumes later: **small PR or single commit**, sync live with `sync-eww.sh`, get owner visual OK **before** push/bake — and watch bar **layer blur** (`nyxus-hyprland-layerblur.conf` catch-all can undo `blur off`).
5. Sudo bake/flash = **owner only**.

---

## 8. Key paths

| Path | Role |
|---|---|
| `artifacts/api-server/nyxus-scripts/eww/` | NS = source of truth at bake |
| `iso-builder/nyx-profile/airootfs/etc/skel/.config/eww/` | Skel mirror (must lockstep) |
| `artifacts/api-server/nyxus-scripts/sync-eww.sh` | Live Hyprland apply |
| `artifacts/api-server/nyxus-scripts/nyxus-hyprland-layerblur.conf` | Layer blur (bars vs catch-all) |
| `artifacts/api-server/nyxus-scripts/livewall/nyxus-livewall-ufo.png` | Wallpaper UFO (future hub art source) |

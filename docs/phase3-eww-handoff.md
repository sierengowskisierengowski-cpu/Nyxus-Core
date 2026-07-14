# Phase 3 → EWW agent handoff

**From:** Worker A (Phase 3 — running-session wiring: keybinds, terminal, menu/panel wiring)
**To:** Phase 5/6 theme/EWW agent (owns everything under `~/.config/eww/`)
**Date:** 2026-07-14

Phase 3 audited every menu / flyout / settings panel reachable from keybinds or
the Hub. Per the coordination rules I did **not** edit any file under
`~/.config/eww/` and did **not** restart/reload the eww daemon. Everything below
is recorded read-only (`eww open <name>` → `eww active-windows` → `eww close`,
plus `eww ping` / `eww logs`). These are for the EWW agent to fix.

---

## 0. IMPORTANT: the running daemon lags the config on disk

- eww daemon PID started **2026-07-14 02:17:17**.
- `~/.config/eww/eww.yuck` was last modified **2026-07-14 03:12** (by the
  theme/EWW agent, mid-session).

So the live daemon is running a config **older than the file on disk**. All test
results below reflect the 02:17 config. **Recommend the EWW agent run
`eww reload` (owner action — I'm not allowed to) and then re-verify**, since some
results may change once the newer `eww.yuck` is actually loaded.

---

## 1. Flyouts that OPEN and register cleanly (13/14)

Tested with `eww open <name>`; each returned rc=0 and appeared in
`eww active-windows`, then closed cleanly:

`powermenu`, `dashboard`, `cheatsheet`, `deepcore`, `quicksettings`,
`notifications`, `wifi`, `mixer`, `calendar`, `bluetooth`, `mission`,
`updates`, `brightness-flyout`.

Caveat: "registers in `active-windows`" confirms the window maps; it does **not**
guarantee the contents render (non-blank) or that every internal poller/var is
healthy. I couldn't assess blank-vs-populated rendering without reloading the
daemon (forbidden for me). Please spot-check visually after `eww reload`.

All keybind targets `eww open --toggle <X>` in `hyprland.conf` point at windows
that **exist** as `defwindow`s (powermenu, dashboard, cheatsheet, deepcore,
quicksettings, notifications, wifi, mixer, calendar, bluetooth) — no missing-window
binds. So there is nothing for Phase 3 to fix on the Hyprland side for these.

---

## 2. BROKEN — needs the EWW agent

### 2.1 `nyxus-hub` — window is defined but fails to map  ⚠️ (signature feature)
- `eww open nyxus-hub` returns **rc=0** (so the window IS defined in the loaded
  config — a genuinely nonexistent name returns rc=1, verified as a control),
  **but it never appears in `eww active-windows`** and is not visible. It opens
  and immediately fails to stay mapped.
- This points at a **widget-construction error inside the Hub's widget tree**,
  not at the window declaration.
- Pointers (read-only):
  - `defwindow nyxus-hub` — `~/.config/eww/eww.yuck:874`
  - `(defwidget nyxus_hub_layout [] …)` — `~/.config/eww/eww.yuck:494`
- Impact: The Hub is called out as a signature feature (build brief §4). The
  center-widget click-to-open-Hub path will be dead until this maps.
- Suggested next step: after `eww reload`, `eww open nyxus-hub` and watch
  `eww logs` for the widget/var error that aborts the build; fix inside
  `nyxus_hub_layout` (or whatever child widget/var it references).

### 2.2 `TIME` defpoll — JSON parse failure breaks `TIME.*`
- `eww logs` shows:
  `error: Failed to turn `date +'{"hms":"%H:%M:%S", …,"long":"%A, %B %-d %Y"}'`
  into a value of type json-value` (interpolation `${TIME.long}`).
- Definition: `defpoll TIME` — `~/.config/eww/eww.yuck:21` (interval 1s, JSON
  `:initial`). `TIME.` is interpolated in **11** places in `eww.yuck` (clock,
  calendar tooltip, etc.).
- Likely cause: the `date +'{…json…}'` poll command's output isn't parsing as a
  json-value in the running daemon (quoting/escaping, or a `date` format token
  producing an invalid-JSON char). When `TIME` can't be parsed, every `TIME.*`
  read fails, which can blank the clock and anything that reads it — and could be
  contributing to 2.1 if `nyxus_hub_layout` reads `TIME.*`.
- Suggested next step: verify `date +'{json}'` emits strictly valid JSON on this
  box, or switch the poll to emit fields separately; confirm after `eww reload`.

---

## 3. Not touched (correctly out of Phase 3 scope)
- No edits to `eww.yuck`, `eww.scss(.source)`, `eww.css`, `eww/scripts/*`,
  `eww/assets/*`, `nyxus.conf`, `accent.scss`, `nyxus-palette.css`.
- Daemon not restarted/reloaded.
- `~/.config/eww/scripts/osd-show.sh` and `osd-capslock.sh` (referenced by
  Hyprland media/caps binds) both **exist and are executable** — no action needed.

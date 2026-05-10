# NYXUS

NYXUS is an Arch Linux-based operating system providing a suite of native Python GTK4 applications and widgets.

## Run & Operate

- `pnpm run typecheck`: Full typecheck across all packages.
- `pnpm run build`: Typecheck and build all packages.
- `pnpm --filter @workspace/api-spec run codegen`: Regenerate API hooks and Zod schemas from OpenAPI spec.
- `pnpm --filter @workspace/db run push`: Push DB schema changes (development only).
- `pnpm --filter @workspace/api-server run dev`: Run API server locally.

**Required Environment Variables:**
- `NYX-J5W-2026-SIERENGOWSKI-LOCKED`: Lock code for brand naming.

**Live ISO credentials** (set by `iso-builder/nyx-profile/airootfs/root/customize_airootfs.sh`):
- User: `nyx` / password: `nyx` (member of `wheel,audio,video,input,storage,network,uucp` — sudo enabled)
- Root: `root` / password: `nyx` (change after install)
- SDDM session: pick **Hyprland** from the bottom selector before signing in.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Where things live

- `/`: Project overview and high-level documentation.
- `iso-builder/`: Archiso profile for building the NYX ISO.
- `artifacts/api-server/nyxus-scripts/`: Contains all GTK4 application sources and installation tarballs.
- `airootfs/etc/nyxus/`: OS-level documentation mirrored from repo root.
- `~/.nyxus/`: Runtime directory for installed GTK4 apps and helper scripts.
- `nyxus-scripts/nyxus_palette.py`: **★ MASTER PALETTE** (Python) — every NYXUS app imports color/font/radius/blur constants from here. Edit this file to change the system look.
- `nyxus-scripts/nyxus-palette.css`: **★ MASTER PALETTE** (CSS) — every CSS file `@import`s this and uses `@define-color` names like `@nyx_white_off`, `@nyx_glass_dark`. Mirrors `nyxus_palette.py` exactly.
- `nyxus-scripts/nyxus_chrome.py`: Source of truth for unified GTK4 application chrome (windows, popovers, headerbars). Imports its colors from `nyxus_palette.py`.
- `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf`: Hyprland configuration template.

## Visual System — DARK MIRROR · TRIPLE-BLACK LAYERED (LOCKED · rev 2026-05-09 r14)

**Triple-black surface stack (rev r14):** Every surface in the system
now uses one of three layered shades of black, defined ONCE in
`nyxus-palette.css` + `nyxus_palette.py`:

| Token         | Value                       | Use                                           |
|---------------|-----------------------------|-----------------------------------------------|
| `nyx_black_smoke` (BLACK_SMOKE) | `rgba(14,14,22,0.55)` | Bars, panels, window backgrounds (lightest, lets blur through) |
| `nyx_black_ink`   (BLACK_INK)   | `rgba(8,8,14,0.78)`   | Raised pebbles, cards, buttons, ticker (mid)  |
| `nyx_black_void`  (BLACK_VOID)  | `rgba(0,0,0,0.92)`    | Hover, active, popovers, tooltips, modals (deepest, maximum pop) |

**Layering rule:** never put two adjacent surfaces at the same tier —
always go one tier darker as you elevate. That's what makes elements
"pop" without using color: pure depth via three blacks.

**White-glow accent (rev r14):** Two new tokens for sparing white-glow
text accents — `nyx_glow_soft` (`rgba(255,255,255,0.45)`) and
`nyx_glow_bright` (`rgba(255,255,255,0.85)`). Use only on wordmarks
(NYXUS, SIERENGOWSKI), focused/active labels, and key headings — never
on body text. Recipe: `text-shadow: 0 0 8px @nyx_glow_bright, 0 0 18px @nyx_glow_soft`.

Legacy tokens (`nyx_glass_dark/deeper/deepest` and Python
`GLASS_DARK/DEEPER/DEEPEST`) are kept as aliases pointing at the new
tiers, so any existing app code keeps working but renders with the new
triple-black palette automatically.

---

### Superseded revisions

Earlier visual systems (DARK MIRROR rev r13 frosted glass + the original
EMBOSSED CREAM PAPER rev r12) have been moved to
[`docs/legacy-visuals.md`](docs/legacy-visuals.md) for historical
reference. They no longer inform new work. Do NOT consult them unless
the user explicitly reverts the lock.

<!-- LEGACY-VISUALS-EXTRACTED-2026-05-10 -->

## Architecture decisions

- **Native GTK4 for all apps**: Every NYXUS app and widget is developed exclusively with native Python GTK4, prohibiting any web-based frameworks for performance and consistency.
- **Unified Visual Chrome**: A single `nyxus_chrome.py` module applies the system-wide DARK MIRROR · TRIPLE-BLACK styling to all GTK4 applications by monkey-patching `Gtk.ApplicationWindow.present`. See the Visual System section above for the locked-in rules `nyxus_chrome.py` enforces.
- **Offline-first Chrome Bootstrap**: The chrome bootstrap mechanism avoids synchronous network fetches by distributing `nyxus_chrome.py` locally during installation, ensuring offline functionality.
- **Dunst for Notifications**: Switched from Mako to Dunst as the sole notification daemon for system-wide consistency and improved features.
- **Modular Studio Suite**: NYXUS Studio is a multi-module GTK4 creative suite, architected with distinct modules (paint, vector, 3d, video, etc.) connected via internal broadcast mechanisms.
- **No-op for `nyxus-panel` Chrome**: `nyxus-panel` is intentionally excluded from the unified chrome bootstrap due to its reliance on `Gtk4LayerShell` which conflicts with window re-parenting.
- **Live fog daemon under waybars** (locked 2026-05-06j): Animated swirling fog inside the bars is rendered by `nyxus-fog.py` — a Python GTK4 + Cairo particle daemon that spawns 4 transparent `wlr-layer-shell` BOTTOM-layer windows aligned to each bar (top/bottom/left/right) and draws 14 soft-edged radial-gradient blobs per bar at 30fps. Palette: pure white + off-white #fbfaf6 + occasional gold #d4a73a (~15%, jewelry accent only). Waybar shell is intentionally low-alpha (~0.18) so the fog reads through. Autostart via Hyprland `exec-once = python3 ~/.nyxus/nyxus-fog.py`. CSS-based animation in waybar was tried (rev i) and abandoned — GTK3 CSS does not animate `background-position` reliably.
- **Wallpaper is full-bleed** (locked 2026-05-06c): `nyxus-frost-sierengowski.png` is the unpadded SIERENGOWSKI graffiti-on-cream artwork edge-to-edge. The padded variant was reverted at user request — side waybars (now 64px left / 72px right) will overlap the outermost letter strokes; the frosted blur softens the overlap. Do NOT re-pad without explicit user confirmation.
- **Asset-driven design pipeline** (locked 2026-05-06): high-fidelity
  3D look (sculpted plaques, liquid drips, extruded monograms) is
  produced as **rendered assets** by the user (Blender / Inkscape /
  Figma) or via AI image generation — NOT faked with CSS box-shadows.
  Pure CSS is reserved for the floating-neomorphic-button recipe and
  positioning. When the user drops a PNG/SVG, it's added to the
  `download.ts` whitelist, mirrored to `dist/`, and wired in as a
  background-image or icon. Stop trying to sculpt 3D depth in CSS.

## Product

- **GTK4 Application Suite**: A collection of native Python GTK4 applications including notepad, stickies, weather, system monitor, settings, terminal, quick settings, launcher, power menu, and screenshot tools.
- **NYXUS Studio**: A comprehensive creative suite with modules for painting, vector graphics, 3D modeling, video editing, animation, photo manipulation, layout, typography, and voice.
- **Integrated Desktop Environment**: Features a custom Waybar setup, Hyprland integration, and a themed SDDM login manager.
- **Application Store**: `nyxus-start` includes an inline NYXUS App Store for discovering and installing additional applications.
- **System Health Auditing**: `nyxus_doctor.py` provides a health audit tool for the system.
- **Notification Management**: Centralized notification system managed by Dunst, with controls in quick settings and a dedicated notifications panel.

## User preferences

- **Visual style is LOCKED** to DARK MIRROR (apps + flyout) + DARK GLASS
  WAYBAR (waybar shells) — see "Visual System" section above (rev
  2026-05-07 r12). Every future change MUST follow the locked monochrome
  palette: white / off-white `#e8edf5` / `#c8ccd6` / black / dark-glass
  rgba(8,12,20,0.55). No neon, no gold, no per-app colors, no alternate
  themes. The only accent permitted is per-workspace identity stripes on
  the bottom waybar.
- **Brand-naming lock**: "NYX" = ISO file only. "NYXUS" = OS + every
  component. "SIERENGOWSKI" = creator wordmark on wallpaper + plaques.
- **Propose-before-build for visual direction changes**: when the user
  shares a reference image or asks for a new look, present options +
  tradeoffs first; do not start implementing until they greenlight.
- **Design bar is "one-of-a-kind, top-tier" — never basic, never derivative**
  (rev r14, 2026-05-09): every visual must be crisp, clean, neat, highly
  polished, and uniquely NYXUS. Forbidden patterns: stock Bootstrap/
  Tailwind/Material card looks, generic flat buttons, default Waybar
  themes, anything that resembles another OS or app already shipping in
  the wild. Every surface must justify its existence — if it could be
  swapped into someone else's product unchanged, it isn't NYXUS enough.
  When in doubt, push the detail further: tighter typography, finer
  hairlines, more deliberate spacing, more careful layering of the
  triple-black tiers.

## Gotchas

- **First-boot bootstrap chain (LOCKED · 2026-05-10 r3)**: The ISO ships
  `/usr/local/bin/nyxus-bootstrap` (first-run installer wrapper) and
  `/usr/local/bin/nyxus-wait-bootstrap` (autostart serializer). Hyprland's
  `exec-once` fires every line in PARALLEL, so any autostart that depends
  on files written by `nyxus_install.sh` (waybar, swaybg wallpaper,
  nyxus-home) MUST be wrapped in `nyxus-wait-bootstrap` or it will race
  the bootstrap and crash on first login. Bootstrap is idempotent via a
  marker at `~/.nyxus/.bootstrapped` — to force re-run:
  `rm ~/.nyxus/.bootstrapped && nyxus-bootstrap`. Both shims live in
  `artifacts/api-server/nyxus-scripts/`, mirror to `dist/`, and are
  pre-staged in `iso-builder/nyx-profile/airootfs/usr/local/bin/` with
  `0755` perms set in `profiledef.sh`. First-boot UX uses `hyprctl notify`
  (built into Hyprland — no daemon dependency, since dunst races
  bootstrap too) to surface phase updates: start, post-download, success,
  and failure. The `notify()` function in `nyxus-bootstrap` is a no-op
  when `hyprctl` is unavailable so the script remains testable on hosts
  without Hyprland.
- **Offline ISO cache (LOCKED · 2026-05-10 r4)**: `iso-builder/build-iso.sh`
  now stages `dist/nyxus-scripts/` into `airootfs/opt/nyxus-cache/` at bake
  time, so `nyxus-bootstrap`'s offline fallback works on a machine with no
  internet on first boot. Adds ~52 MB to the squashfs. Bake order matters:
  `pnpm --filter @workspace/api-server run build` MUST run before
  `sudo ./build-iso.sh` so `dist/` is populated; build-iso.sh warns and
  continues if `dist/` is missing (online-only ISO in that case).
- **Hyprland Lua migration (TODO · 2026-05-10)**: Hyprland 0.55 deprecated the
  `hyprlang` config syntax in favor of Lua. The new API uses `hl.animation({...})`
  and `hl.curve({...})` function calls instead of `animation = ...` / `bezier = ...`
  lines. NYXUS configs (`nyxus-scripts/hyprland.conf`,
  `iso-builder/.../hyprland.conf`, all `nyxus-hyprland-*.conf` shards) are still
  in the old syntax — it works (deprecated ≠ removed) but at some point the
  hyprlang parser will be dropped. Plan a Lua migration sweep before that
  happens. Until then, **do not** use Lua-only features (native spring curves,
  etc.) — fake them with overshoot beziers (see `nyx-spring` / `nyx-glass` in
  the animations block).
- **ISO Build Environment**: The `iso-builder/` cannot be built within Replit; it requires root privileges and an Arch Linux host.
- **Hyprland Config Placeholder**: `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf` is a placeholder; users must replace it with their daily-driver configuration before building the ISO.
- **Brand Naming**: Strictly adhere to "NYX" for the ISO file and "NYXUS" for the operating system and all its components.

## Pointers

- **pnpm-workspace skill**: Refer to the `pnpm-workspace` skill for details on workspace structure, TypeScript setup, and package management.
- **OpenAPI Spec**: The OpenAPI specification defines API contracts and is used for codegen.
- **Drizzle ORM Documentation**: Consult Drizzle ORM documentation for database schema management.
- **Orval Documentation**: Refer to Orval documentation for API codegen specifics.
- **GTK4 Documentation**: For native Python GTK4 development, refer to official GTK4 documentation.
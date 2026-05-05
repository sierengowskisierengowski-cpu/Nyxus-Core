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
- `nyxus-scripts/nyxus_chrome.py`: Source of truth for unified GTK4 application styling.
- `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf`: Hyprland configuration template.

## Architecture decisions

- **Native GTK4 for all apps**: Every NYXUS app and widget is developed exclusively with native Python GTK4, prohibiting any web-based frameworks for performance and consistency.
- **Unified Visual Chrome**: A single `nyxus_chrome.py` module applies system-wide visual styling (GodsApp visual language, Caveat font, neon palette) to all GTK4 applications by monkey-patching `Gtk.ApplicationWindow.present`.
- **Offline-first Chrome Bootstrap**: The chrome bootstrap mechanism avoids synchronous network fetches by distributing `nyxus_chrome.py` locally during installation, ensuring offline functionality.
- **Dunst for Notifications**: Switched from Mako to Dunst as the sole notification daemon for system-wide consistency and improved features.
- **Modular Studio Suite**: NYXUS Studio is a multi-module GTK4 creative suite, architected with distinct modules (paint, vector, 3d, video, etc.) connected via internal broadcast mechanisms.
- **No-op for `nyxus-panel` Chrome**: `nyxus-panel` is intentionally excluded from the unified chrome bootstrap due to its reliance on `Gtk4LayerShell` which conflicts with window re-parenting.

## Product

- **GTK4 Application Suite**: A collection of native Python GTK4 applications including notepad, stickies, weather, system monitor, settings, terminal, quick settings, launcher, power menu, and screenshot tools.
- **NYXUS Studio**: A comprehensive creative suite with modules for painting, vector graphics, 3D modeling, video editing, animation, photo manipulation, layout, typography, and voice.
- **Integrated Desktop Environment**: Features a custom Waybar setup, Hyprland integration, and a themed SDDM login manager.
- **Application Store**: `nyxus-start` includes an inline NYXUS App Store for discovering and installing additional applications.
- **System Health Auditing**: `nyxus_doctor.py` provides a health audit tool for the system.
- **Notification Management**: Centralized notification system managed by Dunst, with controls in quick settings and a dedicated notifications panel.

## User preferences

- _Populate as you build_

## Gotchas

- **ISO Build Environment**: The `iso-builder/` cannot be built within Replit; it requires root privileges and an Arch Linux host.
- **Hyprland Config Placeholder**: `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf` is a placeholder; users must replace it with their daily-driver configuration before building the ISO.
- **Brand Naming**: Strictly adhere to "NYX" for the ISO file and "NYXUS" for the operating system and all its components.

## Pointers

- **pnpm-workspace skill**: Refer to the `pnpm-workspace` skill for details on workspace structure, TypeScript setup, and package management.
- **OpenAPI Spec**: The OpenAPI specification defines API contracts and is used for codegen.
- **Drizzle ORM Documentation**: Consult Drizzle ORM documentation for database schema management.
- **Orval Documentation**: Refer to Orval documentation for API codegen specifics.
- **GTK4 Documentation**: For native Python GTK4 development, refer to official GTK4 documentation.
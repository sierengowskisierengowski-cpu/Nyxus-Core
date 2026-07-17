# Nyxus Multi-Repository Dependencies

© 2026 Joseph A. Sierengowski

## Core Dependency Rules

### Repositories depending on Nyxus-Libs

- Nyxus-API-Server
- Nyxus-Web
- Nyxus-Notepad
- Nyxus-Stickies
- Nyxus-Sysmon
- Nyxus-Widgets
- Nyxus-Mockup-Sandbox
- Nyxus-Store
- Nyxus-Welcome
- Nyxus-Intel
- Nyxus-Dockd
- Nyxus-Hotkeyd
- Nyxus-Snapd
- Nyxus-QSD
- Nyxus-Wallpaper-Studio

### Applications connecting to Nyxus-API-Server

- Nyxus-Web
- Nyxus-Notepad
- Nyxus-Stickies
- Nyxus-Sysmon
- Nyxus-Widgets
- Nyxus-Mockup-Sandbox
- Nyxus-Store
- Nyxus-Welcome
- Nyxus-ISO-Builder (artifact metadata/release endpoints)

## Recommended Build Order

1. Nyxus-Libs
2. Nyxus-API-Server
3. Nyxus-Scripts
4. Nyxus-ISO-Builder
5. Python services (Nyxus-Intel, Dockd, Hotkeyd, Snapd, QSD, Wallpaper-Studio)
6. Web applications (Nyxus-Web, Notepad, Stickies, Sysmon, Widgets, Mockup-Sandbox, Store, Welcome)

## Development Workflow for Multi-Repo Changes

1. Implement shared contract changes in **Nyxus-Libs**
2. Update **Nyxus-API-Server** interfaces/versioning first
3. Update dependent Python daemons and web apps
4. Validate cross-repo CI on feature branches
5. Tag releases in dependency order (libs → backend/services → apps)

## Communication/Integration Pattern

- **Contract-first**: APIs/types originate from Nyxus-Libs and API OpenAPI contracts
- **Version pinning**: depend on released tags for stable environments
- **Staging validation**: integration tests in Nyxus-Core mirror expected production interactions

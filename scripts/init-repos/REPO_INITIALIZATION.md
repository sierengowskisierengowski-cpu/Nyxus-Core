# Nyxus Repository Initialization System

© 2026 Joseph A. Sierengowski

This folder provides a repeatable bootstrap for all 18 Nyxus repositories split out from Nyxus-Core.

> Main repository: [Nyxus-Core](https://github.com/sierengowskisierengowski-cpu/Nyxus-Core)

## 18-Repository Architecture Overview

- **Platform backend**: Nyxus-API-Server
- **Web apps**: Nyxus-Web, Nyxus-Notepad, Nyxus-Stickies, Nyxus-Sysmon, Nyxus-Widgets, Nyxus-Mockup-Sandbox, Nyxus-Store, Nyxus-Welcome
- **Python services/daemons**: Nyxus-Intel, Nyxus-Dockd, Nyxus-Hotkeyd, Nyxus-Snapd, Nyxus-QSD, Nyxus-Wallpaper-Studio
- **Shared/runtime support**: Nyxus-Libs, Nyxus-Scripts, Nyxus-ISO-Builder

## Dependency Graph Summary

See [DEPENDENCIES.md](./DEPENDENCIES.md) for full graph details and build order.

## Initialization Usage

```bash
cd scripts/init-repos
chmod +x init-all-repos.sh
export GITHUB_TOKEN=<token-with-repo-scope>
# optional if needed:
export GITHUB_OWNER=sierengowskisierengowski-cpu
./init-all-repos.sh
```

What the script does for each repo:
1. Clones the repository
2. Confirms it is empty (skips if already initialized)
3. Applies the mapped template set from `templates/`
4. Replaces template placeholders (`{{REPO_NAME}}`, `{{REPO_DESCRIPTION}}`)
5. Creates `main` branch
6. Commits and pushes initial baseline

## Manual Initialization (Fallback)

If you need to initialize one repository manually:

1. Clone empty repo
2. Copy template folder contents matching type from `scripts/init-repos/templates/<type>/`
3. Replace placeholders in files
4. Run:
   ```bash
   git checkout --orphan main
   git add .
   git commit -m "chore: initialize repository"
   git push -u origin main
   ```

## Repository Naming Conventions

- Canonical naming pattern: `Nyxus-<Component>`
- All names in `repo-types.json` are source-of-truth for automation
- Keep names stable to preserve CI badge/workflow links

## CI/CD Workflow Model

Template workflows include:
- **CI**: lint/typecheck/build/test gates
- **Release**: tag-triggered artifact/release automation
- **Dependency maintenance**: scheduled update checks (Node templates)

Each README includes CI badge placeholders and points back to Nyxus-Core for ecosystem architecture context.

## Environment Variables by Context

### Initialization Script
- `GITHUB_TOKEN` (**required**) – push access to all target repositories
- `GITHUB_OWNER` (optional) – defaults to `sierengowskisierengowski-cpu`

### Runtime/CI (per-template)
- Node templates: use `NODE_ENV`, optional release token from default `GITHUB_TOKEN`
- Python template: `PYTHONUNBUFFERED=1` suggested in deployments
- Shell template: no mandatory runtime secrets by default

## Inter-Repository Communication Patterns

- UI apps communicate with **Nyxus-API-Server** over HTTPS APIs
- Python daemons consume shared contracts/utilities from **Nyxus-Libs**
- **Nyxus-Scripts** distributes automation and bootstrap helpers reused by other repos
- **Nyxus-ISO-Builder** composes release artifacts by consuming outputs from API/web/scripts repos

Keep external contracts versioned and backward-compatible, and document breaking changes in each repository changelog.

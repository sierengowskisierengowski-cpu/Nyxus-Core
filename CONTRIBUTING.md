# Contributing to Nyxus-Core

Thanks for contributing to Nyxus-Core.

## Scope and terminology

- **NYX** = bootable ISO artifact
- **NYXUS** = OS/runtime/application ecosystem delivered by NYX

Please keep this naming consistent in code, docs, and PRs.

## Local setup

```bash
corepack enable
corepack prepare pnpm@latest --activate
pnpm install --no-frozen-lockfile
```

## Validation before opening a PR

Run from repository root:

```bash
pnpm run typecheck
pnpm run build
bash iso-builder/verify-profile.sh
bash scripts/iso-build-verify.sh
```

If your change is docs-only, run the checks that are still relevant to the area you touched.

## Documentation expectations

When repository reality changes, update related docs in the same PR where applicable:

- `README.md` (high-level "What works today" and links)
- `STATUS.md` (verified snapshot)
- `ROADMAP.md` (vision and milestones)
- `SHIPPING.md` (release-readiness checklist)
- `docs/README.md` (documentation map)
- `iso-builder/README.md` (ISO pipeline specifics)

Keep claims concrete and verifiable. Avoid aspirational wording in status-oriented docs.

## Pull request guidance

- Keep changes focused and minimal.
- Include a short summary of what changed and why.
- Note any validation commands you ran.
- For operational changes, include the exact file paths affected.

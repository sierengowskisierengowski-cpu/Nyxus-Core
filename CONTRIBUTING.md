# Contributing to Nyxus-Core

Thanks for contributing to Nyxus-Core.

## ⛔ Before your first change (updated 2026-07-30)

1. **Read [`HANDOFF.md`](HANDOFF.md) end to end.** It is not optional and it is
   not a summary of this file. It carries the one-canonical-repo rule, how the
   desktop is actually delivered, what is already fixed, and the do-not-repeat
   gotchas. This project has repeatedly paid for the same bug twice because
   somebody started work without it.
2. **There is exactly one canonical repo: `~/Nyxus-Core`, branch `main`.** A
   lowercase `~/nyxus-core`, or any `~/.nyxus-backup-*` / `~/nyxus-KNOWN-GOOD-*`
   / `~/Backups/nyxus*`, is a stale snapshot — never work in one.
3. **The palette is LOCKED.** ALIEN NEON, preset `prism`, `follow_wallpaper:
   false`. `nyxus_palette.py` and `accent.json` are the machine-readable canon;
   [`docs/THEME.md`](docs/THEME.md) and
   [`docs/DESIGN_CONTRACT.md`](docs/DESIGN_CONTRACT.md) are the human ones and
   carry the banned-hex list. Never hard-code a hex; import or `@import` the
   tokens. Deliberate carve-outs that may differ: Bifrost, GodsApp, Meli, the
   Arsenal / security-lab apps, Security Center.
4. **Editing a file under `iso-builder/nyx-profile/airootfs/` is often not
   enough to ship it.** The bake wipes large parts of `etc/skel/.config` and
   repopulates them from `artifacts/api-server/nyxus-scripts/` (**NS = the source
   of truth**). Change NS, or your fix is silently reverted on the next bake.
   This has cost multiple ISOs.
5. **`bash iso-builder/verify-profile.sh` must PASS.** Its gates are regression
   tests for bugs that already shipped. Fix the cause, never the gate.

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

- `HANDOFF.md` — **append** a dated section for anything a future agent would
  otherwise have to re-derive. Never restructure it; it is append-only by
  convention because several agents write to it.
- `README.md` (high-level "What works today" and links)
- `STATUS.md` (verified repository/CI snapshot — *not* bake readiness)
- `ROADMAP.md` (goals only; annotate any goal an owner decision has overridden)
- `SHIPPING.md` (bake → flash → boot checklist)
- `docs/README.md` (documentation map + freshness markers)
- `docs/KEYBINDS.md` (**if you touch a bind** — this file is the source of truth
  and is derived from the shipped config, not from memory)
- `docs/THEME.md` / `docs/DESIGN_CONTRACT.md` (if you touch a token)
- `iso-builder/README.md` (ISO pipeline specifics)

**Rules for docs, learned the hard way:**

- **Date every change you make to a doc.** A claim with no date cannot be aged out.
- **Verify before you assert.** Grep the tree for the path, the binary, the
  keybind, the hex. Two docs (`THEME.md`, `DESIGN_CONTRACT.md`) once presented
  the *purged* palette as current, and any agent following either would have
  reintroduced banned colour. A third (`docs/KEYBINDS.md`) documented five
  keybinds that did not exist.
- **When you correct a doc, say what it used to claim.** A silent correction
  invites the next agent to "fix" it back.
- **Do not rewrite the historical docs.** `docs/legacy-visuals.md`, the ALIEN
  NEON audit docs and the palette ban-list comments describe superseded designs
  **on purpose**. Making them ALIEN NEON destroys the record of what was banned.
- Keep claims concrete and verifiable. Avoid aspirational wording in
  status-oriented docs, and mark aspirational content as such in `ROADMAP.md`.

## Pull request guidance

- Keep changes focused and minimal.
- Include a short summary of what changed and why.
- Note any validation commands you ran.
- For operational changes, include the exact file paths affected.

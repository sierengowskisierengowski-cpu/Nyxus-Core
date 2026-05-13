# NYXUS i18n scaffold

Internationalisation infrastructure for the NYXUS Python desktop apps
(Settings, Security, Backup, Welcome, etc).

## Workflow

1. Mark translatable strings in Python with `_(...)` (the gettext
   convention) — wrappers will be added as code is migrated.
2. Run `bash extract.sh` from this directory to walk the
   `artifacts/api-server/nyxus-scripts/` tree, extract every `_()`
   call, and refresh `nyxus.pot`.
3. Translators copy `nyxus.pot` → `locale/<lang>/LC_MESSAGES/nyxus.po`,
   fill in the `msgstr` strings, then `msgfmt` compiles to `.mo`.
4. The runtime initialises gettext with
   `bindtextdomain("nyxus", "/usr/share/locale")` and
   `textdomain("nyxus")` once at app startup.

## Status

This is the **scaffold** — the extraction script, the `.pot` template,
and starter `.po` files for **en**, **es**, **fr**. Migrating every
existing string from string literals to `_()` calls is intentionally
phased: we stop new strings being added in raw English, while the
existing 90k LOC is migrated incrementally.

## Why now

A NYXUS milestone in the master plan (P6.31) is full multi-language
support. Shipping the scaffold first means every new feature can land
already-translatable, even if older code is still pure-English. This
matches the way GNOME, KDE, and macOS adopted i18n — incrementally,
behind a stable extraction pipeline.

## Files

- `extract.sh`           — walks the codebase and refreshes `nyxus.pot`
- `nyxus.pot`            — gettext template (machine-generated)
- `locale/en/…/nyxus.po` — English (canonical)
- `locale/es/…/nyxus.po` — Spanish
- `locale/fr/…/nyxus.po` — French

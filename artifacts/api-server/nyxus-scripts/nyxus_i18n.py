"""
NYXUS · gettext shim
====================

Tiny wrapper around the stdlib `gettext` module so every NYXUS Python
script can do::

    from nyxus_i18n import _
    label = _("Display")

…without each script having to repeat the bind/textdomain dance.

Domain
------
The translation domain is **`nyxus`**. PO files live under one of the
locations checked in priority order below, and compiled `nyxus.mo`
files must sit at::

    <localedir>/<lang>/LC_MESSAGES/nyxus.mo

Locale lookup order
-------------------
1. ``$NYXUS_LANG``                      — explicit override (testing).
2. ``~/.config/nyxus/locale.conf``      — user override written by
   Settings → Language & Region.  One line, key=value::

        LANGUAGE=es

3. ``$LANG`` / ``$LANGUAGE``            — system environment.
4. ``en``                               — final fallback.

Localedir lookup order (first existing wins)
--------------------------------------------
1. ``$NYXUS_LOCALEDIR``                 — explicit override.
2. ``/usr/share/locale``                — system install path.
3. ``<this file>/locale``               — repo / dev path.

Behaviour
---------
* If no `.mo` file is found, gettext returns the English msgid
  unchanged. That is the desired fallback — never raise just because a
  translation is missing.
* All errors are logged to ``~/.cache/nyxus/i18n.log`` per the global
  NYXUS rule (no print, no silent swallow).
"""
from __future__ import annotations

import gettext as _gettext
import logging
import os
from pathlib import Path
from typing import Optional

# ── logging ─────────────────────────────────────────────────────────
_LOG_DIR = Path.home() / ".cache" / "nyxus"
try:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:  # pylint: disable=broad-except
    pass
log = logging.getLogger("nyxus_i18n")
if not log.handlers:
    try:
        h = logging.FileHandler(_LOG_DIR / "i18n.log", encoding="utf-8")
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    except Exception:  # pylint: disable=broad-except
        pass

DOMAIN = "nyxus"
USER_CONF = Path.home() / ".config" / "nyxus" / "locale.conf"

# Stub locales we ship as scaffolding. Real translators add more by
# dropping a `<lang>/LC_MESSAGES/nyxus.po` next to the .pot template
# and running `compile.sh`.
SHIPPED_LOCALES = ("en", "es", "fr")


def _read_user_conf() -> Optional[str]:
    """Return the LANGUAGE= value from the user override file or None."""
    try:
        if not USER_CONF.is_file():
            return None
        for raw in USER_CONF.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip().upper() == "LANGUAGE":
                return v.strip().strip('"').strip("'")
    except Exception as e:  # pylint: disable=broad-except
        log.warning("read user locale.conf failed: %s", e)
    return None


def _pick_lang() -> str:
    """Resolve the active language code (e.g. 'es', 'fr', 'en')."""
    for src in (
        os.environ.get("NYXUS_LANG"),
        _read_user_conf(),
        os.environ.get("LANGUAGE"),
        os.environ.get("LANG"),
    ):
        if not src:
            continue
        # Normalize 'es_ES.UTF-8' / 'es:en' / 'es-ES' → 'es'
        code = src.split(":")[0].split(".")[0].split("@")[0].replace("-", "_")
        short = code.split("_")[0].lower()
        if short and short != "c" and short != "posix":
            return short
    return "en"


def _pick_localedir() -> Path:
    """First existing localedir from the priority list."""
    candidates = [
        os.environ.get("NYXUS_LOCALEDIR"),
        "/usr/share/locale",
        str(Path(__file__).resolve().parent / "locale"),
    ]
    for c in candidates:
        if c and Path(c).is_dir():
            return Path(c)
    # Fall back to the repo path even if missing — gettext will then
    # silently return msgids unchanged, which is the documented
    # fallback behaviour.
    return Path(__file__).resolve().parent / "locale"


_lang = _pick_lang()
_localedir = _pick_localedir()
log.info("i18n init: lang=%s localedir=%s", _lang, _localedir)

try:
    _translation = _gettext.translation(
        DOMAIN, localedir=str(_localedir),
        languages=[_lang], fallback=True)
except Exception as e:  # pylint: disable=broad-except
    log.warning("translation init failed (%s) — using NullTranslations", e)
    _translation = _gettext.NullTranslations()


def _(msgid: str) -> str:
    """Translate `msgid` to the active language; return msgid on miss."""
    try:
        return _translation.gettext(msgid)
    except Exception as e:  # pylint: disable=broad-except
        log.warning("gettext(%r) failed: %s", msgid, e)
        return msgid


def current_language() -> str:
    """Active short language code (e.g. 'en', 'es', 'fr')."""
    return _lang


def localedir() -> str:
    """Resolved localedir (for the Settings UI to display / verify)."""
    return str(_localedir)


def available_locales() -> list[str]:
    """Languages with a real ``nyxus.mo`` under the resolved localedir,
    plus the shipped scaffold list, deduped and sorted."""
    found: set[str] = set(SHIPPED_LOCALES)
    try:
        for lc in _localedir.iterdir():
            if not lc.is_dir():
                continue
            mo = lc / "LC_MESSAGES" / f"{DOMAIN}.mo"
            if mo.is_file():
                found.add(lc.name.split("_")[0].lower())
    except Exception as e:  # pylint: disable=broad-except
        log.warning("scan localedir failed: %s", e)
    return sorted(found)


def write_user_locale(code: str) -> None:
    """Persist the user's language pick to ``~/.config/nyxus/locale.conf``.

    Sign-out is required for the change to fully take effect (env vars
    are read at session start). The Settings page shows that hint.
    """
    short = (code or "en").split("_")[0].lower()
    try:
        USER_CONF.parent.mkdir(parents=True, exist_ok=True)
        USER_CONF.write_text(
            f"# NYXUS language override — applied at next sign-in\n"
            f"LANGUAGE={short}\n",
            encoding="utf-8")
        log.info("wrote user locale: %s", short)
    except Exception as e:  # pylint: disable=broad-except
        log.error("write user locale failed: %s", e)
        raise

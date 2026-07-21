"""Central configuration for the GSL backend.

Loads a local ``.env`` file (if present) into ``os.environ`` without any external
dependency, then exposes typed settings. Designed for local / isolated-lab use.
"""
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../gsl-backend


def _load_dotenv() -> None:
    """Minimal .env loader — only sets keys that are not already in the env.

    Supports ``KEY=value`` lines, ``#`` comments, blank lines, optional
    surrounding quotes, and an optional leading ``export``. Values are taken
    literally (no shell expansion), which is what we want for secrets/hashes.
    """
    env_path = BACKEND_DIR / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


_load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


# ── Auth ────────────────────────────────────────────────────────────────────
AUTH_USERNAME: str = _get("GSL_AUTH_USERNAME", "admin")
# Preferred: a pbkdf2 hash produced by hash_password.py. Fallback: plaintext
# password from the env (still never committed). If neither is set, main.py
# generates a random one-time password at startup and logs it.
AUTH_PASSWORD_HASH: str = _get("GSL_AUTH_PASSWORD_HASH", "")
AUTH_PASSWORD: str = _get("GSL_AUTH_PASSWORD", "")
SESSION_TTL_HOURS: int = _get_int("GSL_SESSION_TTL_HOURS", 12)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Same-origin (via the Vite proxy or the FastAPI-served build) needs no CORS.
# These defaults only matter if you run the Vite dev server as a *separate*
# origin talking directly to the backend. Override with a comma-separated list.
_default_cors = "http://localhost:19670,http://127.0.0.1:19670"
CORS_ORIGINS: list[str] = [
    o.strip() for o in _get("GSL_CORS_ORIGINS", _default_cors).split(",") if o.strip()
]

# ── Static SPA serving (production single-port mode) ──────────────────────────
# If set (or if the default built path exists) FastAPI serves the built SPA so
# the whole app runs from one `uvicorn` process with no CORS / proxy needed.
_default_static = BACKEND_DIR.parent / "artifacts" / "gsl" / "dist" / "public"
STATIC_DIR: str = _get("GSL_STATIC_DIR", str(_default_static))

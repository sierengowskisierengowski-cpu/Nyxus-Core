"""Authentication for the GSL backend.

Single-user token auth suitable for a local / isolated-lab deployment. Powerful
endpoints (arbitrary command execution + the streaming WebSocket) must never be
reachable without a valid session token.

- Passwords are verified against a PBKDF2-HMAC-SHA256 hash (see hash_password.py)
  or, as a fallback, a plaintext password supplied via the environment.
- Sessions are opaque random tokens held in memory with a TTL. Because this is a
  single-user local tool, an in-memory store is intentional; restarting the
  backend simply invalidates existing sessions.
"""
import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import Depends, HTTPException, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config

_PBKDF2_ALGO = "sha256"
_PBKDF2_ITERATIONS = 240_000

# token -> expiry epoch seconds
_sessions: dict[str, float] = {}

# Resolved at startup by configure(); a generated password is stored here so the
# startup banner can print it exactly once.
_generated_password: Optional[str] = None

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Return a self-describing PBKDF2 hash string for ``password``."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode(), salt, iterations)
    return f"pbkdf2_{_PBKDF2_ALGO}${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verify ``password`` against a stored PBKDF2 hash string."""
    try:
        scheme, iters, salt_hex, hash_hex = stored.split("$")
        algo = scheme.split("_", 1)[1]
        iterations = int(iters)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, IndexError):
        return False
    dk = hashlib.pbkdf2_hmac(algo, password.encode(), salt, iterations)
    return hmac.compare_digest(dk, expected)


def configure() -> None:
    """Resolve the effective password hash. Called once at startup.

    Priority: GSL_AUTH_PASSWORD_HASH > GSL_AUTH_PASSWORD > generated one-time.
    Guarantees the powerful endpoints are never exposed without a credential.
    """
    global _generated_password
    if config.AUTH_PASSWORD_HASH:
        return  # already have a hash; nothing to do
    if config.AUTH_PASSWORD:
        config.AUTH_PASSWORD_HASH = hash_password(config.AUTH_PASSWORD)
        return
    # No credential configured — generate a strong one-time password so the app
    # stays protected but usable. It is NOT persisted anywhere.
    _generated_password = secrets.token_urlsafe(12)
    config.AUTH_PASSWORD_HASH = hash_password(_generated_password)


def startup_banner() -> str:
    """Human-readable auth status for the startup log."""
    lines = [
        "─" * 62,
        " GSL authentication is ENABLED",
        f"   username: {config.AUTH_USERNAME}",
    ]
    if _generated_password is not None:
        lines += [
            "   password: (generated for this run — set GSL_AUTH_PASSWORD_HASH",
            "              in gsl-backend/.env to make it permanent)",
            f"   >>> {_generated_password} <<<",
        ]
    else:
        lines.append("   password: (from environment)")
    lines.append("─" * 62)
    return "\n".join(lines)


def authenticate(username: str, password: str) -> bool:
    user_ok = hmac.compare_digest(username, config.AUTH_USERNAME)
    pass_ok = verify_password(password, config.AUTH_PASSWORD_HASH)
    return user_ok and pass_ok


def create_session() -> tuple[str, float]:
    token = secrets.token_urlsafe(32)
    expiry = time.time() + config.SESSION_TTL_HOURS * 3600
    _sessions[token] = expiry
    return token, expiry


def revoke_session(token: str) -> None:
    _sessions.pop(token, None)


def _token_valid(token: Optional[str]) -> bool:
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None:
        return False
    if expiry < time.time():
        _sessions.pop(token, None)
        return False
    return True


def require_auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: require a valid Bearer token. Returns the token."""
    token = creds.credentials if creds else None
    if not _token_valid(token):
        raise HTTPException(status_code=401, detail="Authentication required")
    return token  # type: ignore[return-value]


async def require_ws_auth(websocket: WebSocket) -> bool:
    """Validate a WebSocket connection using a ``?token=`` query parameter.

    Browsers cannot set Authorization headers on WebSocket handshakes, so the
    token is passed as a query parameter. Closes the socket on failure.
    """
    token = websocket.query_params.get("token")
    if _token_valid(token):
        return True
    await websocket.close(code=4401)  # 4401 = unauthorized (application code)
    return False

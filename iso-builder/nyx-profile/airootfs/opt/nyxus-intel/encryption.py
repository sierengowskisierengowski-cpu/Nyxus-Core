# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · encryption.py
AES-256-GCM at-rest encryption with PBKDF2-derived keys.

Every case is encrypted with a per-case key wrapped by a key derived from
the master password. The DEK (data-encryption key) is generated randomly
per case; we then wrap it with a KEK (key-encryption key) derived from
the master password + a per-case salt via PBKDF2-HMAC-SHA256, 200_000
iterations. AES-GCM gives us authenticated encryption — tampering is
detected on decrypt.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import json
import base64
from typing import Tuple, Dict, Any

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────


PBKDF2_ITERATIONS = 200_000
KEY_LEN           = 32   # AES-256
SALT_LEN          = 16
NONCE_LEN         = 12   # GCM standard


def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def derive_key(password: str, salt: bytes,
               iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """PBKDF2-HMAC-SHA256 → 32 byte key."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LEN,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def new_salt() -> bytes:
    return os.urandom(SALT_LEN)


def new_nonce() -> bytes:
    return os.urandom(NONCE_LEN)


def encrypt_bytes(plaintext: bytes, key: bytes,
                  associated_data: bytes | None = None
                  ) -> Tuple[bytes, bytes]:
    """Encrypt plaintext with AES-256-GCM. Returns (nonce, ciphertext_with_tag)."""
    if len(key) != KEY_LEN:
        raise ValueError(f"key must be {KEY_LEN} bytes")
    nonce = new_nonce()
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, plaintext, associated_data)
    return nonce, ct


def decrypt_bytes(nonce: bytes, ciphertext: bytes, key: bytes,
                  associated_data: bytes | None = None) -> bytes:
    """Decrypt AES-256-GCM ciphertext. Raises on tamper / bad key."""
    if len(key) != KEY_LEN:
        raise ValueError(f"key must be {KEY_LEN} bytes")
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


# ── case envelope helpers ─────────────────────────────────────────────────
# A case envelope is a JSON dict written to disk. The JSON itself is plain,
# but every value field that holds case content is base64-encoded ciphertext.
# Schema:
#   {
#     "v": 1,
#     "salt": <b64>,                # KEK salt for this case
#     "wrapped_dek": {
#         "nonce": <b64>, "ct": <b64>
#     },
#     "payload": {
#         "nonce": <b64>, "ct": <b64>
#     }
#   }

def encrypt_case(payload_obj: Dict[str, Any], password: str
                 ) -> Dict[str, Any]:
    salt = new_salt()
    kek  = derive_key(password, salt)
    dek  = AESGCM.generate_key(bit_length=256)

    n1, wrapped = encrypt_bytes(dek, kek, associated_data=b"NYXUS-INTEL/v1/dek")
    payload_bytes = json.dumps(payload_obj, separators=(",", ":")).encode("utf-8")
    n2, ct = encrypt_bytes(payload_bytes, dek, associated_data=b"NYXUS-INTEL/v1/case")

    return {
        "v": 1,
        "salt": _b64e(salt),
        "wrapped_dek": {"nonce": _b64e(n1), "ct": _b64e(wrapped)},
        "payload":     {"nonce": _b64e(n2), "ct": _b64e(ct)},
    }


def decrypt_case(envelope: Dict[str, Any], password: str
                 ) -> Dict[str, Any]:
    if envelope.get("v") != 1:
        raise ValueError("unsupported envelope version")
    salt = _b64d(envelope["salt"])
    kek  = derive_key(password, salt)
    n1   = _b64d(envelope["wrapped_dek"]["nonce"])
    wct  = _b64d(envelope["wrapped_dek"]["ct"])
    dek  = decrypt_bytes(n1, wct, kek, associated_data=b"NYXUS-INTEL/v1/dek")

    n2   = _b64d(envelope["payload"]["nonce"])
    ct   = _b64d(envelope["payload"]["ct"])
    payload_bytes = decrypt_bytes(n2, ct, dek, associated_data=b"NYXUS-INTEL/v1/case")
    return json.loads(payload_bytes.decode("utf-8"))


def secure_delete(path: str, passes: int = 3) -> None:
    """Best-effort multi-pass overwrite then unlink. Not perfect on SSDs (the
    hardware may rewrite to a fresh block) but better than a plain unlink."""
    try:
        sz = os.path.getsize(path)
    except OSError:
        return
    try:
        with open(path, "r+b", buffering=0) as f:
            for _ in range(max(1, passes)):
                f.seek(0)
                f.write(os.urandom(sz))
                f.flush()
                os.fsync(f.fileno())
        os.remove(path)
    except OSError:
        # Fall back to plain unlink so we never leave the file behind.
        try: os.remove(path)
        except OSError: pass

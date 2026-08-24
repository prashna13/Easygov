"""
doc_crypto.py
-------------
Encryption at rest for user-uploaded documents.

Files are stored server-side as Fernet (AES) ciphertext. The key is read from
the `DOC_ENCRYPTION_KEY` environment variable, or — for local dev where the
variable is not set — generated once and persisted to `db_storage/` so existing
encrypted files remain readable across restarts. `db_storage/` is gitignored.

On read, previously-stored plaintext files (from before encryption was added)
are detected and served unchanged, so enabling encryption is non-destructive
to existing data.
"""

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_STORAGE_DIR = Path("db_storage")
_KEY_FILE = _STORAGE_DIR / "doc_encryption_key"


def _load_or_create_key() -> bytes:
    # 1. Prefer an explicit env key (stable, intended for production).
    env_key = os.getenv("DOC_ENCRYPTION_KEY")
    if env_key:
        # Accept either a raw Fernet key or base64 text; validate later.
        return env_key.encode("utf-8")

    # 2. Reuse a previously generated/persisted key if present.
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes()

    # 3. Generate, persist, and warn.
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    logger.warning(
        "DOC_ENCRYPTION_KEY is not set — generated and persisted a key at %s. "
        "Back up this file, or set DOC_ENCRYPTION_KEY in production, or uploaded "
        "documents will be unrecoverable if it is lost.",
        _KEY_FILE,
    )
    return key


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt_bytes(data: bytes) -> bytes:
    """Return Fernet ciphertext for a plaintext document."""
    return _get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    """Return the plaintext document from Fernet ciphertext.

    Raises `ValueError` (legacy_plaintext sentinel) if `data` is not valid
    ciphertext — i.e. it is a pre-encryption plaintext file. Callers should
    treat that as "serve as-is" rather than a hard error.
    """
    try:
        return _get_fernet().decrypt(data)
    except InvalidToken as exc:
        raise ValueError("document is not encrypted (legacy plaintext)") from exc

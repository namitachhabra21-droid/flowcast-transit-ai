"""API key generation/verification for programmatic access.

Only a SHA-256 hash is ever persisted (see models.ApiKey.key_hash). The
plaintext key is generated here, returned once at creation time, and never
recoverable from the database afterwards.
"""
import hashlib
import secrets
from typing import Tuple

from app.config import get_settings

_RANDOM_BYTES = 24


def generate_api_key() -> Tuple[str, str, str]:
    """Returns (plaintext_key, key_prefix, key_hash)."""
    prefix = get_settings().api_key_prefix
    token = secrets.token_urlsafe(_RANDOM_BYTES)
    plaintext = f"{prefix}_{token}"
    key_prefix = plaintext[: len(prefix) + 9]  # enough to identify a key in a list without revealing it
    return plaintext, key_prefix, hash_api_key(plaintext)


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()

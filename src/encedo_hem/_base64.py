"""Base64 helpers for the two distinct conventions used by HEM.

The HEM REST API uses **standard** base64 (with padding) for payload fields
like ``msg``, ``aad``, ``ciphertext`` and for the ``iss`` claim, but uses
**base64url without padding** for JWT segments. Mixing them is the #1 source
of bugs, so they live in two named pairs here.
"""

from __future__ import annotations

import base64


def b64_std_encode(data: bytes) -> str:
    """Standard base64 with padding (RFC 4648 §4).

    Used for API payload fields like ``msg``, ``aad``, ``ciphertext``, and
    for ``iss`` in the eJWT payload.
    """
    return base64.b64encode(data).decode("ascii")


def b64_std_decode(text: str) -> bytes:
    """Inverse of :func:`b64_std_encode`. Padding is required."""
    return base64.b64decode(text, validate=False)


def b64url_nopad_encode(data: bytes) -> str:
    """base64url without padding (RFC 4648 §5).

    Used only for JWT segments (header, payload, signature).
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_nopad_decode(text: str) -> bytes:
    """Inverse of :func:`b64url_nopad_encode`. Re-adds padding before decoding."""
    pad = (-len(text)) % 4
    return base64.urlsafe_b64decode(text + ("=" * pad))

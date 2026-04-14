"""Integration tests for POST /api/crypto/cipher/wrap and /unwrap."""

from __future__ import annotations

import secrets

from encedo_hem import HemClient, KeyType, WrapAlg


def test_cipher_wrap_unwrap(hem: HemClient) -> None:
    kid = hem.keys.create("it-wrap", KeyType.AES256)
    try:
        key_material = secrets.token_bytes(16)  # 16 bytes — RFC 3394 minimum
        wrap_result = hem.crypto.cipher.wrap(kid, WrapAlg.AES256, msg=key_material)
        unwrapped = hem.crypto.cipher.unwrap(kid, wrap_result.wrapped, alg=WrapAlg.AES256)
        assert unwrapped == key_material
    finally:
        hem.keys.delete(kid)

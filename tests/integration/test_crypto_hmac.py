"""Integration tests for POST /api/crypto/hmac/hash and /verify."""

from __future__ import annotations

import secrets

from encedo_hem import HashAlg, HemClient, KeyType


def test_hmac_hash_and_verify(hem: HemClient) -> None:
    kid = hem.keys.create("it-hmac", KeyType.SHA2_256)
    try:
        msg = secrets.token_bytes(32)
        result = hem.crypto.hmac.hash(kid, msg, alg=HashAlg.SHA2_256)
        assert len(result.mac) > 0

        assert hem.crypto.hmac.verify(kid, msg, result.mac, alg=HashAlg.SHA2_256)
        assert not hem.crypto.hmac.verify(kid, b"wrong message", result.mac, alg=HashAlg.SHA2_256)
    finally:
        hem.keys.delete(kid)

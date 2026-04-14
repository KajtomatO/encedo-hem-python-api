"""Integration tests for POST /api/crypto/ecdh."""

from __future__ import annotations

import contextlib

from encedo_hem import HashAlg, HemClient, HemError, KeyType


def test_ecdh_exchange(hem: HemClient) -> None:
    kid1 = kid2 = None
    try:
        kid1 = hem.keys.create("it-ecdh-1", KeyType.SECP256R1)
        kid2 = hem.keys.create("it-ecdh-2", KeyType.SECP256R1)
        details2 = hem.keys.get(kid2)
        assert details2.pubkey is not None

        result = hem.crypto.ecdh.exchange(kid1, pubkey=details2.pubkey, alg=HashAlg.SHA2_256)
        assert len(result.shared_secret) == 32  # SHA2-256 output
    finally:
        for kid in (kid1, kid2):
            if kid:
                with contextlib.suppress(HemError):
                    hem.keys.delete(kid)

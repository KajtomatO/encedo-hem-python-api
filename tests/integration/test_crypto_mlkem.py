"""Integration tests for POST /api/crypto/pqc/mlkem/encaps and /decaps."""

from __future__ import annotations

from encedo_hem import HemClient, KeyType


def test_mlkem_encaps_decaps(hem: HemClient) -> None:
    kid = hem.keys.create("it-mlkem", KeyType.MLKEM768)
    try:
        encaps = hem.crypto.pqc.mlkem.encaps(kid)
        assert len(encaps.ciphertext) > 0
        assert len(encaps.shared_secret) > 0

        decaps = hem.crypto.pqc.mlkem.decaps(kid, encaps.ciphertext)
        assert decaps.shared_secret == encaps.shared_secret
    finally:
        hem.keys.delete(kid)

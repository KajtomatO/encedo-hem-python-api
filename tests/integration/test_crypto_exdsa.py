"""Integration tests for POST /api/crypto/exdsa/sign and /verify."""

from __future__ import annotations

import secrets

from encedo_hem import HemClient, KeyType, SignAlg


def test_exdsa_secp256r1(hem: HemClient) -> None:
    kid = hem.keys.create("it-exdsa-secp256r1", KeyType.SECP256R1)
    try:
        msg = secrets.token_bytes(32)
        result = hem.crypto.exdsa.sign(kid, msg, SignAlg.SHA256_ECDSA)
        assert hem.crypto.exdsa.verify(kid, msg, result.signature, SignAlg.SHA256_ECDSA)
        assert not hem.crypto.exdsa.verify(
            kid, b"wrong message", result.signature, SignAlg.SHA256_ECDSA
        )
    finally:
        hem.keys.delete(kid)


def test_exdsa_ed25519(hem: HemClient) -> None:
    kid = hem.keys.create("it-exdsa-ed25519", KeyType.ED25519)
    try:
        msg = secrets.token_bytes(32)
        result = hem.crypto.exdsa.sign(kid, msg, SignAlg.ED25519)
        assert hem.crypto.exdsa.verify(kid, msg, result.signature, SignAlg.ED25519)
        assert not hem.crypto.exdsa.verify(kid, b"wrong message", result.signature, SignAlg.ED25519)
    finally:
        hem.keys.delete(kid)

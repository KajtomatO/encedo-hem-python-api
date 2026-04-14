"""Integration tests for POST /api/crypto/pqc/mldsa/sign and /verify."""

from __future__ import annotations

import secrets

import pytest

from encedo_hem import HemClient, KeyType


@pytest.mark.skip(reason="OQ-22: mldsa/verify returns HTTP 795 instead of 406 for invalid sig.")
def test_mldsa_sign_verify(hem: HemClient) -> None:
    kid = hem.keys.create("it-mldsa", KeyType.MLDSA65)
    try:
        msg = secrets.token_bytes(32)
        result = hem.crypto.pqc.mldsa.sign(kid, msg)
        assert hem.crypto.pqc.mldsa.verify(kid, msg, result.signature)
        assert not hem.crypto.pqc.mldsa.verify(kid, b"wrong message", result.signature)
    finally:
        hem.keys.delete(kid)

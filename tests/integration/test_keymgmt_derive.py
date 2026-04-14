"""Integration tests for POST /api/keymgmt/derive."""

from __future__ import annotations

import contextlib
import secrets

from encedo_hem import CipherAlg, HemClient, HemError, KeyType


def test_derive_aes_key_and_use(hem: HemClient) -> None:
    src_kid = peer_kid = derived_kid = None
    try:
        src_kid = hem.keys.create("it-derive-src", KeyType.CURVE25519)
        peer_kid = hem.keys.create("it-derive-peer", KeyType.CURVE25519)
        peer_details = hem.keys.get(peer_kid)
        assert peer_details.pubkey is not None

        derived_kid = hem.keys.derive(
            src_kid, "it-derive-aes", KeyType.AES256, pubkey=peer_details.pubkey
        )

        # Derived key must be usable for crypto operations.
        plaintext = secrets.token_bytes(32)
        enc = hem.crypto.cipher.encrypt(derived_kid, plaintext, alg=CipherAlg.AES256_GCM)
        recovered = hem.crypto.cipher.decrypt(
            derived_kid, enc.ciphertext, alg=CipherAlg.AES256_GCM, iv=enc.iv, tag=enc.tag
        )
        assert recovered == plaintext
    finally:
        for kid in (src_kid, peer_kid, derived_kid):
            if kid:
                with contextlib.suppress(HemError):
                    hem.keys.delete(kid)

"""Integration tests for POST /api/keymgmt/import."""

from __future__ import annotations

import contextlib

import pytest

from encedo_hem import HemClient, HemError, HemNotAcceptableError, KeyType


def test_import_pubkey_returns_kid(hem: HemClient) -> None:
    imported_kid = None
    try:
        # Create a key, capture its pubkey, then delete it so the device no
        # longer holds the key — import of the same pubkey then succeeds.
        original_kid = hem.keys.create("it-import-src", KeyType.ED25519)
        details = hem.keys.get(original_kid)
        assert details.pubkey is not None
        hem.keys.delete(original_kid)

        imported_kid = hem.keys.import_key("it-import-pub", details.pubkey, KeyType.ED25519)
        assert imported_kid is not None
    finally:
        if imported_kid:
            with contextlib.suppress(HemError):
                hem.keys.delete(imported_kid)


def test_import_duplicate_raises_not_acceptable(hem: HemClient) -> None:
    """OQ-20: importing the same public key twice returns HTTP 406."""
    imported_kid = None
    try:
        original_kid = hem.keys.create("it-import-dup-src", KeyType.ED25519)
        details = hem.keys.get(original_kid)
        assert details.pubkey is not None
        hem.keys.delete(original_kid)

        imported_kid = hem.keys.import_key("it-import-dup", details.pubkey, KeyType.ED25519)

        with pytest.raises(HemNotAcceptableError):
            hem.keys.import_key("it-import-dup-2", details.pubkey, KeyType.ED25519)
    finally:
        if imported_kid:
            with contextlib.suppress(HemError):
                hem.keys.delete(imported_kid)

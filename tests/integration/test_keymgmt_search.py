"""Integration tests for POST /api/keymgmt/search."""

from __future__ import annotations

import base64
import contextlib
import secrets

from encedo_hem import HemClient, HemError, KeyType


def test_search_finds_key_by_descr_prefix(hem: HemClient) -> None:
    prefix = secrets.token_bytes(8)
    descr = prefix + b"-it-search"
    pattern = "^" + base64.b64encode(prefix).decode()
    kid = None
    try:
        kid = hem.keys.create("it-search", KeyType.AES256, descr=descr)
        results = list(hem.keys.search(pattern))
        kids = [k.kid for k in results]
        assert kid in kids
    finally:
        if kid:
            with contextlib.suppress(HemError):
                hem.keys.delete(kid)


def test_search_no_match_yields_nothing(hem: HemClient) -> None:
    # Use a prefix that is extremely unlikely to match any key on the device.
    prefix = b"\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8"
    pattern = "^" + base64.b64encode(prefix).decode()
    results = list(hem.keys.search(pattern))
    assert results == []

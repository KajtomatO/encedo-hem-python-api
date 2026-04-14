"""Tests for KeyMgmtAPI.derive()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import KeyType
from encedo_hem.models import KeyId

_KID = KeyId("a" * 32)
_NEW_KID = "b" * 32


def _mock_auth(router: respx.MockRouter) -> None:
    challenge_body = {
        "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
        "spk": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
        "jti": "0123456789abcdef",
        "exp": 2_000_000_000,
        "lbl": "alice",
    }
    router.get("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json=challenge_body)
    )
    router.post("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json={"token": "bearer-xyz"})
    )


def _make_client() -> HemClient:
    return HemClient("device.local", "passw0rd")


def test_derive_returns_key_id() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/keymgmt/derive").mock(
            return_value=httpx.Response(200, json={"kid": _NEW_KID})
        )
        result = client.keys.derive(_KID, "derived-key", KeyType.AES256)
    assert result == _NEW_KID


def test_derive_scope_is_keymgmt_gen() -> None:
    # OQ-23: keymgmt:ecdh is documented but rejected by firmware; keymgmt:gen is used instead.
    posted: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        challenge_body = {
            "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
            "spk": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
            "jti": "0123456789abcdef",
            "exp": 2_000_000_000,
            "lbl": "alice",
        }
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=challenge_body)
        )

        def auth_handler(request: httpx.Request) -> httpx.Response:
            posted.append(json.loads(request.content))
            return httpx.Response(200, json={"token": "bearer"})

        router.post("https://device.local/api/auth/token").mock(side_effect=auth_handler)
        router.post("https://device.local/api/keymgmt/derive").mock(
            return_value=httpx.Response(200, json={"kid": _NEW_KID})
        )

        client.keys.derive(_KID, "derived-key", KeyType.AES256)

    from encedo_hem._base64 import b64url_nopad_decode

    payload = json.loads(b64url_nopad_decode(posted[0]["auth"].split(".")[1]))
    assert payload["scope"] == "keymgmt:gen"


def test_derive_body_fields() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"kid": _NEW_KID})

        router.post("https://device.local/api/keymgmt/derive").mock(side_effect=handler)
        pubkey = b"\x04" + b"\x00" * 31
        client.keys.derive(_KID, "derived-key", KeyType.AES256, pubkey=pubkey, descr=b"hello")

    body = captured[0]
    assert body["kid"] == _KID
    assert body["label"] == "derived-key"
    assert body["type"] == "AES256"
    assert body["pubkey"] == base64.b64encode(pubkey).decode()
    assert body["descr"] == base64.b64encode(b"hello").decode()


def test_derive_ext_kid_and_pubkey_mutually_exclusive() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="mutually exclusive"):
        client.keys.derive(
            _KID,
            "k",
            KeyType.AES256,
            ext_kid=KeyId("c" * 32),
            pubkey=b"\x00" * 32,
        )


def test_derive_label_too_long_rejected() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="label"):
        client.keys.derive(_KID, "x" * 32, KeyType.AES256)


def test_derive_descr_too_long_rejected() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="descr"):
        client.keys.derive(_KID, "k", KeyType.AES256, descr=b"x" * 129)

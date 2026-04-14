"""Tests for KeyMgmtAPI.import_key()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import KeyType
from encedo_hem.errors import HemNotAcceptableError

_NEW_KID = "c" * 32
_PUBKEY = b"\x04" + b"\xab" * 32


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


def test_import_key_returns_key_id() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/keymgmt/import").mock(
            return_value=httpx.Response(200, json={"kid": _NEW_KID})
        )
        result = client.keys.import_key("ext-key", _PUBKEY, KeyType.ED25519)
    assert result == _NEW_KID


def test_import_key_scope_is_keymgmt_imp() -> None:
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
        router.post("https://device.local/api/keymgmt/import").mock(
            return_value=httpx.Response(200, json={"kid": _NEW_KID})
        )
        client.keys.import_key("ext-key", _PUBKEY, KeyType.ED25519)

    from encedo_hem._base64 import b64url_nopad_decode

    payload = json.loads(b64url_nopad_decode(posted[0]["auth"].split(".")[1]))
    assert payload["scope"] == "keymgmt:imp"


def test_import_key_body_fields() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"kid": _NEW_KID})

        router.post("https://device.local/api/keymgmt/import").mock(side_effect=handler)
        client.keys.import_key("ext-key", _PUBKEY, KeyType.ED25519)

    body = captured[0]
    assert body["label"] == "ext-key"
    assert body["pubkey"] == base64.b64encode(_PUBKEY).decode()
    assert body["type"] == "ED25519"


def test_import_key_406_raises_not_acceptable() -> None:
    """OQ-20: 406 from import means duplicate public key."""
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/keymgmt/import").mock(
            return_value=httpx.Response(406, json={})
        )
        with pytest.raises(HemNotAcceptableError):
            client.keys.import_key("dup-key", _PUBKEY, KeyType.ED25519)

"""Tests for EcdhAPI.exchange()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import HashAlg
from encedo_hem.models import EcdhResult, KeyId

_KID = KeyId("a" * 32)
_SECRET = b"\x11" * 32


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


def test_exchange_returns_ecdh_result() -> None:
    pubkey = b"\x04" + b"\x00" * 31

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/ecdh").mock(
            return_value=httpx.Response(200, json={"ecdh": base64.b64encode(_SECRET).decode()})
        )
        result = client.crypto.ecdh.exchange(_KID, pubkey=pubkey)

    assert isinstance(result, EcdhResult)
    assert result.shared_secret == _SECRET


def test_exchange_error_when_neither_pubkey_nor_ext_kid() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="exactly one"):
        client.crypto.ecdh.exchange(_KID)


def test_exchange_error_when_both_pubkey_and_ext_kid() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="mutually exclusive"):
        client.crypto.ecdh.exchange(
            _KID,
            pubkey=b"\x00" * 32,
            ext_kid=KeyId("b" * 32),
        )


def test_exchange_without_alg_omits_alg_field() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"ecdh": base64.b64encode(_SECRET).decode()})

        router.post("https://device.local/api/crypto/ecdh").mock(side_effect=handler)
        client.crypto.ecdh.exchange(_KID, pubkey=b"\x00" * 32)

    assert "alg" not in captured[0]


def test_exchange_with_alg_sends_alg_field() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"ecdh": base64.b64encode(_SECRET).decode()})

        router.post("https://device.local/api/crypto/ecdh").mock(side_effect=handler)
        client.crypto.ecdh.exchange(_KID, pubkey=b"\x00" * 32, alg=HashAlg.SHA2_256)

    assert captured[0]["alg"] == "SHA2-256"


def test_exchange_with_ext_kid_sends_ext_kid_field() -> None:
    captured: list[dict[str, Any]] = []
    ext = KeyId("b" * 32)

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"ecdh": base64.b64encode(_SECRET).decode()})

        router.post("https://device.local/api/crypto/ecdh").mock(side_effect=handler)
        client.crypto.ecdh.exchange(_KID, ext_kid=ext)

    assert captured[0]["ext_kid"] == ext
    assert "pubkey" not in captured[0]

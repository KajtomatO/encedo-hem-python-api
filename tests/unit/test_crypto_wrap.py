"""Tests for CipherAPI.wrap() and CipherAPI.unwrap()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import WrapAlg
from encedo_hem.models import KeyId, WrapResult

_KID = KeyId("a" * 32)
_WRAPPED = b"\xaa" * 24  # 24 bytes (multiple of 8, >= 16)
_UNWRAPPED = b"\xbb" * 16


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


def test_wrap_returns_wrap_result() -> None:
    msg = b"\x00" * 16

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/cipher/wrap").mock(
            return_value=httpx.Response(200, json={"wrapped": base64.b64encode(_WRAPPED).decode()})
        )
        result = client.crypto.cipher.wrap(_KID, WrapAlg.AES256, msg=msg)

    assert isinstance(result, WrapResult)
    assert result.wrapped == _WRAPPED


def test_unwrap_returns_bytes() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/cipher/unwrap").mock(
            return_value=httpx.Response(
                200, json={"unwrapped": base64.b64encode(_UNWRAPPED).decode()}
            )
        )
        result = client.crypto.cipher.unwrap(_KID, _WRAPPED, alg=WrapAlg.AES256)

    assert result == _UNWRAPPED


def test_wrap_constraint_not_multiple_of_8() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="multiple of 8"):
        client.crypto.cipher.wrap(_KID, WrapAlg.AES256, msg=b"\x00" * 17)


def test_wrap_constraint_less_than_16_bytes() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="16 bytes"):
        client.crypto.cipher.wrap(_KID, WrapAlg.AES256, msg=b"\x00" * 8)


def test_wrap_without_msg_omits_msg_field() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"wrapped": base64.b64encode(_WRAPPED).decode()})

        router.post("https://device.local/api/crypto/cipher/wrap").mock(side_effect=handler)
        client.crypto.cipher.wrap(_KID, WrapAlg.AES128)

    assert "msg" not in captured[0]


def test_wrap_alg_wire_values() -> None:
    """WrapAlg values must not have cipher-mode suffixes."""
    assert WrapAlg.AES128.value == "AES128"
    assert WrapAlg.AES192.value == "AES192"
    assert WrapAlg.AES256.value == "AES256"


def test_wrap_sends_correct_alg() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"wrapped": base64.b64encode(_WRAPPED).decode()})

        router.post("https://device.local/api/crypto/cipher/wrap").mock(side_effect=handler)
        client.crypto.cipher.wrap(_KID, WrapAlg.AES192, msg=b"\x00" * 16)

    assert captured[0]["alg"] == "AES192"

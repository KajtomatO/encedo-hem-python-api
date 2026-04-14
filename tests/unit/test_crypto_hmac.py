"""Tests for HmacAPI.hash() and HmacAPI.verify()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import HashAlg
from encedo_hem.models import HmacResult, KeyId

_KID = KeyId("a" * 32)
_MAC = b"\xde\xad\xbe\xef" * 4


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


def test_hash_returns_hmac_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/hmac/hash").mock(
            return_value=httpx.Response(200, json={"mac": base64.b64encode(_MAC).decode()})
        )
        result = client.crypto.hmac.hash(_KID, b"hello")
    assert isinstance(result, HmacResult)
    assert result.mac == _MAC


def test_hash_base64_decodes_mac() -> None:
    mac_bytes = b"\x01\x02\x03\x04"
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/hmac/hash").mock(
            return_value=httpx.Response(200, json={"mac": base64.b64encode(mac_bytes).decode()})
        )
        result = client.crypto.hmac.hash(_KID, b"msg")
    assert result.mac == mac_bytes


def test_verify_returns_true_on_200() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/hmac/verify").mock(
            return_value=httpx.Response(200, json={})
        )
        assert client.crypto.hmac.verify(_KID, b"msg", _MAC) is True


def test_verify_returns_false_on_406() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/hmac/verify").mock(
            return_value=httpx.Response(406, json={})
        )
        assert client.crypto.hmac.verify(_KID, b"msg", _MAC) is False


def test_hash_with_alg_sends_alg_field() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"mac": base64.b64encode(_MAC).decode()})

        router.post("https://device.local/api/crypto/hmac/hash").mock(side_effect=handler)
        client.crypto.hmac.hash(_KID, b"msg", alg=HashAlg.SHA2_256)

    assert captured[0]["alg"] == "SHA2-256"


def test_hash_without_alg_omits_alg_field() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"mac": base64.b64encode(_MAC).decode()})

        router.post("https://device.local/api/crypto/hmac/hash").mock(side_effect=handler)
        client.crypto.hmac.hash(_KID, b"msg")

    assert "alg" not in captured[0]


def test_hash_with_ext_kid_sends_ext_kid_field() -> None:
    captured: list[dict[str, Any]] = []
    ext = KeyId("b" * 32)

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"mac": base64.b64encode(_MAC).decode()})

        router.post("https://device.local/api/crypto/hmac/hash").mock(side_effect=handler)
        client.crypto.hmac.hash(_KID, b"msg", ext_kid=ext)

    assert captured[0]["ext_kid"] == ext


def test_hash_with_pubkey_sends_pubkey_field() -> None:
    captured: list[dict[str, Any]] = []
    pub = b"\x04" + b"\x00" * 31

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"mac": base64.b64encode(_MAC).decode()})

        router.post("https://device.local/api/crypto/hmac/hash").mock(side_effect=handler)
        client.crypto.hmac.hash(_KID, b"msg", pubkey=pub)

    assert captured[0]["pubkey"] == base64.b64encode(pub).decode()

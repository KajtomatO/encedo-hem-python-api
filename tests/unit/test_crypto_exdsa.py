"""Tests for ExdsaAPI.sign() and ExdsaAPI.verify()."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import SignAlg
from encedo_hem.models import KeyId, SignResult

_KID = KeyId("a" * 32)
_SIG = b"\xca\xfe\xba\xbe" * 8


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


def test_sign_returns_sign_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/exdsa/sign").mock(
            return_value=httpx.Response(200, json={"sign": base64.b64encode(_SIG).decode()})
        )
        result = client.crypto.exdsa.sign(_KID, b"hello", SignAlg.ED25519)
    assert isinstance(result, SignResult)
    assert result.signature == _SIG


def test_sign_alg_wire_value() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"sign": base64.b64encode(_SIG).decode()})

        router.post("https://device.local/api/crypto/exdsa/sign").mock(side_effect=handler)
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.SHA256_ECDSA)

    assert captured[0]["alg"] == "SHA256WithECDSA"


def test_verify_returns_true_on_200() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/exdsa/verify").mock(
            return_value=httpx.Response(200, json={})
        )
        assert client.crypto.exdsa.verify(_KID, b"msg", _SIG, SignAlg.ED25519) is True


def test_verify_returns_false_on_406() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/exdsa/verify").mock(
            return_value=httpx.Response(406, json={})
        )
        assert client.crypto.exdsa.verify(_KID, b"msg", _SIG, SignAlg.ED25519) is False


def test_sign_ctx_required_for_ed25519ph() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="ctx is required"):
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED25519PH)


def test_sign_ctx_required_for_ed25519ctx() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="ctx is required"):
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED25519CTX)


def test_sign_ctx_required_for_ed448() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="ctx is required"):
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED448)


def test_sign_ctx_required_for_ed448ph() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="ctx is required"):
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED448PH)


def test_sign_ctx_not_required_for_ed25519() -> None:
    """Ed25519 does not require ctx — should not raise."""
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/exdsa/sign").mock(
            return_value=httpx.Response(200, json={"sign": base64.b64encode(_SIG).decode()})
        )
        result = client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED25519)
    assert result.signature == _SIG


def test_sign_ctx_too_long_rejected() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="255 bytes"):
        client.crypto.exdsa.sign(_KID, b"msg", SignAlg.ED25519PH, ctx=b"x" * 256)


def test_sign_wire_field_for_signature_is_sign() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={})

        router.post("https://device.local/api/crypto/exdsa/verify").mock(side_effect=handler)
        client.crypto.exdsa.verify(_KID, b"msg", _SIG, SignAlg.ED25519)

    assert "sign" in captured[0]
    assert "signature" not in captured[0]

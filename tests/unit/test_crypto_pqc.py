"""Tests for MlKemAPI and MlDsaAPI."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.models import KeyId, MlKemDecapsResult, MlKemEncapsResult, SignResult

_KID = KeyId("a" * 32)
_CT = b"\xcc" * 64
_SS = b"\xdd" * 32
_SIG = b"\xee" * 64


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


# --- ML-KEM ---


def test_mlkem_encaps_returns_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mlkem/encaps").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ct": base64.b64encode(_CT).decode(),
                    "ss": base64.b64encode(_SS).decode(),
                    "alg": "MLKEM768",
                },
            )
        )
        result = client.crypto.pqc.mlkem.encaps(_KID)

    assert isinstance(result, MlKemEncapsResult)
    assert result.ciphertext == _CT
    assert result.shared_secret == _SS
    assert result.alg == "MLKEM768"


def test_mlkem_decaps_returns_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mlkem/decaps").mock(
            return_value=httpx.Response(200, json={"ss": base64.b64encode(_SS).decode()})
        )
        result = client.crypto.pqc.mlkem.decaps(_KID, _CT)

    assert isinstance(result, MlKemDecapsResult)
    assert result.shared_secret == _SS


def test_mlkem_decaps_wire_field_is_ct() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"ss": base64.b64encode(_SS).decode()})

        router.post("https://device.local/api/crypto/pqc/mlkem/decaps").mock(side_effect=handler)
        client.crypto.pqc.mlkem.decaps(_KID, _CT)

    assert "ct" in captured[0]
    assert "ciphertext" not in captured[0]


# --- ML-DSA ---


def test_mldsa_sign_returns_sign_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mldsa/sign").mock(
            return_value=httpx.Response(
                200,
                json={
                    "sign": base64.b64encode(_SIG).decode(),
                    "alg": "MLDSA65",
                },
            )
        )
        result = client.crypto.pqc.mldsa.sign(_KID, b"hello")

    assert isinstance(result, SignResult)
    assert result.signature == _SIG


def test_mldsa_verify_returns_true_on_200() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mldsa/verify").mock(
            return_value=httpx.Response(200, json={})
        )
        assert client.crypto.pqc.mldsa.verify(_KID, b"msg", _SIG) is True


def test_mldsa_verify_returns_false_on_406() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mldsa/verify").mock(
            return_value=httpx.Response(406, json={})
        )
        assert client.crypto.pqc.mldsa.verify(_KID, b"msg", _SIG) is False


def test_mldsa_verify_ctx_max_64_bytes() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="64 bytes"):
        client.crypto.pqc.mldsa.verify(_KID, b"msg", _SIG, ctx=b"x" * 65)


def test_mldsa_sign_ctx_max_255_bytes() -> None:
    with _make_client() as client, pytest.raises(ValueError, match="255 bytes"):
        client.crypto.pqc.mldsa.sign(_KID, b"msg", ctx=b"x" * 256)


def test_mldsa_verify_ctx_64_bytes_is_ok() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/crypto/pqc/mldsa/verify").mock(
            return_value=httpx.Response(200, json={})
        )
        assert client.crypto.pqc.mldsa.verify(_KID, b"msg", _SIG, ctx=b"x" * 64) is True


def test_mldsa_sign_wire_field_is_sign() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={})

        router.post("https://device.local/api/crypto/pqc/mldsa/verify").mock(side_effect=handler)
        client.crypto.pqc.mldsa.verify(_KID, b"msg", _SIG)

    assert "sign" in captured[0]
    assert "signature" not in captured[0]

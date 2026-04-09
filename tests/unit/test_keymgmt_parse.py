"""Pagination, scope-routing, and field-shape tests for KeyMgmtAPI."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import KeyType
from encedo_hem.models import KeyId


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


def test_list_pagination_three_pages() -> None:
    """30 keys spread across 3 pages of 10 should yield exactly 30."""
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def page_handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            offset = int(path.rstrip("/").split("/")[-2])
            keys = [
                {
                    "kid": f"{i:032x}",
                    "label": f"k{i}",
                    "type": "AES256",
                    "created": 0,
                    "updated": 0,
                }
                for i in range(offset, min(offset + 10, 30))
            ]
            return httpx.Response(200, json={"total": 30, "listed": len(keys), "list": keys})

        router.get(url__regex=r"https://device.local/api/keymgmt/list/\d+/\d+").mock(
            side_effect=page_handler
        )

        out = list(client.keys.list())
        assert len(out) == 30


def test_list_single_page() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        body = {
            "total": 5,
            "listed": 5,
            "list": [
                {"kid": f"{i:032x}", "label": "k", "type": "AES256", "created": 0, "updated": 0}
                for i in range(5)
            ],
        }
        router.get("https://device.local/api/keymgmt/list/0/10").mock(
            return_value=httpx.Response(200, json=body)
        )
        out = list(client.keys.list())
        assert len(out) == 5


def test_list_total_15_terminates() -> None:
    """OQ-17 edge case: total=15, listed=10 first page, listed=5 second page."""
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            offset = int(request.url.path.rstrip("/").split("/")[-2])
            remaining = max(0, 15 - offset)
            n = min(10, remaining)
            keys = [
                {
                    "kid": f"{(offset + i):032x}",
                    "label": "k",
                    "type": "AES256",
                    "created": 0,
                    "updated": 0,
                }
                for i in range(n)
            ]
            return httpx.Response(200, json={"total": 15, "listed": n, "list": keys})

        router.get(url__regex=r".*/api/keymgmt/list/\d+/\d+").mock(side_effect=handler)
        out = list(client.keys.list())
        assert len(out) == 15


def test_get_returns_pubkey_for_asymmetric_keys() -> None:
    """IT-OQ-1 counterpart: asymmetric responses still surface ``pubkey``."""
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get(url__regex=r".*/api/keymgmt/get/.*").mock(
            return_value=httpx.Response(
                200,
                json={
                    "pubkey": "AAAA",
                    "type": "PKEY,ECDH,ExDSA,SECP256R1",
                    "updated": 0,
                },
            )
        )
        details = client.keys.get(KeyId("a" * 32))
        assert details.pubkey == b"\x00\x00\x00"
        assert details.type.algorithm == "SECP256R1"


def test_get_uses_use_scope_token() -> None:
    """OQ-16: keys.get must request keymgmt:use:<kid>, not keymgmt:get."""
    posted_payloads: list[dict[str, Any]] = []

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

        def post_handler(request: httpx.Request) -> httpx.Response:
            posted_payloads.append(json.loads(request.content))
            return httpx.Response(200, json={"token": "bearer"})

        router.post("https://device.local/api/auth/token").mock(side_effect=post_handler)
        # IT-OQ-1: device omits ``pubkey`` for symmetric (AES) keys; the mock
        # mirrors that so the parser is exercised against the real wire shape.
        router.get(url__regex=r".*/api/keymgmt/get/.*").mock(
            return_value=httpx.Response(200, json={"type": "AES256", "updated": 0})
        )

        kid = KeyId("a" * 32)
        details = client.keys.get(kid)
        assert details.pubkey is None

        # The eJWT in the auth POST should encode the use:<kid> scope.
        assert posted_payloads
        ejwt = posted_payloads[0]["auth"]
        # Decode the payload segment.
        from encedo_hem._base64 import b64url_nopad_decode

        payload = json.loads(b64url_nopad_decode(ejwt.split(".")[1]))
        assert payload["scope"] == f"keymgmt:use:{kid}"


def test_update_always_sends_label() -> None:
    """OQ-18: label is mandatory on the wire."""
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={})

        router.post("https://device.local/api/keymgmt/update").mock(side_effect=handler)

        client.keys.update(KeyId("a" * 32), label="x")

    assert captured == [{"kid": "a" * 32, "label": "x"}]


def test_create_nist_ecc_default_mode_is_ecdh_exdsa() -> None:
    """OQ-19: library default for NIST ECC is ECDH,ExDSA, not ECDH-only."""
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"kid": "f" * 32})

        router.post("https://device.local/api/keymgmt/create").mock(side_effect=handler)

        client.keys.create("ec-key", KeyType.SECP256R1)

    assert captured[0]["mode"] == "ECDH,ExDSA"


def test_create_aes_does_not_send_mode() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"kid": "0" * 32})

        router.post("https://device.local/api/keymgmt/create").mock(side_effect=handler)

        client.keys.create("aes-key", KeyType.AES256)

    assert "mode" not in captured[0]


def test_create_label_too_long_rejected() -> None:
    with _make_client() as client, pytest.raises(ValueError):
        client.keys.create("x" * 32, KeyType.AES256)

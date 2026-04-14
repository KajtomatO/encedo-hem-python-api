"""Tests for KeyMgmtAPI.search()."""

from __future__ import annotations

import json
from typing import Any

import httpx
import respx

from encedo_hem.client import HemClient

_PATTERN = "^" + "AAAAAAAAAA=="  # base64 of 8 zero bytes


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


def _make_key(i: int) -> dict[str, Any]:
    return {"kid": f"{i:032x}", "label": f"k{i}", "type": "AES256", "created": 0, "updated": 0}


def test_search_returns_results() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        body = {"total": 3, "listed": 3, "list": [_make_key(i) for i in range(3)]}
        router.post("https://device.local/api/keymgmt/search").mock(
            return_value=httpx.Response(200, json=body)
        )
        results = list(client.keys.search(_PATTERN))
    assert len(results) == 3


def test_search_404_yields_nothing() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/keymgmt/search").mock(
            return_value=httpx.Response(404, json={})
        )
        results = list(client.keys.search(_PATTERN))
    assert results == []


def test_search_pagination() -> None:
    pages: list[dict[str, Any]] = [
        {"total": 15, "listed": 10, "list": [_make_key(i) for i in range(10)]},
        {"total": 15, "listed": 5, "list": [_make_key(i) for i in range(10, 15)]},
    ]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        body = pages[call_count]
        call_count += 1
        return httpx.Response(200, json=body)

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.post("https://device.local/api/keymgmt/search").mock(side_effect=handler)
        results = list(client.keys.search(_PATTERN))

    assert len(results) == 15
    assert call_count == 2


def test_search_descr_passed_as_is() -> None:
    captured: list[dict[str, Any]] = []

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"total": 0, "listed": 0, "list": []})

        router.post("https://device.local/api/keymgmt/search").mock(side_effect=handler)
        list(client.keys.search(_PATTERN))

    assert captured[0]["descr"] == _PATTERN

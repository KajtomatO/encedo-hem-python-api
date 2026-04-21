"""Tests for LoggerAPI."""

from __future__ import annotations

import json

import httpx
import respx

from encedo_hem.client import HemClient
from encedo_hem.models import LoggerKeyInfo


def _challenge() -> dict:
    return {
        "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
        "spk": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
        "jti": "0123456789abcdef",
        "exp": 2_000_000_000,
        "lbl": "alice",
    }


def _mock_auth(router: respx.MockRouter) -> None:
    router.get("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json=_challenge())
    )
    router.post("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json={"token": "tok"})
    )


def _captured_scope(router: respx.MockRouter) -> str:
    import base64
    for call in router.calls:
        if call.request.method == "POST" and "/api/auth/token" in str(call.request.url):
            body = json.loads(call.request.content)
            auth = body.get("auth", "")
            try:
                payload_b64 = auth.split(".")[1]
                padding = "=" * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
                return payload.get("scope", "")
            except Exception:
                pass
    return ""


def _make_client() -> HemClient:
    return HemClient("device.local", "passw0rd")


def test_key_returns_logger_key_info() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/logger/key").mock(
            return_value=httpx.Response(200, json={
                "key": "abc123==",
                "nonce": "nonce==",
                "nonce_signed": "signed==",
            })
        )
        result = client.logger.key()
    assert isinstance(result, LoggerKeyInfo)
    assert result.key == "abc123=="
    assert result.nonce == "nonce=="
    assert result.nonce_signed == "signed=="


def test_key_uses_logger_get_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/logger/key").mock(
            return_value=httpx.Response(200, json={"key": "k", "nonce": "n", "nonce_signed": "s"})
        )
        client.logger.key()
        assert _captured_scope(router) == "logger:get"


def test_list_paginates() -> None:
    pages = [
        {"total": 15, "id": [f"id{i}" for i in range(10)]},
        {"total": 15, "id": [f"id{i}" for i in range(10, 15)]},
    ]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        body = pages[call_count]
        call_count += 1
        return httpx.Response(200, json=body)

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get(url__regex=r"/api/logger/list/\d+").mock(side_effect=handler)
        ids = list(client.logger.list())

    assert len(ids) == 15
    assert call_count == 2


def test_list_single_page() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/logger/list/0").mock(
            return_value=httpx.Response(200, json={"total": 3, "id": ["a", "b", "c"]})
        )
        ids = list(client.logger.list())
    assert ids == ["a", "b", "c"]


def test_get_returns_text() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/logger/abc123").mock(
            return_value=httpx.Response(200, text="log entry text content")
        )
        result = client.logger.get("abc123")
    assert result == "log entry text content"


def test_delete_uses_del_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.delete("https://device.local/api/logger/abc123").mock(
            return_value=httpx.Response(200, json={})
        )
        client.logger.delete("abc123")
        assert _captured_scope(router) == "logger:del"


def test_delete_sends_delete_method() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        delete_route = router.delete("https://device.local/api/logger/abc123").mock(
            return_value=httpx.Response(200, json={})
        )
        client.logger.delete("abc123")
    assert delete_route.called

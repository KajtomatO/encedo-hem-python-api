"""Tests for Transport.request_no_raise() and Transport.request_text()."""

from __future__ import annotations

import httpx
import respx

from encedo_hem.errors import HemNotFoundError
from encedo_hem.transport import Transport


def _make_transport() -> Transport:
    return Transport("device.local")


# --- request_no_raise ---

def test_no_raise_returns_status_and_body_on_200() -> None:
    with respx.mock() as router:
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            return_value=httpx.Response(200, json={"ver": "1.2.3"})
        )
        t = _make_transport()
        status, body = t.request_no_raise("GET", "/api/system/upgrade/check_fw")
    assert status == 200
    assert body == {"ver": "1.2.3"}


def test_no_raise_returns_202_without_raising() -> None:
    with respx.mock() as router:
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            return_value=httpx.Response(202, json={})
        )
        t = _make_transport()
        status, body = t.request_no_raise("GET", "/api/system/upgrade/check_fw")
    assert status == 202
    assert body == {}


def test_no_raise_returns_406_without_raising() -> None:
    with respx.mock() as router:
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            return_value=httpx.Response(406, json={})
        )
        t = _make_transport()
        status, _ = t.request_no_raise("GET", "/api/system/upgrade/check_fw")
    assert status == 406


# --- request_text ---

def test_request_text_returns_string() -> None:
    with respx.mock() as router:
        router.get("https://device.local/api/logger/abc123").mock(
            return_value=httpx.Response(200, text="log entry content")
        )
        t = _make_transport()
        result = t.request_text("GET", "/api/logger/abc123")
    assert result == "log entry content"


def test_request_text_non_200_raises() -> None:
    with respx.mock() as router:
        router.get("https://device.local/api/logger/missing").mock(
            return_value=httpx.Response(404, json={})
        )
        t = _make_transport()
        try:
            t.request_text("GET", "/api/logger/missing")
            raise AssertionError("should have raised")
        except HemNotFoundError:
            pass

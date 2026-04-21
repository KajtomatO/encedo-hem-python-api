"""Tests for UpgradeAPI."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import respx

from encedo_hem.client import HemClient
from encedo_hem.errors import HemNotAcceptableError, HemTransportError
from encedo_hem.models import FirmwareCheckResult


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


def _make_client() -> HemClient:
    return HemClient("device.local", "passw0rd")


def test_upload_fw_uses_binary_transport() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        route = router.post("https://device.local/api/system/upgrade/upload_fw").mock(
            return_value=httpx.Response(200, json={})
        )
        client.upgrade.upload_fw(b"\xde\xad\xbe\xef")
        req = route.calls[0].request
    assert req.headers["content-type"] == "application/octet-stream"
    assert 'filename="fw.bin"' in req.headers["content-disposition"]


def test_check_fw_returns_on_200() -> None:
    responses = [
        httpx.Response(202, json={}),
        httpx.Response(200, json={"ver": "1.2.3"}),
    ]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        resp = responses[call_count]
        call_count += 1
        return resp

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            side_effect=handler
        )
        with patch("encedo_hem.api.upgrade.time.sleep"):
            result = client.upgrade.check_fw()

    assert isinstance(result, FirmwareCheckResult)
    assert result.raw == {"ver": "1.2.3"}
    assert call_count == 2


def test_check_fw_raises_on_406() -> None:
    responses = [httpx.Response(202, json={}), httpx.Response(406, json={})]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        resp = responses[call_count]
        call_count += 1
        return resp

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            side_effect=handler
        )
        with patch("encedo_hem.api.upgrade.time.sleep"):
            try:
                client.upgrade.check_fw()
                raise AssertionError("should have raised")
            except HemNotAcceptableError:
                pass


def test_check_fw_timeout_raises() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/upgrade/check_fw").mock(
            return_value=httpx.Response(202, json={})
        )
        with patch("encedo_hem.api.upgrade.time.sleep"):
            try:
                client.upgrade.check_fw()
                raise AssertionError("should have raised")
            except HemTransportError as exc:
                assert "timed out" in str(exc)


def test_upload_bootldr_only_one_request() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        route = router.post("https://device.local/api/system/upgrade/upload_bootldr").mock(
            return_value=httpx.Response(200, json={})
        )
        client.upgrade.upload_bootldr(b"\x00\x01")
    assert route.call_count == 1


def test_usbmode_uses_system_upgrade_scope() -> None:
    import base64
    import json

    def _scope(router: respx.MockRouter) -> str:
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

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/upgrade/usbmode").mock(
            return_value=httpx.Response(200, json={})
        )
        client.upgrade.usbmode()
        assert _scope(router) == "system:upgrade"


def test_check_ui_initial_wait() -> None:
    """check_ui must sleep before the first poll."""
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/upgrade/check_ui").mock(
            return_value=httpx.Response(200, json={})
        )
        with patch("encedo_hem.api.upgrade.time.sleep", side_effect=fake_sleep):
            client.upgrade.check_ui()

    # First sleep must be the 60-second initial wait.
    assert sleep_calls[0] == 60.0

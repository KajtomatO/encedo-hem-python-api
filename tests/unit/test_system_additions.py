"""Tests for new SystemAPI methods added in Phase 3."""

from __future__ import annotations

import base64
import json

import httpx
import respx

from encedo_hem.client import HemClient
from encedo_hem.errors import HemAuthError
from encedo_hem.models import AttestationResult, SelftestResult

_CHALLENGE = {
    "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
    "spk": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
    "jti": "0123456789abcdef",
    "exp": 2_000_000_000,
    "lbl": "alice",
}


def _mock_auth(router: respx.MockRouter) -> None:
    router.get("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json=_CHALLENGE)
    )
    router.post("https://device.local/api/auth/token").mock(
        return_value=httpx.Response(200, json={"token": "bearer-xyz"})
    )


def _captured_scope(router: respx.MockRouter) -> str:
    """Decode the scope from the eJWT sent in POST /api/auth/token."""
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


# --- reboot scope fix ---

def test_reboot_uses_system_upgrade_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_CHALLENGE)
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        router.get("https://device.local/api/system/reboot").mock(
            return_value=httpx.Response(200, json={})
        )
        client.system.reboot()
        assert _captured_scope(router) == "system:upgrade"


# --- shutdown ---

def test_shutdown_uses_system_shutdown_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_CHALLENGE)
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        router.get("https://device.local/api/system/shutdown").mock(
            return_value=httpx.Response(200, json={})
        )
        client.system.shutdown()
        assert _captured_scope(router) == "system:shutdown"


# --- selftest ---

def test_selftest_returns_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/selftest").mock(
            return_value=httpx.Response(200, json={
                "last_selftest_ts": 1700000000,
                "fls_state": 0,
                "kat_busy": False,
                "se_state": 1,
            })
        )
        result = client.system.selftest()
    assert isinstance(result, SelftestResult)
    assert result.last_selftest_ts == 1700000000
    assert result.fls_state == 0
    assert result.kat_busy is False
    assert result.se_state == 1


def test_selftest_unknown_fields_ignored() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/selftest").mock(
            return_value=httpx.Response(200, json={
                "last_selftest_ts": 0,
                "fls_state": 0,
                "kat_busy": False,
                "se_state": 0,
                "future_field": "ignored",
            })
        )
        result = client.system.selftest()
    assert result.fls_state == 0


# --- config_attestation ---

def test_config_attestation_returns_result() -> None:
    with _make_client() as client, respx.mock() as router:
        _mock_auth(router)
        router.get("https://device.local/api/system/config/attestation").mock(
            return_value=httpx.Response(200, json={"crt": "-----BEGIN CERT-----", "genuine": True})
        )
        result = client.system.config_attestation()
        assert _captured_scope(router) == "system:config"
    assert isinstance(result, AttestationResult)
    assert result.crt == "-----BEGIN CERT-----"
    assert result.genuine is True


# --- config_provisioning ---

def test_config_provisioning_posts_body() -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={})

    with _make_client() as client, respx.mock() as router:
        router.post("https://device.local/api/system/config/provisioning").mock(
            side_effect=handler
        )
        client.system.config_provisioning("Alice", "alice@example.com", "secret")

    assert captured[0]["user"] == "Alice"
    assert captured[0]["email"] == "alice@example.com"


def test_config_provisioning_403_raises() -> None:
    with _make_client() as client, respx.mock() as router:
        router.post("https://device.local/api/system/config/provisioning").mock(
            return_value=httpx.Response(403, json={})
        )
        try:
            client.system.config_provisioning("Alice", "alice@example.com", "secret")
            raise AssertionError("should have raised")
        except HemAuthError:
            pass

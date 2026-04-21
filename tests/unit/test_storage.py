"""Tests for StorageAPI."""

from __future__ import annotations

import json

import httpx
import respx

from encedo_hem.client import HemClient
from encedo_hem.enums import StorageDisk


def _challenge() -> dict:
    return {
        "eid": "d4ad81b06b1d493ab2b6f9b1a3e2c7f0",
        "spk": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE=",
        "jti": "0123456789abcdef",
        "exp": 2_000_000_000,
        "lbl": "alice",
    }


def _captured_scope(router: respx.MockRouter) -> str:
    """Return the scope embedded in the POST /api/auth/token eJWT."""
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


def test_unlock_disk0_path_and_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_challenge())
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        unlock_ro = router.get("https://device.local/api/storage/unlock/ro").mock(
            return_value=httpx.Response(200, json={})
        )
        client.storage.unlock(StorageDisk.DISK0)
        assert unlock_ro.called
        assert _captured_scope(router) == "storage:disk0"


def test_unlock_disk1_rw_path_and_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_challenge())
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        unlock_rw = router.get("https://device.local/api/storage/unlock/rw").mock(
            return_value=httpx.Response(200, json={})
        )
        client.storage.unlock(StorageDisk.DISK1_RW)
        assert unlock_rw.called
        assert _captured_scope(router) == "storage:disk1:rw"


def test_lock_default_disk0_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_challenge())
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        router.get("https://device.local/api/storage/lock").mock(
            return_value=httpx.Response(200, json={})
        )
        client.storage.lock()
        assert _captured_scope(router) == "storage:disk0"


def test_lock_disk1_rw_uses_per_disk_scope() -> None:
    with _make_client() as client, respx.mock() as router:
        router.get("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json=_challenge())
        )
        router.post("https://device.local/api/auth/token").mock(
            return_value=httpx.Response(200, json={"token": "tok"})
        )
        router.get("https://device.local/api/storage/lock").mock(
            return_value=httpx.Response(200, json={})
        )
        client.storage.lock(StorageDisk.DISK1_RW)
        assert _captured_scope(router) == "storage:disk1"

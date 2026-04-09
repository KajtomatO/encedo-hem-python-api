from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from encedo_hem.errors import (
    HemAuthError,
    HemDeviceFailureError,
    HemPayloadTooLargeError,
    HemTransportError,
)
from encedo_hem.transport import MAX_BODY_BYTES, Transport


@pytest.fixture
def captured_clients(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Capture every kwargs dict passed to httpx.Client.__init__."""
    captured: list[dict[str, Any]] = []
    orig_init = httpx.Client.__init__

    def spy_init(self: httpx.Client, *args: Any, **kwargs: Any) -> None:
        captured.append(kwargs)
        orig_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", spy_init)
    return captured


def test_get_returns_parsed_json() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock(assert_all_called=True) as router:
            router.get("https://device.local/api/system/status").mock(
                return_value=httpx.Response(200, json={"hostname": "h", "fls_state": 0})
            )
            body = transport.request("GET", "/api/system/status")
        assert body == {"hostname": "h", "fls_state": 0}
    finally:
        transport.close()


def test_post_body_too_large_short_circuits_before_network() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            big = "A" * (MAX_BODY_BYTES + 100)
            with pytest.raises(HemPayloadTooLargeError) as excinfo:
                transport.request("POST", "/api/x", json_body={"k": big})
            assert excinfo.value.size_actual > MAX_BODY_BYTES
            assert router.calls.call_count == 0
    finally:
        transport.close()


def test_401_maps_to_auth_error() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(
                return_value=httpx.Response(401, json={"error": "denied"})
            )
            with pytest.raises(HemAuthError) as excinfo:
                transport.request("GET", "/api/x")
            assert excinfo.value.status_code == 401
    finally:
        transport.close()


def test_409_maps_to_device_failure() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(return_value=httpx.Response(409))
            with pytest.raises(HemDeviceFailureError):
                transport.request("GET", "/api/x")
    finally:
        transport.close()


def test_413_maps_to_payload_too_large() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(return_value=httpx.Response(413))
            with pytest.raises(HemPayloadTooLargeError) as excinfo:
                transport.request("GET", "/api/x")
            assert excinfo.value.size_actual == -1
    finally:
        transport.close()


def test_connect_error_maps_to_transport_error() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            with pytest.raises(HemTransportError) as excinfo:
                transport.request("GET", "/api/x")
            assert isinstance(excinfo.value.__cause__, httpx.ConnectError)
    finally:
        transport.close()


def test_device_client_kwargs(captured_clients: list[dict[str, Any]]) -> None:
    transport = Transport("device.local")
    try:
        # Two clients: device first, backend second.
        assert len(captured_clients) >= 2
        device_kwargs = captured_clients[0]
        assert device_kwargs["verify"] is False
        assert device_kwargs["base_url"] == "https://device.local"
        assert device_kwargs["limits"].max_keepalive_connections == 0
        assert device_kwargs["headers"]["Connection"] == "close"
    finally:
        transport.close()


def test_backend_client_kwargs(captured_clients: list[dict[str, Any]]) -> None:
    transport = Transport("device.local")
    try:
        # CRITICAL: backend MUST verify TLS or check-in is MITM-able.
        backend_kwargs = captured_clients[1]
        assert backend_kwargs["verify"] is True
        assert backend_kwargs["base_url"] == "https://api.encedo.com"
        assert backend_kwargs["limits"].max_keepalive_connections == 0
        assert backend_kwargs["headers"]["Connection"] == "close"
    finally:
        transport.close()


def test_backend_post_returns_parsed_body() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.post("https://api.encedo.com/checkin").mock(
                return_value=httpx.Response(200, json={"reply": "ok"})
            )
            body = transport.backend_post("/checkin", {"nonce": "abc"})
        assert body == {"reply": "ok"}
    finally:
        transport.close()


def test_backend_post_connect_error_maps_to_transport_error() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.post("https://api.encedo.com/checkin").mock(
                side_effect=httpx.ConnectError("dns")
            )
            with pytest.raises(HemTransportError):
                transport.backend_post("/checkin", {})
    finally:
        transport.close()


def test_backend_post_non_200_maps_via_from_status() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.post("https://api.encedo.com/checkin").mock(
                return_value=httpx.Response(409, json={"error": "fls"})
            )
            with pytest.raises(HemDeviceFailureError):
                transport.backend_post("/checkin", {})
    finally:
        transport.close()


def test_backend_post_empty_body_raises() -> None:
    from encedo_hem.errors import HemError

    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.post("https://api.encedo.com/checkin").mock(
                return_value=httpx.Response(200, content=b"")
            )
            with pytest.raises(HemError):
                transport.backend_post("/checkin", {})
    finally:
        transport.close()


def test_request_invalid_json_returns_empty_dict() -> None:
    """A 200 response with garbage in the body should not crash; treat as {}."""
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(
                return_value=httpx.Response(200, content=b"not-json")
            )
            assert transport.request("GET", "/api/x") == {}
    finally:
        transport.close()


def test_request_json_array_returns_empty_dict() -> None:
    """A 200 response that parses to a non-dict (e.g. list) should also fall back to {}."""
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            router.get("https://device.local/api/x").mock(
                return_value=httpx.Response(200, json=[1, 2, 3])
            )
            assert transport.request("GET", "/api/x") == {}
    finally:
        transport.close()


def test_request_sends_connection_close_header() -> None:
    transport = Transport("device.local")
    try:
        with respx.mock() as router:
            route = router.get("https://device.local/api/x").mock(
                return_value=httpx.Response(200, json={})
            )
            transport.request("GET", "/api/x")
            sent = route.calls.last.request
            # The header set on the client is merged into every request.
            assert sent.headers.get("Connection", "").lower() == "close"
    finally:
        transport.close()
